"""evaluate_change(): THE centrepiece (CLAUDE.md §7).

Propose controls -> clone -> compile before/after (naive for the path count, real for the
simulation) -> search + simulate -> security delta, broken flows, computed confidence,
verdict, and the safer alternatives.
"""

from itertools import combinations
from typing import Literal

from pydantic import BaseModel

from engine.models import Agent, CompiledEdge, Control, Evidence, ServiceFlow, Twin
from engine.results import Delta, Result, diff
from engine.scenario import Scenario
from engine.search import search
from engine.twin import clone
from engine.walk import simulate
from rules.compile import broken_flows, compile
from rules.loader import TechniqueTable, load_techniques
from rules.optimize import risk

WEIGHT: dict[Evidence, float] = {"observed": 1.0, "inventory": 0.9, "inferred": 0.5, "assumed": 0.0}


class Confidence(BaseModel, frozen=True):
    level: Literal["High", "Medium", "Low"]
    score: float
    unknowns: tuple[str, ...]            # "svc.backup admin on prod-db - inferred"
    undetermined: bool                   # any decisive element is 'assumed'


class AgentOutcome(BaseModel, frozen=True):
    agent_id: str
    before: Result
    after: Result
    naive_before: int
    naive_after: int
    delta: Delta


class Alternative(BaseModel, frozen=True):
    control_ids: tuple[str, ...]
    cost: int
    effort_increase_pct: float | None
    route_eliminated: bool
    p_success_delta: float
    broken_flows: tuple[str, ...]
    recommendation: str


class ChangeVerdict(BaseModel, frozen=True):
    twin_id: str
    after_twin_id: str
    control_ids: tuple[str, ...]
    delta: Delta                          # primary agent (first requested)
    before: Result
    after: Result
    outcomes: tuple[AgentOutcome, ...]
    broken_flows: tuple[ServiceFlow, ...]
    cost: int
    confidence: Confidence
    recommendation: Literal["deploy", "blocked", "review"]
    reasons: tuple[str, ...]
    alternatives: tuple[Alternative, ...]


def _outcome(before_twin: Twin, after_twin: Twin, agent: Agent, techniques: TechniqueTable, n: int, seed: int) -> AgentOutcome:
    nb = len(search(compile(before_twin, techniques, naive=True), agent, before_twin).routes)
    na = len(search(compile(after_twin, techniques, naive=True), agent, after_twin).routes)
    before = simulate(compile(before_twin, techniques), agent, before_twin, n, seed)
    after = simulate(compile(after_twin, techniques), agent, after_twin, n, seed)
    return AgentOutcome(agent_id=agent.id, before=before, after=after, naive_before=nb, naive_after=na,
                        delta=diff(before, after, naive_before=nb, naive_after=na))


def _describe(e: CompiledEdge) -> str:
    who = f" as {e.identity_id}" if e.identity_id else ""
    return f"{e.technique} {e.src}->{e.dst}{who}"


def confidence_of(outcomes: tuple[AgentOutcome, ...], broken: tuple[ServiceFlow, ...]) -> Confidence:
    """Decisive elements: every flow in broken_flows and every compiled edge (which carries the
    weaker of its edge and grant evidence) on any top-K route before or after."""
    decisive: dict[str, Evidence] = {}
    for f in broken:
        decisive[f"{f.name} ({f.src}->{f.dst} as {f.identity_id})"] = f.evidence
    for o in outcomes:
        for res in (o.before, o.after):
            for rs in res.routes:
                for e in rs.route:
                    decisive.setdefault(_describe(e), e.evidence)
    if not decisive:
        return Confidence(level="Low", score=0.0, unknowns=("no route and no flow decided this verdict",), undetermined=True)
    score = sum(WEIGHT[ev] for ev in decisive.values()) / len(decisive)
    unknowns = tuple(f"{name} - {ev}" for name, ev in decisive.items() if ev in ("inferred", "assumed"))
    undetermined = any(ev == "assumed" for ev in decisive.values())
    level = "High" if score >= 0.85 else "Medium" if score >= 0.6 else "Low"
    return Confidence(level=level, score=round(score, 3), unknowns=unknowns, undetermined=undetermined)


def _weak(d: Delta) -> bool:
    return d.effort_increase_pct is not None and d.effort_increase_pct < 5 and d.p_success_delta > -0.02


def verdict_of(broken: tuple[ServiceFlow, ...], conf: Confidence, deltas: tuple[Delta, ...]):
    reasons: list[str] = []
    critical = [f for f in broken if f.criticality >= 4]
    if critical:
        reasons.append("breaks critical flow(s): " + ", ".join(f"{f.id} {f.name} (P{6 - f.criticality})" for f in critical))
        return "blocked", tuple(reasons)
    if broken:
        reasons.append("breaks non-critical flow(s): " + ", ".join(f.id for f in broken))
    if conf.level == "Low":
        reasons.append("confidence Low")
    if conf.undetermined:
        reasons.append("cannot be determined: a decisive element is assumed, not evidenced")
    if deltas and all(_weak(d) for d in deltas):
        reasons.append("weak security gain (effort +<5% and p_success barely moves)")
    if reasons:
        return "review", tuple(reasons)
    gains = [f"route eliminated for {i}" if d.route_eliminated else f"effort +{d.effort_increase_pct:.0f}%" for i, d in enumerate(deltas)]
    return "deploy", ("no flow impact; " + ", ".join(gains),)


def _alternatives(scenario: Scenario, twin: Twin, proposal: tuple[Control, ...], agents: tuple[Agent, ...],
                  techniques: TechniqueTable, n: int, seed: int) -> tuple[Alternative, ...]:
    """Best two catalogue subsets (size <= 2) costing <= 1.25x the proposal that break no
    critical flow, ranked by the deterministic risk reduction the optimiser uses."""
    budget = int(sum(c.cost for c in proposal) * 1.25)
    proposal_ids = {c.id for c in proposal}
    pool = [c for c in scenario.catalogue if c.id not in {x.id for x in twin.controls}]
    base = risk(twin, agents, techniques)
    scored = []
    for k in (1, 2):
        for subset in combinations(pool, k):
            ids = tuple(c.id for c in subset)
            cost = sum(c.cost for c in subset)
            if set(ids) == proposal_ids or cost > budget:
                continue
            cand = clone(twin, add_controls=subset)
            broken = broken_flows(cand)
            if any(f.criticality >= 4 for f in broken):
                continue
            reduction = base - risk(cand, agents, techniques)
            if reduction <= 0:
                continue
            scored.append((reduction, -cost, ids, subset, broken))
    scored.sort(key=lambda s: (-s[0], -s[1], s[2]))
    out = []
    for reduction, _, ids, subset, broken in scored[:2]:
        cand = clone(twin, add_controls=subset)
        o = _outcome(twin, cand, agents[0], techniques, n, seed)
        conf = confidence_of((o,), broken)
        rec, _ = verdict_of(broken, conf, (o.delta,))
        out.append(Alternative(control_ids=ids, cost=sum(c.cost for c in subset),
                               effort_increase_pct=o.delta.effort_increase_pct, route_eliminated=o.delta.route_eliminated,
                               p_success_delta=o.delta.p_success_delta, broken_flows=tuple(f.id for f in broken),
                               recommendation=rec))
    return tuple(out)


def evaluate_change(scenario: Scenario, control_ids: tuple[str, ...], agent_ids: tuple[str, ...] = (),
                    *, twin: Twin | None = None, seed: int = 1, n: int = 1000,
                    techniques: TechniqueTable | None = None, with_alternatives: bool = True) -> ChangeVerdict:
    techniques = techniques or load_techniques()
    twin = twin or scenario.twin
    catalogue = {c.id: c for c in scenario.catalogue}
    proposal = tuple(catalogue[c] for c in control_ids)
    agents = tuple(a for a in scenario.agents if not agent_ids or a.id in agent_ids)
    if not agents:
        raise ValueError(f"no agent matches {agent_ids}")

    after_twin = clone(twin, add_controls=proposal)
    outcomes = tuple(_outcome(twin, after_twin, a, techniques, n, seed) for a in agents)
    broken = tuple(f for f in broken_flows(after_twin) if f not in broken_flows(twin))
    conf = confidence_of(outcomes, broken)
    rec, reasons = verdict_of(broken, conf, tuple(o.delta for o in outcomes))
    alts = _alternatives(scenario, twin, proposal, agents, techniques, n, seed) if with_alternatives else ()
    return ChangeVerdict(
        twin_id=twin.id, after_twin_id=after_twin.id, control_ids=control_ids,
        delta=outcomes[0].delta, before=outcomes[0].before, after=outcomes[0].after, outcomes=outcomes,
        broken_flows=broken, cost=sum(c.cost for c in proposal), confidence=conf,
        recommendation=rec, reasons=reasons, alternatives=alts,
    )


__all__ = ["Confidence", "AgentOutcome", "Alternative", "ChangeVerdict", "confidence_of", "verdict_of", "evaluate_change"]
