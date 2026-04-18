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


# --- Pass A tests -----------------------------------------------------------

def test_pass_a_creates_new_set_on_new_true() -> None:
    from f1.inventory import build_inventory

    stints = {
        "FP1": [SessionStint("FP1", "1", 0, "SOFT", True, 0, 8)],
    }
    sets = build_inventory(driver_number="1", driver_tla="VER", stints_by_session=stints)
    assert len(sets) == 1
    s = sets[0]
    assert s.set_id == "VER-SOFT-1"
    assert s.compound == "SOFT"
    assert s.laps == 8
    assert s.new_at_first_use is True
    assert s.first_seen_session == "FP1"
    assert s.last_seen_session == "FP1"


def test_pass_a_matches_continuing_set_by_compound_and_laps() -> None:
    from f1.inventory import build_inventory

    stints = {
        "FP1": [SessionStint("FP1", "1", 0, "SOFT", True, 0, 8)],
        "FP2": [SessionStint("FP2", "1", 0, "SOFT", False, 8, 10)],
    }
    sets = build_inventory(driver_number="1", driver_tla="VER", stints_by_session=stints)
    assert len(sets) == 1
    s = sets[0]
    assert s.laps == 10
    assert s.first_seen_session == "FP1"
    assert s.last_seen_session == "FP2"


def test_pass_a_two_separate_same_compound_sets_get_distinct_ids() -> None:
    from f1.inventory import build_inventory

    stints = {
        "Q": [
            SessionStint("Q", "1", 0, "SOFT", True, 0, 3),
            SessionStint("Q", "1", 1, "SOFT", True, 0, 2),
            SessionStint("Q", "1", 2, "SOFT", True, 0, 3),
        ],
    }
    sets = build_inventory(driver_number="1", driver_tla="VER", stints_by_session=stints)
    assert [s.set_id for s in sets] == ["VER-SOFT-1", "VER-SOFT-2", "VER-SOFT-3"]
    assert [s.laps for s in sets] == [3, 2, 3]


def test_pass_a_unmatched_used_stint_creates_set_with_start_laps() -> None:
    from f1.inventory import build_inventory

    # Used stint with no earlier history — treat as best-effort new set.
    stints = {
        "FP2": [SessionStint("FP2", "1", 0, "HARD", False, 4, 7)],
    }
    sets = build_inventory(driver_number="1", driver_tla="VER", stints_by_session=stints)
    assert len(sets) == 1
    assert sets[0].laps == 7
    assert sets[0].new_at_first_use is False


def test_pass_a_skips_sessions_with_no_stints_for_driver() -> None:
    from f1.inventory import build_inventory

    stints = {
        "FP1": [SessionStint("FP1", "1", 0, "SOFT", True, 0, 8)],
        # no FP2, FP3, Q for this driver
    }
    sets = build_inventory(driver_number="1", driver_tla="VER", stints_by_session=stints)
    assert len(sets) == 1


# --- Pass B tests -----------------------------------------------------------

def test_pass_b_discovers_saved_for_race_set() -> None:
    from f1.inventory import build_inventory

    # MED-2 first appears in the Race session as a new set -> saved for race.
    stints = {
        "FP1": [SessionStint("FP1", "1", 0, "MEDIUM", True, 0, 5)],
        "R": [SessionStint("R", "1", 0, "MEDIUM", True, 0, 25)],
    }
    sets = build_inventory(driver_number="1", driver_tla="VER", stints_by_session=stints)
    assert len(sets) == 2
    saved = [s for s in sets if s.first_seen_session == "R"]
    assert len(saved) == 1
    assert saved[0].laps == 0  # pre-race state
    assert saved[0].new_at_first_use is True


def test_pass_b_does_not_mutate_existing_set_laps() -> None:
    from f1.inventory import build_inventory

    # HARD-1 seen in FP2 at 12 laps; race uses it from lap 12 -> 45 laps.
    # Pre-race laps must remain 12.
    stints = {
        "FP2": [SessionStint("FP2", "1", 0, "HARD", True, 0, 12)],
        "R": [SessionStint("R", "1", 0, "HARD", False, 12, 45)],
    }
    sets = build_inventory(driver_number="1", driver_tla="VER", stints_by_session=stints)
    assert len(sets) == 1
    assert sets[0].laps == 12
    assert sets[0].last_seen_session == "FP2"


def test_pass_b_used_set_first_seen_in_race_is_created_with_start_laps() -> None:
    from f1.inventory import build_inventory

    # Used HARD first appears in Race — something we missed earlier.
    # Include at pre-race state start_laps=8.
    stints = {
        "R": [SessionStint("R", "1", 0, "HARD", False, 8, 33)],
    }
    sets = build_inventory(driver_number="1", driver_tla="VER", stints_by_session=stints)
    assert len(sets) == 1
    assert sets[0].laps == 8
    assert sets[0].first_seen_session == "R"


def test_full_weekend_example_verstappen() -> None:
    from f1.inventory import build_inventory

    stints = {
        "FP1": [
            SessionStint("FP1", "1", 0, "SOFT", True, 0, 8),
            SessionStint("FP1", "1", 1, "MEDIUM", True, 0, 5),
        ],
        "FP2": [
            SessionStint("FP2", "1", 0, "SOFT", False, 8, 10),
            SessionStint("FP2", "1", 1, "HARD", True, 0, 12),
        ],
        "FP3": [
            SessionStint("FP3", "1", 0, "MEDIUM", False, 5, 8),
        ],
        "Q": [
            SessionStint("Q", "1", 0, "SOFT", True, 0, 3),
            SessionStint("Q", "1", 1, "SOFT", True, 0, 2),
            SessionStint("Q", "1", 2, "SOFT", True, 0, 3),
        ],
        "R": [
            SessionStint("R", "1", 0, "MEDIUM", True, 0, 25),
            SessionStint("R", "1", 1, "HARD", False, 12, 45),
        ],
    }
    sets = build_inventory(driver_number="1", driver_tla="VER", stints_by_session=stints)
    by_id = {s.set_id: s for s in sets}
    assert by_id["VER-HARD-1"].laps == 12
    assert by_id["VER-MED-1"].laps == 8
    assert by_id["VER-MED-2"].laps == 0
    assert by_id["VER-MED-2"].first_seen_session == "R"
    assert by_id["VER-SOFT-1"].laps == 10
    assert by_id["VER-SOFT-2"].laps == 3
    assert by_id["VER-SOFT-3"].laps == 2
    assert by_id["VER-SOFT-4"].laps == 3


def test_pass_a_includes_sprint_sessions_in_chronological_order() -> None:
    from f1.inventory import build_inventory

    stints = {
        "FP1": [],
        "SQ": [SessionStint("SQ", "1", 0, "MEDIUM", True, 0, 2)],
        "S":  [SessionStint("S",  "1", 0, "HARD",   True, 0, 8)],
        "Q":  [SessionStint("Q",  "1", 0, "MEDIUM", False, 2, 3)],
    }
    sets = build_inventory(driver_number="1", driver_tla="VER", stints_by_session=stints)

    # One MEDIUM (continued SQ → Q) and one HARD (only S).
    assert len(sets) == 2
    med = next(s for s in sets if s.compound == "MEDIUM")
    assert med.first_seen_session == "SQ"
    assert med.last_seen_session == "Q"
    assert med.laps == 3           # 2 (SQ) + 1 (Q)
    hard = next(s for s in sets if s.compound == "HARD")
    assert hard.first_seen_session == "S"
    assert hard.last_seen_session == "S"
    assert hard.laps == 8
