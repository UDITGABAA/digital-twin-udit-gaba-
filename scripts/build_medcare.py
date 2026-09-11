"""A second scenario with a different shape, to prove the engine is not tuned to FinBank.
MedCare: a hospital. Different zones, a P1 clinical-access flow that MFA-for-everyone would
sever, a vendor VPN, and one privilege grant that is merely ASSUMED (exercises the
"cannot be determined" verdict path). Writes scenarios/medcare.json."""

import json
from pathlib import Path

from engine.models import (Agent, Asset, Control, ControlImpact, Edge, FlowSelector, Identity,
                           PrivilegeGrant, ServiceFlow, Twin, twin_hash)
from engine.scenario import Scenario

A = lambda id, name, kind, zone, crit, cj=False: Asset(id=id, name=name, kind=kind, zone=zone, criticality=crit, crown_jewel=cj)
I = lambda id, name, kind, tier: Identity(id=id, name=name, kind=kind, tier=tier)
G = lambda ident, asset, cap, ev="inventory": PrivilegeGrant(identity_id=ident, asset_id=asset, capability=cap, evidence=ev)
E = lambda src, dst, tech, ev="inventory": Edge(src=src, dst=dst, technique=tech, evidence=ev)
F = lambda id, name, src, dst, proto, port, ident, crit, ev="inventory": ServiceFlow(
    id=id, name=name, src=src, dst=dst, protocol=proto, port=port, identity_id=ident, criticality=crit, evidence=ev)
S = lambda **kw: FlowSelector(**{k: frozenset(v) for k, v in kw.items()})

assets = (
    A("internet", "Internet", "internet", "external", 1),
    A("patient-portal", "Patient portal", "server", "dmz", 3),
    A("vpn-gw", "Vendor VPN gateway", "server", "dmz", 3),
    A("ws-nurse", "Nursing station", "workstation", "clinical", 3),
    A("ws-admin", "IT admin workstation", "workstation", "corp", 2),
    A("ehr-app", "EHR application server", "server", "prod", 4),
    A("pacs-imaging", "PACS imaging server", "server", "prod", 3),
    A("lab-db", "Lab results database", "database", "prod", 4),
    A("backup-nas", "Backup NAS", "share", "mgmt", 3),
    A("ehr-db", "Patient records database", "database", "prod", 5, True),
)
identities = (
    I("nurse.k", "Nurse (K. Rao)", "user", 2),
    I("it.admin", "IT administrator", "admin", 0),
    I("vendor.pacs", "Imaging vendor engineer", "user", 2),
    I("svc.ehr", "EHR service account", "service_account", 1),
    I("svc.lab", "Lab interface account", "service_account", 1),
    I("svc.backup", "Backup service account", "service_account", 1),
)
grants = (
    G("nurse.k", "ws-nurse", "session", "observed"),
    G("nurse.k", "ehr-app", "login", "observed"),
    G("it.admin", "ws-admin", "session", "observed"),
    G("it.admin", "backup-nas", "admin"),
    G("it.admin", "ehr-db", "admin"),
    G("vendor.pacs", "pacs-imaging", "admin", "inferred"),     # vendor has remote admin - inferred from a ticket
    G("vendor.pacs", "lab-db", "login", "inferred"),
    G("svc.ehr", "ehr-app", "session"),
    G("svc.ehr", "ehr-db", "login"),
    G("svc.lab", "lab-db", "session"),
    G("svc.lab", "ehr-db", "login", "inferred"),
    G("svc.backup", "backup-nas", "session"),
    G("svc.backup", "ehr-db", "admin", "assumed"),             # nobody has checked - ASSUMED
)
edges = (
    E("internet", "patient-portal", "exploit_public_app", "observed"),
    E("patient-portal", "ehr-app", "exploit_public_app", "inferred"),
    E("internet", "vpn-gw", "exploit_public_app"),
    E("internet", "ws-nurse", "phish"),
    E("internet", "ws-admin", "phish"),
    E("vpn-gw", "pacs-imaging", "rdp_lateral"),
    E("ws-nurse", "ws-nurse", "cred_dump"),
    E("ws-nurse", "ehr-app", "rdp_lateral"),
    E("ehr-app", "ehr-app", "priv_esc_local"),
    E("ehr-app", "ehr-app", "cred_dump"),
    E("ehr-app", "ehr-db", "db_login"),
    E("ws-admin", "ws-admin", "cred_dump"),
    E("ws-admin", "backup-nas", "smb_lateral"),
    E("ws-admin", "ehr-db", "rdp_lateral"),
    E("backup-nas", "backup-nas", "cred_dump"),
    E("backup-nas", "ehr-db", "db_login"),
    E("pacs-imaging", "pacs-imaging", "cred_dump"),
    E("pacs-imaging", "lab-db", "ssh_lateral"),
    E("lab-db", "lab-db", "priv_esc_local"),
    E("lab-db", "lab-db", "cred_dump"),
    E("lab-db", "ehr-db", "db_login"),
    E("ehr-db", "internet", "exfil_c2"),
)
flows = (
    F("G1", "EHR app -> patient records", "ehr-app", "ehr-db", "tcp", 5432, "svc.ehr", 5),
    F("G2", "Lab results feed -> patient records", "lab-db", "ehr-db", "tcp", 5432, "svc.lab", 4, "inferred"),
    F("G3", "Nightly backup -> patient records", "backup-nas", "ehr-db", "tcp", 5432, "svc.backup", 3, "assumed"),
    F("G4", "Vendor remote support -> PACS", "vpn-gw", "pacs-imaging", "rdp", 3389, "vendor.pacs", 3),
    F("G5", "Clinicians -> EHR app", "ws-nurse", "ehr-app", "rdp", 3389, "nurse.k", 4, "observed"),
    F("G6", "Admin -> backup NAS", "ws-admin", "backup-nas", "smb", 445, "it.admin", 2, "observed"),
)

ehr_db = S(dst_assets={"ehr-db"})
allow_g1 = S(src_assets={"ehr-app"}, dst_assets={"ehr-db"}, protocols={"tcp"}, ports={5432}, identity_ids={"svc.ehr"})
allow_g2 = S(src_assets={"lab-db"}, dst_assets={"ehr-db"}, protocols={"tcp"}, ports={5432}, identity_ids={"svc.lab"})
allow_g3 = S(src_assets={"backup-nas"}, dst_assets={"ehr-db"}, protocols={"tcp"}, ports={5432}, identity_ids={"svc.backup"})

catalogue = (
    Control(id="seg_ehr_db_full", name="Segment patient records DB (deny all)", cost=8,
            impacts=(ControlImpact(deny=ehr_db, efficacy=0.95, breaks_flows=True),)),
    Control(id="seg_ehr_db_scoped", name="Segment patient records DB (allow EHR, lab, backup)", cost=6,
            impacts=(ControlImpact(deny=ehr_db, exceptions=(allow_g1, allow_g2, allow_g3), efficacy=0.95, breaks_flows=True),)),
    Control(id="mfa_everyone", name="MFA for every account", cost=4,
            impacts=(ControlImpact(deny=S(identity_kinds={"user", "admin"}), efficacy=0.9, breaks_flows=False),
                     ControlImpact(deny=S(identity_kinds={"service_account"}), efficacy=0.9, breaks_flows=True))),
    Control(id="mfa_admins_vendors", name="MFA for admins and vendor accounts", cost=3,
            impacts=(ControlImpact(deny=S(identity_kinds={"admin"}), efficacy=0.9, breaks_flows=False),
                     ControlImpact(deny=S(identity_ids={"vendor.pacs"}), efficacy=0.9, breaks_flows=False))),
    Control(id="patch_portal", name="Patch the patient portal", cost=2,
            impacts=(ControlImpact(deny=S(techniques={"exploit_public_app"}, dst_assets={"patient-portal"}), efficacy=0.95, breaks_flows=False),)),
    Control(id="edr_cred_dump", name="EDR credential-dump prevention", cost=5,
            impacts=(ControlImpact(deny=S(techniques={"cred_dump"}), efficacy=0.7, breaks_flows=False),)),
    Control(id="cut_vendor_vpn", name="Remove the vendor VPN", cost=1,
            impacts=(ControlImpact(deny=S(dst_assets={"pacs-imaging"}, protocols={"rdp"}), efficacy=1.0, breaks_flows=True),)),
    Control(id="isolate_backup", name="Isolate the backup NAS from the DB", cost=2,
            impacts=(ControlImpact(deny=S(src_assets={"backup-nas"}, dst_assets={"ehr-db"}), efficacy=0.95, breaks_flows=True),)),
)
agents = (
    Agent(id="external", name="External ransomware crew", start_zones=("external",), capabilities=frozenset(),
          objective="specific_target", target="ehr-db", noise_budget=3.0, skill=0.6),
    Agent(id="vendor", name="Compromised imaging vendor", start_zones=("dmz",), capabilities=frozenset({"creds:vendor.pacs"}),
          objective="specific_target", target="ehr-db", noise_budget=2.5, skill=0.5),
)

base = Twin(id="", assets=assets, identities=identities, grants=grants, edges=edges, flows=flows, controls=())
twin = base.model_copy(update={"id": twin_hash(base)})
out = Path(__file__).resolve().parent.parent / "scenarios" / "medcare.json"
out.write_text(json.dumps(Scenario(name="MedCare hospital", twin=twin, agents=agents, catalogue=catalogue).model_dump(mode="json"),
                          indent=1, sort_keys=True, default=sorted) + "\n", encoding="utf-8")
print("medcare", twin.id[:12], len(assets), "assets", len(edges), "edges", len(flows), "flows", len(catalogue), "controls")
