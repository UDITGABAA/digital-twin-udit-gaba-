"""Deterministic rule engine for evaluating attack path edge traversal."""

from typing import Dict, Any, List, Optional, Union
from engine.attacker import AttackerState


class RuleEngine:
    """Evaluates whether an attacker can traverse a relationship edge in the digital twin."""

    def is_control_enabled(self, ctrl: Any) -> bool:
        """Generic evaluation of whether a security control is currently active/enabled."""
        if ctrl is None:
            # Control reference not found in registry; assume active by default
            return True
        if isinstance(ctrl, bool):
            return ctrl
        if isinstance(ctrl, dict):
            if "enabled" in ctrl:
                return bool(ctrl["enabled"])
            status = str(ctrl.get("status", "active")).lower()
            return status not in ("disabled", "inactive", "off")
        
        # Check model or custom object attributes
        if hasattr(ctrl, "enabled") and ctrl.enabled is not None:
            return bool(ctrl.enabled)
        if hasattr(ctrl, "status") and ctrl.status is not None:
            return str(ctrl.status).lower() not in ("disabled", "inactive", "off")
        
        return True

    def can_traverse(
        self,
        edge_data: Dict[str, Any],
        attacker_state: AttackerState,
        controls: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Evaluate if the attacker state satisfies requirements and is not blocked by controls.

        Parameters
        ----------
        edge_data : Dict[str, Any]
            Attributes of the graph edge (requires, grants, control, etc.).
        attacker_state : AttackerState
            Current state of the attacker.
        controls : Optional[Dict[str, Any]]
            Security controls registry from the digital twin.

        Returns
        -------
        Dict[str, Any]
            Structured result containing 'allowed', 'reason',
            'acquired_capabilities', and 'acquired_privileges'.
        """
        controls = controls or {}
        requires = edge_data.get("requires") or {}
        grants = edge_data.get("grants") or {}

        # 1. Check Required Capabilities
        req_capabilities: List[str] = requires.get("capabilities") or []
        for cap in req_capabilities:
            if not attacker_state.has_capability(cap):
                return {
                    "allowed": False,
                    "reason": f"Missing required capability: {cap}",
                    "acquired_capabilities": [],
                    "acquired_privileges": []
                }

        # 2. Check Required Privileges
        req_privileges: List[str] = requires.get("privileges") or []
        for priv in req_privileges:
            if not attacker_state.has_privilege(priv):
                return {
                    "allowed": False,
                    "reason": f"Missing required privilege: {priv}",
                    "acquired_capabilities": [],
                    "acquired_privileges": []
                }

        # 3. Check Enforced Security Controls
        # Support single control ID string or list of control IDs
        ctrl_field = edge_data.get("control") or edge_data.get("controls")
        edge_controls: List[str] = []
        if isinstance(ctrl_field, str):
            edge_controls = [ctrl_field]
        elif isinstance(ctrl_field, (list, tuple, set)):
            edge_controls = [c for c in ctrl_field if c]

        for ctrl_id in edge_controls:
            ctrl_obj = controls.get(ctrl_id)
            if self.is_control_enabled(ctrl_obj):
                return {
                    "allowed": False,
                    "reason": f"Blocked by enabled control: {ctrl_id}",
                    "acquired_capabilities": [],
                    "acquired_privileges": []
                }

        # 4. Traversal Succeeded: Resolve granted capabilities & privileges
        acquired_caps = list(grants.get("capabilities") or [])
        acquired_privs = list(grants.get("privileges") or [])

        return {
            "allowed": True,
            "reason": "All traversal requirements satisfied",
            "acquired_capabilities": acquired_caps,
            "acquired_privileges": acquired_privs
        }
