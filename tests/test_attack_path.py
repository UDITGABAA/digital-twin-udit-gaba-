"""Unit tests for StatefulAttackEngine discovery, cycles, branching, and what-if controls."""

import pytest
import networkx as nx
from pathlib import Path

from engine.twin import FinBankTwin, CyberDigitalTwin
from engine.rules import RuleEngine
from engine.attack_path import StatefulAttackEngine
from engine.models import ScenarioModel, AssetModel, RelationshipModel, ControlModel


@pytest.fixture
def scenario_path() -> Path:
    return Path("scenarios/scenario.json")


@pytest.fixture
def finbank_twin(scenario_path) -> FinBankTwin:
    return FinBankTwin.from_file(scenario_path)


def test_successful_multi_hop_attack_path_when_controls_permit(finbank_twin):
    """Test multi-hop traversal: corp-workstation -> admin-jumpbox -> backup-vault."""
    engine = StatefulAttackEngine(finbank_twin)

    # In-memory disable ctrl-mfa to simulate bypass/permitted traversal
    finbank_twin.controls["ctrl-mfa"].enabled = False
    finbank_twin.controls["ctrl-mfa"].status = "disabled"

    result = engine.find_attack_paths(
        initial_node="corp-workstation",
        target_node="backup-vault",
        initial_capabilities=["admin_credentials"],
        initial_privileges=["infrastructure_admin"]
    )

    assert result["target_reachable"] is True
    assert result["path_count"] >= 1

    primary_path = result["paths"][0]
    # Check nodes in path
    assert "asset-corp-workstation" in primary_path["nodes"][0]
    assert "asset-admin-jumpbox" in primary_path["nodes"][1]
    assert "asset-backup-vault" in primary_path["nodes"][2]
    assert primary_path["hops"] == 2

    # Check acquired capabilities along the path
    assert "jumpbox_access" in primary_path["capabilities_acquired"]
    assert len(primary_path["steps"]) == 2


def test_target_unreachable_when_required_control_blocks(finbank_twin):
    """Test that active MFA blocks the path at corp-workstation -> admin-jumpbox."""
    engine = StatefulAttackEngine(finbank_twin)

    # Ensure MFA is actively enabled
    finbank_twin.controls["ctrl-mfa"].enabled = True
    finbank_twin.controls["ctrl-mfa"].status = "active"

    result = engine.find_attack_paths(
        initial_node="corp-workstation",
        target_node="backup-vault",
        initial_capabilities=["admin_credentials"],
        initial_privileges=["infrastructure_admin"]
    )

    assert result["target_reachable"] is False
    assert result["path_count"] == 0
    assert len(result["paths"]) == 0

    # Verify blocked steps indicate ctrl-mfa
    blocked = result["blocked_steps"]
    assert len(blocked) >= 1
    assert any("ctrl-mfa" in b["reason"] for b in blocked)


def test_control_what_if_mfa_in_memory_simulation(finbank_twin):
    """Verify in-memory What-If analysis toggles reachability without modifying disk files."""
    engine = StatefulAttackEngine(finbank_twin)

    # 1. First run: MFA OFF
    finbank_twin.controls["ctrl-mfa"].enabled = False
    finbank_twin.controls["ctrl-mfa"].status = "disabled"

    res_off = engine.find_attack_paths(
        initial_node="corp-workstation",
        target_node="backup-vault",
        initial_capabilities=["admin_credentials"],
        initial_privileges=["infrastructure_admin"]
    )
    assert res_off["target_reachable"] is True
    assert res_off["path_count"] == 1

    # 2. Second run: MFA ON
    finbank_twin.controls["ctrl-mfa"].enabled = True
    finbank_twin.controls["ctrl-mfa"].status = "active"

    res_on = engine.find_attack_paths(
        initial_node="corp-workstation",
        target_node="backup-vault",
        initial_capabilities=["admin_credentials"],
        initial_privileges=["infrastructure_admin"]
    )
    assert res_on["target_reachable"] is False
    assert res_on["path_count"] == 0


def test_missing_credentials_blocks_path_even_if_control_disabled(finbank_twin):
    """Verify that even with MFA disabled, missing admin credentials blocks access."""
    engine = StatefulAttackEngine(finbank_twin)

    finbank_twin.controls["ctrl-mfa"].enabled = False
    finbank_twin.controls["ctrl-mfa"].status = "disabled"

    # Attacker lacks admin_credentials
    result = engine.find_attack_paths(
        initial_node="corp-workstation",
        target_node="backup-vault",
        initial_capabilities=["basic_user"],
        initial_privileges=["infrastructure_admin"]
    )

    assert result["target_reachable"] is False
    assert any("Missing required capability: admin_credentials" in b["reason"] for b in result["blocked_steps"])


def test_cycle_does_not_cause_infinite_loop():
    """Verify state-based visited tracking stops infinite loop on cyclic topology."""
    scenario = ScenarioModel(
        scenario_id="cyclic-test",
        name="Cyclic Twin",
        assets=[
            AssetModel(id="nodeA", name="Node A", type="server", zone="lan"),
            AssetModel(id="nodeB", name="Node B", type="server", zone="lan"),
            AssetModel(id="nodeC", name="Node C", type="server", zone="lan"),
        ],
        relationships=[
            # Cycle between A and B
            RelationshipModel(id="r1", source="nodeA", target="nodeB", relation_type="CONNECTS"),
            RelationshipModel(id="r2", source="nodeB", target="nodeA", relation_type="CONNECTS"),
            # B also connects to C
            RelationshipModel(id="r3", source="nodeB", target="nodeC", relation_type="CONNECTS"),
        ]
    )
    twin = CyberDigitalTwin(scenario)
    engine = StatefulAttackEngine(twin)

    # Search path from nodeA to nodeC
    result = engine.find_attack_paths(initial_node="nodeA", target_node="nodeC")
    assert result["target_reachable"] is True
    assert len(result["paths"]) == 1
    assert result["paths"][0]["nodes"] == ["nodeA", "nodeB", "nodeC"]


def test_multiple_possible_paths_returned():
    """Verify that multiple valid alternative paths are discovered."""
    scenario = ScenarioModel(
        scenario_id="multi-path-test",
        name="Multi Path Twin",
        assets=[
            AssetModel(id="start", name="Start", type="server", zone="lan"),
            AssetModel(id="path1_mid", name="Mid 1", type="server", zone="lan"),
            AssetModel(id="path2_mid", name="Mid 2", type="server", zone="lan"),
            AssetModel(id="target", name="Target", type="server", zone="lan"),
        ],
        relationships=[
            RelationshipModel(id="r1", source="start", target="path1_mid", relation_type="CONNECTS"),
            RelationshipModel(id="r2", source="path1_mid", target="target", relation_type="CONNECTS"),
            RelationshipModel(id="r3", source="start", target="path2_mid", relation_type="CONNECTS"),
            RelationshipModel(id="r4", source="path2_mid", target="target", relation_type="CONNECTS"),
        ]
    )
    twin = CyberDigitalTwin(scenario)
    engine = StatefulAttackEngine(twin)

    result = engine.find_attack_paths(initial_node="start", target_node="target")
    assert result["target_reachable"] is True
    assert result["path_count"] == 2
    paths_nodes = [p["nodes"] for p in result["paths"]]
    assert ["start", "path1_mid", "target"] in paths_nodes
    assert ["start", "path2_mid", "target"] in paths_nodes


def test_max_depth_prevents_deep_traversal():
    """Verify max_depth limits the search horizon."""
    # Chain of 5 nodes
    assets = [AssetModel(id=f"n{i}", name=f"N{i}", type="server", zone="lan") for i in range(5)]
    relationships = [
        RelationshipModel(id=f"r{i}", source=f"n{i}", target=f"n{i+1}", relation_type="CONNECTS")
        for i in range(4)
    ]
    scenario = ScenarioModel(scenario_id="depth-test", name="Depth Twin", assets=assets, relationships=relationships)
    twin = CyberDigitalTwin(scenario)
    engine = StatefulAttackEngine(twin)

    # Distance is 4 hops. If max_depth=2, target shouldn't be reached
    res = engine.find_attack_paths(initial_node="n0", target_node="n4", max_depth=2)
    assert res["target_reachable"] is False

    # If max_depth=5, reachable
    res_ok = engine.find_attack_paths(initial_node="n0", target_node="n4", max_depth=5)
    assert res_ok["target_reachable"] is True
