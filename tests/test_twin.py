"""Unit tests for the Cyber Digital Twin NetworkX graph engine."""

import pytest
from pathlib import Path
from engine.twin import FinBankTwin, CyberDigitalTwin
from engine.models import ScenarioModel
from engine.parser import load_scenario_from_file


@pytest.fixture
def scenario_path() -> Path:
    return Path("scenarios/scenario.json")


@pytest.fixture
def finbank_twin(scenario_path) -> FinBankTwin:
    return FinBankTwin.from_file(scenario_path)


def test_scenario_file_exists(scenario_path):
    assert scenario_path.exists(), "scenarios/scenario.json should exist"


def test_load_scenario_model(scenario_path):
    scenario = load_scenario_from_file(scenario_path)
    assert isinstance(scenario, ScenarioModel)
    assert scenario.name == "FinBank Twin"
    assert len(scenario.assets) == 9
    assert len(scenario.identities) == 4
    assert len(scenario.relationships) == 8
    assert len(scenario.controls) == 4


def test_twin_exact_counts(finbank_twin):
    """Verify exact counts requested in the pipeline."""
    assert finbank_twin.asset_count == 9, "Expected 9 assets detected"
    assert finbank_twin.identity_count == 4, "Expected 4 identities detected"
    assert finbank_twin.relationship_count == 8, "Expected 8 relationships detected"
    assert finbank_twin.control_count == 4, "Expected 4 controls detected"


def test_networkx_graph_topology(finbank_twin):
    """Verify NetworkX DiGraph representation."""
    graph = finbank_twin.graph
    
    # Total nodes = 9 assets + 4 identities = 13
    assert graph.number_of_nodes() == 13
    assert graph.number_of_edges() == 8

    # Verify asset node attributes
    web_portal = graph.nodes["asset-web-portal"]
    assert web_portal["node_type"] == "asset"
    assert web_portal["asset_type"] == "web_server"
    assert web_portal["zone"] == "dmz"
    assert "ctrl-waf" in web_portal["controls"]

    # Verify identity node attributes
    customer = graph.nodes["id-user-customer"]
    assert customer["node_type"] == "identity"
    assert customer["role"] == "customer"
    assert customer["privilege_level"] == "unprivileged"

    # Verify edge attributes
    edge = graph.edges["id-user-customer", "asset-web-portal"]
    assert edge["relation_type"] == "ACCESSES"
    assert edge["protocol"] == "HTTPS"
    assert edge["port"] == 443
    assert edge["encrypted"] is True


def test_security_controls_mapping(finbank_twin):
    """Verify controls are properly mapped to guarded entities."""
    controls = finbank_twin.controls
    assert "ctrl-mfa" in controls
    assert "ctrl-waf" in controls
    assert "ctrl-edr" in controls
    assert "ctrl-db-enc" in controls

    # Check MFA coverage
    mfa = controls["ctrl-mfa"]
    assert "asset-auth-service" in mfa.covered_entities
    assert "asset-admin-jumpbox" in mfa.covered_entities
    
    # Check DB encryption coverage
    db_enc = controls["ctrl-db-enc"]
    assert "asset-core-banking-db" in db_enc.covered_entities
    assert "ctrl-db-enc" in finbank_twin.graph.nodes["asset-core-banking-db"]["controls"]


def test_detection_summary(finbank_twin):
    summary = finbank_twin.get_detection_summary()
    assert summary["scenario"] == "FinBank Twin"
    assert summary["assets_detected"] == 9
    assert summary["identities_detected"] == 4
    assert summary["relationships_detected"] == 8
    assert summary["controls_detected"] == 4
    assert summary["graph_nodes"] == 13
    assert summary["graph_edges"] == 8


def test_render_flow_banner(finbank_twin):
    banner = finbank_twin.render_flow_banner("scenario.json")
    expected_lines = [
        "scenario.json",
        "      ↓",
        "Python",
        "      ↓",
        "NetworkX",
        "      ↓",
        "        ┌──────────────┐",
        "        │ FinBank Twin │",
        "        └──────────────┘",
        "              │",
        "              ▼",
        "        9 assets detected",
        "        4 identities detected",
        "        8 relationships detected",
        "        4 controls detected",
    ]
    for line in expected_lines:
        assert line in banner, f"Expected '{line}' to be present in banner output"


def test_nonexistent_file_raises_error():
    with pytest.raises(FileNotFoundError):
        FinBankTwin.from_file("scenarios/does_not_exist.json")
