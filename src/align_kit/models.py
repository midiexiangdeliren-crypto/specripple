"""Core data models for artifact entries (schema v0)."""

from __future__ import annotations

import re
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

ID_PATTERN = re.compile(r"^(?:REQ|TASK|PLAN|CON|RAT)-\d{3}$")


class EntryType(str, Enum):
    REQ = "req"
    TASK = "task"
    PLAN = "plan"
    CON = "con"
    RATIONALE = "rationale"


class EntryStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    DONE = "done"
    DEPRECATED = "deprecated"


class LinkKind(str, Enum):
    REALIZED_BY = "realized-by"
    REFINES = "refines"
    VERIFIES = "verifies"
    CLARIFIES = "clarifies"


class Link(BaseModel):
    model_config = ConfigDict(extra="forbid")

    to: str
    kind: LinkKind
    src: str = "manual"


class Entry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    type: EntryType
    title: str = Field(min_length=1)
    status: EntryStatus = EntryStatus.DRAFT
    depends_on: list[str] = []
    links: list[Link] = []
    path: Path
    body: str = ""

    @field_validator("id")
    @classmethod
    def _check_id(cls, value: str) -> str:
        if not ID_PATTERN.match(value):
            raise ValueError(f"invalid artifact id: {value!r} (expected REQ|TASK|PLAN|CON|RAT-NNN)")
        return value
