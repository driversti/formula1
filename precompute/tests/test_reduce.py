"""Tests for the generic event reducer."""
from __future__ import annotations

from f1.parse import Event
from f1.reduce import deep_merge, reduce_events


def test_deep_merge_overwrites_scalars() -> None:
    base: dict[str, object] = {"a": 1, "b": 2}
    deep_merge(base, {"a": 99})
    assert base == {"a": 99, "b": 2}


def test_deep_merge_recursively_merges_nested_dicts() -> None:
    base: dict[str, object] = {"outer": {"kept": 1, "changed": 2}}
    deep_merge(base, {"outer": {"changed": 20, "added": 30}})
    assert base == {"outer": {"kept": 1, "changed": 20, "added": 30}}


def test_deep_merge_replaces_lists_wholesale() -> None:
    base: dict[str, object] = {"items": [1, 2, 3]}
    deep_merge(base, {"items": [9]})
    assert base == {"items": [9]}


def test_deep_merge_removes_keys_listed_in_deleted() -> None:
    base: dict[str, object] = {"a": 1, "b": 2, "c": 3}
    deep_merge(base, {"_deleted": ["b", "c"], "a": 99})
    assert base == {"a": 99}


def test_deep_merge_deleted_is_tolerant_of_missing_keys() -> None:
    base: dict[str, object] = {"a": 1}
    deep_merge(base, {"_deleted": ["does-not-exist"]})
    assert base == {"a": 1}


def test_reduce_events_applies_patches_in_order() -> None:
    events = [
        Event(timestamp_ms=0, data={"Stints": {}}),
        Event(timestamp_ms=100, data={"Stints": {"1": []}}),
        Event(
            timestamp_ms=200,
            data={"Stints": {"1": {"0": {"Compound": "SOFT", "TotalLaps": 0}}}},
        ),
        Event(
            timestamp_ms=300,
            data={"Stints": {"1": {"0": {"TotalLaps": 5}}}},
        ),
    ]
    state = reduce_events(events)
    assert state == {
        "Stints": {"1": {"0": {"Compound": "SOFT", "TotalLaps": 5}}}
    }


def test_reduce_events_on_empty_list_returns_empty_state() -> None:
    assert reduce_events([]) == {}
