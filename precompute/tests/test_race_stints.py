"""Tests for race/sprint stint derivation from SessionStint records."""
from __future__ import annotations

from f1.inventory import SessionStint, build_race_stints
from f1.models import RaceStint


def test_build_race_stints_single_stop_strategy() -> None:
    # Two stints: MEDIUM for 18 laps, then HARD for 39 laps.
    session = [
        SessionStint("R", "1", 0, "MEDIUM", True, 0, 18),
        SessionStint("R", "1", 1, "HARD",   True, 0, 39),
    ]
    stints = build_race_stints(driver_number="1", stints_for_session=session)
    assert stints == [
        RaceStint(stint_idx=0, compound="MEDIUM", start_lap=1,  end_lap=18, laps=18, new=True),
        RaceStint(stint_idx=1, compound="HARD",   start_lap=19, end_lap=57, laps=39, new=True),
    ]


def test_build_race_stints_two_stop_strategy_preserves_continuity() -> None:
    session = [
        SessionStint("R", "1", 0, "SOFT",   True,  0, 14),
        SessionStint("R", "1", 1, "MEDIUM", True,  0, 18),
        SessionStint("R", "1", 2, "HARD",   True,  0, 25),
    ]
    stints = build_race_stints(driver_number="1", stints_for_session=session)
    assert [s.start_lap for s in stints] == [1, 15, 33]
    assert [s.end_lap   for s in stints] == [14, 32, 57]
    assert [s.laps      for s in stints] == [14, 18, 25]


def test_build_race_stints_filters_other_drivers() -> None:
    session = [
        SessionStint("R", "1",  0, "MEDIUM", True, 0, 18),
        SessionStint("R", "16", 0, "HARD",   True, 0, 57),
    ]
    stints = build_race_stints(driver_number="16", stints_for_session=session)
    assert len(stints) == 1
    assert stints[0].compound == "HARD"
    assert stints[0].laps == 57


def test_build_race_stints_skips_zero_lap_stints() -> None:
    # A stint recorded with TotalLaps=0 means the driver never completed a lap
    # on it — treat as not-yet-run (or dropout mid-pit). Filter out.
    session = [
        SessionStint("R", "1", 0, "MEDIUM", True, 0, 18),
        SessionStint("R", "1", 1, "HARD",   True, 0, 0),
    ]
    stints = build_race_stints(driver_number="1", stints_for_session=session)
    assert len(stints) == 1
    assert stints[0].compound == "MEDIUM"


def test_build_race_stints_empty_input_returns_empty_list() -> None:
    assert build_race_stints(driver_number="1", stints_for_session=[]) == []


def test_build_race_stints_sorted_by_stint_idx_even_when_input_is_not() -> None:
    session = [
        SessionStint("R", "1", 1, "HARD",   True, 0, 39),
        SessionStint("R", "1", 0, "MEDIUM", True, 0, 18),
    ]
    stints = build_race_stints(driver_number="1", stints_for_session=session)
    assert [s.stint_idx for s in stints] == [0, 1]
    assert stints[0].start_lap == 1
    assert stints[1].start_lap == 19


def test_build_race_stints_extends_last_stint_when_lap_count_exceeds_sum() -> None:
    # Simulates RUS: TyreStintSeries under-reports, NumberOfLaps is
    # authoritative and larger.
    session = [
        SessionStint("S", "1", 0, "MEDIUM", False, 3, 16),  # stint_laps = 13
    ]
    stints = build_race_stints(
        driver_number="1",
        stints_for_session=session,
        driver_lap_count=19,
    )
    assert len(stints) == 1
    assert stints[0].laps == 19
    assert stints[0].end_lap == 19


def test_build_race_stints_no_extension_when_lap_count_matches() -> None:
    session = [SessionStint("R", "1", 0, "HARD", True, 0, 19)]
    stints = build_race_stints(
        driver_number="1",
        stints_for_session=session,
        driver_lap_count=19,
    )
    assert stints[0].laps == 19


def test_build_race_stints_no_extension_when_lap_count_lower() -> None:
    # Don't trim — safer to trust TyreStintSeries in this direction.
    session = [SessionStint("R", "1", 0, "MEDIUM", True, 0, 20)]
    stints = build_race_stints(
        driver_number="1",
        stints_for_session=session,
        driver_lap_count=15,
    )
    assert stints[0].laps == 20
