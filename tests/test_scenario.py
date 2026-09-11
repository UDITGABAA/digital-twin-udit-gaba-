"""The golden demo as a regression test: the numbers in docs/DEMO_SCRIPT.md, pinned.
If a change moves one of these, the run sheet moves with it - or the change is reverted."""

import pytest

from engine.scenario import load_scenario
from engine.walk import simulate
from rules.compile import compile
from rules.evaluate import evaluate_change
from rules.loader import load_techniques
from rules.optimize import optimize, risk

T = load_techniques()


@pytest.fixture(scope="module")
def golden():
    return load_scenario("golden")


@pytest.fixture(scope="module")
def sync():
    return load_scenario("golden_sync")


def test_beat_1_and_2_baseline(golden):
    ext = golden.agents[0]
    r = simulate(compile(golden.twin, T), ext, golden.twin, 1000, 1)
    assert r.p_success == 0.886
    assert r.p_success_ci == (0.8648, 0.9042)
    assert r.mean_effort == 8.1242 and r.p90_effort == 11.0
    assert r.weighted_risk == 4.8509
    assert [e.technique for e in r.routes[0].route] == ["phish", "cred_dump", "smb_lateral", "creds_in_files", "db_login"]   # route C rated best


def test_beat_3_full_segmentation_is_blocked(golden):
    v = evaluate_change(golden, ("seg_prod_db_full",), ("external",))
    assert v.recommendation == "blocked"
    assert v.delta.naive_path_reduction_pct == 100.0
    assert v.delta.effort_increase_pct == 13.71
    assert v.delta.p_success_delta == -0.781 and v.after.p_success == 0.105
    assert [f.id for f in v.broken_flows] == ["F1", "F2", "F6"]
    assert v.confidence.level == "Medium" and v.confidence.score == 0.829
    assert v.alternatives[0].control_ids == ("mfa_humans", "patch_web_dmz") and v.alternatives[0].recommendation == "deploy"


def test_beat_4_safer_option_deploys_with_route_d(golden):
    v = evaluate_change(golden, ("seg_prod_db_scoped", "mfa_humans"), ("external",))
    assert v.recommendation == "deploy" and v.broken_flows == ()
    assert v.delta.naive_path_reduction_pct == 87.5
    assert v.delta.effort_increase_pct == 38.02 and v.after.p_success == 0.244
    assert [e.dst for e in v.delta.substituted_paths[0]] == ["web-dmz", "ci-runner", "ci-runner", "ci-runner", "backup-01", "backup-01", "prod-db"]
    v2 = evaluate_change(golden, ("mfa_humans", "patch_web_dmz"), ("external",))
    assert v2.recommendation == "deploy" and v2.delta.effort_increase_pct == 22.12


def test_beat_5_optimizer_contrast(golden):
    p = optimize(golden, 5, ("external", "insider"))
    assert p.constrained == ("mfa_humans", "patch_web_dmz") and p.constrained_broken_flows == ()
    assert p.naive == ("mfa_all", "disable_smb_share") and {"F1", "F2"} <= set(p.naive_broken_flows)
    # the deterministic score ignores detection on retries, so it is an upper bound on what the simulation sees
    ext = golden.agents[0]
    det = risk(golden.twin, (ext,), T)
    sim = simulate(compile(golden.twin, T), ext, golden.twin, 1000, 1).p_success * 5
    assert sim <= det <= sim * 1.15


def test_beat_6_sync_raises_risk(golden, sync):
    ext = golden.agents[0]
    assert sync.twin.parent_id == golden.twin.id
    before = simulate(compile(golden.twin, T), ext, golden.twin, 1000, 1)
    after = simulate(compile(sync.twin, T), ext, sync.twin, 1000, 1)
    assert after.p_success == 0.947 > before.p_success
    assert after.weighted_risk > before.weighted_risk
