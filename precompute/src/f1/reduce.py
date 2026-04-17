"""Generic event-sourcing reducer for F1 live-timing streams.

Events are JSON patches against an accumulating state dict. Objects merge
recursively, lists are replaced wholesale, and a special ``_deleted`` key
removes top-level entries at that nesting level.
"""
from __future__ import annotations

from collections.abc import Iterable

from f1.parse import Event


def deep_merge(base: dict[str, object], patch: dict[str, object]) -> dict[str, object]:
    """Apply ``patch`` onto ``base`` in place and return ``base``."""
    deleted = patch.pop("_deleted", None)
    if isinstance(deleted, list):
        for key in deleted:
            base.pop(str(key), None)

    for key, value in patch.items():
        existing = base.get(key)
        if isinstance(value, dict) and isinstance(existing, dict):
            deep_merge(existing, value)
        else:
            base[key] = value
    return base


def reduce_events(events: Iterable[Event]) -> dict[str, object]:
    """Apply all events in order and return the final state."""
    state: dict[str, object] = {}
    for event in events:
        # Copy so callers keep their event data untouched.
        deep_merge(state, dict(event.data))
    return state
