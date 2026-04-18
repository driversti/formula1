"""Extract per-session stints and track tyre sets across the weekend."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from f1.models import Compound, SessionKey, TyreSet

if TYPE_CHECKING:
    from f1.models import RaceStint

_SESSION_ORDER: list[SessionKey] = ["FP1", "FP2", "FP3", "SQ", "S", "Q", "R"]


@dataclass(frozen=True, slots=True)
class SessionStint:
    """One stint by one driver in one session."""

    session_key: SessionKey
    driver_number: str
    stint_idx: int
    compound: Compound
    new_when_out: bool
    start_laps: int
    total_laps: int

    @property
    def stint_laps(self) -> int:
        """Laps driven in this stint (= total wear now minus wear at stint start)."""
        return max(0, self.total_laps - self.start_laps)

    @property
    def end_laps(self) -> int:
        """Total tyre wear after this stint (alias for total_laps)."""
        return self.total_laps


def _to_bool(value: object) -> bool:
    """The raw feed encodes booleans as the strings 'true' / 'false'."""
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


def _to_int(value: object, default: int = 0) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def extract_session_stints(
    session_key: SessionKey,
    reduced_state: dict[str, object],
) -> list[SessionStint]:
    """Turn a reduced TyreStintSeries state into ordered SessionStint records.

    Stints whose Compound is not one of the five canonical values are
    silently skipped; they represent transitional pit-stop states.
    """
    stints_by_driver = reduced_state.get("Stints")
    if not isinstance(stints_by_driver, dict):
        return []

    valid_compounds = {"SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"}
    result: list[SessionStint] = []
    for driver_number in sorted(stints_by_driver.keys(), key=_sort_key):
        driver_stints = stints_by_driver[driver_number]
        if not isinstance(driver_stints, dict):
            continue
        for idx_key in sorted(driver_stints.keys(), key=_sort_key):
            raw = driver_stints[idx_key]
            if not isinstance(raw, dict):
                continue
            compound = raw.get("Compound")
            if compound not in valid_compounds:
                continue
            result.append(
                SessionStint(
                    session_key=session_key,
                    driver_number=str(driver_number),
                    stint_idx=_to_int(idx_key),
                    compound=compound,  # type: ignore[arg-type]
                    new_when_out=_to_bool(raw.get("New")),
                    start_laps=_to_int(raw.get("StartLaps")),
                    total_laps=_to_int(raw.get("TotalLaps")),
                )
            )
    return result


def _sort_key(value: object) -> tuple[int, str]:
    """Sort numeric keys numerically, but keep non-numeric keys stable."""
    s = str(value)
    try:
        return (0, f"{int(s):08d}")
    except ValueError:
        return (1, s)


_COMPOUND_SHORT: dict[Compound, str] = {
    "SOFT": "SOFT",
    "MEDIUM": "MED",
    "HARD": "HARD",
    "INTERMEDIATE": "INT",
    "WET": "WET",
}


def _next_set_id(driver_tla: str, compound: Compound, sets: list[TyreSet]) -> str:
    count = sum(1 for s in sets if s.compound == compound) + 1
    return f"{driver_tla}-{_COMPOUND_SHORT[compound]}-{count}"


def _find_match(sets: list[TyreSet], compound: Compound, target_laps: int) -> TyreSet | None:
    for s in sets:
        if s.compound == compound and s.laps == target_laps:
            return s
    return None


def build_inventory(
    driver_number: str,
    driver_tla: str,
    stints_by_session: dict[SessionKey, list[SessionStint]],
) -> list[TyreSet]:
    """Two-pass algorithm: fully track FP1-Q, then discover saved-for-race in R.

    The resulting ``TyreSet.laps`` always holds the pre-race state.
    """
    sets: list[TyreSet] = []

    # Pass A: FP1 -> FP2 -> FP3 -> SQ -> S -> Q, full tracking.
    for session in ("FP1", "FP2", "FP3", "SQ", "S", "Q"):
        session_key: SessionKey = session  # type: ignore[assignment]
        for stint in stints_by_session.get(session_key, []):
            if stint.driver_number != driver_number:
                continue
            if stint.new_when_out:
                sets.append(
                    TyreSet(
                        set_id=_next_set_id(driver_tla, stint.compound, sets),
                        compound=stint.compound,
                        laps=stint.end_laps,
                        new_at_first_use=True,
                        first_seen_session=session_key,
                        last_seen_session=session_key,
                    )
                )
                continue

            match = _find_match(sets, stint.compound, stint.start_laps)
            if match is not None:
                match.laps = stint.end_laps
                match.last_seen_session = session_key
            else:
                # Used stint with no prior match — best-effort inclusion.
                sets.append(
                    TyreSet(
                        set_id=_next_set_id(driver_tla, stint.compound, sets),
                        compound=stint.compound,
                        laps=stint.end_laps,
                        new_at_first_use=False,
                        first_seen_session=session_key,
                        last_seen_session=session_key,
                    )
                )

    # Pass B: Race, discovery only — never mutate existing sets.
    for stint in stints_by_session.get("R", []):
        if stint.driver_number != driver_number:
            continue
        match = _find_match(sets, stint.compound, stint.start_laps)
        if match is not None:
            # Pre-race state preserved — do nothing.
            continue
        if stint.new_when_out:
            # Driver saved this set for the race.
            sets.append(
                TyreSet(
                    set_id=_next_set_id(driver_tla, stint.compound, sets),
                    compound=stint.compound,
                    laps=0,
                    new_at_first_use=True,
                    first_seen_session="R",
                    last_seen_session="R",
                )
            )
        else:
            # Used set never seen before — include with its start_laps.
            sets.append(
                TyreSet(
                    set_id=_next_set_id(driver_tla, stint.compound, sets),
                    compound=stint.compound,
                    laps=stint.start_laps,
                    new_at_first_use=False,
                    first_seen_session="R",
                    last_seen_session="R",
                )
            )

    return sets


def build_race_stints(
    *,
    driver_number: str,
    stints_for_session: list[SessionStint],
    driver_lap_count: int | None = None,
) -> list[RaceStint]:
    """Turn this driver's ``SessionStint`` records into lap-indexed ``RaceStint``s.

    ``stints_for_session`` is all stints for this driver in the session.
    Zero-lap stints are skipped (they represent in-progress states the feed
    sometimes emits at pit exit/entry). Output is sorted by ``stint_idx`` and
    stints are laid end-to-end: stint N starts at the lap after stint N-1 ends.

    If driver_lap_count is provided (from TimingData.NumberOfLaps) and
    exceeds the sum of per-stint laps, the last stint is extended by the
    delta. This reconciles TyreStintSeries underreporting (the feed can
    stop emitting updates mid-session, most commonly right after a pit
    stop).
    """
    from f1.models import RaceStint  # local import to keep inventory.py model-light

    mine = [s for s in stints_for_session if s.driver_number == driver_number and s.stint_laps > 0]
    mine.sort(key=lambda s: s.stint_idx)

    result: list[RaceStint] = []
    next_start = 1
    for s in mine:
        laps = s.stint_laps
        end = next_start + laps - 1
        result.append(
            RaceStint(
                stint_idx=s.stint_idx,
                compound=s.compound,
                start_lap=next_start,
                end_lap=end,
                laps=laps,
                new=s.new_when_out,
            )
        )
        next_start = end + 1

    # Reconcile against authoritative TimingData lap count.
    if result and driver_lap_count is not None:
        total_stint_laps = sum(s.laps for s in result)
        gap = driver_lap_count - total_stint_laps
        if gap > 0:
            last = result[-1]
            result[-1] = RaceStint(
                stint_idx=last.stint_idx,
                compound=last.compound,
                start_lap=last.start_lap,
                end_lap=last.end_lap + gap,
                laps=last.laps + gap,
                new=last.new,
            )

    return result
