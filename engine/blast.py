"""Blast radius calculation with realistic credential expansion vs upper-bound topological reachability.

Track A component implementing blast_radius() according to docs/INTERFACES.md:
- upper_bound: NetworkX descendants (pure topology, ignores credentials and controls)
- reachable: Real reachable assets with credential and privilege accumulation
- crown_jewels_hit: Crown jewels intersected with reachable
"""

from typing import Set, Tuple
import networkx as nx
from pydantic import BaseModel

from engine.models import CompiledEdge, Twin


class Blast(BaseModel, frozen=True):
    """Blast radius result comparing realistic credential reachability against topological upper bound."""
    asset_id: str
    reachable: tuple[str, ...]
    crown_jewels_hit: tuple[str, ...]
    upper_bound: tuple[str, ...]                                # nx.descendants, ignores credentials


def blast_radius(
    twin: Twin,
    edges: tuple[CompiledEdge, ...],
    asset_id: str
) -> Blast:
    """Compute compromised asset blast radius.
    
    Parameters
    ----------
    twin : Twin
        The digital twin containing asset metadata and privilege grants.
    edges : tuple[CompiledEdge, ...]
        Compiled attack edges.
    asset_id : str
        ID of the initial compromised asset.
    """
    # 1. Topological upper bound using nx.descendants (ignoring credentials)
    digraph = nx.DiGraph()
    for asset in twin.assets:
        digraph.add_node(asset.id)
    for edge in edges:
        if edge.src != edge.dst:
            digraph.add_edge(edge.src, edge.dst)

    if digraph.has_node(asset_id):
        descendants = nx.descendants(digraph, asset_id)
        upper_bound = tuple(sorted(descendants))
    else:
        upper_bound = ()

    # 2. Realistic credential-aware reachable assets
    reached_assets: Set[str] = {asset_id}
    held_caps: Set[str] = {f"session:{asset_id}"}

    # Seed grants and credentials present on initial asset
    for grant in twin.grants:
        if grant.asset_id == asset_id:
            held_caps.add(f"{grant.capability}:{asset_id}")
            held_caps.add(f"creds:{grant.identity_id}")

    changed = True
    while changed:
        changed = False
        for edge in edges:
            if edge.src in reached_assets and edge.requires.issubset(held_caps):
                if edge.dst not in reached_assets:
                    reached_assets.add(edge.dst)
                    changed = True

                for grant_cap in edge.grants:
                    if grant_cap not in held_caps:
                        held_caps.add(grant_cap)
                        changed = True

                # If administrator access is acquired on edge.dst, harvest sessions/credentials
                if f"admin:{edge.dst}" in held_caps:
                    for grant in twin.grants:
                        if grant.asset_id == edge.dst:
                            cred_cap = f"creds:{grant.identity_id}"
                            if cred_cap not in held_caps:
                                held_caps.add(cred_cap)
                                changed = True

    reachable = tuple(sorted(a for a in reached_assets if a != asset_id))

    # 3. Crown jewels hit
    crown_jewel_ids = {a.id for a in twin.assets if a.crown_jewel}
    crown_jewels_hit = tuple(sorted(a for a in reachable if a in crown_jewel_ids))

    return Blast(
        asset_id=asset_id,
        reachable=reachable,
        crown_jewels_hit=crown_jewels_hit,
        upper_bound=upper_bound,
    )


__all__ = [
    "Blast",
    "blast_radius",
]
