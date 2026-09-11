"""Unit tests for complete state-space attack path search (Algorithm A).

Written FIRST with a hand-built 6-node CompiledEdge graph before search.py is finalized.
Tests known paths by inspection, including the required pattern where an edge is reachable
ONLY after collecting a credential two hops earlier.
"""

import pytest
from engine.models import Asset, Twin, Agent, CompiledEdge
from engine.search import search, SearchBudgetExceeded, Inventory


@pytest.fixture
def six_node_twin() -> Twin:
    """Hand-crafted 6-node environment twin."""
    assets = (
        Asset(id="n_ext", name="External Internet", kind="internet", zone="external", criticality=1),
        Asset(id="ws_dev", name="Dev Workstation", kind="workstation", zone="corp", criticality=2),
        Asset(id="jump_box", name="Management Bastion", kind="server", zone="mgmt", criticality=3),
        Asset(id="app_srv", name="Public Web App", kind="server", zone="dmz", criticality=3),
        Asset(id="backup_srv", name="Backup Server", kind="server", zone="prod", criticality=4),
        Asset(id="crown_db", name="Core Banking DB", kind="database", zone="prod", criticality=5, crown_jewel=True),
    )
    return Twin(
        id="twin-fixture-6node",
        assets=assets,
        identities=(),
        grants=(),
        edges=(),
        flows=(),
        controls=(),
    )


@pytest.fixture
def six_node_compiled_edges() -> tuple[CompiledEdge, ...]:
    """Hand-built CompiledEdge tuples with known traversability by inspection."""
    return (
        # Route 1: Credential two hops earlier
        # Hop 1: External -> Dev Workstation (phish grants local admin)
        CompiledEdge(
            src="n_ext", dst="ws_dev", technique="phish",
            identity_id=None,
            requires=frozenset({"session:n_ext"}),
            grants=frozenset({"session:ws_dev", "admin:ws_dev"}),
            p_success=0.85, cost=1.0, noise=0.2, evidence="observed"
        ),
        # Hop 2 (Self-edge): Credential dumping on ws_dev grants adm.ops credentials
        CompiledEdge(
            src="ws_dev", dst="ws_dev", technique="cred_dump",
            identity_id="adm.ops",
            requires=frozenset({"session:ws_dev", "admin:ws_dev"}),
            grants=frozenset({"creds:adm.ops"}),
            p_success=0.8, cost=1.0, noise=0.4, evidence="observed"
        ),
        # Hop 3: ws_dev -> jump_box requires session:ws_dev + creds:adm.ops collected at Hop 2
        CompiledEdge(
            src="ws_dev", dst="jump_box", technique="rdp_lateral",
            identity_id="adm.ops",
            requires=frozenset({"session:ws_dev", "creds:adm.ops"}),
            grants=frozenset({"session:jump_box", "admin:jump_box"}),
            p_success=0.9, cost=2.0, noise=0.3, evidence="observed"
        ),
        # Hop 4: jump_box -> crown_db requires session:jump_box + creds:adm.ops (TWO hops after dump!)
        CompiledEdge(
            src="jump_box", dst="crown_db", technique="rdp_lateral",
            identity_id="adm.ops",
            requires=frozenset({"session:jump_box", "creds:adm.ops"}),
            grants=frozenset({"session:crown_db"}),
            p_success=0.9, cost=2.0, noise=0.3, evidence="observed"
        ),

        # Route 2: Exploit web app directly to crown_db
        # Hop 1: External -> Web App
        CompiledEdge(
            src="n_ext", dst="app_srv", technique="exploit_public_app",
            identity_id=None,
            requires=frozenset({"session:n_ext"}),
            grants=frozenset({"session:app_srv"}),
            p_success=0.75, cost=2.0, noise=0.5, evidence="inventory"
        ),
        # Hop 2: Web App -> Crown DB
        CompiledEdge(
            src="app_srv", dst="crown_db", technique="exploit_public_app",
            identity_id=None,
            requires=frozenset({"session:app_srv"}),
            grants=frozenset({"session:crown_db"}),
            p_success=0.7, cost=2.0, noise=0.5, evidence="inventory"
        ),

        # Blocked branch: app_srv -> backup_srv requires missing credentials that are never granted
        CompiledEdge(
            src="app_srv", dst="backup_srv", technique="ssh_lateral",
            identity_id="svc.missing",
            requires=frozenset({"session:app_srv", "creds:missing_key"}),
            grants=frozenset({"session:backup_srv"}),
            p_success=0.9, cost=2.0, noise=0.2, evidence="assumed"
        ),
        # backup_srv -> crown_db (unreachable because backup_srv cannot be breached)
        CompiledEdge(
            src="backup_srv", dst="crown_db", technique="db_login",
            identity_id="svc.backup",
            requires=frozenset({"session:backup_srv", "creds:svc.backup"}),
            grants=frozenset({"session:crown_db"}),
            p_success=0.95, cost=1.0, noise=0.2, evidence="inferred"
        ),
    )


@pytest.fixture
def external_agent() -> Agent:
    return Agent(
        id="agent-ext",
        name="External Adversary",
        start_zones=("external",),
        capabilities=frozenset(),
        objective="specific_target",
        target="crown_db",
        noise_budget=2.0,
        skill=0.8,
    )


def test_search_discovers_exact_known_paths(six_node_twin, six_node_compiled_edges, external_agent):
    """Verify search finds exactly the two valid paths and handles 2-hop credential collection."""
    inv = search(six_node_compiled_edges, external_agent, six_node_twin)
    
    assert isinstance(inv, Inventory)
    assert len(inv.routes) == 2, f"Expected exactly 2 paths, found {len(inv.routes)}"
    assert inv.naive_count == 2

    route_signatures = [
        [(e.src, e.dst, e.technique) for e in route]
        for route in inv.routes
    ]

    expected_route_1 = [
        ("n_ext", "ws_dev", "phish"),
        ("ws_dev", "ws_dev", "cred_dump"),
        ("ws_dev", "jump_box", "rdp_lateral"),
        ("jump_box", "crown_db", "rdp_lateral"),
    ]
    expected_route_2 = [
        ("n_ext", "app_srv", "exploit_public_app"),
        ("app_srv", "crown_db", "exploit_public_app"),
    ]

    assert expected_route_1 in route_signatures, "Route 1 (with 2-hop credential dump) must be discovered"
    assert expected_route_2 in route_signatures, "Route 2 (public app exploit) must be discovered"


def test_removing_cred_dump_eliminates_route_1(six_node_twin, six_node_compiled_edges, external_agent):
    """Without the cred_dump self-edge, Route 1 cannot be traversed."""
    edges_without_dump = tuple(e for e in six_node_compiled_edges if e.technique != "cred_dump")
    inv = search(edges_without_dump, external_agent, six_node_twin)

    assert len(inv.routes) == 1, "Only Route 2 should survive when cred_dump is removed"
    route_sigs = [[(e.src, e.dst, e.technique) for e in route] for route in inv.routes]
    assert [("n_ext", "app_srv", "exploit_public_app"), ("app_srv", "crown_db", "exploit_public_app")] in route_sigs


def test_missing_credentials_blocks_traversal(six_node_twin, six_node_compiled_edges, external_agent):
    """Edges requiring missing credentials are never traversed."""
    inv = search(six_node_compiled_edges, external_agent, six_node_twin)
    all_traversed_edges = {e for route in inv.routes for e in route}
    blocked_edges = {e for e in six_node_compiled_edges if e.dst == "backup_srv"}
    assert blocked_edges.isdisjoint(all_traversed_edges), "Blocked edges into backup_srv must never be in routes"


def test_search_caps_prevent_infinite_loops(six_node_twin, external_agent):
    """Search budget must be enforced on cycles rather than hanging."""
    loopy_edges = (
        CompiledEdge(
            src="n_ext", dst="n_ext", technique="phish",
            identity_id=None, requires=frozenset({"session:n_ext"}),
            grants=frozenset({"session:n_ext"}),
            p_success=1.0, cost=1.0, noise=0.0, evidence="observed"
        ),
        CompiledEdge(
            src="n_ext", dst="ws_dev", technique="phish",
            identity_id=None, requires=frozenset({"session:n_ext"}),
            grants=frozenset({"session:ws_dev"}),
            p_success=1.0, cost=1.0, noise=0.0, evidence="observed"
        ),
        CompiledEdge(
            src="ws_dev", dst="n_ext", technique="ssh_lateral",
            identity_id=None, requires=frozenset({"session:ws_dev"}),
            grants=frozenset({"session:n_ext"}),
            p_success=1.0, cost=1.0, noise=0.0, evidence="observed"
        ),
    )
    inv = search(loopy_edges, external_agent, six_node_twin, max_depth=3)
    assert len(inv.routes) == 0
