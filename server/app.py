"""FastAPI surface over the engine. Localhost only. No database: scenarios are JSON files,
twins live in an in-memory dict keyed by twin hash, results in a dict keyed by request."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from engine.blast import Blast, blast_radius
from engine.models import Agent, Control, PrivilegeGrant, Twin
from engine.results import Result
from engine.scenario import Scenario, list_scenarios, load_scenario
from engine.search import SearchBudgetExceeded, search
from engine.twin import clone
from engine.walk import simulate
from rules.compile import compile
from rules.evaluate import ChangeVerdict, evaluate_change
from rules.loader import load_techniques
from rules.optimize import Portfolio, optimize

app = FastAPI(title="Security Change Sandbox", version="2.1")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])

TECH = load_techniques()
SCENARIO: Scenario = load_scenario("golden")
TWINS: dict[str, Twin] = {}
LABELS: dict[str, str] = {}
VERDICTS: dict[tuple, ChangeVerdict] = {}


def _register(twin: Twin, label: str) -> Twin:
    TWINS[twin.id] = twin
    LABELS.setdefault(twin.id, label)
    return twin


def _twin(twin_id: str) -> Twin:
    if twin_id == "current":
        return SCENARIO.twin
    if twin_id not in TWINS:
        raise HTTPException(404, f"unknown twin {twin_id}")
    return TWINS[twin_id]


def _agent(agent_id: str) -> Agent:
    for a in SCENARIO.agents:
        if a.id == agent_id:
            return a
    raise HTTPException(422, f"unknown agent {agent_id}")


def _load(name: str) -> Scenario:
    global SCENARIO
    try:
        SCENARIO = load_scenario(name)
    except FileNotFoundError:
        raise HTTPException(404, f"unknown scenario {name}")
    _register(SCENARIO.twin, name)
    return SCENARIO


_load("golden")


# --- scenarios / twins ---------------------------------------------------------------------

@app.get("/scenarios")
def scenarios() -> dict:
    return {"scenarios": list_scenarios(), "current": SCENARIO.twin.id}


@app.post("/scenarios/{name}/load")
def load(name: str) -> Twin:
    """The ONE sync action: re-import a scenario file (e.g. golden_sync) as the current twin."""
    return _load(name).twin


@app.get("/twin/{twin_id}")
def get_twin(twin_id: str) -> Twin:
    return _twin(twin_id)


class CloneRequest(BaseModel):
    control_ids: tuple[str, ...] = ()
    add_grants: tuple[PrivilegeGrant, ...] = ()
    label: str = "what-if"


@app.post("/twin/{twin_id}/clone")
def clone_twin(twin_id: str, req: CloneRequest) -> Twin:
    cat = {c.id: c for c in SCENARIO.catalogue}
    try:
        controls = tuple(cat[c] for c in req.control_ids)
    except KeyError as e:
        raise HTTPException(422, f"unknown control {e}")
    return _register(clone(_twin(twin_id), add_controls=controls, add_grants=req.add_grants), req.label)


@app.get("/agents")
def agents() -> tuple[Agent, ...]:
    return SCENARIO.agents


@app.get("/controls/{twin_id}")
def controls(twin_id: str) -> dict:
    twin = _twin(twin_id)
    return {"applied": twin.controls, "catalogue": SCENARIO.catalogue}


@app.get("/graph/{twin_id}")
def graph(twin_id: str) -> dict:
    """Assets + compiled attack edges + flows in a shape React Flow can draw directly."""
    twin = _twin(twin_id)
    edges = compile(twin, TECH)
    seen: dict[tuple, dict] = {}
    for e in edges:
        k = (e.src, e.dst, e.technique)
        seen.setdefault(k, {"src": e.src, "dst": e.dst, "technique": e.technique, "attck": TECH[e.technique].attck,
                            "identities": [], "p_success": e.p_success, "evidence": e.evidence})
        if e.identity_id:
            seen[k]["identities"].append(e.identity_id)
        seen[k]["p_success"] = max(seen[k]["p_success"], e.p_success)
    return {"twin_id": twin.id, "assets": twin.assets, "identities": twin.identities, "grants": twin.grants,
            "attack_edges": list(seen.values()), "flows": twin.flows, "controls": twin.controls}


@app.get("/paths/{twin_id}")
def paths(twin_id: str, agent_id: str = "external") -> dict:
    """Attack path discovery: the complete inventory (controls treated as perfect = the
    industry path count) and the routes the agent actually rates highest."""
    twin = _twin(twin_id)
    agent = _agent(agent_id)
    try:
        naive = search(compile(twin, TECH, naive=True), agent, twin)
        real = search(compile(twin, TECH), agent, twin)
    except SearchBudgetExceeded as e:
        raise HTTPException(409, str(e))
    return {"twin_id": twin.id, "agent_id": agent.id, "naive_count": len(naive.routes), "count": len(real.routes),
            "routes": [[{"src": e.src, "dst": e.dst, "technique": e.technique, "identity_id": e.identity_id, "p_success": e.p_success}
                        for e in r] for r in real.routes]}


# --- simulation / decision ------------------------------------------------------------------

class SimulateRequest(BaseModel):
    twin_id: str = "current"
    agent_id: str = "external"
    n: int = 1000
    seed: int = 1


@app.post("/simulate")
def run_simulate(req: SimulateRequest) -> Result:
    twin = _twin(req.twin_id)
    try:
        return simulate(compile(twin, TECH), _agent(req.agent_id), twin, req.n, req.seed)
    except SearchBudgetExceeded as e:
        raise HTTPException(409, str(e))


class EvaluateRequest(BaseModel):
    twin_id: str = "current"
    control_ids: tuple[str, ...]
    agent_ids: tuple[str, ...] = ("external",)
    seed: int = 1
    n: int = 1000


@app.post("/evaluate-change")
def run_evaluate(req: EvaluateRequest) -> ChangeVerdict:
    twin = _twin(req.twin_id)
    key = (twin.id, req.control_ids, req.agent_ids, req.seed, req.n)
    if not req.control_ids:
        raise HTTPException(422, "propose at least one control")
    if key not in VERDICTS:
        cat = {c.id for c in SCENARIO.catalogue}
        unknown = set(req.control_ids) - cat
        if unknown:
            raise HTTPException(422, f"unknown control(s) {sorted(unknown)}")
        try:
            v = evaluate_change(SCENARIO, req.control_ids, req.agent_ids, twin=twin, seed=req.seed, n=req.n, techniques=TECH)
        except SearchBudgetExceeded as e:
            raise HTTPException(409, str(e))
        _register(TWINS.get(v.after_twin_id) or clone(twin, add_controls=tuple(c for c in SCENARIO.catalogue if c.id in req.control_ids)),
                  "+".join(req.control_ids))
        VERDICTS[key] = v
    return VERDICTS[key]


class OptimizeRequest(BaseModel):
    twin_id: str = "current"
    budget: int = 12
    agent_ids: tuple[str, ...] = ("external", "insider")


@app.post("/optimize")
def run_optimize(req: OptimizeRequest) -> Portfolio:
    return optimize(SCENARIO, req.budget, req.agent_ids, twin=_twin(req.twin_id), techniques=TECH)


@app.get("/matrix/{twin_id}")
def matrix(twin_id: str, seed: int = 1, n: int = 500) -> dict:
    """Controls x agents: effort increase % (null = route eliminated) and p_success delta."""
    twin = _twin(twin_id)
    rows = []
    for c in SCENARIO.catalogue:
        cells = []
        for a in SCENARIO.agents:
            v = evaluate_change(SCENARIO, (c.id,), (a.id,), twin=twin, seed=seed, n=n, techniques=TECH, with_alternatives=False)
            cells.append({"agent_id": a.id, "effort_increase_pct": v.delta.effort_increase_pct,
                          "route_eliminated": v.delta.route_eliminated, "p_success_delta": v.delta.p_success_delta,
                          "recommendation": v.recommendation})
        rows.append({"control_id": c.id, "name": c.name, "cost": c.cost,
                     "broken_flows": [f.id for f in evaluate_change(SCENARIO, (c.id,), (SCENARIO.agents[0].id,), twin=twin,
                                                                       seed=seed, n=50, techniques=TECH, with_alternatives=False).broken_flows],
                     "cells": cells})
    return {"twin_id": twin.id, "agents": [a.id for a in SCENARIO.agents], "rows": rows}


@app.get("/blast-radius/{twin_id}/{asset_id}")
def blast(twin_id: str, asset_id: str) -> Blast:
    twin = _twin(twin_id)
    if asset_id not in {a.id for a in twin.assets}:
        raise HTTPException(404, f"unknown asset {asset_id}")
    return blast_radius(twin, compile(twin, TECH), asset_id)


@app.get("/lineage/{twin_id}")
def lineage(twin_id: str) -> dict:
    _twin(twin_id)
    nodes = [{"id": t.id, "parent_id": t.parent_id, "label": LABELS.get(t.id, t.id[:8]),
              "controls": [c.id for c in t.controls]} for t in TWINS.values()]
    edges = [[t.parent_id, t.id] for t in TWINS.values() if t.parent_id in TWINS]
    return {"nodes": nodes, "edges": edges}
