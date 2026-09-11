"""Data models and validation schema for Cyber Digital Twin scenarios.

Frozen v2.1 contract (CLAUDE.md §5): Asset, Identity, PrivilegeGrant, Edge, ServiceFlow,
FlowSelector, ControlImpact, Control, Agent, Twin, CompiledEdge, twin_hash.
"""

from typing import Optional, Literal
from pydantic import BaseModel
import hashlib
import json


# =====================================================================
# Frozen v2.1 Architecture Models (The Core Contract - CLAUDE.md §5)
# All collection fields are tuple[...] or frozenset[...]. Never list or set.
# =====================================================================

Evidence = Literal["observed", "inventory", "inferred", "assumed"]
# Confidence weights: observed 1.0, inventory 0.9, inferred 0.5, assumed 0.0 (= undetermined)


class Asset(BaseModel, frozen=True):
    """Represents a cyber or physical infrastructure asset."""
    id: str
    name: str
    kind: Literal["server", "workstation", "database", "cloud_role", "share", "internet"]
    zone: str                       # external | dmz | corp | prod | mgmt
    criticality: int                # 1-5
    crown_jewel: bool = False


class Identity(BaseModel, frozen=True):
    """Represents an actor or service identity within the organization."""
    id: str
    name: str
    kind: Literal["user", "admin", "service_account", "cloud_role"]
    tier: int                       # 0 = most privileged


class PrivilegeGrant(BaseModel, frozen=True):
    """Identity <-> asset privilege mapping (BloodHound HasSession/CanLogin/AdminTo)."""
    identity_id: str
    asset_id: str
    capability: Literal["session", "login", "admin"]
    evidence: Evidence = "inventory"


class Edge(BaseModel, frozen=True):
    """Reachability edge: technique is attemptable src->dst. ONE technique per edge."""
    src: str
    dst: str
    technique: str
    evidence: Evidence = "inventory"


class ServiceFlow(BaseModel, frozen=True):
    """A LEGITIMATE dependency that must keep working. A real channel, not a technique name."""
    id: str
    name: str
    src: str                        # asset ids
    dst: str
    protocol: str                   # tcp, rdp, ssh, smb, https
    port: int                       # 5432, 3389, 22, 445, 443
    identity_id: str                # what the flow authenticates as
    criticality: int                # 1-5; >=4 must never be broken
    evidence: Evidence = "inventory"


class FlowSelector(BaseModel, frozen=True):
    """Unified matcher for attack edges AND legitimate service flows. Empty field = wildcard."""
    techniques: frozenset[str] = frozenset()
    src_zones: frozenset[str] = frozenset()
    dst_zones: frozenset[str] = frozenset()
    src_assets: frozenset[str] = frozenset()
    dst_assets: frozenset[str] = frozenset()
    protocols: frozenset[str] = frozenset()
    ports: frozenset[int] = frozenset()
    identity_ids: frozenset[str] = frozenset()
    identity_kinds: frozenset[str] = frozenset()


class ControlImpact(BaseModel, frozen=True):
    """Impact of a security control on matched channels."""
    deny: FlowSelector
    exceptions: tuple[FlowSelector, ...] = ()   # affected iff deny matches AND no exception matches
    efficacy: float                             # matched attack edges: p_success *= (1 - efficacy)
    breaks_flows: bool                          # matched legitimate flows are broken


class Control(BaseModel, frozen=True):
    """Defensive security control with structured impacts."""
    id: str
    name: str
    cost: int
    impacts: tuple[ControlImpact, ...]


class Agent(BaseModel, frozen=True):
    """Adversary agent specification with defined capabilities and objectives."""
    id: str
    name: str
    start_zones: tuple[str, ...]
    capabilities: frozenset[str]    # e.g. {"creds:u.hr"}
    objective: Literal["specific_target", "exfil"]
    target: str                     # asset id
    noise_budget: float
    skill: float                    # 0-1, sharpens route choice


class Twin(BaseModel, frozen=True):
    """Complete digital twin model."""
    id: str
    assets: tuple[Asset, ...]
    identities: tuple[Identity, ...]
    grants: tuple[PrivilegeGrant, ...]
    edges: tuple[Edge, ...]
    flows: tuple[ServiceFlow, ...]
    controls: tuple[Control, ...]
    parent_id: Optional[str] = None  # lineage tracking


class CompiledEdge(BaseModel, frozen=True):
    """The ONLY thing search.py and walk.py read. Produced by rules/compile.py."""
    src: str
    dst: str
    technique: str
    identity_id: Optional[str]      # which credential this expansion uses
    requires: frozenset[str]
    grants: frozenset[str]
    p_success: float
    cost: float
    noise: float
    evidence: Evidence


def canonical_repr(val):
    """Recursively converts data to canonically sorted structures for stable hashing."""
    if isinstance(val, (frozenset, set)):
        return sorted([canonical_repr(x) for x in val])
    if isinstance(val, tuple):
        return [canonical_repr(x) for x in val]
    if isinstance(val, list):
        return [canonical_repr(x) for x in val]
    if isinstance(val, dict):
        return {k: canonical_repr(v) for k, v in sorted(val.items())}
    if isinstance(val, BaseModel):
        return canonical_repr(val.model_dump())
    return val


def twin_hash(twin: Twin) -> str:
    """Canonical SHA-256 hash of a Twin instance, independent of process set order."""
    data = twin.model_dump()
    data.pop("id", None)
    data.pop("parent_id", None)   # content-addressed: same content => same hash, whatever the lineage
    payload = canonical_repr(data)
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
