"""Stateful attack path discovery engine for Cyber Digital Twins."""

from collections import deque
from typing import Dict, Any, List, Optional, Iterable, Tuple, Set

from engine.twin import CyberDigitalTwin
from engine.rules import RuleEngine
from engine.attacker import AttackerState


class StatefulAttackEngine:
    """Explores attack paths on a Cyber Digital Twin guided by attacker state and security rules."""

    def __init__(self, digital_twin: CyberDigitalTwin, rule_engine: Optional[RuleEngine] = None):
        self.digital_twin = digital_twin
        self.rule_engine = rule_engine or RuleEngine()

    def find_attack_paths(
        self,
        initial_node: str,
        target_node: str,
        initial_capabilities: Optional[Iterable[str]] = None,
        initial_privileges: Optional[Iterable[str]] = None,
        max_depth: int = 20,
    ) -> Dict[str, Any]:
        """Search for valid attack paths from initial_node to target_node.

        Parameters
        ----------
        initial_node : str
            Initial foothold node name or ID.
        target_node : str
            Target asset or identity node name or ID.
        initial_capabilities : Optional[Iterable[str]]
            Initial capabilities possessed by the attacker.
        initial_privileges : Optional[Iterable[str]]
            Initial privileges possessed by the attacker.
        max_depth : int
            Maximum number of hops allowed in path exploration to avoid unbounded search.

        Returns
        -------
        Dict[str, Any]
            Structured result containing target_reachable, path_count, paths, and blocked_steps.
        """
        # Resolve friendly node names to exact graph node IDs
        start_id = self.digital_twin.resolve_node_id(initial_node)
        target_id = self.digital_twin.resolve_node_id(target_node)

        graph = self.digital_twin.graph

        if start_id not in graph:
            return {
                "target_reachable": False,
                "path_count": 0,
                "paths": [],
                "blocked_steps": [
                    {
                        "from": initial_node,
                        "to": None,
                        "allowed": False,
                        "reason": f"Initial node '{initial_node}' does not exist in graph"
                    }
                ]
            }

        if target_id not in graph:
            return {
                "target_reachable": False,
                "path_count": 0,
                "paths": [],
                "blocked_steps": [
                    {
                        "from": None,
                        "to": target_node,
                        "allowed": False,
                        "reason": f"Target node '{target_node}' does not exist in graph"
                    }
                ]
            }

        initial_caps = set(initial_capabilities) if initial_capabilities else set()
        initial_privs = set(initial_privileges) if initial_privileges else set()

        # Handle trivial case where initial_node is already target_node
        if start_id == target_id:
            return {
                "target_reachable": True,
                "path_count": 1,
                "paths": [
                    {
                        "nodes": [start_id],
                        "hops": 0,
                        "capabilities_acquired": [],
                        "privileges_acquired": [],
                        "steps": []
                    }
                ],
                "blocked_steps": []
            }

        root_state = AttackerState(
            current_node=start_id,
            capabilities=initial_caps,
            privileges=initial_privs
        )

        discovered_paths: List[Dict[str, Any]] = []
        blocked_steps: List[Dict[str, Any]] = []
        seen_blocked: Set[Tuple[str, str, str]] = set()

        # Visited tracking per (node, frozenset(capabilities), frozenset(privileges))
        visited_states: Set[Tuple[str, frozenset, frozenset]] = set()
        visited_states.add(root_state.state_key())

        # Queue items: (current_attacker_state, step_records_list)
        queue: deque = deque([(root_state, [])])

        while queue:
            current_state, steps = queue.popleft()
            curr_node = current_state.current_node

            if len(steps) >= max_depth:
                continue

            for neighbor in graph.successors(curr_node):
                edge_data = graph.get_edge_data(curr_node, neighbor) or {}
                traversal_result = self.rule_engine.can_traverse(
                    edge_data=edge_data,
                    attacker_state=current_state,
                    controls=self.digital_twin.controls
                )

                if not traversal_result["allowed"]:
                    reason = traversal_result["reason"]
                    block_key = (curr_node, neighbor, reason)
                    if block_key not in seen_blocked:
                        seen_blocked.add(block_key)
                        blocked_steps.append({
                            "from": curr_node,
                            "to": neighbor,
                            "allowed": False,
                            "reason": reason
                        })
                    continue

                # Traversal allowed: clone state to prevent branch contamination
                next_state = current_state.clone()
                next_state.move_to(neighbor)

                # Acquire new capabilities and privileges granted by traversal
                for cap in traversal_result.get("acquired_capabilities") or []:
                    next_state.add_capability(cap)
                for priv in traversal_result.get("acquired_privileges") or []:
                    next_state.add_privilege(priv)

                step_record = {
                    "from": curr_node,
                    "to": neighbor,
                    "allowed": True,
                    "reason": traversal_result["reason"]
                }
                new_steps = steps + [step_record]

                if neighbor == target_id:
                    # Target reached!
                    acquired_caps = sorted(list(next_state.capabilities - initial_caps))
                    acquired_privs = sorted(list(next_state.privileges - initial_privs))
                    discovered_paths.append({
                        "nodes": list(next_state.path),
                        "hops": len(next_state.path) - 1,
                        "capabilities_acquired": acquired_caps,
                        "privileges_acquired": acquired_privs,
                        "steps": new_steps
                    })
                else:
                    state_key = next_state.state_key()
                    if state_key not in visited_states:
                        visited_states.add(state_key)
                        queue.append((next_state, new_steps))

        return {
            "target_reachable": len(discovered_paths) > 0,
            "path_count": len(discovered_paths),
            "paths": discovered_paths,
            "blocked_steps": blocked_steps
        }
