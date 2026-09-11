"""Property tests on random twins: the engine's guarantees must hold on data it has never seen,
not just on the golden story. 30 seeds, each a different environment shape."""

import random

import pytest

from engine.models import (Agent, Asset, Control, ControlImpact, Edge, FlowSelector, Identity,
                           PrivilegeGrant, ServiceFlow, Twin, twin_hash)
from engine.scenario import Scenario
from engine.search import SearchBudgetExceeded, search
from engine.twin import clone
from engine.walk import route_policy, simulate, trace
from rules.compile import broken_flows, compile
from rules.evaluate import evaluate_change
from rules.loader import load_techniques
from rules.optimize import optimize

T = load_techniques()
ZONES = ["external", "dmz", "corp", "mgmt", "prod"]
LATERAL = {"rdp_lateral": ("rdp", 3389), "ssh_lateral": ("ssh", 22), "smb_lateral": ("smb", 445), "db_login": ("tcp", 5432)}
EVID = ["observed", "inventory", "inferred", "assumed"]


def random_scenario(seed: int, n_assets: int | None = None, n_ids: int | None = None, fanout: int = 3) -> Scenario:
    rng = random.Random(seed)
    n_assets = n_assets or rng.randint(6, 14)
    assets = [Asset(id="internet", name="Internet", kind="internet", zone="external", criticality=1)]
    for i in range(1, n_assets):
        zone = rng.choice(ZONES[1:])
        kind = rng.choice(["server", "workstation", "database", "share"])
        assets.append(Asset(id=f"a{i}", name=f"Asset {i}", kind=kind, zone=zone, criticality=rng.randint(1, 4)))
    target = rng.choice([a for a in assets if a.id != "internet"])
    assets = [a.model_copy(update={"criticality": 5, "crown_jewel": True}) if a.id == target.id else a for a in assets]
    ids = [Identity(id=f"i{k}", name=f"Identity {k}", kind=rng.choice(["user", "admin", "service_account"]), tier=rng.randint(0, 2))
           for k in range(n_ids or rng.randint(3, 7))]
    inner = [a for a in assets if a.id != "internet"]
    grants: list[PrivilegeGrant] = []
    edges: set[Edge] = set()

    # A guaranteed credential spine, so every twin has at least one real multi-hop route:
    # internet -phish-> w0 (admin) -dump-> creds(i0) -lateral-> w1 (i0 login/admin) -dump-> creds(i1) ... -> target
    spine_len = rng.randint(2, min(4 if n_assets <= 14 else 7, len(inner)))
    spine = rng.sample([x for x in inner if x.id != target.id], k=spine_len - 1) + [target]
    edges.add(Edge(src="internet", dst=spine[0].id, technique="phish"))
    for k in range(len(spine) - 1):
        cur, nxt = spine[k], spine[k + 1]
        ident = ids[k % len(ids)]
        grants.append(PrivilegeGrant(identity_id=ident.id, asset_id=cur.id, capability="session", evidence=rng.choice(EVID)))
        grants.append(PrivilegeGrant(identity_id=ident.id, asset_id=nxt.id, capability=rng.choice(["login", "admin"]), evidence=rng.choice(EVID)))
        edges.add(Edge(src=cur.id, dst=cur.id, technique="cred_dump"))
        if k > 0:
            edges.add(Edge(src=cur.id, dst=cur.id, technique="priv_esc_local"))   # phish grants admin on w0; later hops need priv-esc
        edges.add(Edge(src=cur.id, dst=nxt.id, technique=rng.choice(list(LATERAL)), evidence=rng.choice(EVID)))

    # Random noise on top: extra grants, footholds, host-local edges, lateral edges.
    for ident in ids:
        for x in rng.sample(inner, k=min(len(inner), rng.randint(1, 3))):
            grants.append(PrivilegeGrant(identity_id=ident.id, asset_id=x.id, capability=rng.choice(["session", "login", "admin"]), evidence=rng.choice(EVID)))
    for x in rng.sample(inner, k=min(len(inner), rng.randint(1, 3))):
        edges.add(Edge(src="internet", dst=x.id, technique=rng.choice(["phish", "exploit_public_app"])))
    for x in inner:
        if rng.random() < 0.7:
            edges.add(Edge(src=x.id, dst=x.id, technique="cred_dump"))
        if rng.random() < 0.6:
            edges.add(Edge(src=x.id, dst=x.id, technique="priv_esc_local"))
        for y in rng.sample(inner, k=min(len(inner), rng.randint(1, fanout))):
            if y.id != x.id:
                edges.add(Edge(src=x.id, dst=y.id, technique=rng.choice(list(LATERAL)), evidence=rng.choice(EVID)))
    edges.add(Edge(src=target.id, dst="internet", technique="exfil_c2"))
    flows = []
    for k in range(rng.randint(2, 6)):
        a, b = rng.sample(inner, 2)
        tech = rng.choice(list(LATERAL))
        flows.append(ServiceFlow(id=f"L{k}", name=f"flow {k}", src=a.id, dst=b.id, protocol=LATERAL[tech][0], port=LATERAL[tech][1],
                                 identity_id=rng.choice(ids).id, criticality=rng.randint(1, 5), evidence=rng.choice(EVID)))
    controls = []
    for k in range(rng.randint(3, 6)):
        pick = rng.random()
        if pick < 0.35:
            sel = FlowSelector(dst_assets=frozenset({rng.choice(inner).id}))
        elif pick < 0.6:
            sel = FlowSelector(identity_kinds=frozenset({rng.choice(["user", "admin", "service_account"])}))
        elif pick < 0.8:
            sel = FlowSelector(techniques=frozenset({rng.choice(list(T))}))
        else:
            sel = FlowSelector(protocols=frozenset({rng.choice(["rdp", "ssh", "smb", "tcp"])}))
        exc = (FlowSelector(src_assets=frozenset({rng.choice(inner).id})),) if rng.random() < 0.3 else ()
        controls.append(Control(id=f"c{k}", name=f"control {k}", cost=rng.randint(1, 6),
                                impacts=(ControlImpact(deny=sel, exceptions=exc, efficacy=rng.choice([0.5, 0.8, 0.95, 1.0]), breaks_flows=rng.random() < 0.6),)))
    agents = (Agent(id="ext", name="ext", start_zones=("external",), capabilities=frozenset(), objective="specific_target",
                    target=target.id, noise_budget=rng.choice([2.0, 3.0, 4.0]), skill=rng.random()),)
    base = Twin(id="", assets=tuple(assets), identities=tuple(ids), grants=tuple(grants), edges=tuple(sorted(edges, key=lambda e: (e.src, e.dst, e.technique))),
                flows=tuple(flows), controls=())
    return Scenario(name=f"fuzz-{seed}", twin=base.model_copy(update={"id": twin_hash(base)}), agents=agents, catalogue=tuple(controls))


def _sig(edges):
    return {(e.src, e.dst, e.technique) for e in edges}


@pytest.mark.parametrize("seed", range(30))
def test_engine_invariants_on_random_twin(seed):
    sc = random_scenario(seed)
    twin, agent = sc.twin, sc.agents[0]

    # compile never invents a transition, with or without controls, naive or not
    for ctl in [()] + [(c,) for c in sc.catalogue]:
        tw = clone(twin, add_controls=ctl)
        for naive in (False, True):
            assert _sig(compile(tw, T, naive=naive)) <= _sig(tw.edges)
    # with no controls every edge survives - except a credential edge whose destination nobody
    # holds a login/admin grant on: there is no identity to log in as, so no transition exists
    has_login = {g.asset_id for g in twin.grants if g.capability in ("login", "admin")}
    expected = {(e.src, e.dst, e.technique) for e in twin.edges if "creds:who" not in T[e.technique].requires or e.dst in has_login}
    assert _sig(compile(twin, T)) == expected

    # search terminates under its caps or raises loudly
    edges = compile(twin, T)
    try:
        inv = search(edges, agent, twin)
    except SearchBudgetExceeded:
        return
    assert len(inv.routes) <= 5000 and all(len(r) <= 8 for r in inv.routes)

    # determinism and internal consistency of the simulation; the replay is the same dice
    r1 = simulate(edges, agent, twin, 300, seed)
    r2 = simulate(edges, agent, twin, 300, seed)
    assert r1 == r2
    assert 0.0 <= r1.p_success <= 1.0 and r1.p_success_ci[0] <= r1.p_success <= r1.p_success_ci[1] + 1e-9
    assert len(r1.effort_distribution) == round(r1.p_success * 300)
    assert sum(t.success for t in trace(edges, agent, twin, seed, 300)) == len(r1.effort_distribution)
    assert abs(sum(c.p_select for c in route_policy(inv, agent)) - (1.0 if inv.routes and route_policy(inv, agent) else 0.0)) < 1e-9

    # a control never makes any route more likely, never adds a naive path
    base_p = {tuple((e.src, e.dst, e.technique, e.identity_id) for e in c.route): c.p_route for c in route_policy(inv, agent, k=len(inv.routes) or 1)}
    base_naive = len(search(compile(twin, T, naive=True), agent, twin).routes)
    for c in sc.catalogue:
        tw = clone(twin, add_controls=(c,))
        try:
            after = search(compile(tw, T), agent, tw)
            assert len(search(compile(tw, T, naive=True), agent, tw).routes) <= base_naive
        except SearchBudgetExceeded:
            continue
        for ch in route_policy(after, agent, k=len(after.routes) or 1):
            sig = tuple((e.src, e.dst, e.technique, e.identity_id) for e in ch.route)
            assert sig in base_p and ch.p_route <= base_p[sig] + 1e-9, (seed, c.id)

    # verdict rules hold for every single-control proposal
    for c in sc.catalogue:
        try:
            v = evaluate_change(sc, (c.id,), (agent.id,), seed=seed, n=200, with_alternatives=False)
        except SearchBudgetExceeded:
            continue
        crit = [f for f in v.broken_flows if f.criticality >= 4]
        if crit:
            assert v.recommendation == "blocked"
        elif v.confidence.undetermined or v.confidence.level == "Low" or v.broken_flows:
            assert v.recommendation == "review"
        if v.recommendation == "deploy":
            assert not v.broken_flows and not v.confidence.undetermined
        assert v.broken_flows == tuple(f for f in broken_flows(clone(twin, add_controls=(c,))) if f not in broken_flows(twin))

    # the optimiser never breaks a critical flow and never exceeds budget
    try:
        p = optimize(sc, 6, (agent.id,))
    except SearchBudgetExceeded:
        return
    assert p.constrained_cost <= 6
    assert not any(f.criticality >= 4 for f in broken_flows(clone(twin, add_controls=tuple(c for c in sc.catalogue if c.id in p.constrained))))
