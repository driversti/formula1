"""Tests for DriverList and grid-position extraction."""
from __future__ import annotations

from f1.driver_meta import DriverMeta, build_driver_meta, extract_grid_positions


def test_build_driver_meta_maps_by_racing_number() -> None:
    driver_list_state: dict[str, object] = {
        "1": {
            "RacingNumber": "1",
            "Tla": "VER",
            "FullName": "Max Verstappen",
            "TeamName": "Red Bull Racing",
            "TeamColour": "4781D7",
        },
        "16": {
            "RacingNumber": "16",
            "Tla": "LEC",
            "FullName": "Charles Leclerc",
            "TeamName": "Ferrari",
            "TeamColour": "ED1131",
        },
    }
    metas = build_driver_meta(driver_list_state)
    assert metas["1"] == DriverMeta(
        racing_number="1",
        tla="VER",
        full_name="Max Verstappen",
        team_name="Red Bull Racing",
        team_color="#4781D7",
    )
    assert metas["16"].tla == "LEC"


def test_build_driver_meta_prepends_hash_when_missing() -> None:
    state: dict[str, object] = {
        "1": {
            "RacingNumber": "1",
            "Tla": "VER",
            "FullName": "Max Verstappen",
            "TeamName": "Red Bull Racing",
            "TeamColour": "4781D7",
        }
    }
    assert build_driver_meta(state)["1"].team_color == "#4781D7"


def test_build_driver_meta_skips_entries_missing_required_fields() -> None:
    state: dict[str, object] = {
        "1": {"RacingNumber": "1"},  # missing everything else
        "16": {
            "RacingNumber": "16",
            "Tla": "LEC",
            "FullName": "Charles Leclerc",
            "TeamName": "Ferrari",
            "TeamColour": "ED1131",
        },
    }
    metas = build_driver_meta(state)
    assert list(metas) == ["16"]


def test_extract_grid_positions_reads_gridpos_from_lines() -> None:
    state: dict[str, object] = {
        "Lines": {
            "1": {"RacingNumber": "1", "GridPos": "2"},
            "16": {"RacingNumber": "16", "GridPos": "1"},
            "44": {"RacingNumber": "44"},  # GridPos missing -> not included
        }
    }
    grid = extract_grid_positions(state)
    assert grid == {"1": 2, "16": 1}


def test_extract_grid_positions_handles_empty_state() -> None:
    assert extract_grid_positions({}) == {}
