"""Unit tests for RuleEngine evaluation of traversal, capabilities, privileges, and controls."""

import pytest
from engine.attacker import AttackerState
from engine.rules import RuleEngine
from engine.models import ControlModel


@pytest.fixture
def rule_engine() -> RuleEngine:
    return RuleEngine()


def test_successful_traversal_when_requirements_satisfied(rule_engine):
    edge_data = {
        "requires": {
            "capabilities": ["admin_credentials"],
            "privileges": ["infrastructure_admin"]
        },
        "grants": {
            "capabilities": ["jumpbox_access"],
            "privileges": ["shell_access"]
        },
        "control": None
    }
    state = AttackerState(
        current_node="corp-workstation",
        capabilities=["admin_credentials"],
        privileges=["infrastructure_admin"]
    )
    result = rule_engine.can_traverse(edge_data, state, controls={})
    assert result["allowed"] is True
    assert "All traversal requirements satisfied" in result["reason"]
    assert result["acquired_capabilities"] == ["jumpbox_access"]
    assert result["acquired_privileges"] == ["shell_access"]


def test_missing_capability_blocks_traversal(rule_engine):
    edge_data = {
        "requires": {
            "capabilities": ["admin_credentials"],
            "privileges": []
        },
        "grants": {},
        "control": None
    }
    state = AttackerState(current_node="corp-workstation", capabilities=[])
    result = rule_engine.can_traverse(edge_data, state, controls={})
    assert result["allowed"] is False
    assert "Missing required capability: admin_credentials" in result["reason"]
    assert result["acquired_capabilities"] == []


def test_missing_privilege_blocks_traversal(rule_engine):
    edge_data = {
        "requires": {
            "capabilities": ["admin_credentials"],
            "privileges": ["infrastructure_admin"]
        },
        "grants": {},
        "control": None
    }
    state = AttackerState(
        current_node="corp-workstation",
        capabilities=["admin_credentials"],
        privileges=[]
    )
    result = rule_engine.can_traverse(edge_data, state, controls={})
    assert result["allowed"] is False
    assert "Missing required privilege: infrastructure_admin" in result["reason"]


def test_enabled_control_blocks_traversal(rule_engine):
    edge_data = {
        "requires": {
            "capabilities": ["admin_credentials"],
            "privileges": ["infrastructure_admin"]
        },
        "grants": {"capabilities": ["jumpbox_access"]},
        "control": "ctrl-mfa"
    }
    state = AttackerState(
        current_node="corp-workstation",
        capabilities=["admin_credentials"],
        privileges=["infrastructure_admin"]
    )
    controls = {
        "ctrl-mfa": ControlModel(
            id="ctrl-mfa",
            name="MFA",
            type="authentication",
            status="active",
            enabled=True
        )
    }
    result = rule_engine.can_traverse(edge_data, state, controls=controls)
    assert result["allowed"] is False
    assert "Blocked by enabled control: ctrl-mfa" in result["reason"]


def test_disabled_control_permits_traversal_when_requirements_met(rule_engine):
    edge_data = {
        "requires": {
            "capabilities": ["admin_credentials"],
            "privileges": ["infrastructure_admin"]
        },
        "grants": {"capabilities": ["jumpbox_access"]},
        "control": "ctrl-mfa"
    }
    state = AttackerState(
        current_node="corp-workstation",
        capabilities=["admin_credentials"],
        privileges=["infrastructure_admin"]
    )
    # Control explicitly disabled
    controls = {
        "ctrl-mfa": ControlModel(
            id="ctrl-mfa",
            name="MFA",
            type="authentication",
            status="disabled",
            enabled=False
        )
    }
    result = rule_engine.can_traverse(edge_data, state, controls=controls)
    assert result["allowed"] is True
    assert result["acquired_capabilities"] == ["jumpbox_access"]


@pytest.mark.parametrize("ctrl_id", ["ctrl-waf", "ctrl-edr", "ctrl-db-enc"])
def test_generic_control_handling_for_different_controls(rule_engine, ctrl_id):
    edge_data = {
        "requires": {},
        "grants": {},
        "control": ctrl_id
    }
    state = AttackerState(current_node="nodeA")
    
    # When enabled
    controls_active = {
        ctrl_id: ControlModel(id=ctrl_id, name="Test Control", type="defense", status="active", enabled=True)
    }
    res_blocked = rule_engine.can_traverse(edge_data, state, controls_active)
    assert res_blocked["allowed"] is False
    assert f"Blocked by enabled control: {ctrl_id}" in res_blocked["reason"]

    # When disabled
    controls_disabled = {
        ctrl_id: ControlModel(id=ctrl_id, name="Test Control", type="defense", status="inactive", enabled=False)
    }
    res_allowed = rule_engine.can_traverse(edge_data, state, controls_disabled)
    assert res_allowed["allowed"] is True
