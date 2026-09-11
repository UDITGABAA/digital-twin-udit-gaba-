"""Complete state-space attack path search (Algorithm A).

DFS over (node, frozenset(capabilities_held)).
Capabilities accumulate.
An edge is admissible from any state whose caps >= edge.requires.
Runs ONCE per twin, cached.
Hard caps: max_depth=8, max_paths=5000, raises SearchBudgetExceeded.
"""

from typing import List, Tuple, Set, Optional, Dict
from pydantic import BaseModel
from engine.models import Twin, Agent, CompiledEdge, Asset

Route = tuple[CompiledEdge, ...]


class SearchBudgetExceeded(Exception):
    """Raised when search exceeds hard-bounded limits."""
    pass


class Inventory(BaseModel, frozen=True):
    """Result of complete path search."""
    routes: tuple[Route, ...]
    naive_count: int


def search(
    edges: tuple[CompiledEdge, ...],
    agent: Agent,
    twin: Twin,
    *,
    max_depth: int = 8,
    max_paths: int = 5000
) -> Inventory:
    """Find all simple attack paths from agent's starting zones to target.
    
    Parameters
    ----------
    edges : tuple[CompiledEdge, ...]
        The compiled attack edges (the only thing search reads).
    agent : Agent
        Adversary agent configuration (start_zones, capabilities, objective, target).
    twin : Twin
        The environment twin (used to resolve start assets and crown jewels).
    max_depth : int
        Maximum number of edge hops along any path (default: 8).
    max_paths : int
        Maximum number of discovered routes before raising SearchBudgetExceeded (default: 5000).
    """
    start_assets = [
        asset for asset in twin.assets
        if asset.zone in agent.start_zones
    ]
    start_asset_ids = {asset.id for asset in start_assets}
    if not start_asset_ids:
        start_asset_ids = {z for z in agent.start_zones if any(e.src == z for e in edges)}

    discovered_routes: List[Route] = []

    def is_target_reached(current_caps: frozenset[str], last_node: str) -> bool:
        if agent.objective == "specific_target":
            target_id = agent.target
            if f"session:{target_id}" in current_caps or f"admin:{target_id}" in current_caps:
                return True
            if last_node == target_id:
                return True
            return False
        elif agent.objective == "exfil":
            return f"data:{agent.target}" in current_caps
        return False

    def dfs(
        current_node: str,
        current_caps: frozenset[str],
        current_path: List[CompiledEdge],
        visited_nodes: Set[str],
        caps_when_left_node: Dict[str, frozenset[str]],
        used_self_edges: Set[Tuple[str, str, str]],
        visited_states: Set[Tuple[str, frozenset[str]]],
    ) -> None:
        if len(discovered_routes) >= max_paths:
            raise SearchBudgetExceeded(f"Exceeded max_paths={max_paths}")

        if len(current_path) >= max_depth:
            return

        for edge in edges:
            # 1. Edge must be feasible given currently held capabilities
            if not edge.requires.issubset(current_caps):
                continue

            # 2. Progression check:
            # Either:
            # Case A: edge starts at current_node (direct progression)
            # Case B: edge starts at an earlier foothold (foothold pivot),
            #         BUT only if edge.requires demands at least one capability
            #         that was NOT held when the attacker was previously at edge.src!
            if edge.src == current_node:
                pass
            elif edge.src in caps_when_left_node:
                prior_caps = caps_when_left_node[edge.src]
                # If all requirements were already satisfied when at edge.src,
                # taking this edge now is an unneeded detour / permutation
                if edge.requires.issubset(prior_caps):
                    continue
            else:
                # Cannot act from a node we haven't visited
                continue

            if edge.src == edge.dst:
                # Host-local self-edge (cred_dump, priv_esc_local)
                self_edge_key = (edge.src, edge.dst, edge.technique)
                if self_edge_key in used_self_edges:
                    continue
                if edge.grants.issubset(current_caps):
                    continue

                next_caps = current_caps | edge.grants
                new_used_self = used_self_edges | {self_edge_key}
                new_path = current_path + [edge]

                if is_target_reached(next_caps, edge.dst):
                    discovered_routes.append(tuple(new_path))
                    if len(discovered_routes) >= max_paths:
                        raise SearchBudgetExceeded(f"Exceeded max_paths={max_paths}")
                else:
                    new_caps_left = dict(caps_when_left_node)
                    new_caps_left[edge.dst] = next_caps
                    dfs(edge.dst, next_caps, new_path, visited_nodes, new_caps_left, new_used_self, visited_states)

            else:
                # Transversal edge to new host
                if edge.dst in visited_nodes:
                    continue

                next_caps = current_caps | edge.grants
                next_state_key = (edge.dst, next_caps)
                if next_state_key in visited_states:
                    continue

                new_visited_nodes = visited_nodes | {edge.dst}
                new_path = current_path + [edge]

                if is_target_reached(next_caps, edge.dst):
                    discovered_routes.append(tuple(new_path))
                    if len(discovered_routes) >= max_paths:
                        raise SearchBudgetExceeded(f"Exceeded max_paths={max_paths}")
                else:
                    visited_states.add(next_state_key)
                    new_caps_left = dict(caps_when_left_node)
                    new_caps_left[current_node] = current_caps
                    new_caps_left[edge.dst] = next_caps
                    dfs(edge.dst, next_caps, new_path, new_visited_nodes, new_caps_left, used_self_edges, visited_states)

    # Launch DFS from each start asset
    for start_id in sorted(start_asset_ids):
        initial_caps = frozenset(agent.capabilities | {f"session:{start_id}"})
        visited_states: Set[Tuple[str, frozenset[str]]] = set()
        visited_states.add((start_id, initial_caps))
        dfs(
            current_node=start_id,
            current_caps=initial_caps,
            current_path=[],
            visited_nodes={start_id},
            caps_when_left_node={start_id: initial_caps},
            used_self_edges=set(),
            visited_states=visited_states,
        )

    # Sort routes deterministically by length then signature
    sorted_routes = sorted(
        discovered_routes,
        key=lambda r: (len(r), [(e.src, e.dst, e.technique) for e in r])
    )

    return Inventory(
        routes=tuple(sorted_routes),
        naive_count=len(sorted_routes)
    )
