"""Attacker state tracking for cyber digital twin simulations."""

from typing import Set, List, Optional, Iterable, Tuple, Any


class AttackerState:
    """Tracks the state, position, capabilities, and privileges of an attacker."""

    def __init__(
        self,
        current_node: str,
        capabilities: Optional[Iterable[str]] = None,
        privileges: Optional[Iterable[str]] = None,
        compromised_nodes: Optional[Iterable[str]] = None,
        path: Optional[List[str]] = None,
    ):
        self.current_node: str = current_node
        self.capabilities: Set[str] = set(capabilities) if capabilities else set()
        self.privileges: Set[str] = set(privileges) if privileges else set()

        # Initialize compromised nodes and path starting at initial node
        self.compromised_nodes: Set[str] = set(compromised_nodes) if compromised_nodes else {current_node}
        if current_node not in self.compromised_nodes:
            self.compromised_nodes.add(current_node)

        self.path: List[str] = list(path) if path else [current_node]

    def has_capability(self, name: str) -> bool:
        """Check if attacker possesses a specific capability."""
        return name in self.capabilities

    def has_privilege(self, name: str) -> bool:
        """Check if attacker possesses a specific privilege."""
        return name in self.privileges

    def add_capability(self, name: str) -> None:
        """Grant a new capability to the attacker."""
        self.capabilities.add(name)

    def add_privilege(self, name: str) -> None:
        """Grant a new privilege to the attacker."""
        self.privileges.add(name)

    def move_to(self, node: str) -> None:
        """Update attacker position to the target node, marking it compromised."""
        self.current_node = node
        self.compromised_nodes.add(node)
        self.path.append(node)

    def clone(self) -> "AttackerState":
        """Create an independent deep copy of the attacker state for search branching."""
        return AttackerState(
            current_node=self.current_node,
            capabilities=set(self.capabilities),
            privileges=set(self.privileges),
            compromised_nodes=set(self.compromised_nodes),
            path=list(self.path),
        )

    def state_key(self) -> Tuple[str, frozenset, frozenset]:
        """Hashable tuple representation for visited-state deduplication."""
        return (
            self.current_node,
            frozenset(self.capabilities),
            frozenset(self.privileges),
        )

    def __repr__(self) -> str:
        return (
            f"AttackerState(current_node={self.current_node!r}, "
            f"capabilities={sorted(self.capabilities)!r}, "
            f"privileges={sorted(self.privileges)!r}, "
            f"compromised_nodes={sorted(self.compromised_nodes)!r}, "
            f"path={self.path!r})"
        )
