"""Comprehensive invariant tests for Track A engine components (CLAUDE.md §7 / IMPLEMENTATION_PLAN Gate G1).

Verifies core architectural invariants:
1. Control Invariant: Adding a control never increases attack success (p_success or p_route).
2. Clone Invariant: clone() never mutates input (verified via canonical twin_hash before/after).
3. Determinism Invariant: Identical seed and inputs produce byte-identical Result objects.
4. Route Policy Invariant: Sum of selection probabilities equals 1.0; noise budget strictly enforced.
5. Blast Radius Invariant: Real credential-reachable assets are strictly bounded by topological upper_bound.
6. Diff Invariant: Delta correctly tracks naive path reduction, effort increase / route elimination, and substituted paths.
"""

import pytest
from engine.models import Asset, Control, Edge, PrivilegeGrant, Twin, Agent, CompiledEdge
from engine.twin import clone, twin_hash
from engine.search import search
from engine.walk import route_policy, simulate, clear_search_cache
from engine.results import diff, Result
from engine.blast import blast_radius


@pytest.fixture
def test_twin() -> Twin:
    assets = (
        Asset(id="ext", name="Internet", kind="internet", zone="external", criticality=1),
        Asset(id="ws_user", name="User PC", kind="workstation", zone="corp", criticality=2),
        Asset(id="app_srv", name="Web Application", kind="server", zone="dmz", criticality=3),
        Asset(id="db_prod", name="Production Database", kind="database", zone="prod", criticality=5, crown_jewel=True),
        Asset(id="isolated_box", name="Air-gapped Box", kind="server", zone="mgmt", criticality=4),
    )
    grants = (
        PrivilegeGrant(identity_id="usr.alice", asset_id="ws_user", capability="session"),
        PrivilegeGrant(identity_id="adm.db", asset_id="db_prod", capability="admin"),
    )
    edges = (
        Edge(src="ext", dst="ws_user", technique="phish"),
        Edge(src="ws_user", dst="app_srv", technique="rdp_lateral"),
        Edge(src="app_srv", dst="db_prod", technique="db_login"),
    )
    twin = Twin(
        id="",
        assets=assets,
        identities=(),
        grants=grants,
        edges=edges,
        flows=(),
        controls=(),
    )
    return twin.model_copy(update={"id": twin_hash(twin)})


@pytest.fixture
def compiled_test_edges() -> tuple[CompiledEdge, ...]:
    return (
        CompiledEdge(
            src="ext", dst="ws_user", technique="phish",
            identity_id=None,
            requires=frozenset({"session:ext"}),
            grants=frozenset({"session:ws_user", "admin:ws_user", "creds:usr.alice"}),
            p_success=0.8, cost=1.0, noise=0.2, evidence="observed"
        ),
        CompiledEdge(
            src="ws_user", dst="app_srv", technique="rdp_lateral",
            identity_id="usr.alice",
            requires=frozenset({"session:ws_user", "creds:usr.alice"}),
            grants=frozenset({"session:app_srv", "creds:adm.db"}),
            p_success=0.85, cost=2.0, noise=0.3, evidence="observed"
        ),
        CompiledEdge(
            src="app_srv", dst="db_prod", technique="db_login",
            identity_id="adm.db",
            requires=frozenset({"session:app_srv", "creds:adm.db"}),
            grants=frozenset({"session:db_prod", "admin:db_prod"}),
            p_success=0.9, cost=2.0, noise=0.2, evidence="observed"
        ),
        # Alternative direct route via web exploit
        CompiledEdge(
            src="ext", dst="app_srv", technique="exploit_public_app",
            identity_id=None,
            requires=frozenset({"session:ext"}),
            grants=frozenset({"session:app_srv", "creds:adm.db"}),
            p_success=0.7, cost=3.0, noise=0.6, evidence="inventory"
        ),
    )


@pytest.fixture
def test_agent() -> Agent:
    return Agent(
        id="adversary-01",
        name="Targeted External Attacker",
        start_zones=("external",),
        capabilities=frozenset(),
        objective="specific_target",
        target="db_prod",
        noise_budget=1.5,
        skill=0.7,
    )


# ---------------------------------------------------------------------
# Invariant 1: clone never mutates its input
# ---------------------------------------------------------------------
def test_clone_never_mutates_input(test_twin):
    hash_before = twin_hash(test_twin)
    assert test_twin.id == hash_before

    new_ctrl = Control(id="ctrl-mfa", name="Enforce MFA", cost=50, impacts=())
    new_edge = Edge(src="app_srv", dst="isolated_box", technique="ssh_lateral")

    cloned = clone(test_twin, add_controls=(new_ctrl,), add_edges=(new_edge,))

    # Input twin must be strictly unchanged
    hash_after = twin_hash(test_twin)
    assert hash_before == hash_after
    assert len(test_twin.controls) == 0
    assert len(test_twin.edges) == 3

    # Cloned twin must reflect additions and correct lineage
    assert cloned.parent_id == test_twin.id
    assert cloned.id == twin_hash(cloned)
    assert len(cloned.controls) == 1
    assert cloned.controls[0].id == "ctrl-mfa"
    assert len(cloned.edges) == 4


# ---------------------------------------------------------------------
# Invariant 2: Determinism (identical seed -> identical output)
# ---------------------------------------------------------------------
def test_simulation_identical_seed_reproducibility(compiled_test_edges, test_agent, test_twin):
    clear_search_cache()
    sim1 = simulate(compiled_test_edges, test_agent, test_twin, n=500, seed=999)
    clear_search_cache()
    sim2 = simulate(compiled_test_edges, test_agent, test_twin, n=500, seed=999)

    assert sim1.p_success == sim2.p_success
    assert sim1.p_success_ci == sim2.p_success_ci
    assert sim1.mean_effort == sim2.mean_effort
    assert sim1.p90_effort == sim2.p90_effort
    assert sim1.edge_frequency == sim2.edge_frequency
    assert sim1.weighted_risk == sim2.weighted_risk
    assert sim1.effort_distribution == sim2.effort_distribution
    assert len(sim1.routes) == len(sim2.routes)
    for r1, r2 in zip(sim1.routes, sim2.routes):
        assert r1.p_select == r2.p_select
        assert r1.observed_freq == r2.observed_freq
        assert r1.observed_success == r2.observed_success


# ---------------------------------------------------------------------
# Invariant 3: Controls never increase route success (monotonicity)
# ---------------------------------------------------------------------
def test_control_never_increases_success(compiled_test_edges, test_agent, test_twin):
    clear_search_cache()
    baseline_result = simulate(compiled_test_edges, test_agent, test_twin, n=1000, seed=42)

    # Apply control at the target bottleneck (e.g. database firewall or MFA on db_prod)
    hardened_edges = tuple(
        e.model_copy(update={"p_success": e.p_success * 0.5})
        if e.dst == "db_prod" else e
        for e in compiled_test_edges
    )

    clear_search_cache()
    hardened_result = simulate(hardened_edges, test_agent, test_twin, n=1000, seed=42)

    # Route policy utility and route success check
    inv_base = search(compiled_test_edges, test_agent, test_twin)
    inv_hard = search(hardened_edges, test_agent, test_twin)

    choices_base = route_policy(inv_base, test_agent)
    choices_hard = route_policy(inv_hard, test_agent)

    # Invariant: For any route present in both, p_route in hardened must be <= p_route in baseline
    base_dict = {tuple((e.src, e.dst, e.technique) for e in c.route): c.p_route for c in choices_base}
    for c in choices_hard:
        sig = tuple((e.src, e.dst, e.technique) for e in c.route)
        if sig in base_dict:
            assert c.p_route <= base_dict[sig] + 1e-9

    # Bottleneck control strictly reduces overall risk and success
    assert hardened_result.p_success < baseline_result.p_success
    assert hardened_result.weighted_risk < baseline_result.weighted_risk


# ---------------------------------------------------------------------
# Invariant 4: Route policy probabilities and noise budget
# ---------------------------------------------------------------------
def test_route_policy_probabilities_and_noise_filtering(compiled_test_edges, test_agent, test_twin):
    clear_search_cache()
    inv = search(compiled_test_edges, test_agent, test_twin)

    # Under standard budget (1.5), both routes are admissible
    choices = route_policy(inv, test_agent)
    assert len(choices) > 0
    total_p_select = sum(c.p_select for c in choices)
    assert total_p_select == pytest.approx(1.0, rel=1e-5)

    # With very strict noise budget (0.3), routes with noise > 0.3 must be dropped
    quiet_agent = test_agent.model_copy(update={"noise_budget": 0.3})
    quiet_choices = route_policy(inv, quiet_agent)
    # The two routes have noise (0.2+0.3+0.2 = 0.7) and (0.6+0.2 = 0.8), both > 0.3
    assert len(quiet_choices) == 0


# ---------------------------------------------------------------------
# Invariant 5: Blast radius containment (reachable subset of upper_bound)
# ---------------------------------------------------------------------
def test_blast_radius_reachable_subset_of_upper_bound(test_twin, compiled_test_edges):
    blast = blast_radius(test_twin, compiled_test_edges, "ext")

    assert set(blast.reachable).issubset(set(blast.upper_bound))
    assert "db_prod" in blast.reachable
    assert "db_prod" in blast.crown_jewels_hit
    assert "isolated_box" not in blast.reachable
    assert "isolated_box" not in blast.upper_bound


# ---------------------------------------------------------------------
# Invariant 6: Diff calculation & Substituted paths
# ---------------------------------------------------------------------
def test_diff_statistics_and_substituted_paths(compiled_test_edges, test_agent, test_twin):
    clear_search_cache()
    # Baseline: only route 1 exists
    route1_edges = tuple(e for e in compiled_test_edges if e.technique != "exploit_public_app")
    res_before = simulate(route1_edges, test_agent, test_twin, n=500, seed=1)

    clear_search_cache()
    # After: route 1 is blocked, only route 2 (exploit) exists
    route2_edges = tuple(e for e in compiled_test_edges if e.technique != "phish")
    res_after = simulate(route2_edges, test_agent, test_twin, n=500, seed=1)

    delta = diff(res_before, res_after, naive_before=1, naive_after=1)

    assert delta.naive_path_reduction_pct == 0.0
    assert len(delta.substituted_paths) > 0  # Route 2 was adopted after Route 1 was closed
    assert not delta.route_eliminated or len(res_after.effort_distribution) < 20


# ---------------------------------------------------------------------
# Invariant 7 (golden, every catalogue control): a control never makes any route more
# likely, never raises the best route's success, never adds a naive path.
# NOTE the selected-route MIX p_success CAN rise (degrade a decoy route and the agent
# picks the easy one more often) - that is modelled behaviour, not a bug, and the
# verdict engine treats it as weak gain.
# ---------------------------------------------------------------------
def test_control_monotone_on_routes_and_naive_count_golden():
    from engine.scenario import load_scenario
    from engine.twin import clone
    from rules.compile import compile as compile_twin
    from rules.loader import load_techniques

    sc = load_scenario("golden")
    tech = load_techniques()
    for agent in sc.agents:
        base_inv = search(compile_twin(sc.twin, tech), agent, sc.twin)
        base_naive = len(search(compile_twin(sc.twin, tech, naive=True), agent, sc.twin).routes)
        base_p = {tuple((e.src, e.dst, e.technique, e.identity_id) for e in c.route): c.p_route
                  for c in route_policy(base_inv, agent, k=len(base_inv.routes) or 1)}
        base_best = max(base_p.values(), default=0.0)
        for control in sc.catalogue:
            twin = clone(sc.twin, add_controls=(control,))
            inv = search(compile_twin(twin, tech), agent, twin)
            naive = len(search(compile_twin(twin, tech, naive=True), agent, twin).routes)
            assert naive <= base_naive, (agent.id, control.id)
            choices = route_policy(inv, agent, k=len(inv.routes) or 1)
            for c in choices:
                sig = tuple((e.src, e.dst, e.technique, e.identity_id) for e in c.route)
                assert sig in base_p, (agent.id, control.id, "control created a route")
                assert c.p_route <= base_p[sig] + 1e-9, (agent.id, control.id)
            assert max((c.p_route for c in choices), default=0.0) <= base_best + 1e-9, (agent.id, control.id)
