"""Tests for the Pydantic data model."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from f1.models import (
    Compound,
    DriverInventory,
    Manifest,
    Race,
    RaceStint,
    SessionRef,
    TyreSet,
)


def _minimal_set(**overrides: object) -> TyreSet:
    base: dict[str, object] = {
        "set_id": "VER-MED-1",
        "compound": "MEDIUM",
        "laps": 0,
        "new_at_first_use": True,
        "first_seen_session": "FP1",
        "last_seen_session": "FP1",
    }
    base.update(overrides)
    return TyreSet(**base)  # type: ignore[arg-type]


def test_tyreset_accepts_valid_payload() -> None:
    s = _minimal_set(laps=5)
    assert s.compound == "MEDIUM"
    assert s.laps == 5


def test_tyreset_rejects_negative_laps() -> None:
    with pytest.raises(ValidationError):
        _minimal_set(laps=-1)


def test_tyreset_rejects_unknown_compound() -> None:
    with pytest.raises(ValidationError):
        _minimal_set(compound="UNKNOWN")  # type: ignore[arg-type]


def test_driver_inventory_requires_three_letter_tla() -> None:
    with pytest.raises(ValidationError):
        DriverInventory(
            racing_number="1",
            tla="VE",
            full_name="Max Verstappen",
            team_name="Red Bull Racing",
            team_color="#4781D7",
            grid_position=1,
            sets=[],
        )


def test_driver_inventory_requires_hex_team_color() -> None:
    with pytest.raises(ValidationError):
        DriverInventory(
            racing_number="1",
            tla="VER",
            full_name="Max Verstappen",
            team_name="Red Bull Racing",
            team_color="red",
            grid_position=1,
            sets=[],
        )


def test_driver_inventory_sets_by_compound_groups_correctly() -> None:
    inv = DriverInventory(
        racing_number="1",
        tla="VER",
        full_name="Max Verstappen",
        team_name="Red Bull Racing",
        team_color="#4781D7",
        grid_position=None,
        sets=[
            _minimal_set(set_id="VER-HARD-1", compound="HARD"),
            _minimal_set(set_id="VER-MED-1", compound="MEDIUM"),
            _minimal_set(set_id="VER-MED-2", compound="MEDIUM"),
        ],
    )
    grouped = inv.sets_by_compound
    assert list(grouped.keys()) == ["HARD", "MEDIUM"]
    assert [s.set_id for s in grouped["MEDIUM"]] == ["VER-MED-1", "VER-MED-2"]


def test_race_and_manifest_compose() -> None:
    session = SessionRef(
        key="R",
        name="Race",
        path="2026/.../2026-03-08_Race/",
        start_utc="2026-03-08T04:00:00Z",
    )
    race = Race(
        slug="australia-2026",
        name="Australian Grand Prix",
        location="Melbourne",
        country="Australia",
        season=2026,
        round=1,
        date="2026-03-08",
        sessions=[session],
        drivers=[],
    )
    manifest = Manifest(
        schema_version="1.0.0",
        generated_at="2026-04-17T12:00:00Z",
        race=race,
    )
    assert manifest.race.slug == "australia-2026"
    assert manifest.schema_version == "1.0.0"


def test_compound_literal_values() -> None:
    allowed = {"SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"}
    assert set(Compound.__args__) == allowed  # type: ignore[attr-defined]


def test_race_stint_accepts_valid_payload() -> None:
    s = RaceStint(
        stint_idx=0,
        compound="MEDIUM",
        start_lap=1,
        end_lap=18,
        laps=18,
        new=True,
    )
    assert s.compound == "MEDIUM"
    assert s.end_lap == 18


def test_race_stint_rejects_unknown_compound() -> None:
    with pytest.raises(ValidationError):
        RaceStint(
            stint_idx=0,
            compound="UNKNOWN",  # type: ignore[arg-type]
            start_lap=1,
            end_lap=2,
            laps=2,
            new=True,
        )


def test_race_stint_rejects_start_lap_below_one() -> None:
    with pytest.raises(ValidationError):
        RaceStint(
            stint_idx=0,
            compound="SOFT",
            start_lap=0,
            end_lap=3,
            laps=3,
            new=True,
        )


def test_driver_inventory_has_empty_stint_lists_by_default() -> None:
    inv = DriverInventory(
        racing_number="1",
        tla="VER",
        full_name="Max Verstappen",
        team_name="Red Bull Racing",
        team_color="#4781D7",
        grid_position=1,
        sets=[],
    )
    assert inv.race_stints == []
    assert inv.sprint_stints == []


def test_driver_inventory_defaults_for_final_position_and_dnf() -> None:
    inv = DriverInventory(
        racing_number="1",
        tla="VER",
        full_name="Max Verstappen",
        team_name="Red Bull Racing",
        team_color="#4781D7",
        grid_position=1,
        sets=[],
    )
    assert inv.final_position is None
    assert inv.dnf_at_lap is None


def test_driver_inventory_accepts_final_position() -> None:
    inv = DriverInventory(
        racing_number="1",
        tla="VER",
        full_name="Max Verstappen",
        team_name="Red Bull Racing",
        team_color="#4781D7",
        grid_position=1,
        sets=[],
        final_position=3,
    )
    assert inv.final_position == 3


def test_driver_inventory_rejects_final_position_out_of_range() -> None:
    with pytest.raises(ValidationError):
        DriverInventory(
            racing_number="1",
            tla="VER",
            full_name="Max Verstappen",
            team_name="Red Bull Racing",
            team_color="#4781D7",
            grid_position=1,
            sets=[],
            final_position=0,
        )


def test_driver_inventory_defaults_for_sprint_position_and_dnf() -> None:
    inv = DriverInventory(
        racing_number="1",
        tla="VER",
        full_name="Max Verstappen",
        team_name="Red Bull Racing",
        team_color="#4781D7",
        grid_position=1,
        sets=[],
    )
    assert inv.sprint_final_position is None
    assert inv.sprint_dnf_at_lap is None
