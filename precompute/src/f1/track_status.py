"""Derive per-session status bands (Yellow / SC / VSC / Red) from raw events.

Inputs are the raw `TrackStatus.jsonStream` and `LapCount.jsonStream` events
(walked directly — we need transitions, not reducer terminal state). Output
is a list of `StatusBand` objects keyed to lap numbers, consumable by the
site's `StrategyChart` overlay.
"""
from __future__ import annotations

from collections.abc import Iterable

from f1.parse import Event


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
