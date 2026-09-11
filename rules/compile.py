"""Edge x declared technique x grants x controls -> CompiledEdge (CLAUDE.md §6).

Guarantee: {(src, dst, technique)} of the output is a subset of the twin's edges. Each Edge
names ONE technique; expansion is only over candidate identities from grants on dst.

A *channel* is the projection both attack edges and legitimate flows share; one matches()
serves both, which is what makes the breakage model real.
"""

from typing import NamedTuple, Optional

from engine.models import (Asset, CompiledEdge, Control, ControlImpact, Evidence, FlowSelector,
                           Identity, ServiceFlow, Twin)
from rules.loader import Technique, TechniqueTable

_EVIDENCE_RANK = {"observed": 3, "inventory": 2, "inferred": 1, "assumed": 0}


class Channel(NamedTuple):
    technique: Optional[str]
    src: str
    src_zone: str
    dst: str
    dst_zone: str
    protocol: Optional[str]
    port: Optional[int]
    identity_id: Optional[str]
    identity_kind: Optional[str]


def matches(selector: FlowSelector, ch: Channel) -> bool:
    """Every non-empty selector field must contain the channel's value."""
    pairs = (
        (selector.techniques, ch.technique), (selector.src_zones, ch.src_zone),
        (selector.dst_zones, ch.dst_zone), (selector.src_assets, ch.src),
        (selector.dst_assets, ch.dst), (selector.protocols, ch.protocol),
        (selector.ports, ch.port), (selector.identity_ids, ch.identity_id),
        (selector.identity_kinds, ch.identity_kind),
    )
    return all((not sel) or (val in sel) for sel, val in pairs)


def affected(impact: ControlImpact, ch: Channel) -> bool:
    return matches(impact.deny, ch) and not any(matches(ex, ch) for ex in impact.exceptions)


def _assets(twin: Twin) -> dict[str, Asset]:
    return {a.id: a for a in twin.assets}


def _identities(twin: Twin) -> dict[str, Identity]:
    return {i.id: i for i in twin.identities}


def flow_channel(flow: ServiceFlow, twin: Twin) -> Channel:
    assets, ids = _assets(twin), _identities(twin)
    return Channel(None, flow.src, assets[flow.src].zone, flow.dst, assets[flow.dst].zone,
                   flow.protocol, flow.port, flow.identity_id,
                   ids[flow.identity_id].kind if flow.identity_id in ids else None)


def edge_channel(edge: CompiledEdge, twin: Twin, techniques: TechniqueTable) -> Channel:
    assets, ids = _assets(twin), _identities(twin)
    t = techniques[edge.technique]
    return Channel(edge.technique, edge.src, assets[edge.src].zone, edge.dst, assets[edge.dst].zone,
                   t.channel.protocol if t.channel else None, t.channel.port if t.channel else None,
                   edge.identity_id,
                   ids[edge.identity_id].kind if edge.identity_id and edge.identity_id in ids else None)


def broken_flows(twin: Twin, controls: tuple[Control, ...] | None = None) -> tuple[ServiceFlow, ...]:
    """Flows severed by the given controls (default: the twin's own controls)."""
    controls = twin.controls if controls is None else controls
    out = []
    for flow in twin.flows:
        ch = flow_channel(flow, twin)
        if any(imp.breaks_flows and affected(imp, ch) for c in controls for imp in c.impacts):
            out.append(flow)
    return tuple(out)


def _weaker(a: Evidence, b: Evidence) -> Evidence:
    return a if _EVIDENCE_RANK[a] <= _EVIDENCE_RANK[b] else b


def _resolve(tokens: tuple[str, ...], src: str, dst: str, who: Optional[str]) -> set[str]:
    out = set()
    for tok in tokens:
        if tok in ("creds:who", "creds:sessions@src"):
            continue                      # handled by the caller
        kind, where = tok.split(":")
        out.add(f"{kind}:{src if where == 'src' else dst}")
    if who is not None:
        out.add(f"creds:{who}")
    return out


def compile(twin: Twin, techniques: TechniqueTable, *, naive: bool = False) -> tuple[CompiledEdge, ...]:
    """naive=True: channels a control affects are DROPPED (perfect control, passive attacker —
    the industry assumption behind the path count). naive=False: p_success *= (1 - efficacy)."""
    sessions_on: dict[str, list] = {}
    login_on: dict[str, list] = {}
    for g in twin.grants:
        if g.capability == "session":
            sessions_on.setdefault(g.asset_id, []).append(g)
        else:
            login_on.setdefault(g.asset_id, []).append(g)

    expanded: list[CompiledEdge] = []
    for edge in twin.edges:
        t: Technique = techniques[edge.technique]
        grants_sessions = "creds:sessions@src" in t.grants
        harvested = {f"creds:{g.identity_id}" for g in sessions_on.get(edge.src, ())} if grants_sessions else set()
        harvest_ev = min((g.evidence for g in sessions_on.get(edge.src, ())), key=_EVIDENCE_RANK.get, default="observed")

        if "creds:who" in t.requires:
            for g in login_on.get(edge.dst, ()):
                grants = _resolve(t.grants, edge.src, edge.dst, None) | harvested
                if g.capability == "admin":
                    grants.add(f"admin:{edge.dst}")
                expanded.append(CompiledEdge(
                    src=edge.src, dst=edge.dst, technique=edge.technique, identity_id=g.identity_id,
                    requires=frozenset(_resolve(t.requires, edge.src, edge.dst, g.identity_id)),
                    grants=frozenset(grants),
                    p_success=t.base_success, cost=t.cost, noise=t.noise,
                    evidence=_weaker(edge.evidence, g.evidence)))
        else:
            expanded.append(CompiledEdge(
                src=edge.src, dst=edge.dst, technique=edge.technique, identity_id=None,
                requires=frozenset(_resolve(t.requires, edge.src, edge.dst, None)),
                grants=frozenset(_resolve(t.grants, edge.src, edge.dst, None) | harvested),
                p_success=t.base_success, cost=t.cost, noise=t.noise,
                evidence=_weaker(edge.evidence, harvest_ev) if grants_sessions else edge.evidence))

    out: list[CompiledEdge] = []
    for ce in expanded:
        ch = edge_channel(ce, twin, techniques)
        p = ce.p_success
        dropped = False
        for c in twin.controls:
            for imp in c.impacts:
                if affected(imp, ch):
                    if naive:
                        dropped = True
                    else:
                        p *= (1.0 - imp.efficacy)
        if dropped:
            continue
        out.append(ce if p == ce.p_success else ce.model_copy(update={"p_success": p}))
    return tuple(out)


__all__ = ["Channel", "matches", "affected", "flow_channel", "edge_channel", "broken_flows", "compile"]
