"""Unit tests for precompute/src/f1/track_status.py."""
from __future__ import annotations

from f1.models import StatusBand
from f1.parse import Event
from f1.track_status import build_status_bands, collect_lap_boundaries, collect_status_transitions


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


def test_collect_lap_boundaries_ignores_zero_and_negative_lap_values() -> None:
    # The live-timing feed emits CurrentLap=0 during the formation-lap window.
    # Those must be filtered so that status timestamps in that window resolve
    # to lap 1 (via the (0, 1) seed) rather than lap 0.
    events = [
        _ev(100,  {"CurrentLap": 0}),     # formation-lap artifact — skip
        _ev(200,  {"CurrentLap": -1}),    # guard: negative also filtered
        _ev(1000, {"CurrentLap": 1}),
        _ev(2000, {"CurrentLap": 2}),
    ]
    # out[0][1] == 1 (not > 1) so the (0, 1) seed is NOT prepended.
    assert collect_lap_boundaries(events) == [(1000, 1), (2000, 2)]


def test_collect_lap_boundaries_empty_input_returns_seed() -> None:
    # An empty stream still returns the (0, 1) seed so downstream code can
    # clamp early-session timestamps without a special case.
    assert collect_lap_boundaries([]) == [(0, 1)]


def test_build_status_bands_standard_yellow_then_sc() -> None:
    # Status transitions at ms: Yellow opens at 0 (lap 1), AllClear at 200000 (lap 3),
    # SC at 2_400_000 (lap 26), AllClear at 3_000_000 (lap 32).
    transitions = [
        (0,       "2"),    # Yellow
        (200_000, "1"),    # AllClear (lap 3)
        (2_400_000, "4"),  # SCDeployed
        (3_000_000, "1"),  # AllClear
    ]
    # Lap boundaries: CurrentLap changes at 90s intervals (93s per lap ~ Japan).
    lap_boundaries = [(0, 1)]
    for lap in range(2, 55):
        lap_boundaries.append((93_000 * (lap - 1), lap))

    bands = build_status_bands(transitions, lap_boundaries, total_laps=53)
    assert bands == [
        StatusBand(status="Yellow",     start_lap=1,  end_lap=2),
        StatusBand(status="SCDeployed", start_lap=26, end_lap=32),
    ]


def _linear_laps(n: int, per_lap_ms: int = 90_000) -> list[tuple[int, int]]:
    """Helper: generate lap boundaries at fixed pace."""
    return [(per_lap_ms * (lap - 1), lap) for lap in range(1, n + 1)]


def test_build_status_bands_status_at_session_start() -> None:
    # Yellow active from t=0 on lap 1.
    transitions = [(0, "2"), (300_000, "1")]
    bands = build_status_bands(transitions, _linear_laps(10), total_laps=10)
    assert bands == [StatusBand(status="Yellow", start_lap=1, end_lap=3)]


def test_build_status_bands_status_extends_to_session_end() -> None:
    # SC deployed partway through lap 6 (t=450_001 = just inside lap 6),
    # never cleared — clamped to total_laps.
    transitions = [(450_001, "4")]
    bands = build_status_bands(transitions, _linear_laps(10), total_laps=10)
    assert bands == [StatusBand(status="SCDeployed", start_lap=6, end_lap=10)]


def test_build_status_bands_vsc_ending_closes_vsc() -> None:
    transitions = [
        (0,        "6"),  # VSCDeployed on lap 1
        (300_000,  "7"),  # VSCEnding on lap 4
    ]
    bands = build_status_bands(transitions, _linear_laps(10), total_laps=10)
    assert bands == [StatusBand(status="VSCDeployed", start_lap=1, end_lap=3)]


def test_build_status_bands_stray_vsc_ending_is_noop() -> None:
    # VSCEnding with no prior VSCDeployed — should produce no band.
    transitions = [(300_000, "7")]
    bands = build_status_bands(transitions, _linear_laps(10), total_laps=10)
    assert bands == []


def test_build_status_bands_duplicate_codes_do_not_split() -> None:
    transitions = [(0, "2"), (90_000, "2"), (180_000, "1")]
    bands = build_status_bands(transitions, _linear_laps(10), total_laps=10)
    assert bands == [StatusBand(status="Yellow", start_lap=1, end_lap=2)]


def test_build_status_bands_red_flag_band() -> None:
    transitions = [(0, "5"), (300_000, "1")]
    bands = build_status_bands(transitions, _linear_laps(10), total_laps=10)
    assert bands == [StatusBand(status="Red", start_lap=1, end_lap=3)]


def test_build_status_bands_empty_inputs_return_empty_list() -> None:
    assert build_status_bands([], _linear_laps(10), total_laps=10) == []
    assert build_status_bands([(0, "2")], [], total_laps=10) == []
    assert build_status_bands([(0, "2")], _linear_laps(10), total_laps=0) == []


def test_build_status_bands_non_green_to_non_green_without_allclear() -> None:
    # Yellow on lap 1, VSC deployed mid-lap-5 (449_000 ms) without AllClear in between —
    # close the Yellow at lap 4, open VSC on lap 5. AllClear at 719_000 ms (mid-lap-8)
    # closes VSC at lap 7. Timestamps deliberately placed mid-lap to avoid boundary
    # ambiguity at the `bisect_right` edge.
    transitions = [(0, "2"), (449_000, "6"), (719_000, "1")]
    bands = build_status_bands(transitions, _linear_laps(15), total_laps=15)
    assert bands == [
        StatusBand(status="Yellow",      start_lap=1, end_lap=4),
        StatusBand(status="VSCDeployed", start_lap=5, end_lap=7),
    ]
