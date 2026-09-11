"""YAML -> technique table. Validates the frozen technique grammar (CLAUDE.md §5)."""

import re
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, field_validator

ATTCK_RE = re.compile(r"^T\d{4}(\.\d{3})?$")
PLACEHOLDERS_REQUIRES = {"session:src", "session:dst", "admin:src", "admin:dst", "creds:who", "data:src", "data:dst"}
PLACEHOLDERS_GRANTS = {"session:src", "session:dst", "admin:src", "admin:dst", "creds:sessions@src", "data:src", "data:dst"}
DEFAULT_PATH = Path(__file__).with_name("techniques.yaml")


class Channel(BaseModel, frozen=True):
    protocol: str
    port: int


class Technique(BaseModel, frozen=True):
    id: str
    attck: str
    channel: Optional[Channel] = None
    requires: tuple[str, ...] = ()
    grants: tuple[str, ...] = ()
    base_success: float
    cost: float
    noise: float

    @field_validator("attck")
    @classmethod
    def _attck(cls, v: str) -> str:
        if not ATTCK_RE.match(v):
            raise ValueError(f"not a MITRE ATT&CK id: {v!r}")
        return v

    @field_validator("requires")
    @classmethod
    def _req(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        bad = set(v) - PLACEHOLDERS_REQUIRES
        if bad:
            raise ValueError(f"unknown requires placeholder(s): {sorted(bad)}")
        return v

    @field_validator("grants")
    @classmethod
    def _gr(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        bad = set(v) - PLACEHOLDERS_GRANTS
        if bad:
            raise ValueError(f"unknown grants placeholder(s): {sorted(bad)}")
        return v


TechniqueTable = dict[str, Technique]


def load_techniques(path: str | Path = DEFAULT_PATH) -> TechniqueTable:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    table: TechniqueTable = {}
    for entry in raw:
        t = Technique.model_validate(entry)
        if t.id in table:
            raise ValueError(f"duplicate technique id: {t.id}")
        table[t.id] = t
    return table
