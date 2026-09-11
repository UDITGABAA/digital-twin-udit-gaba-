"""Builds scenarios/golden.json (FinBank) and golden_sync.json from the story in
docs/IMPLEMENTATION_PLAN.md. Re-run after editing; never hand-edit the JSON."""

import json
from pathlib import Path

from engine.models import (Agent, Asset, Control, ControlImpact, Edge, FlowSelector, Identity,
                           PrivilegeGrant, ServiceFlow, Twin, twin_hash)
from engine.scenario import Scenario
from engine.twin import clone

A = lambda id, name, kind, zone, crit, cj=False: Asset(id=id, name=name, kind=kind, zone=zone, criticality=crit, crown_jewel=cj)
I = lambda id, name, kind, tier: Identity(id=id, name=name, kind=kind, tier=tier)
G = lambda ident, asset, cap, ev="inventory": PrivilegeGrant(identity_id=ident, asset_id=asset, capability=cap, evidence=ev)
E = lambda src, dst, tech, ev="inventory": Edge(src=src, dst=dst, technique=tech, evidence=ev)
F = lambda id, name, src, dst, proto, port, ident, crit, ev="inventory": ServiceFlow(
    id=id, name=name, src=src, dst=dst, protocol=proto, port=port, identity_id=ident, criticality=crit, evidence=ev)
S = lambda **kw: FlowSelector(**{k: frozenset(v) for k, v in kw.items()})

assets = (
    A("internet", "Internet", "internet", "external", 1),
    A("web-dmz", "Customer web portal", "server", "dmz", 3),
    A("ws-dev", "Developer workstation", "workstation", "corp", 2),
    A("ws-hr", "HR workstation", "workstation", "corp", 2),
    A("fileshare", "HR file share", "share", "corp", 2),
    A("ci-runner", "CI runner", "server", "corp", 3),
    A("jump-01", "Ops jump host", "server", "mgmt", 3),
    A("payroll-api", "Payroll API", "server", "prod", 4),
    A("backup-01", "Backup server", "server", "prod", 3),
    A("prod-db", "Core banking database", "database", "prod", 5, True),
)
identities = (
    I("u.dev", "Dev user (alice)", "user", 2),
    I("u.hr", "HR user (bob)", "user", 2),
    I("adm.ops", "Ops administrator", "admin", 0),
    I("svc.payroll", "Payroll service account", "service_account", 1),
    I("svc.backup", "Backup service account", "service_account", 1),
    I("svc.ci", "CI service account", "service_account", 1),
)
grants = (
    G("u.dev", "ws-dev", "session", "observed"),
    G("u.dev", "jump-01", "login"),
    G("u.dev", "ci-runner", "admin", "inferred"),          # developers are admin on CI - inferred
    G("u.hr", "ws-hr", "session", "observed"),
    G("u.hr", "fileshare", "login"),
    G("adm.ops", "jump-01", "session", "observed"),
    G("adm.ops", "prod-db", "admin"),
    G("adm.ops", "backup-01", "admin"),
    G("svc.payroll", "payroll-api", "session"),
    G("svc.payroll", "prod-db", "login"),
    G("svc.payroll", "fileshare", "session", "inferred"),  # a credential file left on the share
    G("svc.backup", "backup-01", "session"),
    G("svc.backup", "prod-db", "admin", "inferred"),       # THE named unknown
    G("svc.ci", "ci-runner", "session"),
    G("svc.ci", "backup-01", "admin"),                     # backup agent runs privileged
)
edges = (
    # footholds
    E("internet", "ws-dev", "phish"), E("internet", "ws-hr", "phish"),
    E("internet", "web-dmz", "exploit_public_app", "observed"),
    E("web-dmz", "ci-runner", "exploit_public_app", "inferred"),   # CI webhook reachable from the portal
    # host-local
    E("ws-dev", "ws-dev", "cred_dump"), E("ws-hr", "ws-hr", "cred_dump"),
    E("jump-01", "jump-01", "priv_esc_local"), E("jump-01", "jump-01", "cred_dump"),
    E("ci-runner", "ci-runner", "priv_esc_local"), E("ci-runner", "ci-runner", "cred_dump"),
    E("backup-01", "backup-01", "cred_dump"),
    E("fileshare", "fileshare", "creds_in_files"),
    # lateral
    E("ws-dev", "jump-01", "rdp_lateral"), E("ws-dev", "ci-runner", "ssh_lateral"),
    E("ws-hr", "fileshare", "smb_lateral"),
    E("ci-runner", "backup-01", "ssh_lateral"),
    E("jump-01", "prod-db", "rdp_lateral"), E("jump-01", "backup-01", "rdp_lateral"),
    E("backup-01", "prod-db", "db_login"), E("ws-hr", "prod-db", "db_login"),
    E("payroll-api", "prod-db", "db_login"),
    E("prod-db", "internet", "exfil_c2"),
)
flows = (
    F("F1", "Payroll API -> core DB", "payroll-api", "prod-db", "tcp", 5432, "svc.payroll", 5),
    F("F2", "Nightly backup -> core DB", "backup-01", "prod-db", "tcp", 5432, "svc.backup", 4, "inferred"),
    F("F3", "Dev RDP to jump host", "ws-dev", "jump-01", "rdp", 3389, "u.dev", 2, "observed"),
    F("F4", "CI deploy to backup server", "ci-runner", "backup-01", "ssh", 22, "svc.ci", 3),
    F("F5", "HR file share access", "ws-hr", "fileshare", "smb", 445, "u.hr", 2, "observed"),
    F("F6", "Ops maintenance RDP to DB host", "jump-01", "prod-db", "rdp", 3389, "adm.ops", 3, "observed"),
)

prod_db = S(dst_assets={"prod-db"})
allow_f1 = S(src_assets={"payroll-api"}, dst_assets={"prod-db"}, protocols={"tcp"}, ports={5432}, identity_ids={"svc.payroll"})
allow_f2 = S(src_assets={"backup-01"}, dst_assets={"prod-db"}, protocols={"tcp"}, ports={5432}, identity_ids={"svc.backup"})
allow_f6 = S(src_assets={"jump-01"}, dst_assets={"prod-db"}, protocols={"rdp"}, ports={3389}, identity_ids={"adm.ops"})
humans = S(identity_kinds={"user", "admin"})
svc = S(identity_kinds={"service_account"})

catalogue = (
    Control(id="seg_prod_db_full", name="Segment prod-db (deny all inbound)", cost=8,
            impacts=(ControlImpact(deny=prod_db, efficacy=0.95, breaks_flows=True),)),
    Control(id="seg_prod_db_scoped", name="Segment prod-db (allow payroll, backup, ops)", cost=6,
            impacts=(ControlImpact(deny=prod_db, exceptions=(allow_f1, allow_f2, allow_f6), efficacy=0.95, breaks_flows=True),)),
    Control(id="mfa_humans", name="MFA for user and admin accounts", cost=3,
            impacts=(ControlImpact(deny=humans, efficacy=0.9, breaks_flows=False),)),
    # interactive MFA is incompatible with non-interactive service identities -> those flows break
    Control(id="mfa_all", name="MFA for every account incl. service accounts", cost=4,
            impacts=(ControlImpact(deny=humans, efficacy=0.9, breaks_flows=False),
                     ControlImpact(deny=svc, efficacy=0.9, breaks_flows=True))),
    Control(id="edr_cred_dump", name="EDR with credential-dump prevention", cost=5,
            impacts=(ControlImpact(deny=S(techniques={"cred_dump"}), efficacy=0.7, breaks_flows=False),)),
    Control(id="patch_web_dmz", name="Patch the customer web portal", cost=2,
            impacts=(ControlImpact(deny=S(techniques={"exploit_public_app"}, dst_assets={"web-dmz"}), efficacy=0.95, breaks_flows=False),)),
    Control(id="jump_hardening", name="Harden the jump host (no local priv-esc)", cost=2,
            impacts=(ControlImpact(deny=S(techniques={"priv_esc_local"}, dst_assets={"jump-01"}), efficacy=0.8, breaks_flows=False),)),
    Control(id="disable_smb_share", name="Decommission the HR SMB share", cost=1,
            impacts=(ControlImpact(deny=S(dst_assets={"fileshare"}, protocols={"smb"}), efficacy=1.0, breaks_flows=True),)),
)
agents = (
    Agent(id="external", name="External criminal crew", start_zones=("external",), capabilities=frozenset(),
          objective="specific_target", target="prod-db", noise_budget=3.0, skill=0.7),
    Agent(id="insider", name="Disgruntled HR insider", start_zones=("corp",), capabilities=frozenset({"creds:u.hr"}),
          objective="specific_target", target="prod-db", noise_budget=2.0, skill=0.4),
)

base = Twin(id="", assets=assets, identities=identities, grants=grants, edges=edges, flows=flows, controls=())
golden = base.model_copy(update={"id": twin_hash(base)})

contractor = I("contractor", "Contractor (temp admin)", "user", 2)
sync_twin = clone(golden, add_grants=(G("contractor", "ws-dev", "session", "observed"),
                                      G("contractor", "jump-01", "admin", "observed")))
sync_twin = sync_twin.model_copy(update={"identities": identities + (contractor,)})
sync_twin = sync_twin.model_copy(update={"id": twin_hash(sync_twin)})

out = Path(__file__).resolve().parent.parent / "scenarios"
for name, twin in (("golden", golden), ("golden_sync", sync_twin)):
    sc = Scenario(twin=twin, agents=agents, catalogue=catalogue)
    (out / f"{name}.json").write_text(json.dumps(sc.model_dump(mode="json"), indent=1, sort_keys=True, default=sorted) + "\n", encoding="utf-8")
    print(name, twin.id[:12], len(twin.assets), "assets", len(twin.edges), "edges", len(twin.flows), "flows", len(catalogue), "controls")
