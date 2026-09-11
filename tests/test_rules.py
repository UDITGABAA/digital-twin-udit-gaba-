"""Track B tests: the compiler never invents a transition; selectors tell an allowed payroll
workload apart from an attacker on an HR workstation holding payroll credentials."""

import pytest

from engine.models import ControlImpact, FlowSelector, Twin, Control
from engine.scenario import load_scenario
from engine.search import search
from engine.twin import clone
from rules.compile import Channel, affected, broken_flows, compile, edge_channel, flow_channel, matches
from rules.loader import Technique, load_techniques


@pytest.fixture(scope="module")
def techniques():
    return load_techniques()


@pytest.fixture(scope="module")
def golden():
    return load_scenario("golden")


def _sig(edges):
    return {(e.src, e.dst, e.technique) for e in edges}


# --- loader ---------------------------------------------------------------------------

def test_ten_techniques_with_attck_ids(techniques):
    assert len(techniques) == 10
    assert all(t.attck.startswith("T") for t in techniques.values())


def test_loader_rejects_bad_attck_and_unknown_placeholder():
    with pytest.raises(ValueError):
        Technique(id="x", attck="1234", base_success=1, cost=1, noise=0)
    with pytest.raises(ValueError):
        Technique(id="x", attck="T1234", requires=("creds:everyone",), base_success=1, cost=1, noise=0)


# --- compile never invents a transition -----------------------------------------------

def test_compiled_transitions_subset_of_twin_edges(golden, techniques):
    compiled = compile(golden.twin, techniques)
    assert _sig(compiled) <= _sig(golden.twin.edges)
    assert _sig(compiled) == _sig(golden.twin.edges)          # no controls applied: every edge survives
    for c in golden.catalogue:
        twin = clone(golden.twin, add_controls=(c,))
        assert _sig(compile(twin, techniques)) <= _sig(twin.edges)
        assert _sig(compile(twin, techniques, naive=True)) <= _sig(twin.edges)


def test_creds_who_expands_only_over_grants_on_dst(golden, techniques):
    compiled = compile(golden.twin, techniques)
    into_db = {e.identity_id for e in compiled if e.dst == "prod-db" and e.technique == "db_login"}
    assert into_db == {"svc.payroll", "svc.backup", "adm.ops"}      # exactly the identities with login|admin on prod-db
    admin_grant = next(e for e in compiled if e.dst == "prod-db" and e.identity_id == "svc.backup" and e.src == "backup-01")
    assert "admin:prod-db" in admin_grant.grants                      # admin grant => admin capability
    assert admin_grant.evidence == "inferred"                         # weaker of edge and grant evidence


def test_cred_dump_harvests_sessions_on_src(golden, techniques):
    compiled = compile(golden.twin, techniques)
    dump = next(e for e in compiled if e.src == "jump-01" and e.technique == "cred_dump")
    assert dump.grants == {"creds:adm.ops"}
    files = next(e for e in compiled if e.src == "fileshare" and e.technique == "creds_in_files")
    assert dump.requires == {"admin:jump-01"} and files.grants == {"creds:svc.payroll"}


# --- scoped segmentation: the key story -----------------------------------------------

def _ch(src, zone, ident, kind, tech="db_login", proto="tcp", port=5432):
    return Channel(tech, src, zone, "prod-db", "prod", proto, port, ident, kind)


def test_scoped_segmentation_selector_semantics(golden):
    scoped = next(c for c in golden.catalogue if c.id == "seg_prod_db_scoped").impacts[0]
    assert affected(scoped, _ch("ws-hr", "corp", "svc.payroll", "service_account"))          # stolen creds, wrong source
    assert not affected(scoped, _ch("backup-01", "prod", "svc.backup", "service_account"))   # allowed workload
    assert not affected(scoped, _ch("payroll-api", "prod", "svc.payroll", "service_account", tech=None))
    assert affected(scoped, _ch("jump-01", "mgmt", "svc.backup", "service_account", "rdp_lateral", "rdp", 3389))


def test_scoped_segmentation_on_golden(golden, techniques):
    scoped = next(c for c in golden.catalogue if c.id == "seg_prod_db_scoped")
    twin = clone(golden.twin, add_controls=(scoped,))
    naive = compile(twin, techniques, naive=True)
    assert ("ws-hr", "prod-db", "db_login") not in _sig(naive)               # route C is dead
    assert any(e.src == "backup-01" and e.identity_id == "svc.backup" for e in naive if e.dst == "prod-db")
    assert broken_flows(twin) == ()                                            # F1, F2, F6 keep working


def test_full_segmentation_breaks_payroll(golden, techniques):
    full = next(c for c in golden.catalogue if c.id == "seg_prod_db_full")
    twin = clone(golden.twin, add_controls=(full,))
    assert [f.id for f in broken_flows(twin)] == ["F1", "F2", "F6"]
    assert not any(e.dst == "prod-db" for e in compile(twin, techniques, naive=True))
    degraded = [e for e in compile(twin, techniques) if e.dst == "prod-db"]
    assert degraded and all(abs(e.p_success - techniques[e.technique].base_success * 0.05) < 1e-9 for e in degraded)


def test_mfa_humans_vs_mfa_all(golden, techniques):
    cat = {c.id: c for c in golden.catalogue}
    humans = clone(golden.twin, add_controls=(cat["mfa_humans"],))
    assert broken_flows(humans) == ()
    comp = compile(humans, techniques)
    assert next(e for e in comp if e.identity_id == "u.dev" and e.technique == "rdp_lateral").p_success < 0.1
    assert next(e for e in comp if e.identity_id == "svc.backup" and e.technique == "db_login").p_success == 0.95
    everyone = clone(golden.twin, add_controls=(cat["mfa_all"],))
    assert [f.id for f in broken_flows(everyone)] == ["F1", "F2", "F4"]     # non-interactive identities


# --- the golden story has its four routes ---------------------------------------------

def test_golden_routes_a_b_c_d(golden, techniques):
    inv = search(compile(golden.twin, techniques), golden.agents[0], golden.twin)
    last = {tuple(e.src for e in r) for r in inv.routes}
    assert any(r[:2] == ("internet", "ws-hr") and r[-1] == "ws-hr" for r in last)         # C ends acting from ws-hr
    assert any("jump-01" in r and "backup-01" not in r for r in last)                       # A
    assert any(r[1] == "ws-dev" and "ci-runner" in r and "backup-01" in r for r in last)  # B
    assert any(r[1] == "web-dmz" and "ci-runner" in r and "backup-01" in r for r in last) # D
    mfa = clone(golden.twin, add_controls=(next(c for c in golden.catalogue if c.id == "mfa_humans"),))
    survivors = search(compile(mfa, techniques, naive=True), golden.agents[0], mfa).routes
    assert len(survivors) == 1 and survivors[0][0].dst == "web-dmz"                       # only D has no human credential
