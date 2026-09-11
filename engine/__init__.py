"""Cyber Digital Twin Engine Package."""

from engine.models import (
    AssetModel,
    IdentityModel,
    ControlModel,
    RelationshipModel,
    ScenarioModel,
)
from engine.parser import load_scenario_from_file, load_scenario_from_dict
from engine.twin import CyberDigitalTwin, FinBankTwin
from engine.attacker import AttackerState
from engine.rules import RuleEngine
from engine.attack_path import StatefulAttackEngine

# v2.1 Architecture Models & Functions
from engine.models import (
    Asset,
    Identity,
    PrivilegeGrant,
    Edge,
    ServiceFlow,
    FlowSelector,
    ControlImpact,
    Control,
    Agent,
    Twin,
    CompiledEdge,
    twin_hash,
)
from engine.twin import clone
from engine.search import search, Inventory, SearchBudgetExceeded, Route
from engine.walk import route_policy, simulate, RouteChoice
from engine.results import Result, Delta, RouteStat, diff
from engine.blast import Blast, blast_radius

# Public convenience alias
load_scenario = load_scenario_from_file

__all__ = [
    # Legacy exports
    "CyberDigitalTwin",
    "FinBankTwin",
    "load_scenario",
    "load_scenario_from_file",
    "load_scenario_from_dict",
    "AssetModel",
    "IdentityModel",
    "ControlModel",
    "RelationshipModel",
    "ScenarioModel",
    "AttackerState",
    "RuleEngine",
    "StatefulAttackEngine",
    # v2.1 Core Contracts
    "Asset",
    "Identity",
    "PrivilegeGrant",
    "Edge",
    "ServiceFlow",
    "FlowSelector",
    "ControlImpact",
    "Control",
    "Agent",
    "Twin",
    "CompiledEdge",
    "twin_hash",
    "clone",
    # v2.1 Algorithms & Output Models
    "search",
    "Inventory",
    "SearchBudgetExceeded",
    "Route",
    "route_policy",
    "simulate",
    "RouteChoice",
    "Result",
    "Delta",
    "RouteStat",
    "diff",
    "Blast",
    "blast_radius",
]
