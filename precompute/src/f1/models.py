"""Pydantic data model for the precomputed JSON artifact.

These models are the single source of truth: JSON Schema is exported from
them and consumed by the TypeScript site to generate matching Zod schemas.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Compound = Literal["SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"]
SessionKey = Literal["FP1", "FP2", "FP3", "Q", "R"]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)


class TyreSet(_StrictModel):
    """One physical tyre set, identified by tracking stints across sessions."""

    set_id: str = Field(..., description="Synthetic id, e.g. VER-MED-1")
    compound: Compound
    laps: int = Field(ge=0, description="Total laps at race start (pre-race state)")
    new_at_first_use: bool
    first_seen_session: SessionKey
    last_seen_session: SessionKey


class DriverInventory(_StrictModel):
    """All tyre sets known to belong to a single driver."""

    racing_number: str = Field(..., min_length=1)
    tla: str = Field(..., min_length=3, max_length=3)
    full_name: str
    team_name: str
    team_color: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$")
    grid_position: int | None = Field(default=None, ge=1, le=22)
    sets: list[TyreSet]

    @property
    def sets_by_compound(self) -> dict[Compound, list[TyreSet]]:
        """Group sets by compound, preserving first-seen order."""
        grouped: dict[Compound, list[TyreSet]] = {}
        for s in self.sets:
            grouped.setdefault(s.compound, []).append(s)
        return grouped


class SessionRef(_StrictModel):
    """Reference to one session in the weekend."""

    key: SessionKey
    name: str
    path: str
    start_utc: str


class Race(_StrictModel):
    """Race metadata plus all driver inventories."""

    slug: str
    name: str
    location: str
    country: str
    season: int
    round: int
    date: str
    sessions: list[SessionRef]
    drivers: list[DriverInventory]


class Manifest(_StrictModel):
    """Top-level JSON artifact."""

    schema_version: str = "1.0.0"
    generated_at: str
    source_commit: str | None = None
    race: Race
