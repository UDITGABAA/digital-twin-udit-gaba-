"""Scenario file = the twin + the adversary profiles + the control catalogue to propose from."""

import json
from pathlib import Path

from pydantic import BaseModel

from engine.models import Agent, Control, Twin

SCENARIO_DIR = Path(__file__).resolve().parent.parent / "scenarios"


class Scenario(BaseModel, frozen=True):
    name: str = ""
    twin: Twin
    agents: tuple[Agent, ...]
    catalogue: tuple[Control, ...]      # proposable controls; twin.controls are the applied ones


def load_scenario(name_or_path: str | Path) -> Scenario:
    p = Path(name_or_path)
    if not p.suffix:
        p = SCENARIO_DIR / f"{p}.json"
    with open(p, encoding="utf-8") as f:
        return Scenario.model_validate(json.load(f))


def list_scenarios() -> tuple[str, ...]:
    return tuple(sorted(p.stem for p in SCENARIO_DIR.glob("*.json")))
