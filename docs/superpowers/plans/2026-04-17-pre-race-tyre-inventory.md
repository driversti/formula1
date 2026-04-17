# Pre-Race Tyre Inventory Viewer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a static website that displays each driver's reconstructed pre-race tyre inventory for the Australian Grand Prix 2026, using Python to precompute JSON from raw `.jsonStream` archives and Vite/React/TypeScript to render the site.

**Architecture:** Two independent sub-projects communicate through a single JSON artifact. Python (`precompute/`) parses raw F1 live-timing files with a generic event-sourcing reducer and runs a two-pass tyre-set tracking algorithm to produce `australia-2026.json`. TypeScript (`site/`) loads and Zod-validates that JSON at runtime, then renders a grid home page and per-driver detail pages. A root-level `Makefile` orchestrates local dev, and GitHub Actions deploys the built `dist/` to GitHub Pages on every push to `main`.

**Tech Stack:** Python 3.13 · uv · Pydantic 2 · Pytest · Vite 6 · React 19 · TypeScript (strict) · React Router 7 · Tailwind CSS 4 · visx · Zod · Vitest · Playwright

---

## File Structure

```
formula1/
├── Makefile                                      # NEW orchestration
├── .github/workflows/deploy.yml                  # NEW CI/CD
│
├── precompute/                                   # NEW Python package
│   ├── pyproject.toml
│   ├── src/f1/
│   │   ├── __init__.py
│   │   ├── models.py         # Pydantic schemas
│   │   ├── parse.py          # jsonStream line parser
│   │   ├── reduce.py         # event → state reducer
│   │   ├── inventory.py      # stint extraction + 2-pass tracker
│   │   ├── driver_meta.py    # DriverList + grid position
│   │   ├── build.py          # CLI entry point
│   │   └── schema.py         # JSON Schema exporter
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_parse.py
│   │   ├── test_reduce.py
│   │   ├── test_models.py
│   │   ├── test_inventory.py
│   │   ├── test_driver_meta.py
│   │   └── test_build.py
│   ├── fixtures/                                 # minimal jsonStream samples
│   └── out/                                      # generated artifacts
│       ├── australia-2026.json
│       └── schema.json
│
└── site/                                         # NEW Vite app
    ├── package.json
    ├── vite.config.ts
    ├── tailwind.config.ts
    ├── tsconfig.json
    ├── tsconfig.node.json
    ├── index.html
    ├── playwright.config.ts
    ├── scripts/gen-zod.mjs                       # JSON Schema → Zod
    ├── public/404.html                           # GH Pages SPA fallback
    ├── public/data/                              # copied from ../precompute/out
    ├── src/
    │   ├── main.tsx
    │   ├── App.tsx
    │   ├── lib/
    │   │   ├── schemas.ts                         # generated Zod (committed)
    │   │   └── data.ts
    │   ├── routes/
    │   │   ├── Home.tsx
    │   │   ├── Driver.tsx
    │   │   └── NotFound.tsx
    │   ├── components/
    │   │   ├── RaceHeader.tsx
    │   │   ├── DriverGrid.tsx
    │   │   ├── DriverCard.tsx
    │   │   ├── DriverHeader.tsx
    │   │   ├── TyreDot.tsx
    │   │   ├── TyreSet.tsx
    │   │   ├── UsageBar.tsx
    │   │   └── InventoryView.tsx
    │   └── styles/index.css
    └── tests/
        ├── unit/
        │   ├── schemas.test.ts
        │   ├── data.test.ts
        │   ├── TyreDot.test.tsx
        │   └── DriverCard.test.tsx
        └── e2e/
            ├── home.spec.ts
            ├── driver.spec.ts
            └── routing.spec.ts
```

---

# Section A — Python Precompute

## Task A1: Scaffold the precompute package

**Files:**
- Create: `precompute/pyproject.toml`
- Create: `precompute/src/f1/__init__.py`
- Create: `precompute/tests/__init__.py`
- Create: `precompute/tests/conftest.py`

- [ ] **Step 1: Create `precompute/pyproject.toml`**

```toml
[project]
name = "f1-precompute"
version = "0.1.0"
description = "Precompute F1 tyre inventory JSON from live-timing archive"
requires-python = ">=3.13"
dependencies = [
    "pydantic>=2.7",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "mypy>=1.10",
    "ruff>=0.5",
]

[project.scripts]
f1-build = "f1.build:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/f1"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-v --strict-markers --cov=f1 --cov-report=term-missing --cov-fail-under=85"

[tool.mypy]
strict = true
python_version = "3.13"

[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "N", "B", "SIM"]
```

- [ ] **Step 2: Create `precompute/src/f1/__init__.py`**

```python
"""F1 tyre inventory precompute package."""

__version__ = "0.1.0"
```

- [ ] **Step 3: Create `precompute/tests/__init__.py`**

```python
```

- [ ] **Step 4: Create `precompute/tests/conftest.py`**

```python
"""Shared pytest fixtures."""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to the fixtures directory."""
    return Path(__file__).parent.parent / "fixtures"
```

- [ ] **Step 5: Install dependencies and verify structure**

Run: `cd precompute && uv sync --extra dev`
Expected: `Resolved X packages` without errors.

Run: `cd precompute && uv run pytest --collect-only`
Expected: Pytest discovers 0 tests (no errors, empty suite).

- [ ] **Step 6: Commit**

```bash
git add precompute/
git commit -m "chore: scaffold precompute Python package"
```

---

## Task A2: jsonStream parser

**Files:**
- Create: `precompute/src/f1/parse.py`
- Create: `precompute/tests/test_parse.py`
- Create: `precompute/fixtures/tiny_stream.jsonStream`

- [ ] **Step 1: Create fixture `precompute/fixtures/tiny_stream.jsonStream`**

Use `printf` to write the exact bytes, including the leading UTF-8 BOM (`\xef\xbb\xbf`):

```bash
mkdir -p precompute/fixtures
printf '\xef\xbb\xbf00:00:05.100{"A":1}\n00:01:30.250{"A":2,"B":"x"}\n' \
  > precompute/fixtures/tiny_stream.jsonStream
```

Verify:
```bash
od -c precompute/fixtures/tiny_stream.jsonStream | head -1
```
Expected first three octal-escaped bytes: `357 273 277` (that's the UTF-8 BOM).

- [ ] **Step 2: Write failing test `precompute/tests/test_parse.py`**

```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd precompute && uv run pytest tests/test_parse.py -v`
Expected: `ModuleNotFoundError: No module named 'f1.parse'`.

- [ ] **Step 4: Implement `precompute/src/f1/parse.py`**

```python
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
        events.append(Event(timestamp_ms=timestamp_ms, data=data))
    return events
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd precompute && uv run pytest tests/test_parse.py -v`
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add precompute/src/f1/parse.py precompute/tests/test_parse.py precompute/fixtures/tiny_stream.jsonStream
git commit -m "feat(precompute): add jsonStream line parser"
```

---

## Task A3: Event reducer

**Files:**
- Create: `precompute/src/f1/reduce.py`
- Create: `precompute/tests/test_reduce.py`

- [ ] **Step 1: Write failing tests `precompute/tests/test_reduce.py`**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd precompute && uv run pytest tests/test_reduce.py -v`
Expected: `ModuleNotFoundError: No module named 'f1.reduce'`.

- [ ] **Step 3: Implement `precompute/src/f1/reduce.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd precompute && uv run pytest tests/test_reduce.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add precompute/src/f1/reduce.py precompute/tests/test_reduce.py
git commit -m "feat(precompute): add generic event reducer"
```

---

## Task A4: Pydantic models

**Files:**
- Create: `precompute/src/f1/models.py`
- Create: `precompute/tests/test_models.py`

- [ ] **Step 1: Write failing tests `precompute/tests/test_models.py`**

```python
"""Tests for the Pydantic data model."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from f1.models import (
    Compound,
    DriverInventory,
    Manifest,
    Race,
    SessionRef,
    TyreSet,
)


def _minimal_set(**overrides: object) -> TyreSet:
    base: dict[str, object] = {
        "set_id": "VER-MED-1",
        "compound": "MEDIUM",
        "laps": 0,
        "new_at_first_use": True,
        "first_seen_session": "FP1",
        "last_seen_session": "FP1",
    }
    base.update(overrides)
    return TyreSet(**base)  # type: ignore[arg-type]


def test_tyreset_accepts_valid_payload() -> None:
    s = _minimal_set(laps=5)
    assert s.compound == "MEDIUM"
    assert s.laps == 5


def test_tyreset_rejects_negative_laps() -> None:
    with pytest.raises(ValidationError):
        _minimal_set(laps=-1)


def test_tyreset_rejects_unknown_compound() -> None:
    with pytest.raises(ValidationError):
        _minimal_set(compound="UNKNOWN")  # type: ignore[arg-type]


def test_driver_inventory_requires_three_letter_tla() -> None:
    with pytest.raises(ValidationError):
        DriverInventory(
            racing_number="1",
            tla="VE",
            full_name="Max Verstappen",
            team_name="Red Bull Racing",
            team_color="#4781D7",
            grid_position=1,
            sets=[],
        )


def test_driver_inventory_requires_hex_team_color() -> None:
    with pytest.raises(ValidationError):
        DriverInventory(
            racing_number="1",
            tla="VER",
            full_name="Max Verstappen",
            team_name="Red Bull Racing",
            team_color="red",
            grid_position=1,
            sets=[],
        )


def test_driver_inventory_sets_by_compound_groups_correctly() -> None:
    inv = DriverInventory(
        racing_number="1",
        tla="VER",
        full_name="Max Verstappen",
        team_name="Red Bull Racing",
        team_color="#4781D7",
        grid_position=None,
        sets=[
            _minimal_set(set_id="VER-HARD-1", compound="HARD"),
            _minimal_set(set_id="VER-MED-1", compound="MEDIUM"),
            _minimal_set(set_id="VER-MED-2", compound="MEDIUM"),
        ],
    )
    grouped = inv.sets_by_compound
    assert list(grouped.keys()) == ["HARD", "MEDIUM"]
    assert [s.set_id for s in grouped["MEDIUM"]] == ["VER-MED-1", "VER-MED-2"]


def test_race_and_manifest_compose() -> None:
    session = SessionRef(
        key="R",
        name="Race",
        path="2026/.../2026-03-08_Race/",
        start_utc="2026-03-08T04:00:00Z",
    )
    race = Race(
        slug="australia-2026",
        name="Australian Grand Prix",
        location="Melbourne",
        country="Australia",
        season=2026,
        round=1,
        date="2026-03-08",
        sessions=[session],
        drivers=[],
    )
    manifest = Manifest(
        schema_version="1.0.0",
        generated_at="2026-04-17T12:00:00Z",
        race=race,
    )
    assert manifest.race.slug == "australia-2026"
    assert manifest.schema_version == "1.0.0"


def test_compound_literal_values() -> None:
    allowed = {"SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"}
    assert set(Compound.__args__) == allowed  # type: ignore[attr-defined]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd precompute && uv run pytest tests/test_models.py -v`
Expected: `ModuleNotFoundError: No module named 'f1.models'`.

- [ ] **Step 3: Implement `precompute/src/f1/models.py`**

```python
"""Pydantic data model for the precomputed JSON artifact.

These models are the single source of truth: JSON Schema is exported from
them and consumed by the TypeScript site to generate matching Zod schemas.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Compound = Literal["SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"]
SessionKey = Literal["FP1", "FP2", "FP3", "Q", "R"]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)


class TyreSet(_StrictModel):
    """One physical tyre set, identified by tracking stints across sessions."""

    set_id: str = Field(..., description="Synthetic id, e.g. VER-MED-1")
    compound: Compound
    laps: int = Field(ge=0, description="Total laps at race start (pre-race state)")
    new_at_first_use: bool
    first_seen_session: SessionKey
    last_seen_session: SessionKey


class DriverInventory(_StrictModel):
    """All tyre sets known to belong to a single driver."""

    racing_number: str = Field(..., min_length=1)
    tla: str = Field(..., min_length=3, max_length=3)
    full_name: str
    team_name: str
    team_color: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$")
    grid_position: int | None = Field(default=None, ge=1, le=22)
    sets: list[TyreSet]

    @property
    def sets_by_compound(self) -> dict[Compound, list[TyreSet]]:
        """Group sets by compound, preserving first-seen order."""
        grouped: dict[Compound, list[TyreSet]] = {}
        for s in self.sets:
            grouped.setdefault(s.compound, []).append(s)
        return grouped


class SessionRef(_StrictModel):
    """Reference to one session in the weekend."""

    key: SessionKey
    name: str
    path: str
    start_utc: str


class Race(_StrictModel):
    """Race metadata plus all driver inventories."""

    slug: str
    name: str
    location: str
    country: str
    season: int
    round: int
    date: str
    sessions: list[SessionRef]
    drivers: list[DriverInventory]


class Manifest(_StrictModel):
    """Top-level JSON artifact."""

    schema_version: str = "1.0.0"
    generated_at: str
    source_commit: str | None = None
    race: Race
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd precompute && uv run pytest tests/test_models.py -v`
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add precompute/src/f1/models.py precompute/tests/test_models.py
git commit -m "feat(precompute): add Pydantic models (TyreSet, DriverInventory, Race, Manifest)"
```

---

## Task A5: Session stint extractor

**Files:**
- Create: `precompute/src/f1/inventory.py`
- Create: `precompute/tests/test_inventory.py`

- [ ] **Step 1: Write the first batch of failing tests `precompute/tests/test_inventory.py`**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd precompute && uv run pytest tests/test_inventory.py -v`
Expected: `ModuleNotFoundError: No module named 'f1.inventory'`.

- [ ] **Step 3: Implement the extractor in `precompute/src/f1/inventory.py`**

```python
"""Extract per-session stints and track tyre sets across the weekend."""
from __future__ import annotations

from dataclasses import dataclass

from f1.models import Compound, SessionKey, TyreSet

_SESSION_ORDER: list[SessionKey] = ["FP1", "FP2", "FP3", "Q", "R"]


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
    def end_laps(self) -> int:
        return self.start_laps + self.total_laps


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd precompute && uv run pytest tests/test_inventory.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add precompute/src/f1/inventory.py precompute/tests/test_inventory.py
git commit -m "feat(precompute): add SessionStint extractor"
```

---

## Task A6: Tyre tracker Pass A (FP1-Q)

**Files:**
- Modify: `precompute/src/f1/inventory.py`
- Modify: `precompute/tests/test_inventory.py`

- [ ] **Step 1: Append Pass-A tests to `precompute/tests/test_inventory.py`**

Add at end of file:

```python


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
        "FP2": [SessionStint("FP2", "1", 0, "SOFT", False, 8, 2)],
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
        "FP2": [SessionStint("FP2", "1", 0, "HARD", False, 4, 3)],
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
```

- [ ] **Step 2: Run tests to verify Pass-A tests fail**

Run: `cd precompute && uv run pytest tests/test_inventory.py -v`
Expected: first 4 pass; new ones fail with `ImportError: cannot import name 'build_inventory'`.

- [ ] **Step 3: Append Pass-A implementation to `precompute/src/f1/inventory.py`**

Add after the `_sort_key` function:

```python


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

    # Pass A: FP1 -> FP2 -> FP3 -> Q, full tracking.
    for session in ("FP1", "FP2", "FP3", "Q"):
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

    return sets
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd precompute && uv run pytest tests/test_inventory.py -v`
Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add precompute/src/f1/inventory.py precompute/tests/test_inventory.py
git commit -m "feat(precompute): add Pass A tyre-set tracking (FP1-Q)"
```

---

## Task A7: Tyre tracker Pass B (Race discovery)

**Files:**
- Modify: `precompute/src/f1/inventory.py`
- Modify: `precompute/tests/test_inventory.py`

- [ ] **Step 1: Append Pass-B tests to `precompute/tests/test_inventory.py`**

```python


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
        "R": [SessionStint("R", "1", 0, "HARD", False, 12, 33)],
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
        "R": [SessionStint("R", "1", 0, "HARD", False, 8, 25)],
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
            SessionStint("FP2", "1", 0, "SOFT", False, 8, 2),
            SessionStint("FP2", "1", 1, "HARD", True, 0, 12),
        ],
        "FP3": [
            SessionStint("FP3", "1", 0, "MEDIUM", False, 5, 3),
        ],
        "Q": [
            SessionStint("Q", "1", 0, "SOFT", True, 0, 3),
            SessionStint("Q", "1", 1, "SOFT", True, 0, 2),
            SessionStint("Q", "1", 2, "SOFT", True, 0, 3),
        ],
        "R": [
            SessionStint("R", "1", 0, "MEDIUM", True, 0, 25),
            SessionStint("R", "1", 1, "HARD", False, 12, 33),
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd precompute && uv run pytest tests/test_inventory.py -v`
Expected: 9 pass, 4 fail (Pass B not yet implemented).

- [ ] **Step 3: Extend `build_inventory` in `precompute/src/f1/inventory.py`**

Append the Pass B logic inside `build_inventory`, after the Pass A loop but before `return sets`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd precompute && uv run pytest tests/test_inventory.py -v`
Expected: 13 passed.

- [ ] **Step 5: Commit**

```bash
git add precompute/src/f1/inventory.py precompute/tests/test_inventory.py
git commit -m "feat(precompute): add Pass B race discovery (saved-for-race detection)"
```

---

## Task A8: Driver metadata extractor

**Files:**
- Create: `precompute/src/f1/driver_meta.py`
- Create: `precompute/tests/test_driver_meta.py`

- [ ] **Step 1: Write failing tests `precompute/tests/test_driver_meta.py`**

```python
"""Tests for DriverList and grid-position extraction."""
from __future__ import annotations

from f1.driver_meta import DriverMeta, build_driver_meta, extract_grid_positions


def test_build_driver_meta_maps_by_racing_number() -> None:
    driver_list_state: dict[str, object] = {
        "1": {
            "RacingNumber": "1",
            "Tla": "VER",
            "FullName": "Max Verstappen",
            "TeamName": "Red Bull Racing",
            "TeamColour": "4781D7",
        },
        "16": {
            "RacingNumber": "16",
            "Tla": "LEC",
            "FullName": "Charles Leclerc",
            "TeamName": "Ferrari",
            "TeamColour": "ED1131",
        },
    }
    metas = build_driver_meta(driver_list_state)
    assert metas["1"] == DriverMeta(
        racing_number="1",
        tla="VER",
        full_name="Max Verstappen",
        team_name="Red Bull Racing",
        team_color="#4781D7",
    )
    assert metas["16"].tla == "LEC"


def test_build_driver_meta_prepends_hash_when_missing() -> None:
    state: dict[str, object] = {
        "1": {
            "RacingNumber": "1",
            "Tla": "VER",
            "FullName": "Max Verstappen",
            "TeamName": "Red Bull Racing",
            "TeamColour": "4781D7",
        }
    }
    assert build_driver_meta(state)["1"].team_color == "#4781D7"


def test_build_driver_meta_skips_entries_missing_required_fields() -> None:
    state: dict[str, object] = {
        "1": {"RacingNumber": "1"},  # missing everything else
        "16": {
            "RacingNumber": "16",
            "Tla": "LEC",
            "FullName": "Charles Leclerc",
            "TeamName": "Ferrari",
            "TeamColour": "ED1131",
        },
    }
    metas = build_driver_meta(state)
    assert list(metas) == ["16"]


def test_extract_grid_positions_reads_gridpos_from_lines() -> None:
    state: dict[str, object] = {
        "Lines": {
            "1": {"RacingNumber": "1", "GridPos": "2"},
            "16": {"RacingNumber": "16", "GridPos": "1"},
            "44": {"RacingNumber": "44"},  # GridPos missing -> not included
        }
    }
    grid = extract_grid_positions(state)
    assert grid == {"1": 2, "16": 1}


def test_extract_grid_positions_handles_empty_state() -> None:
    assert extract_grid_positions({}) == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd precompute && uv run pytest tests/test_driver_meta.py -v`
Expected: `ModuleNotFoundError: No module named 'f1.driver_meta'`.

- [ ] **Step 3: Implement `precompute/src/f1/driver_meta.py`**

```python
"""Extract driver metadata (name, team, color) and grid positions."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DriverMeta:
    racing_number: str
    tla: str
    full_name: str
    team_name: str
    team_color: str  # canonical form "#RRGGBB"


_REQUIRED_FIELDS = ("Tla", "FullName", "TeamName", "TeamColour")


def _normalize_color(raw: object) -> str | None:
    if not isinstance(raw, str) or not raw:
        return None
    return raw if raw.startswith("#") else f"#{raw}"


def build_driver_meta(driver_list_state: dict[str, object]) -> dict[str, DriverMeta]:
    """Turn reduced DriverList state into a racing_number -> DriverMeta map.

    Entries missing any required field are dropped.
    """
    result: dict[str, DriverMeta] = {}
    for racing_number, raw in driver_list_state.items():
        if not isinstance(raw, dict):
            continue
        if any(field not in raw or not raw[field] for field in _REQUIRED_FIELDS):
            continue
        color = _normalize_color(raw.get("TeamColour"))
        if color is None:
            continue
        result[str(racing_number)] = DriverMeta(
            racing_number=str(racing_number),
            tla=str(raw["Tla"]),
            full_name=str(raw["FullName"]),
            team_name=str(raw["TeamName"]),
            team_color=color,
        )
    return result


def extract_grid_positions(timing_app_state: dict[str, object]) -> dict[str, int]:
    """Read GridPos from the reduced TimingAppData state (Qualifying session)."""
    lines = timing_app_state.get("Lines")
    if not isinstance(lines, dict):
        return {}
    grid: dict[str, int] = {}
    for racing_number, raw in lines.items():
        if not isinstance(raw, dict):
            continue
        pos = raw.get("GridPos")
        if pos is None or pos == "":
            continue
        try:
            grid[str(racing_number)] = int(pos)
        except (TypeError, ValueError):
            continue
    return grid
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd precompute && uv run pytest tests/test_driver_meta.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add precompute/src/f1/driver_meta.py precompute/tests/test_driver_meta.py
git commit -m "feat(precompute): add driver metadata and grid-position extractors"
```

---

## Task A9: Build CLI orchestrator

**Files:**
- Create: `precompute/src/f1/build.py`
- Create: `precompute/tests/test_build.py`
- Create: fixture files under `precompute/fixtures/mini-race/` (see Step 1)

- [ ] **Step 1: Create minimal integration fixture**

Copy a small end-to-end slice so we can test orchestration without requiring the full 2026 directory.

```bash
mkdir -p precompute/fixtures/mini-race/2026/2026-03-08_Australian_Grand_Prix/2026-03-08_Race
cd precompute/fixtures/mini-race/2026/2026-03-08_Australian_Grand_Prix/2026-03-08_Race
```

Write `SessionInfo.json`:
```bash
cat > SessionInfo.json <<'JSON'
{"Meeting":{"Key":1271,"Name":"Australian Grand Prix","OfficialName":"FORMULA 1 AUSTRALIAN GRAND PRIX 2026","Location":"Melbourne","Number":1,"Country":{"Key":5,"Code":"AUS","Name":"Australia"},"Circuit":{"Key":10,"ShortName":"Melbourne"}},"SessionStatus":"Finalised","Key":9999,"Type":"Race","Name":"Race","StartDate":"2026-03-08T14:00:00","EndDate":"2026-03-08T16:00:00","GmtOffset":"+11:00:00","Path":"2026/2026-03-08_Australian_Grand_Prix/2026-03-08_Race/"}
JSON
```

Write `DriverList.jsonStream` (BOM + one event):
```bash
printf '\xef\xbb\xbf00:00:00.000{"1":{"RacingNumber":"1","Tla":"VER","FullName":"Max Verstappen","TeamName":"Red Bull Racing","TeamColour":"4781D7"},"16":{"RacingNumber":"16","Tla":"LEC","FullName":"Charles Leclerc","TeamName":"Ferrari","TeamColour":"ED1131"}}\n' \
  > DriverList.jsonStream
```

Write `TyreStintSeries.jsonStream`:
```bash
printf '\xef\xbb\xbf00:00:00.000{"Stints":{}}\n00:00:10.000{"Stints":{"1":{"0":{"Compound":"MEDIUM","New":"true","TotalLaps":0,"StartLaps":0}},"16":{"0":{"Compound":"SOFT","New":"true","TotalLaps":0,"StartLaps":0}}}}\n00:30:00.000{"Stints":{"1":{"0":{"TotalLaps":25}},"16":{"0":{"TotalLaps":20}}}}\n' \
  > TyreStintSeries.jsonStream
```

Create the Qualifying session so grid positions exist:
```bash
cd ../..
mkdir -p 2026-03-07_Qualifying
cd 2026-03-07_Qualifying
cat > SessionInfo.json <<'JSON'
{"Meeting":{"Key":1271,"Name":"Australian Grand Prix","Location":"Melbourne","Number":1,"Country":{"Key":5,"Code":"AUS","Name":"Australia"}},"Key":9998,"Type":"Qualifying","Name":"Qualifying","StartDate":"2026-03-07T15:00:00","EndDate":"2026-03-07T16:00:00","GmtOffset":"+11:00:00","Path":"2026/2026-03-08_Australian_Grand_Prix/2026-03-07_Qualifying/"}
JSON

printf '\xef\xbb\xbf00:00:00.000{"Stints":{"1":{"0":{"Compound":"SOFT","New":"true","TotalLaps":3,"StartLaps":0}},"16":{"0":{"Compound":"SOFT","New":"true","TotalLaps":3,"StartLaps":0}}}}\n' \
  > TyreStintSeries.jsonStream

printf '\xef\xbb\xbf00:00:00.000{"Lines":{"1":{"RacingNumber":"1","GridPos":"2"},"16":{"RacingNumber":"16","GridPos":"1"}}}\n' \
  > TimingAppData.jsonStream

cd ../../../../..
```

Expected layout:
```
precompute/fixtures/mini-race/
└── 2026/2026-03-08_Australian_Grand_Prix/
    ├── 2026-03-07_Qualifying/
    │   ├── SessionInfo.json
    │   ├── TyreStintSeries.jsonStream
    │   └── TimingAppData.jsonStream
    └── 2026-03-08_Race/
        ├── SessionInfo.json
        ├── DriverList.jsonStream
        └── TyreStintSeries.jsonStream
```

- [ ] **Step 2: Write failing tests `precompute/tests/test_build.py`**

```python
"""End-to-end tests for the build CLI."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from f1.build import build_race_manifest
from f1.models import Manifest


@pytest.fixture
def mini_race_root(fixtures_dir: Path) -> Path:
    return fixtures_dir / "mini-race"


def test_build_race_manifest_produces_validated_model(mini_race_root: Path) -> None:
    manifest = build_race_manifest(
        data_root=mini_race_root,
        race_dir="2026/2026-03-08_Australian_Grand_Prix",
        season=2026,
        round_number=1,
        slug="australia-2026",
    )
    assert isinstance(manifest, Manifest)
    assert manifest.race.slug == "australia-2026"
    assert manifest.race.name == "Australian Grand Prix"
    assert manifest.race.location == "Melbourne"
    assert manifest.race.country == "Australia"
    assert manifest.race.season == 2026
    assert manifest.race.round == 1


def test_build_race_manifest_includes_all_drivers(mini_race_root: Path) -> None:
    manifest = build_race_manifest(
        data_root=mini_race_root,
        race_dir="2026/2026-03-08_Australian_Grand_Prix",
        season=2026,
        round_number=1,
        slug="australia-2026",
    )
    tlas = sorted(d.tla for d in manifest.race.drivers)
    assert tlas == ["LEC", "VER"]


def test_build_race_manifest_attaches_grid_positions(mini_race_root: Path) -> None:
    manifest = build_race_manifest(
        data_root=mini_race_root,
        race_dir="2026/2026-03-08_Australian_Grand_Prix",
        season=2026,
        round_number=1,
        slug="australia-2026",
    )
    by_tla = {d.tla: d for d in manifest.race.drivers}
    assert by_tla["LEC"].grid_position == 1
    assert by_tla["VER"].grid_position == 2


def test_build_race_manifest_discovers_saved_for_race_sets(mini_race_root: Path) -> None:
    manifest = build_race_manifest(
        data_root=mini_race_root,
        race_dir="2026/2026-03-08_Australian_Grand_Prix",
        season=2026,
        round_number=1,
        slug="australia-2026",
    )
    ver = next(d for d in manifest.race.drivers if d.tla == "VER")
    # VER used MEDIUM new in the race and SOFT new in Q.
    saved_for_race = [s for s in ver.sets if s.first_seen_session == "R"]
    assert len(saved_for_race) == 1
    assert saved_for_race[0].compound == "MEDIUM"
    assert saved_for_race[0].laps == 0


def test_build_race_manifest_fails_if_zero_drivers(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="no drivers"):
        build_race_manifest(
            data_root=tmp_path,
            race_dir="2026/empty",
            season=2026,
            round_number=1,
            slug="empty",
        )


def test_build_race_manifest_json_round_trip(mini_race_root: Path, tmp_path: Path) -> None:
    from f1.build import write_manifest

    manifest = build_race_manifest(
        data_root=mini_race_root,
        race_dir="2026/2026-03-08_Australian_Grand_Prix",
        season=2026,
        round_number=1,
        slug="australia-2026",
    )
    out = tmp_path / "out.json"
    write_manifest(manifest, out)
    loaded = json.loads(out.read_text())
    assert loaded["race"]["slug"] == "australia-2026"
    # Re-validate through Pydantic.
    Manifest.model_validate(loaded)
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd precompute && uv run pytest tests/test_build.py -v`
Expected: `ModuleNotFoundError: No module named 'f1.build'`.

- [ ] **Step 4: Implement `precompute/src/f1/build.py`**

```python
"""CLI entry point that assembles the final Manifest JSON artifact."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from f1.driver_meta import DriverMeta, build_driver_meta, extract_grid_positions
from f1.inventory import (
    SessionStint,
    build_inventory,
    extract_session_stints,
)
from f1.models import (
    DriverInventory,
    Manifest,
    Race,
    SessionKey,
    SessionRef,
    TyreSet,
)
from f1.parse import parse_stream
from f1.reduce import reduce_events

# Folder-name fragment → SessionKey used internally
_SESSION_FOLDER_HINTS: list[tuple[str, SessionKey]] = [
    ("Practice_1", "FP1"),
    ("Practice_2", "FP2"),
    ("Practice_3", "FP3"),
    ("Qualifying", "Q"),
    ("Race", "R"),
]

_SESSION_DISPLAY_NAME: dict[SessionKey, str] = {
    "FP1": "Practice 1",
    "FP2": "Practice 2",
    "FP3": "Practice 3",
    "Q": "Qualifying",
    "R": "Race",
}


def _discover_sessions(race_abs_dir: Path) -> list[tuple[SessionKey, Path]]:
    """Return session key + absolute directory for every session we recognise."""
    if not race_abs_dir.is_dir():
        return []
    discovered: list[tuple[SessionKey, Path]] = []
    for child in sorted(race_abs_dir.iterdir()):
        if not child.is_dir():
            continue
        for hint, key in _SESSION_FOLDER_HINTS:
            if hint in child.name:
                discovered.append((key, child))
                break
    return discovered


def _load_session_info(session_dir: Path) -> dict[str, object]:
    info_path = session_dir / "SessionInfo.json"
    if not info_path.exists():
        return {}
    try:
        return json.loads(info_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}


def _reduce_stream(session_dir: Path, filename: str) -> dict[str, object]:
    path = session_dir / filename
    if not path.exists():
        return {}
    events = parse_stream(path)
    return reduce_events(events)


def build_race_manifest(
    *,
    data_root: Path,
    race_dir: str,
    season: int,
    round_number: int,
    slug: str,
) -> Manifest:
    """Assemble a validated Manifest from raw archive files under ``data_root``."""
    race_abs = (data_root / race_dir).resolve()
    sessions = _discover_sessions(race_abs)
    if not sessions:
        raise RuntimeError(f"no session folders found under {race_abs}")

    # Aggregate driver metadata from whichever session first provides DriverList.
    driver_meta: dict[str, DriverMeta] = {}
    for _, sess_dir in sessions:
        reduced = _reduce_stream(sess_dir, "DriverList.jsonStream")
        if reduced:
            driver_meta.update(build_driver_meta(reduced))
            if driver_meta:
                break

    if not driver_meta:
        raise RuntimeError("no drivers found in any DriverList.jsonStream")

    # Stints per session key.
    stints_by_session: dict[SessionKey, list[SessionStint]] = {}
    for key, sess_dir in sessions:
        reduced = _reduce_stream(sess_dir, "TyreStintSeries.jsonStream")
        stints_by_session[key] = extract_session_stints(key, reduced)

    # Grid positions from Qualifying TimingAppData if present.
    grid_positions: dict[str, int] = {}
    for key, sess_dir in sessions:
        if key == "Q":
            ta = _reduce_stream(sess_dir, "TimingAppData.jsonStream")
            grid_positions = extract_grid_positions(ta)
            break

    # Session refs (metadata + path relative to data_root).
    session_refs: list[SessionRef] = []
    race_info: dict[str, object] = {}
    location = "Unknown"
    country = "Unknown"
    race_name = "Unknown Grand Prix"
    for key, sess_dir in sessions:
        info = _load_session_info(sess_dir)
        rel_path = sess_dir.resolve().relative_to(data_root.resolve()).as_posix() + "/"
        session_refs.append(
            SessionRef(
                key=key,
                name=_SESSION_DISPLAY_NAME[key],
                path=rel_path,
                start_utc=str(info.get("StartDate", "")),
            )
        )
        if key == "R":
            race_info = info

    meeting = race_info.get("Meeting") if isinstance(race_info.get("Meeting"), dict) else {}
    if isinstance(meeting, dict):
        race_name = str(meeting.get("Name", race_name))
        location = str(meeting.get("Location", location))
        country_obj = meeting.get("Country")
        if isinstance(country_obj, dict):
            country = str(country_obj.get("Name", country))

    # Assemble drivers.
    drivers: list[DriverInventory] = []
    for racing_number, meta in driver_meta.items():
        sets: list[TyreSet] = build_inventory(
            driver_number=racing_number,
            driver_tla=meta.tla,
            stints_by_session=stints_by_session,
        )
        drivers.append(
            DriverInventory(
                racing_number=meta.racing_number,
                tla=meta.tla,
                full_name=meta.full_name,
                team_name=meta.team_name,
                team_color=meta.team_color,
                grid_position=grid_positions.get(racing_number),
                sets=sets,
            )
        )
    drivers.sort(key=lambda d: d.tla)

    race = Race(
        slug=slug,
        name=race_name,
        location=location,
        country=country,
        season=season,
        round=round_number,
        date=str(race_info.get("StartDate", ""))[:10],
        sessions=session_refs,
        drivers=drivers,
    )

    return Manifest(
        schema_version="1.0.0",
        generated_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        race=race,
    )


def write_manifest(manifest: Manifest, out_path: Path) -> None:
    """Serialize ``manifest`` to ``out_path`` as pretty JSON."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        manifest.model_dump_json(indent=2, exclude_none=False),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build race tyre inventory JSON")
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
        help="Root directory containing year folders (defaults to repo root)",
    )
    parser.add_argument(
        "--race-dir",
        default="2026/2026-03-08_Australian_Grand_Prix",
    )
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--round", type=int, default=1, dest="round_number")
    parser.add_argument("--slug", default="australia-2026")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "out" / "australia-2026.json",
    )
    args = parser.parse_args(argv)

    try:
        manifest = build_race_manifest(
            data_root=args.data_root,
            race_dir=args.race_dir,
            season=args.season,
            round_number=args.round_number,
            slug=args.slug,
        )
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    write_manifest(manifest, args.out)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd precompute && uv run pytest tests/test_build.py -v`
Expected: 6 passed.

- [ ] **Step 6: Run the full suite**

Run: `cd precompute && uv run pytest -v`
Expected: all tests pass; coverage ≥ 85% on `f1/`.

- [ ] **Step 7: Commit**

```bash
git add precompute/src/f1/build.py precompute/tests/test_build.py precompute/fixtures/
git commit -m "feat(precompute): add build CLI and mini-race integration test"
```

---

## Task A10: JSON Schema exporter

**Files:**
- Create: `precompute/src/f1/schema.py`

- [ ] **Step 1: Implement `precompute/src/f1/schema.py`**

```python
"""Emit JSON Schema for the TypeScript side to consume."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from f1.models import Manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export Manifest JSON Schema")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "out" / "schema.json",
    )
    args = parser.parse_args(argv)

    schema = Manifest.model_json_schema()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Smoke-test the exporter**

Run: `cd precompute && uv run python -m f1.schema --out out/schema.json`
Expected: `wrote .../out/schema.json`. Inspect `out/schema.json` — it must contain `"title": "Manifest"` and `"$defs"` with `TyreSet`, `DriverInventory`, etc.

- [ ] **Step 3: Commit**

```bash
git add precompute/src/f1/schema.py
git commit -m "feat(precompute): export Pydantic-derived JSON Schema"
```

---

## Task A11: Run the pipeline on real Australia 2026 data

**Files:** (runtime artifacts only)
- Create: `precompute/out/australia-2026.json` (generated, gitignored)

- [ ] **Step 1: Generate the real artifact**

Run: `cd precompute && uv run python -m f1.build`
Expected: `wrote .../out/australia-2026.json`.

- [ ] **Step 2: Inspect the output**

Run: `python -c "import json,sys; d=json.load(open('precompute/out/australia-2026.json')); print(len(d['race']['drivers']),'drivers'); print([dr['tla'] for dr in d['race']['drivers']])"`
Expected: `22 drivers` and TLAs like `['ALB', 'ALO', 'ANT', 'BEA', ...]` (alphabetical).

- [ ] **Step 3: Sanity-check one driver's inventory**

Run: `python -c "import json; d=json.load(open('precompute/out/australia-2026.json')); ver=[x for x in d['race']['drivers'] if x['tla']=='VER'][0]; print(f'VER sets:', len(ver['sets'])); [print(' ', s['set_id'], s['compound'], 'laps=', s['laps'], 'first=', s['first_seen_session']) for s in ver['sets']]"`
Expected: between 5 and 10 sets, mixture of HARD/MEDIUM/SOFT, at least one with `first_seen_session='R'` (saved-for-race).

- [ ] **Step 4: No commit needed**

`precompute/out/` is gitignored. Generated data is not checked in.

---

# Section B — Site Scaffold

## Task B1: Scaffold Vite + React + TypeScript app

**Files:**
- Create: `site/package.json`
- Create: `site/vite.config.ts`
- Create: `site/tsconfig.json`
- Create: `site/tsconfig.node.json`
- Create: `site/index.html`
- Create: `site/src/main.tsx`
- Create: `site/src/App.tsx`
- Create: `site/src/styles/index.css`

- [ ] **Step 1: Create `site/package.json`**

```json
{
  "name": "f1-tyre-inventory-site",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest",
    "test:e2e": "playwright test",
    "gen:zod": "node scripts/gen-zod.mjs"
  },
  "dependencies": {
    "react": "^19.1.0",
    "react-dom": "^19.1.0",
    "react-router-dom": "^7.1.0",
    "zod": "^3.23.8",
    "@visx/scale": "^3.12.0",
    "@visx/shape": "^3.12.0",
    "@visx/axis": "^3.12.0",
    "@visx/group": "^3.12.0",
    "@visx/responsive": "^3.12.0",
    "@visx/tooltip": "^3.12.0"
  },
  "devDependencies": {
    "typescript": "^5.6.0",
    "vite": "^6.0.0",
    "@vitejs/plugin-react": "^4.3.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "tailwindcss": "^4.0.0",
    "@tailwindcss/vite": "^4.0.0",
    "vitest": "^2.1.0",
    "@vitest/coverage-v8": "^2.1.0",
    "@testing-library/react": "^16.1.0",
    "@testing-library/jest-dom": "^6.6.0",
    "@testing-library/user-event": "^14.5.0",
    "jsdom": "^25.0.0",
    "@playwright/test": "^1.49.0",
    "json-schema-to-zod": "^2.4.0"
  }
}
```

- [ ] **Step 2: Create `site/vite.config.ts`**

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: "/",
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./tests/unit/setup.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "html"],
      thresholds: { lines: 80, statements: 80, functions: 80, branches: 75 },
    },
  },
});
```

- [ ] **Step 3: Create `site/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["src", "tests"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 4: Create `site/tsconfig.node.json`**

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true
  },
  "include": ["vite.config.ts", "playwright.config.ts"]
}
```

- [ ] **Step 5: Create `site/index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link rel="preload" as="fetch" href="/data/australia-2026.json" crossorigin="anonymous" />
    <title>Australia GP 2026 · Pre-Race Tyre Inventory</title>
  </head>
  <body class="bg-f1-bg text-f1-text">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 6: Create `site/src/styles/index.css`**

```css
@import "tailwindcss";

@theme {
  --color-f1-bg: #0f1419;
  --color-f1-panel: #1b2330;
  --color-f1-border: #2a2f3a;
  --color-f1-text: #e6e6e6;
  --color-f1-muted: #8a8f99;

  --color-compound-soft: #ff3030;
  --color-compound-medium: #ffdd00;
  --color-compound-hard: #ffffff;
  --color-compound-inter: #00b050;
  --color-compound-wet: #0099ff;

  --font-sans: "Inter", ui-sans-serif, system-ui, sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, Menlo, monospace;
}

html, body, #root {
  height: 100%;
}

body {
  background: var(--color-f1-bg);
  color: var(--color-f1-text);
  -webkit-font-smoothing: antialiased;
}
```

- [ ] **Step 7: Create `site/src/main.tsx`**

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles/index.css";

const rootEl = document.getElementById("root");
if (!rootEl) {
  throw new Error("#root element missing in index.html");
}
createRoot(rootEl).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

- [ ] **Step 8: Create `site/src/App.tsx` (placeholder, will grow later)**

```tsx
export default function App() {
  return (
    <main className="mx-auto max-w-6xl p-6">
      <h1 className="text-2xl font-bold">F1 Tyre Inventory — scaffolding</h1>
      <p className="text-f1-muted mt-2">Site scaffolded. Routes and data come next.</p>
    </main>
  );
}
```

- [ ] **Step 9: Install and verify**

Run: `cd site && npm install`
Expected: dependencies resolve without errors.

Run: `cd site && npm run build`
Expected: `tsc` succeeds; `vite build` emits `dist/`.

- [ ] **Step 10: Commit**

```bash
git add site/
git commit -m "chore(site): scaffold Vite + React + TypeScript app"
```

---

## Task B2: Generate Zod schemas from JSON Schema

**Files:**
- Create: `site/scripts/gen-zod.mjs`
- Create: `site/src/lib/schemas.ts` (generated output, committed)

- [ ] **Step 1: Create `site/scripts/gen-zod.mjs`**

```js
// Reads ../precompute/out/schema.json and writes src/lib/schemas.ts.
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import jsonSchemaToZod from "json-schema-to-zod";

const here = dirname(fileURLToPath(import.meta.url));
const schemaPath = resolve(here, "../../precompute/out/schema.json");
const outPath = resolve(here, "../src/lib/schemas.ts");

const schema = JSON.parse(readFileSync(schemaPath, "utf8"));
const zodSource = jsonSchemaToZod(schema, { name: "ManifestSchema", module: "esm" });

const header = `// AUTO-GENERATED from precompute/out/schema.json — do not edit by hand.\n// Regenerate with: npm run gen:zod\n\n`;
mkdirSync(dirname(outPath), { recursive: true });
writeFileSync(outPath, header + zodSource + "\nexport type Manifest = import(\"zod\").z.infer<typeof ManifestSchema>;\n", "utf8");
console.log(`wrote ${outPath}`);
```

- [ ] **Step 2: Ensure the Python schema exists, then generate Zod**

Run: `cd precompute && uv run python -m f1.schema`
Expected: writes `precompute/out/schema.json`.

Run: `cd site && npm run gen:zod`
Expected: writes `site/src/lib/schemas.ts`.

- [ ] **Step 3: Verify the generated file compiles**

Run: `cd site && npx tsc --noEmit -p tsconfig.json`
Expected: no errors.

If `json-schema-to-zod` output uses property names that tsc flags (e.g., extra properties), adjust the header/export in the generated file or add a thin re-export module `site/src/lib/types.ts`. For this plan, the auto-generated file is committed as-is.

- [ ] **Step 4: Commit the generator and the generated file**

```bash
git add site/scripts/gen-zod.mjs site/src/lib/schemas.ts
git commit -m "feat(site): generate Zod schemas from JSON Schema"
```

---

## Task B3: Data loader with Zod validation

**Files:**
- Create: `site/src/lib/data.ts`
- Create: `site/tests/unit/setup.ts`
- Create: `site/tests/unit/data.test.ts`

- [ ] **Step 1: Create `site/tests/unit/setup.ts`**

```ts
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 2: Write failing test `site/tests/unit/data.test.ts`**

```ts
import { describe, it, expect, vi, afterEach } from "vitest";
import { loadManifest } from "../../src/lib/data";

const validFixture = {
  schema_version: "1.0.0",
  generated_at: "2026-04-17T00:00:00Z",
  source_commit: null,
  race: {
    slug: "australia-2026",
    name: "Australian Grand Prix",
    location: "Melbourne",
    country: "Australia",
    season: 2026,
    round: 1,
    date: "2026-03-08",
    sessions: [
      { key: "R", name: "Race", path: "2026/.../Race/", start_utc: "2026-03-08T04:00:00Z" },
    ],
    drivers: [
      {
        racing_number: "1",
        tla: "VER",
        full_name: "Max Verstappen",
        team_name: "Red Bull Racing",
        team_color: "#4781D7",
        grid_position: 2,
        sets: [],
      },
    ],
  },
};

afterEach(() => vi.restoreAllMocks());

describe("loadManifest", () => {
  it("parses and validates a well-formed payload", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => validFixture,
    }));
    const m = await loadManifest("/data/australia-2026.json");
    expect(m.race.drivers[0].tla).toBe("VER");
  });

  it("throws a descriptive error on HTTP failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 404 }));
    await expect(loadManifest("/missing.json")).rejects.toThrow(/404/);
  });

  it("throws when schema_version does not match", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ...validFixture, schema_version: "2.0.0" }),
    }));
    await expect(loadManifest("/data/x.json")).rejects.toThrow(/schema_version/);
  });

  it("rejects payloads that fail Zod validation", async () => {
    const bad = { ...validFixture, race: { ...validFixture.race, drivers: [{ tla: "X" }] } };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => bad }));
    await expect(loadManifest("/data/x.json")).rejects.toThrow();
  });
});
```

- [ ] **Step 3: Run the test and verify it fails**

Run: `cd site && npm run test -- tests/unit/data.test.ts`
Expected: fails because `src/lib/data.ts` does not exist.

- [ ] **Step 4: Implement `site/src/lib/data.ts`**

```ts
import { ManifestSchema, type Manifest } from "./schemas";

export const EXPECTED_SCHEMA_VERSION = "1.0.0";

/**
 * Fetch and validate a Manifest JSON artifact.
 * @throws Error with a context-rich message on HTTP, schema, or version failures.
 */
export async function loadManifest(url: string): Promise<Manifest> {
  const resp = await fetch(url, { cache: "no-cache" });
  if (!resp.ok) {
    throw new Error(`failed to load ${url}: HTTP ${resp.status}`);
  }
  const raw: unknown = await resp.json();
  const parsed = ManifestSchema.parse(raw);
  if (parsed.schema_version !== EXPECTED_SCHEMA_VERSION) {
    throw new Error(
      `schema_version mismatch: got ${parsed.schema_version}, expected ${EXPECTED_SCHEMA_VERSION}. Rebuild the data artifact.`,
    );
  }
  return parsed;
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd site && npm run test -- tests/unit/data.test.ts`
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add site/src/lib/data.ts site/tests/unit/setup.ts site/tests/unit/data.test.ts
git commit -m "feat(site): add validated data loader"
```

---

# Section C — UI Components and Routes

## Task C1: TyreDot compound-color primitive

**Files:**
- Create: `site/src/components/TyreDot.tsx`
- Create: `site/tests/unit/TyreDot.test.tsx`

- [ ] **Step 1: Write failing test `site/tests/unit/TyreDot.test.tsx`**

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { TyreDot } from "../../src/components/TyreDot";

describe("<TyreDot />", () => {
  it("renders with the SOFT background class", () => {
    render(<TyreDot compound="SOFT" aria-label="soft tyre" />);
    const el = screen.getByLabelText("soft tyre");
    expect(el.className).toMatch(/bg-compound-soft/);
  });

  it("renders the HARD variant with a ring for visibility on dark bg", () => {
    render(<TyreDot compound="HARD" aria-label="hard tyre" />);
    const el = screen.getByLabelText("hard tyre");
    expect(el.className).toMatch(/bg-compound-hard/);
    expect(el.className).toMatch(/ring-/);
  });

  it("applies size-sm dimensions by default", () => {
    render(<TyreDot compound="MEDIUM" aria-label="med" />);
    const el = screen.getByLabelText("med");
    expect(el.className).toMatch(/w-3/);
    expect(el.className).toMatch(/h-3/);
  });

  it("applies size-lg dimensions when size='lg'", () => {
    render(<TyreDot compound="MEDIUM" size="lg" aria-label="med lg" />);
    const el = screen.getByLabelText("med lg");
    expect(el.className).toMatch(/w-6/);
    expect(el.className).toMatch(/h-6/);
  });
});
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `cd site && npm run test -- tests/unit/TyreDot.test.tsx`
Expected: fails because `src/components/TyreDot.tsx` does not exist.

- [ ] **Step 3: Implement `site/src/components/TyreDot.tsx`**

```tsx
import type { Manifest } from "../lib/schemas";

type Compound = Manifest["race"]["drivers"][number]["sets"][number]["compound"];

const COLOR_CLASS: Record<Compound, string> = {
  SOFT: "bg-compound-soft",
  MEDIUM: "bg-compound-medium",
  HARD: "bg-compound-hard ring-1 ring-f1-border",
  INTERMEDIATE: "bg-compound-inter",
  WET: "bg-compound-wet",
};

const SIZE_CLASS = {
  sm: "w-3 h-3",
  md: "w-4 h-4",
  lg: "w-6 h-6",
} as const;

type Props = {
  compound: Compound;
  size?: keyof typeof SIZE_CLASS;
  "aria-label"?: string;
  className?: string;
};

export function TyreDot({ compound, size = "sm", className = "", ...rest }: Props) {
  const classes = [
    "inline-block rounded-full",
    SIZE_CLASS[size],
    COLOR_CLASS[compound],
    className,
  ].join(" ");
  return <span className={classes} {...rest} />;
}
```

- [ ] **Step 4: Run tests and verify they pass**

Run: `cd site && npm run test -- tests/unit/TyreDot.test.tsx`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add site/src/components/TyreDot.tsx site/tests/unit/TyreDot.test.tsx
git commit -m "feat(site): add TyreDot compound primitive"
```

---

## Task C2: DriverCard + DriverGrid + Home route

**Files:**
- Create: `site/src/components/RaceHeader.tsx`
- Create: `site/src/components/DriverCard.tsx`
- Create: `site/src/components/DriverGrid.tsx`
- Create: `site/src/routes/Home.tsx`
- Create: `site/tests/unit/DriverCard.test.tsx`

- [ ] **Step 1: Write failing test `site/tests/unit/DriverCard.test.tsx`**

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { DriverCard } from "../../src/components/DriverCard";

const driver = {
  racing_number: "16",
  tla: "LEC",
  full_name: "Charles Leclerc",
  team_name: "Ferrari",
  team_color: "#ED1131",
  grid_position: 1,
  sets: [
    { set_id: "LEC-MED-1", compound: "MEDIUM", laps: 0, new_at_first_use: true, first_seen_session: "R", last_seen_session: "R" },
    { set_id: "LEC-HARD-1", compound: "HARD", laps: 12, new_at_first_use: true, first_seen_session: "FP2", last_seen_session: "FP2" },
  ],
} as const;

describe("<DriverCard />", () => {
  it("shows the TLA, team name and grid position", () => {
    render(
      <MemoryRouter>
        <DriverCard driver={driver} />
      </MemoryRouter>,
    );
    expect(screen.getByText("LEC")).toBeInTheDocument();
    expect(screen.getByText(/Ferrari/)).toBeInTheDocument();
    expect(screen.getByText(/P1/)).toBeInTheDocument();
  });

  it("renders one TyreDot per set", () => {
    const { container } = render(
      <MemoryRouter>
        <DriverCard driver={driver} />
      </MemoryRouter>,
    );
    const dots = container.querySelectorAll('[data-testid="tyre-dot"]');
    expect(dots.length).toBe(2);
  });

  it("links to /driver/:tla", () => {
    render(
      <MemoryRouter>
        <DriverCard driver={driver} />
      </MemoryRouter>,
    );
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/driver/LEC");
  });

  it("uses the team_color as left border inline style", () => {
    render(
      <MemoryRouter>
        <DriverCard driver={driver} />
      </MemoryRouter>,
    );
    const link = screen.getByRole("link");
    expect(link.style.borderLeftColor).toBe("rgb(237, 17, 49)");
  });
});
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `cd site && npm run test -- tests/unit/DriverCard.test.tsx`
Expected: fails — components don't exist yet.

- [ ] **Step 3: Implement `site/src/components/RaceHeader.tsx`**

```tsx
import type { Manifest } from "../lib/schemas";

type Race = Manifest["race"];

export function RaceHeader({ race }: { race: Race }) {
  return (
    <header className="mb-6 flex items-baseline justify-between border-b border-f1-border pb-3">
      <div>
        <p className="text-xs uppercase tracking-widest text-f1-muted">Round {race.round} · {race.season}</p>
        <h1 className="text-2xl font-bold">{race.name}</h1>
        <p className="text-sm text-f1-muted">{race.location}, {race.country} · {race.date}</p>
      </div>
      <p className="font-mono text-xs text-f1-muted">Pre-race tyre inventory</p>
    </header>
  );
}
```

- [ ] **Step 4: Implement `site/src/components/DriverCard.tsx`**

```tsx
import { Link } from "react-router-dom";
import { TyreDot } from "./TyreDot";
import type { Manifest } from "../lib/schemas";

type Driver = Manifest["race"]["drivers"][number];

export function DriverCard({ driver }: { driver: Driver }) {
  return (
    <Link
      to={`/driver/${driver.tla}`}
      style={{ borderLeftColor: driver.team_color }}
      className="block rounded-md border-l-4 border-transparent bg-f1-panel p-3 transition hover:bg-f1-border focus-visible:outline-2 focus-visible:outline-compound-medium"
    >
      <div className="flex items-center justify-between">
        <span className="font-mono text-lg font-bold">{driver.tla}</span>
        {driver.grid_position != null && (
          <span className="font-mono text-xs text-f1-muted">P{driver.grid_position}</span>
        )}
      </div>
      <p className="truncate text-xs text-f1-muted">{driver.team_name}</p>
      <div className="mt-2 flex flex-wrap gap-1">
        {driver.sets.map((s) => (
          <span key={s.set_id} data-testid="tyre-dot">
            <TyreDot compound={s.compound} aria-label={`${s.compound} ${s.laps} laps`} />
          </span>
        ))}
      </div>
    </Link>
  );
}
```

- [ ] **Step 5: Implement `site/src/components/DriverGrid.tsx`**

```tsx
import type { Manifest } from "../lib/schemas";
import { DriverCard } from "./DriverCard";

type Drivers = Manifest["race"]["drivers"];

export function DriverGrid({ drivers }: { drivers: Drivers }) {
  const sorted = [...drivers].sort((a, b) => {
    const ag = a.grid_position ?? 99;
    const bg = b.grid_position ?? 99;
    if (ag !== bg) return ag - bg;
    return a.tla.localeCompare(b.tla);
  });
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
      {sorted.map((d) => (
        <DriverCard key={d.racing_number} driver={d} />
      ))}
    </div>
  );
}
```

- [ ] **Step 6: Implement `site/src/routes/Home.tsx`**

```tsx
import { useEffect, useState } from "react";
import { RaceHeader } from "../components/RaceHeader";
import { DriverGrid } from "../components/DriverGrid";
import { loadManifest } from "../lib/data";
import type { Manifest } from "../lib/schemas";

export default function Home() {
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadManifest("/data/australia-2026.json")
      .then(setManifest)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  if (error) {
    return (
      <main className="mx-auto max-w-6xl p-6">
        <p className="text-compound-soft">Data unavailable: {error}</p>
      </main>
    );
  }
  if (!manifest) {
    return (
      <main className="mx-auto max-w-6xl p-6">
        <p className="text-f1-muted">Loading…</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-6xl p-6">
      <RaceHeader race={manifest.race} />
      <DriverGrid drivers={manifest.race.drivers} />
    </main>
  );
}
```

- [ ] **Step 7: Run the test and verify it passes**

Run: `cd site && npm run test -- tests/unit/DriverCard.test.tsx`
Expected: 4 passed.

- [ ] **Step 8: Commit**

```bash
git add site/src/components/RaceHeader.tsx site/src/components/DriverCard.tsx site/src/components/DriverGrid.tsx site/src/routes/Home.tsx site/tests/unit/DriverCard.test.tsx
git commit -m "feat(site): add RaceHeader, DriverCard, DriverGrid, Home route"
```

---

## Task C3: Router, NotFound, Driver route skeleton

**Files:**
- Replace: `site/src/App.tsx`
- Create: `site/src/routes/NotFound.tsx`
- Create: `site/src/routes/Driver.tsx`
- Create: `site/src/components/DriverHeader.tsx`
- Create: `site/public/404.html`

- [ ] **Step 1: Replace `site/src/App.tsx`**

```tsx
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import Home from "./routes/Home";
import Driver from "./routes/Driver";
import NotFound from "./routes/NotFound";

const router = createBrowserRouter([
  { path: "/", element: <Home /> },
  { path: "/driver/:tla", element: <Driver />, errorElement: <NotFound /> },
  { path: "*", element: <NotFound /> },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
```

- [ ] **Step 2: Create `site/src/routes/NotFound.tsx`**

```tsx
import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <main className="mx-auto max-w-6xl p-6">
      <h1 className="text-3xl font-bold">404</h1>
      <p className="mt-2 text-f1-muted">That page does not exist.</p>
      <Link to="/" className="mt-4 inline-block text-compound-medium underline">
        Back to grid
      </Link>
    </main>
  );
}
```

- [ ] **Step 3: Create `site/src/components/DriverHeader.tsx`**

```tsx
import { Link } from "react-router-dom";
import type { Manifest } from "../lib/schemas";

type Driver = Manifest["race"]["drivers"][number];

export function DriverHeader({ driver }: { driver: Driver }) {
  return (
    <section
      style={{ borderLeftColor: driver.team_color }}
      className="mb-6 flex items-baseline justify-between rounded-md border-l-4 bg-f1-panel p-4"
    >
      <div>
        <p className="text-xs uppercase tracking-widest text-f1-muted">#{driver.racing_number}</p>
        <h2 className="text-2xl font-bold">{driver.full_name}</h2>
        <p className="text-sm text-f1-muted">{driver.team_name}</p>
      </div>
      <div className="text-right">
        {driver.grid_position != null ? (
          <p className="font-mono text-lg">P{driver.grid_position}</p>
        ) : (
          <p className="font-mono text-lg text-f1-muted">—</p>
        )}
        <Link to="/" className="text-xs text-f1-muted underline">
          ← back to grid
        </Link>
      </div>
    </section>
  );
}
```

- [ ] **Step 4: Create placeholder `site/src/routes/Driver.tsx`**

```tsx
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { DriverHeader } from "../components/DriverHeader";
import { RaceHeader } from "../components/RaceHeader";
import { loadManifest } from "../lib/data";
import type { Manifest } from "../lib/schemas";
import NotFound from "./NotFound";

export default function Driver() {
  const { tla } = useParams<{ tla: string }>();
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadManifest("/data/australia-2026.json")
      .then(setManifest)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  if (error) {
    return (
      <main className="mx-auto max-w-6xl p-6">
        <p className="text-compound-soft">Data unavailable: {error}</p>
      </main>
    );
  }
  if (!manifest) {
    return (
      <main className="mx-auto max-w-6xl p-6">
        <p className="text-f1-muted">Loading…</p>
      </main>
    );
  }

  const driver = manifest.race.drivers.find((d) => d.tla === tla);
  if (!driver) return <NotFound />;

  return (
    <main className="mx-auto max-w-6xl p-6">
      <RaceHeader race={manifest.race} />
      <DriverHeader driver={driver} />
      {/* InventoryView comes in Task C5 */}
    </main>
  );
}
```

- [ ] **Step 5: Create `site/public/404.html` (SPA fallback for GitHub Pages)**

```html
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>Redirecting…</title>
    <script>
      // Preserve the requested path and redirect to the SPA at /?redirect=PATH,
      // which main.tsx (below) consumes on first render.
      (function () {
        var path = window.location.pathname + window.location.search + window.location.hash;
        var base = "/";
        window.location.replace(base + "?redirect=" + encodeURIComponent(path));
      })();
    </script>
  </head>
  <body></body>
</html>
```

- [ ] **Step 6: Extend `site/src/main.tsx` to honour `?redirect=`**

Replace the body of `main.tsx` with:

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles/index.css";

// If the 404 fallback redirected us with ?redirect=<path>, restore that URL
// before rendering so React Router matches the right route.
const params = new URLSearchParams(window.location.search);
const redirect = params.get("redirect");
if (redirect) {
  window.history.replaceState({}, "", redirect);
}

const rootEl = document.getElementById("root");
if (!rootEl) {
  throw new Error("#root element missing in index.html");
}
createRoot(rootEl).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

- [ ] **Step 7: Smoke-test locally**

Run: `cd site && npm run dev`
Open `http://localhost:5173/driver/VER` and then `/driver/NOPE`.
Expected: VER shows the header; NOPE shows the 404 page with "back to grid" link. `/` shows the grid.

Stop the dev server with Ctrl+C when done.

- [ ] **Step 8: Commit**

```bash
git add site/src/App.tsx site/src/routes/NotFound.tsx site/src/routes/Driver.tsx site/src/components/DriverHeader.tsx site/public/404.html site/src/main.tsx
git commit -m "feat(site): wire router, 404 fallback, driver route skeleton"
```

---

## Task C4: UsageBar (visx)

**Files:**
- Create: `site/src/components/UsageBar.tsx`

- [ ] **Step 1: Implement `site/src/components/UsageBar.tsx`**

```tsx
import { Group } from "@visx/group";
import { AxisBottom } from "@visx/axis";
import { scaleBand, scaleLinear } from "@visx/scale";
import { Bar } from "@visx/shape";
import { ParentSize } from "@visx/responsive";
import type { Manifest } from "../lib/schemas";

type Set = Manifest["race"]["drivers"][number]["sets"][number];

const SESSIONS: ReadonlyArray<"FP1" | "FP2" | "FP3" | "Q" | "R"> = ["FP1", "FP2", "FP3", "Q", "R"];
const HEIGHT = 44;
const MARGIN = { top: 4, right: 4, bottom: 18, left: 4 };

function firstToLastIndex(set: Set): [number, number] {
  return [SESSIONS.indexOf(set.first_seen_session), SESSIONS.indexOf(set.last_seen_session)];
}

export function UsageBar({ set }: { set: Set }) {
  return (
    <ParentSize>
      {({ width }) => {
        if (width === 0) return null;

        const xScale = scaleBand<string>({
          domain: SESSIONS as unknown as string[],
          range: [MARGIN.left, width - MARGIN.right],
          padding: 0.2,
        });
        const innerHeight = HEIGHT - MARGIN.top - MARGIN.bottom;
        const yScale = scaleLinear<number>({
          domain: [0, 1],
          range: [innerHeight, 0],
        });
        const [firstIdx, lastIdx] = firstToLastIndex(set);

        return (
          <svg width={width} height={HEIGHT} aria-label={`usage timeline for ${set.set_id}`}>
            <Group top={MARGIN.top}>
              {SESSIONS.map((s, i) => {
                const x = xScale(s)!;
                const bw = xScale.bandwidth();
                const active = i >= firstIdx && i <= lastIdx;
                return (
                  <Bar
                    key={s}
                    x={x}
                    y={yScale(1)}
                    width={bw}
                    height={innerHeight - yScale(1)}
                    fill={active ? "currentColor" : "rgba(255,255,255,0.08)"}
                    rx={2}
                  />
                );
              })}
            </Group>
            <AxisBottom
              top={HEIGHT - MARGIN.bottom}
              scale={xScale}
              tickFormat={(s) => String(s)}
              stroke="transparent"
              tickStroke="transparent"
              tickLabelProps={() => ({
                fill: "var(--color-f1-muted)",
                fontSize: 10,
                textAnchor: "middle",
                dy: "0.33em",
                fontFamily: "var(--font-mono)",
              })}
            />
          </svg>
        );
      }}
    </ParentSize>
  );
}
```

- [ ] **Step 2: Smoke-check with tsc**

Run: `cd site && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add site/src/components/UsageBar.tsx
git commit -m "feat(site): add visx UsageBar for per-set timeline"
```

---

## Task C5: TyreSet card + InventoryView

**Files:**
- Create: `site/src/components/TyreSet.tsx`
- Create: `site/src/components/InventoryView.tsx`
- Modify: `site/src/routes/Driver.tsx`

- [ ] **Step 1: Implement `site/src/components/TyreSet.tsx`**

```tsx
import type { Manifest } from "../lib/schemas";
import { TyreDot } from "./TyreDot";
import { UsageBar } from "./UsageBar";

type Set = Manifest["race"]["drivers"][number]["sets"][number];

function historyLabel(set: Set): string {
  if (set.first_seen_session === "R" && set.laps === 0) return "Saved for race";
  if (set.first_seen_session === set.last_seen_session) return set.first_seen_session;
  return `${set.first_seen_session} → ${set.last_seen_session}`;
}

function lapsLabel(set: Set): string {
  return set.laps === 0 ? "NEW" : `${set.laps} laps`;
}

export function TyreSet({ set }: { set: Set }) {
  const savedForRace = set.first_seen_session === "R" && set.laps === 0;
  return (
    <div
      className={[
        "rounded-md bg-f1-panel p-3 text-compound-" + set.compound.toLowerCase(),
        "border border-f1-border",
      ].join(" ")}
    >
      <div className="flex items-center gap-3">
        <TyreDot compound={set.compound} size="lg" />
        <div className="flex-1">
          <p className="font-mono text-sm text-f1-text">{set.set_id}</p>
          <p className="text-xs text-f1-muted">{lapsLabel(set)}</p>
        </div>
        <span
          className={[
            "rounded px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider",
            savedForRace ? "bg-compound-medium text-f1-bg" : "bg-f1-border text-f1-muted",
          ].join(" ")}
        >
          {historyLabel(set)}
        </span>
      </div>
      <div className="mt-2 text-f1-text/80">
        <UsageBar set={set} />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Implement `site/src/components/InventoryView.tsx`**

```tsx
import type { Manifest } from "../lib/schemas";
import { TyreSet } from "./TyreSet";

type Driver = Manifest["race"]["drivers"][number];
type Compound = Driver["sets"][number]["compound"];

const COMPOUND_ORDER: Compound[] = ["HARD", "MEDIUM", "SOFT", "INTERMEDIATE", "WET"];

export function InventoryView({ driver }: { driver: Driver }) {
  if (driver.sets.length === 0) {
    return <p className="text-f1-muted">No tyre data available.</p>;
  }
  const grouped: Record<Compound, typeof driver.sets> = {
    HARD: [],
    MEDIUM: [],
    SOFT: [],
    INTERMEDIATE: [],
    WET: [],
  };
  for (const s of driver.sets) grouped[s.compound].push(s);

  return (
    <section className="grid grid-cols-1 gap-4 md:grid-cols-2">
      {COMPOUND_ORDER.filter((c) => grouped[c].length > 0).map((c) => (
        <div key={c}>
          <h3 className="mb-2 text-xs font-mono uppercase tracking-widest text-f1-muted">{c}</h3>
          <div className="flex flex-col gap-2">
            {grouped[c].map((s) => (
              <TyreSet key={s.set_id} set={s} />
            ))}
          </div>
        </div>
      ))}
    </section>
  );
}
```

- [ ] **Step 3: Update `site/src/routes/Driver.tsx` to render InventoryView**

Replace the placeholder comment `{/* InventoryView comes in Task C5 */}` with:

```tsx
      <InventoryView driver={driver} />
```

Add the import at the top:

```tsx
import { InventoryView } from "../components/InventoryView";
```

- [ ] **Step 4: Copy the real data JSON into `site/public/data/` and smoke-test**

Run:
```bash
mkdir -p site/public/data
cp precompute/out/australia-2026.json site/public/data/
cd site && npm run dev
```

Open `http://localhost:5173/`, click any driver.
Expected: driver detail shows grouped tyre sets (HARD/MEDIUM/SOFT), each with a TyreDot, lap counter, history badge, and a small SVG timeline.

Stop the server with Ctrl+C.

- [ ] **Step 5: Commit**

```bash
git add site/src/components/TyreSet.tsx site/src/components/InventoryView.tsx site/src/routes/Driver.tsx
git commit -m "feat(site): render per-driver tyre inventory with usage bars"
```

---

## Task C6: Playwright E2E tests

**Files:**
- Create: `site/playwright.config.ts`
- Create: `site/tests/e2e/home.spec.ts`
- Create: `site/tests/e2e/driver.spec.ts`
- Create: `site/tests/e2e/routing.spec.ts`

- [ ] **Step 1: Create `site/playwright.config.ts`**

```ts
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  retries: 0,
  workers: 2,
  use: {
    baseURL: "http://localhost:4173",
    trace: "on-first-retry",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
  webServer: {
    command: "npm run build && npm run preview -- --port 4173 --strictPort",
    url: "http://localhost:4173",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
```

- [ ] **Step 2: Install Playwright browsers**

Run: `cd site && npx playwright install chromium`

- [ ] **Step 3: Create `site/tests/e2e/home.spec.ts`**

```ts
import { test, expect } from "@playwright/test";

test("home grid shows 22 driver cards", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Australian Grand Prix/ })).toBeVisible();
  // Each DriverCard is an anchor with an href that starts with /driver/
  const cards = page.locator('a[href^="/driver/"]');
  await expect(cards).toHaveCount(22);
});

test("clicking a card navigates to the driver detail page", async ({ page }) => {
  await page.goto("/");
  const first = page.locator('a[href^="/driver/"]').first();
  const href = await first.getAttribute("href");
  await first.click();
  await expect(page).toHaveURL(new RegExp(href!));
});
```

- [ ] **Step 4: Create `site/tests/e2e/driver.spec.ts`**

```ts
import { test, expect } from "@playwright/test";

test("driver page shows inventory groups", async ({ page }) => {
  await page.goto("/driver/VER");
  await expect(page.getByRole("heading", { name: /Max Verstappen/ })).toBeVisible();
  // At least one of HARD/MEDIUM/SOFT sections should appear.
  const sections = page.locator("h3");
  await expect(sections.first()).toBeVisible();
  // The set cards render SVG usage bars.
  await expect(page.locator("svg").first()).toBeVisible();
});
```

- [ ] **Step 5: Create `site/tests/e2e/routing.spec.ts`**

```ts
import { test, expect } from "@playwright/test";

test("unknown driver TLA renders the NotFound page", async ({ page }) => {
  await page.goto("/driver/ZZZ");
  await expect(page.getByRole("heading", { name: "404" })).toBeVisible();
});

test("unknown route renders the NotFound page", async ({ page }) => {
  await page.goto("/totally-unknown");
  await expect(page.getByRole("heading", { name: "404" })).toBeVisible();
});
```

- [ ] **Step 6: Run E2E tests**

Run: `cd site && npm run test:e2e`
Expected: 5 tests pass. (Playwright spins up `npm run preview` automatically.)

- [ ] **Step 7: Commit**

```bash
git add site/playwright.config.ts site/tests/e2e/
git commit -m "test(site): add Playwright E2E tests for home, driver, routing"
```

---

# Section D — Orchestration and Deploy

## Task D1: Root-level Makefile

**Files:**
- Create: `Makefile`

- [ ] **Step 1: Create `Makefile` at the repository root**

```makefile
.PHONY: install precompute schema genzod build dev test test-py test-site test-e2e clean deploy-local

# -------- setup ------------------------------------------------------------

install:
	cd precompute && uv sync --extra dev
	cd site && npm ci

# -------- precompute -------------------------------------------------------

schema:
	cd precompute && uv run python -m f1.schema

precompute: schema
	cd precompute && uv run python -m f1.build

# -------- site -------------------------------------------------------------

genzod:
	cd site && npm run gen:zod

build: precompute genzod
	mkdir -p site/public/data
	cp precompute/out/australia-2026.json site/public/data/
	cd site && npm run build

dev: precompute genzod
	mkdir -p site/public/data
	cp precompute/out/australia-2026.json site/public/data/
	cd site && npm run dev

# -------- tests ------------------------------------------------------------

test-py:
	cd precompute && uv run pytest

test-site:
	cd site && npm run test

test-e2e:
	cd site && npm run test:e2e

test: test-py test-site test-e2e

# -------- deploy (local) ---------------------------------------------------

# Builds and then pushes site/dist to the gh-pages branch using gh-pages npm.
# Requires: npm i -D gh-pages (added on first use).
deploy-local: test build
	cd site && npx --yes gh-pages@6 -d dist

# -------- housekeeping -----------------------------------------------------

clean:
	rm -rf precompute/out/*
	rm -rf site/dist site/public/data/*.json
```

- [ ] **Step 2: Test each relevant target**

```bash
make install
make precompute
make genzod
make build
make test-py
make test-site
make test-e2e
```

Expected: every command exits with code 0. `make build` produces `site/dist/index.html`.

- [ ] **Step 3: Commit**

```bash
git add Makefile
git commit -m "chore: add root Makefile orchestration"
```

---

## Task D2: GitHub Actions deploy workflow

**Files:**
- Create: `.github/workflows/deploy.yml`

- [ ] **Step 1: Enable GitHub Pages for the repo**

On github.com, Settings → Pages → Build and deployment → Source: "GitHub Actions".

- [ ] **Step 2: Create `.github/workflows/deploy.yml`**

```yaml
name: Deploy

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - uses: astral-sh/setup-uv@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
      - run: make install
      - run: make test-py
      - run: make test-site
      - run: make build
      - name: Install Playwright browsers
        run: cd site && npx playwright install --with-deps chromium
      - run: make test-e2e
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: site/dist

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 3: Commit and push**

```bash
git add .github/workflows/deploy.yml
git commit -m "ci: deploy site to GitHub Pages on push to main"
```

After push: watch the Actions tab. First run should complete in under 3 minutes and publish a URL under `https://<username>.github.io/<repo>/`.

- [ ] **Step 4: Verify the live site**

Open the URL printed by the Actions run.
Expected: home page renders 22 cards; `/driver/VER` works as a direct link (thanks to the 404.html fallback).

---

# Section E — Self-Review and Wrap-Up

## Task E1: Run the full test matrix once more

- [ ] **Step 1: Run all tests from a clean state**

```bash
make clean
make install
make test
```

Expected: all three test suites pass (pytest, vitest, playwright). If anything fails, fix before continuing.

- [ ] **Step 2: Check Python coverage**

Run: `cd precompute && uv run pytest`
Expected: `TOTAL ... 85%+` coverage on `f1/`. If below, add tests to the weakest module.

- [ ] **Step 3: Lighthouse check (manual, optional but encouraged)**

Run: `cd site && npm run preview -- --port 4173`
In a browser, open DevTools → Lighthouse on `http://localhost:4173/`.
Expected: Performance ≥ 90, Accessibility ≥ 90. If below, inspect Lighthouse recommendations and address the top items.

- [ ] **Step 4: Commit any fixups**

```bash
git add -A
git commit -m "test: coverage and performance tuning"  # only if there is anything to commit
```

---

# Spec Coverage Map

Quick cross-reference from spec sections to plan tasks, to confirm nothing was dropped:

| Spec section | Implementing tasks |
|--------------|-------------------|
| §1 Product Overview | C2, C5 (grid + detail) |
| §2 Scope / Non-goals | whole plan — out-of-scope items never appear |
| §3 Architecture | A1, B1, D1, D2 |
| §3 JSON Schema bridge | A10, B2 |
| §4 Data model (TyreSet, DriverInventory, Race, Manifest) | A4 |
| §5 Algorithm — parse | A2 |
| §5 Algorithm — reduce | A3 |
| §5 Algorithm — extract session stints | A5 |
| §5 Algorithm — Pass A | A6 |
| §5 Algorithm — Pass B (saved-for-race, no mutation) | A7 |
| §5 Driver metadata, grid positions | A8 |
| §5 Build orchestration | A9 |
| §6 UI routes | C2 (Home), C3 (Driver + 404) |
| §6 TyreDot, DriverCard, DriverGrid | C1, C2 |
| §6 TyreSet card + UsageBar (visx) | C4, C5 |
| §6 Tailwind theme + team colors | B1 (CSS), C2 (inline style) |
| §6 Responsive breakpoints | C2 (DriverGrid grid-cols-*), C5 (md:grid-cols-2) |
| §6 GH Pages 404.html fallback | C3 |
| §7 Error handling (Python build fails on 0 drivers / bad Pydantic) | A9 (raises RuntimeError) |
| §7 Error handling (TS Zod + HTTP + schema_version) | B3 |
| §7 Error handling (NotFound) | C3 |
| §8 Testing — Python unit | A2..A9 tests |
| §8 Testing — Vitest component | C1, C2, B3 tests |
| §8 Testing — Playwright E2E | C6 |
| §9 Performance (preload, lazy JSON) | B1 (preload link), loader fetches at runtime |
| §9 Makefile | D1 |
| §9 GitHub Actions | D2 |

---

# Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-17-pre-race-tyre-inventory.md`. Two execution options:

**1. Subagent-Driven (recommended)** — Dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using `executing-plans`, batch execution with checkpoints.

**Which approach?**
