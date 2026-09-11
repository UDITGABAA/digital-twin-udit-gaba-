"""Unit tests for AttackerState tracking, capability detection, and cloning."""

import pytest
from engine.attacker import AttackerState


def test_attacker_state_creation():
    state = AttackerState(
        current_node="corp-workstation",
        capabilities=["basic_user", "admin_credentials"],
        privileges=["internal_read"]
    )
    assert state.current_node == "corp-workstation"
    assert "corp-workstation" in state.compromised_nodes
    assert state.path == ["corp-workstation"]
    assert len(state.capabilities) == 2
    assert len(state.privileges) == 1


def test_capability_detection():
    state = AttackerState(
        current_node="corp-workstation",
        capabilities=["network_scan", "admin_credentials"]
    )
    assert state.has_capability("admin_credentials") is True
    assert state.has_capability("domain_admin") is False


def test_privilege_detection():
    state = AttackerState(
        current_node="corp-workstation",
        privileges=["infrastructure_admin"]
    )
    assert state.has_privilege("infrastructure_admin") is True
    assert state.has_privilege("root_access") is False


def test_capability_and_privilege_acquisition():
    state = AttackerState(current_node="corp-workstation")
    assert state.has_capability("jumpbox_access") is False
    assert state.has_privilege("backup_operator") is False

    state.add_capability("jumpbox_access")
    state.add_privilege("backup_operator")

    assert state.has_capability("jumpbox_access") is True
    assert state.has_privilege("backup_operator") is True


def test_move_to_updates_path_and_compromised():
    state = AttackerState(current_node="corp-workstation")
    state.move_to("admin-jumpbox")

    assert state.current_node == "admin-jumpbox"
    assert state.path == ["corp-workstation", "admin-jumpbox"]
    assert "corp-workstation" in state.compromised_nodes
    assert "admin-jumpbox" in state.compromised_nodes


def test_state_cloning_prevents_branch_mutation():
    original = AttackerState(
        current_node="corp-workstation",
        capabilities=["admin_credentials"],
        privileges=["internal_read"]
    )
    clone = original.clone()

    # Mutate the clone
    clone.move_to("admin-jumpbox")
    clone.add_capability("jumpbox_access")
    clone.add_privilege("infrastructure_admin")

    # Verify original remains completely untouched
    assert original.current_node == "corp-workstation"
    assert original.path == ["corp-workstation"]
    assert "admin-jumpbox" not in original.compromised_nodes
    assert not original.has_capability("jumpbox_access")
    assert not original.has_privilege("infrastructure_admin")


def test_state_key_hashability():
    state = AttackerState(
        current_node="corp-workstation",
        capabilities=["admin_credentials"],
        privileges=["read"]
    )
    key = state.state_key()
    assert isinstance(key, tuple)
    assert key[0] == "corp-workstation"
    
    # Can be placed in a set
    visited = {key}
    assert state.clone().state_key() in visited
