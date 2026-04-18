"""Unit tests for precompute/src/f1/track_status.py."""
from __future__ import annotations

from f1.parse import Event
from f1.track_status import collect_lap_boundaries, collect_status_transitions


def _ev(ts: int, payload: dict) -> Event:
    return Event(timestamp_ms=ts, data=payload)


def test_collect_status_transitions_extracts_all_codes() -> None:
    events = [
        _ev(0,    {"Status": "2", "Message": "Yellow"}),
        _ev(1000, {"Status": "1", "Message": "AllClear"}),
        _ev(2000, {"Status": "4", "Message": "SCDeployed"}),
        _ev(3000, {"Status": "1", "Message": "AllClear"}),
    ]
    assert collect_status_transitions(events) == [
        (0, "2"),
        (1000, "1"),
        (2000, "4"),
        (3000, "1"),
    ]


def test_collect_status_transitions_skips_malformed_payloads() -> None:
    events = [
        _ev(0, {"Message": "no-status"}),
        _ev(1, {"Status": 42, "Message": "not-a-string"}),
        _ev(2, {"Status": "4"}),
    ]
    assert collect_status_transitions(events) == [(2, "4")]


def test_collect_lap_boundaries_extracts_current_lap_changes() -> None:
    events = [
        _ev(0,     {"CurrentLap": 1, "TotalLaps": 53}),
        _ev(90000, {"CurrentLap": 2}),
        _ev(180000,{"CurrentLap": 3}),
    ]
    assert collect_lap_boundaries(events) == [
        (0, 1),
        (90000, 2),
        (180000, 3),
    ]


def test_collect_lap_boundaries_seeds_lap_one_if_first_event_is_later() -> None:
    # Defensive: if LapCount stream starts at CurrentLap=5 (partial archive),
    # seed (0, 1) so callers can resolve any early timestamp to lap 1.
    events = [
        _ev(120000, {"CurrentLap": 5}),
        _ev(180000, {"CurrentLap": 6}),
    ]
    assert collect_lap_boundaries(events) == [
        (0, 1),
        (120000, 5),
        (180000, 6),
    ]


def test_collect_lap_boundaries_ignores_non_int_and_missing_values() -> None:
    events = [
        _ev(0,  {"CurrentLap": 1}),
        _ev(1,  {"TotalLaps": 53}),       # no CurrentLap
        _ev(2,  {"CurrentLap": "two"}),   # not int
        _ev(3,  {"CurrentLap": 2}),
    ]
    assert collect_lap_boundaries(events) == [(0, 1), (3, 2)]


def test_collect_lap_boundaries_empty_input_returns_seed() -> None:
    # An empty stream still returns the (0, 1) seed so downstream code can
    # clamp early-session timestamps without a special case.
    assert collect_lap_boundaries([]) == [(0, 1)]
