"""Derive per-session status bands (Yellow / SC / VSC / Red) from raw events.

Inputs are the raw `TrackStatus.jsonStream` and `LapCount.jsonStream` events
(walked directly — we need transitions, not reducer terminal state). Output
is a list of `StatusBand` objects keyed to lap numbers, consumable by the
site's `StrategyChart` overlay.
"""
from __future__ import annotations

from collections.abc import Iterable

from f1.parse import Event


def collect_lap_boundaries(events: Iterable[Event]) -> list[tuple[int, int]]:
    """Return `(timestamp_ms, current_lap)` tuples from LapCount events.

    Seeds `(0, 1)` when the first observed lap is > 1 or when the stream is
    empty, so that any timestamp within the session can be resolved to a
    lap via a simple `bisect`.
    """
    out: list[tuple[int, int]] = []
    for event in events:
        current = event.data.get("CurrentLap")
        if isinstance(current, int):
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
