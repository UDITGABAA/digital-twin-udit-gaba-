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

# Public convenience alias
load_scenario = load_scenario_from_file

__all__ = [
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
]
