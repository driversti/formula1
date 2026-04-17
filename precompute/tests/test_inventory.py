"""Tests for stint extraction and tyre-set tracking."""
from __future__ import annotations

from f1.inventory import SessionStint, extract_session_stints


def test_extract_session_stints_returns_typed_records() -> None:
    state: dict[str, object] = {
        "Stints": {
            "1": {
                "0": {
                    "Compound": "SOFT",
                    "New": "true",
                    "TotalLaps": 8,
                    "StartLaps": 0,
                },
                "1": {
                    "Compound": "MEDIUM",
                    "New": "false",
                    "TotalLaps": 5,
                    "StartLaps": 2,
                },
            },
            "16": {
                "0": {
                    "Compound": "HARD",
                    "New": "true",
                    "TotalLaps": 12,
                    "StartLaps": 0,
                },
            },
        },
    }
    stints = extract_session_stints("FP1", state)
    # Ordered by driver, then by stint index.
    assert stints == [
        SessionStint("FP1", "1", 0, "SOFT", True, 0, 8),
        SessionStint("FP1", "1", 1, "MEDIUM", False, 2, 5),
        SessionStint("FP1", "16", 0, "HARD", True, 0, 12),
    ]


def test_extract_session_stints_tolerates_empty_and_list_values() -> None:
    state: dict[str, object] = {
        "Stints": {
            "1": [],
            "2": {},
            "3": {"0": {"Compound": "SOFT", "New": "true", "TotalLaps": 0, "StartLaps": 0}},
        }
    }
    stints = extract_session_stints("FP1", state)
    assert [s.driver_number for s in stints] == ["3"]


def test_extract_session_stints_returns_empty_when_no_stints_key() -> None:
    assert extract_session_stints("FP1", {}) == []


def test_extract_session_stints_ignores_unknown_compound() -> None:
    state: dict[str, object] = {
        "Stints": {
            "1": {
                "0": {
                    "Compound": "UNKNOWN",
                    "New": "false",
                    "TotalLaps": 0,
                    "StartLaps": 0,
                },
                "1": {
                    "Compound": "SOFT",
                    "New": "true",
                    "TotalLaps": 3,
                    "StartLaps": 0,
                },
            }
        }
    }
    stints = extract_session_stints("FP1", state)
    assert [s.compound for s in stints] == ["SOFT"]
