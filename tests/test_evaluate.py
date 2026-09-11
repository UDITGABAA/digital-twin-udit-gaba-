"""Verdict rules, computed confidence, the None-effort case, and the golden G3 assertions."""

import pytest

from engine.models import ServiceFlow
from engine.results import Delta
from engine.scenario import load_scenario
from rules.evaluate import Confidence, confidence_of, evaluate_change, verdict_of
from rules.optimize import optimize


def _flow(id, crit, ev="inventory"):
    return ServiceFlow(id=id, name=id, src="a", dst="b", protocol="tcp", port=1, identity_id="i", criticality=crit, evidence=ev)


def _delta(effort, dp, eliminated=False):
    return Delta(naive_path_reduction_pct=0, effort_increase_pct=effort, route_eliminated=eliminated,
                 p_success_delta=dp, substituted_paths=())


HIGH = Confidence(level="High", score=0.95, unknowns=(), undetermined=False)
LOW = Confidence(level="Low", score=0.4, unknowns=("x - inferred",), undetermined=False)
ASSUMED = Confidence(level="Medium", score=0.7, unknowns=("x - assumed",), undetermined=True)


# --- verdict rules -----------------------------------------------------------------------

def test_block_on_critical_flow_regardless_of_gain():
    rec, reasons = verdict_of((_flow("F1", 5),), HIGH, (_delta(80.0, -0.7),))
    assert rec == "blocked" and "F1" in reasons[0]


def test_review_on_noncritical_flow_low_confidence_or_undetermined():
    assert verdict_of((_flow("F5", 2),), HIGH, (_delta(30.0, -0.3),))[0] == "review"
    assert verdict_of((), LOW, (_delta(30.0, -0.3),))[0] == "review"
    assert verdict_of((), ASSUMED, (_delta(30.0, -0.3),))[0] == "review"


def test_weak_gain_only_when_effort_pct_exists():
    assert verdict_of((), HIGH, (_delta(2.0, -0.01),))[0] == "review"
    assert verdict_of((), HIGH, (_delta(None, -0.5, eliminated=True),))[0] == "deploy"   # route eliminated = strong gain
    assert verdict_of((), HIGH, (_delta(2.0, -0.3),))[0] == "deploy"                     # p_success moved a lot


def test_deploy_when_clean():
    rec, reasons = verdict_of((), HIGH, (_delta(25.0, -0.4),))
    assert rec == "deploy" and "no flow impact" in reasons[0]


# --- confidence ---------------------------------------------------------------------------

def test_confidence_scores_only_decisive_elements():
    c = confidence_of((), (_flow("F1", 5, "observed"), _flow("F2", 4, "inferred")))
    assert c.level == "Medium" and c.score == 0.75 and c.unknowns == ("F2 (a->b as i) - inferred",)
    assert confidence_of((), (_flow("F1", 5, "assumed"),)).undetermined is True
    assert confidence_of((), ()).level == "Low"


# --- golden: the G3 assertions --------------------------------------------------------------

@pytest.fixture(scope="module")
def golden():
    return load_scenario("golden")


def test_full_segmentation_is_blocked_with_named_unknown(golden):
    v = evaluate_change(golden, ("seg_prod_db_full",), ("external",))
    assert v.recommendation == "blocked"
    assert [f.id for f in v.broken_flows] == ["F1", "F2", "F6"]
    assert v.delta.naive_path_reduction_pct == 100.0
    assert v.after.p_success < 0.2 < 0.8 < v.before.p_success
    assert v.confidence.level == "Medium"
    assert any("svc.backup" in u and "inferred" in u for u in v.confidence.unknowns)
    assert v.alternatives and v.alternatives[0].recommendation == "deploy" and not v.alternatives[0].broken_flows


def test_scoped_plus_mfa_deploys_with_route_d_substituted(golden):
    v = evaluate_change(golden, ("seg_prod_db_scoped", "mfa_humans"), ("external",))
    assert v.recommendation == "deploy" and v.broken_flows == ()
    assert v.delta.effort_increase_pct > 20 and v.delta.p_success_delta < -0.5
    assert v.outcomes[0].naive_after == 1
    assert any(r[0].dst == "web-dmz" for r in v.delta.substituted_paths)      # the attacker's new route is D


def test_mfa_all_blocked_by_service_identities(golden):
    v = evaluate_change(golden, ("mfa_all",), ("external",), with_alternatives=False)
    assert v.recommendation == "blocked" and [f.id for f in v.broken_flows] == ["F1", "F2", "F4"]


def test_same_seed_same_verdict(golden):
    a = evaluate_change(golden, ("edr_cred_dump",), ("external",), with_alternatives=False)
    b = evaluate_change(golden, ("edr_cred_dump",), ("external",), with_alternatives=False)
    assert a == b


def test_optimizer_never_breaks_critical_flow_and_naive_does(golden):
    p = optimize(golden, 12, ("external", "insider"))
    assert not {"F1", "F2"} & set(p.constrained_broken_flows)
    assert {"F1", "F2"} <= set(p.naive_broken_flows)
    assert p.constrained_cost <= 12 and p.evaluated > 0
