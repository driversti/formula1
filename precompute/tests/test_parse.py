"""Tests for the jsonStream line parser."""
from __future__ import annotations

from pathlib import Path

import pytest

from f1.parse import Event, parse_stream


def test_parse_stream_returns_events_with_offsets(fixtures_dir: Path) -> None:
    events = parse_stream(fixtures_dir / "tiny_stream.jsonStream")
    assert len(events) == 2
    assert events[0] == Event(timestamp_ms=5_100, data={"A": 1})
    assert events[1] == Event(timestamp_ms=90_250, data={"A": 2, "B": "x"})


def test_parse_stream_strips_utf8_bom(fixtures_dir: Path) -> None:
    # The fixture starts with a BOM; parsing must not choke on it.
    events = parse_stream(fixtures_dir / "tiny_stream.jsonStream")
    assert events[0].data == {"A": 1}


def test_parse_stream_skips_blank_and_malformed_lines(tmp_path: Path) -> None:
    path = tmp_path / "mixed.jsonStream"
    path.write_text(
        '\n'
        '00:00:01.000{"ok":true}\n'
        'not-a-line\n'
        '   \n'
        '00:00:02.000{"also":true}\n',
        encoding="utf-8",
    )
    events = parse_stream(path)
    assert [e.timestamp_ms for e in events] == [1_000, 2_000]


def test_parse_stream_raises_on_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        parse_stream(tmp_path / "nope.jsonStream")


def test_parse_stream_skips_lines_whose_json_is_not_a_dict(tmp_path: Path) -> None:
    path = tmp_path / "nondict.jsonStream"
    path.write_text(
        '00:00:01.000[1,2,3]\n'       # JSON list — must be skipped
        '00:00:02.000"hello"\n'       # JSON string — must be skipped
        '00:00:03.000{"ok":true}\n',  # Proper dict — must survive
        encoding="utf-8",
    )
    events = parse_stream(path)
    assert [e.timestamp_ms for e in events] == [3_000]
    assert events[0].data == {"ok": True}
