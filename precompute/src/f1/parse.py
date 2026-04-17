"""Parse F1 live-timing .jsonStream files into typed events.

Each line of a .jsonStream file has the shape ``HH:MM:SS.mmm{json-patch}``.
The file begins with a UTF-8 BOM. Malformed lines are skipped so the parser
survives real-world noise in the archive.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

_LINE_RE = re.compile(r"^(\d{2}):(\d{2}):(\d{2})\.(\d{3})(.+)$")


@dataclass(frozen=True, slots=True)
class Event:
    """A single event read from a .jsonStream file."""

    timestamp_ms: int
    data: dict[str, object]


def parse_stream(path: Path) -> list[Event]:
    """Read ``path`` as a .jsonStream file and return its events in order."""
    content = path.read_text(encoding="utf-8-sig")
    events: list[Event] = []
    for raw in content.splitlines():
        line = raw.strip()
        if not line:
            continue
        match = _LINE_RE.match(line)
        if not match:
            continue
        h, m, s, ms, payload = match.groups()
        timestamp_ms = (
            int(h) * 3_600_000
            + int(m) * 60_000
            + int(s) * 1_000
            + int(ms)
        )
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        events.append(Event(timestamp_ms=timestamp_ms, data=data))
    return events
