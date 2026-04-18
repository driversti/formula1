"""Derive per-session status bands (Yellow / SC / VSC / Red) from raw events.

Inputs are the raw `TrackStatus.jsonStream` and `LapCount.jsonStream` events
(walked directly — we need transitions, not reducer terminal state). Output
is a list of `StatusBand` objects keyed to lap numbers, consumable by the
site's `StrategyChart` overlay.
"""
from __future__ import annotations

import bisect
from collections.abc import Iterable

from f1.models import StatusBand, TrackStatusCode
from f1.parse import Event

# F1 live-timing TrackStatus code → our enum label. Codes not in this map
# (notably "1" AllClear and "7" VSCEnding) are treated as band closers.
_CODE_TO_STATUS: dict[str, TrackStatusCode] = {
    "2": "Yellow",
    "4": "SCDeployed",
    "5": "Red",
    "6": "VSCDeployed",
}


def collect_lap_boundaries(events: Iterable[Event]) -> list[tuple[int, int]]:
    """Return `(timestamp_ms, current_lap)` tuples from LapCount events.

    Seeds `(0, 1)` when the first observed lap is > 1 or when the stream is
    empty, so that any timestamp within the session can be resolved to a
    lap via a simple `bisect`.
    """
    out: list[tuple[int, int]] = []
    for event in events:
        current = event.data.get("CurrentLap")
        # The live-timing feed occasionally emits CurrentLap=0 during the
        # formation-lap window before the race begins. Skip those so the seed
        # below always establishes lap ≥ 1 as the floor.
        if isinstance(current, int) and current >= 1:
            out.append((event.timestamp_ms, current))

    if not out or out[0][1] > 1:
        out.insert(0, (0, 1))
    return out


def collect_status_transitions(events: Iterable[Event]) -> list[tuple[int, str]]:
    """Return `(timestamp_ms, status_code)` tuples for well-formed TrackStatus events.

    Skips events that are missing the `Status` field or have a non-string value.
    Includes `AllClear` ("1") so callers can detect band-closing transitions.
    """
    out: list[tuple[int, str]] = []
    for event in events:
        status = event.data.get("Status")
        if isinstance(status, str):
            out.append((event.timestamp_ms, status))
    return out


def _lap_at(timestamp_ms: int, lap_boundaries: list[tuple[int, int]]) -> int:
    """Return the lap number that was current at ``timestamp_ms``.

    Binary search by timestamp. Because ``collect_lap_boundaries`` seeds
    ``(0, 1)``, any non-negative timestamp resolves to lap ≥ 1.
    """
    timestamps = [ts for ts, _ in lap_boundaries]
    idx = bisect.bisect_right(timestamps, timestamp_ms) - 1
    if idx < 0:
        return 1
    return lap_boundaries[idx][1]


def build_status_bands(
    transitions: list[tuple[int, str]],
    lap_boundaries: list[tuple[int, int]],
    total_laps: int,
) -> list[StatusBand]:
    """Collapse transitions into ``StatusBand`` objects mapped to lap numbers.

    A non-green code opens a band. ``AllClear`` closes any active band.
    ``VSCEnding`` closes only an active ``VSCDeployed``. If a band is still
    open at the end of the stream, ``end_lap`` is clamped to ``total_laps``.
    """
    if not lap_boundaries or total_laps < 1:
        return []

    bands: list[StatusBand] = []
    open_status: TrackStatusCode | None = None
    open_start_lap: int | None = None

    for ts, code in transitions:
        lap = min(_lap_at(ts, lap_boundaries), total_laps)

        if code == "1":  # AllClear closes any active band
            if open_status is not None and open_start_lap is not None:
                end_lap = max(lap - 1, open_start_lap)
                bands.append(
                    StatusBand(status=open_status, start_lap=open_start_lap, end_lap=end_lap)
                )
                open_status = None
                open_start_lap = None
            continue

        if code == "7":  # VSCEnding closes only VSCDeployed
            if open_status == "VSCDeployed" and open_start_lap is not None:
                end_lap = max(lap - 1, open_start_lap)
                bands.append(
                    StatusBand(status="VSCDeployed", start_lap=open_start_lap, end_lap=end_lap)
                )
                open_status = None
                open_start_lap = None
            continue

        new_status = _CODE_TO_STATUS.get(code)
        if new_status is None:
            continue  # Unknown code — ignore.
        if open_status == new_status:
            continue  # Duplicate; don't split the band.

        # Different non-green status arrives without an AllClear between —
        # close the old one at lap-1 (or start_lap if same lap) and open the new.
        if open_status is not None and open_start_lap is not None:
            end_lap = max(lap - 1, open_start_lap)
            bands.append(
                StatusBand(status=open_status, start_lap=open_start_lap, end_lap=end_lap)
            )

        open_status = new_status
        open_start_lap = lap

    # Band still open at session end → clamp to total_laps.
    if open_status is not None and open_start_lap is not None:
        bands.append(StatusBand(status=open_status, start_lap=open_start_lap, end_lap=total_laps))

    return bands
