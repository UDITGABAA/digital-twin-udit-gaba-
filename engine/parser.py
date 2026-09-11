"""Scenario parser and validator for Cyber Digital Twin scenarios."""

import json
from pathlib import Path
from typing import Dict, Any, Union
from engine.models import ScenarioModel


def load_scenario_from_file(filepath: Union[str, Path]) -> ScenarioModel:
    """Load and validate a scenario from a JSON file path."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Scenario configuration file not found: {filepath}")
    
    with open(path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    
    return load_scenario_from_dict(raw_data)


def load_scenario_from_dict(data: Dict[str, Any]) -> ScenarioModel:
    """Validate and instantiate ScenarioModel from dictionary data."""
    return ScenarioModel.model_validate(data)
