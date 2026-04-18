"""Unit tests for precompute/src/f1/track_status.py."""
from __future__ import annotations

from f1.parse import Event
from f1.track_status import collect_status_transitions


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
