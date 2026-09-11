"""Cyber Digital Twin graph representation backed by NetworkX."""

from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import networkx as nx

from engine.models import ScenarioModel, AssetModel, IdentityModel, ControlModel, RelationshipModel
from engine.parser import load_scenario_from_file, load_scenario_from_dict


class CyberDigitalTwin:
    """Graph-based Cyber Digital Twin built on top of NetworkX."""

    def __init__(self, scenario: ScenarioModel):
        self.scenario = scenario
        self.name: str = scenario.name
        self.scenario_id: str = scenario.scenario_id
        self.version: str = scenario.version
        self.environment: Optional[str] = scenario.environment
        
        # NetworkX directed graph representation
        self.graph: nx.DiGraph = nx.DiGraph(name=scenario.name)
        
        # Registries
        self._assets: Dict[str, AssetModel] = {}
        self._identities: Dict[str, IdentityModel] = {}
        self._controls: Dict[str, ControlModel] = {}
        self._relationships: List[RelationshipModel] = []
        
        self._build_graph()

    @classmethod
    def from_file(cls, filepath: Union[str, Path]) -> "CyberDigitalTwin":
        """Factory method to instantiate a digital twin from a scenario file."""
        scenario = load_scenario_from_file(filepath)
        return cls(scenario)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CyberDigitalTwin":
        """Factory method to instantiate a digital twin from a dictionary."""
        scenario = load_scenario_from_dict(data)
        return cls(scenario)

    def _build_graph(self) -> None:
        """Construct the NetworkX graph from scenario entities and relationships."""
        # 1. Register and add Asset nodes
        for asset in self.scenario.assets:
            self._assets[asset.id] = asset
            self.graph.add_node(
                asset.id,
                name=asset.name,
                node_type="asset",
                asset_type=asset.type,
                zone=asset.zone,
                ip_address=asset.ip_address,
                os=asset.os,
                criticality=asset.criticality,
                tags=asset.tags,
                controls=[]
            )

        # 2. Register and add Identity nodes
        for identity in self.scenario.identities:
            self._identities[identity.id] = identity
            self.graph.add_node(
                identity.id,
                name=identity.name,
                node_type="identity",
                identity_type=identity.type,
                role=identity.role,
                privilege_level=identity.privilege_level,
                department=identity.department,
                controls=[]
            )

        # 3. Register Security Controls & map coverage
        for control in self.scenario.controls:
            self._controls[control.id] = control
            for target_id in control.covered_entities:
                if target_id in self.graph:
                    self.graph.nodes[target_id]["controls"].append(control.id)

        # 4. Add Relationship edges
        for rel in self.scenario.relationships:
            self._relationships.append(rel)
            self.graph.add_edge(
                rel.source,
                rel.target,
                id=rel.id,
                relation_type=rel.relation_type,
                protocol=rel.protocol,
                port=rel.port,
                encrypted=rel.encrypted
            )

    # ------------------------------------------------------------------
    # Detection & Property Metrics
    # ------------------------------------------------------------------
    @property
    def asset_count(self) -> int:
        """Total number of assets detected in the twin."""
        return len(self._assets)

    @property
    def identity_count(self) -> int:
        """Total number of identities detected in the twin."""
        return len(self._identities)

    @property
    def relationship_count(self) -> int:
        """Total number of relationships detected in the twin."""
        return len(self._relationships)

    @property
    def control_count(self) -> int:
        """Total number of security controls detected in the twin."""
        return len(self._controls)

    @property
    def assets(self) -> Dict[str, AssetModel]:
        return self._assets

    @property
    def identities(self) -> Dict[str, IdentityModel]:
        return self._identities

    @property
    def controls(self) -> Dict[str, ControlModel]:
        return self._controls

    @property
    def relationships(self) -> List[RelationshipModel]:
        return self._relationships

    def get_detection_summary(self) -> Dict[str, Any]:
        """Return structured summary of detected entities."""
        return {
            "scenario": self.name,
            "assets_detected": self.asset_count,
            "identities_detected": self.identity_count,
            "relationships_detected": self.relationship_count,
            "controls_detected": self.control_count,
            "graph_nodes": self.graph.number_of_nodes(),
            "graph_edges": self.graph.number_of_edges()
        }

    def render_flow_banner(self, source_file: str = "scenario.json") -> str:
        """Render the exact ASCII flow diagram representing ingestion into the twin."""
        lines = [
            f"{source_file}",
            "      ↓",
            "Python",
            "      ↓",
            "NetworkX",
            "      ↓",
            "        ┌──────────────┐",
            f"        │ {self.name.center(12)} │",
            "        └──────────────┘",
            "              │",
            "              ▼",
            f"        {self.asset_count} assets detected",
            f"        {self.identity_count} identities detected",
            f"        {self.relationship_count} relationships detected",
            f"        {self.control_count} controls detected",
        ]
        return "\n".join(lines)

    def print_detailed_breakdown(self) -> None:
        """Print detailed tabular breakdown using Rich if available, else plain text."""
        try:
            from rich.console import Console
            from rich.table import Table
            from rich.panel import Panel

            console = Console()
            console.print(Panel.fit(
                f"[bold cyan]{self.name}[/bold cyan] (Cyber Digital Twin)\n"
                f"[dim]Environment: {self.environment} | Version: {self.version}[/dim]",
                title="FinBank Digital Twin State"
            ))

            # Assets Table
            t_assets = Table(title="Detected Assets (9)")
            t_assets.add_column("Asset ID", style="cyan")
            t_assets.add_column("Name", style="white")
            t_assets.add_column("Type", style="yellow")
            t_assets.add_column("Zone", style="green")
            t_assets.add_column("IP Address", style="magenta")
            t_assets.add_column("Criticality", style="red")
            for a in self._assets.values():
                t_assets.add_row(a.id, a.name, a.type, a.zone, a.ip_address or "-", a.criticality)
            console.print(t_assets)

            # Identities Table
            t_id = Table(title="Detected Identities (4)")
            t_id.add_column("Identity ID", style="cyan")
            t_id.add_column("Name", style="white")
            t_id.add_column("Type", style="yellow")
            t_id.add_column("Role", style="blue")
            t_id.add_column("Privilege", style="magenta")
            for i in self._identities.values():
                t_id.add_row(i.id, i.name, i.type, i.role, i.privilege_level)
            console.print(t_id)

            # Relationships Table
            t_rel = Table(title="Detected Relationships (8)")
            t_rel.add_column("ID", style="cyan")
            t_rel.add_column("Source", style="white")
            t_rel.add_column("Relation", style="bold yellow")
            t_rel.add_column("Target", style="white")
            t_rel.add_column("Protocol", style="green")
            t_rel.add_column("Port", style="magenta")
            for r in self._relationships:
                t_rel.add_row(r.id, r.source, f"-> {r.relation_type} ->", r.target, r.protocol or "-", str(r.port or "-"))
            console.print(t_rel)

            # Controls Table
            t_ctrl = Table(title="Detected Controls (4)")
            t_ctrl.add_column("Control ID", style="cyan")
            t_ctrl.add_column("Name", style="white")
            t_ctrl.add_column("Type", style="yellow")
            t_ctrl.add_column("Status", style="green")
            t_ctrl.add_column("Covered Entities", style="dim")
            for c in self._controls.values():
                t_ctrl.add_row(c.id, c.name, c.type, c.status, ", ".join(c.covered_entities))
            console.print(t_ctrl)

        except ImportError:
            # Fallback to plain text output
            print(f"--- {self.name} Detailed Breakdown ---")
            print(f"Assets ({self.asset_count}): {', '.join(self._assets.keys())}")
            print(f"Identities ({self.identity_count}): {', '.join(self._identities.keys())}")
            print(f"Relationships ({self.relationship_count}): {len(self._relationships)} edges")
            print(f"Controls ({self.control_count}): {', '.join(self._controls.keys())}")


# Alias for explicit domain naming
FinBankTwin = CyberDigitalTwin
