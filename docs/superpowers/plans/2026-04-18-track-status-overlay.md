# Track Status Overlay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render low-opacity full-height bands + a thin top strip on the Race Strategy chart that mark yellow / Safety Car / VSC / red-flag windows, for Race and Sprint sessions across the three featured 2026 races.

**Architecture:** Add `TrackStatus.jsonStream` and `LapCount.jsonStream` to the CI fetch list. A new `precompute/src/f1/track_status.py` module walks raw events to produce `StatusBand` objects keyed to lap numbers, which are emitted on `manifest.race.race_status_bands` / `sprint_status_bands`. Site reads these via the generated Zod schema and renders them as an SVG overlay on `StrategyChart`, with a tooltip reusing the chart's existing `useTooltip` via a discriminated union payload.

**Tech Stack:** Python 3.13 (Pydantic v2, pytest, ruff, mypy --strict), React 19, TypeScript, Vite, Tailwind, @visx, Zod, Vitest, Playwright.

**Spec:** `docs/superpowers/specs/2026-04-18-track-status-overlay-design.md`

---

## Task 0: Create feature branch

**Files:** none (git state only)

- [ ] **Step 1: Branch from main**

Run:
```bash
git switch main
git pull --ff-only
git switch -c feat/track-status-overlay
```

Expected: branch `feat/track-status-overlay` is checked out and tracks nothing remote yet.

- [ ] **Step 2: Verify clean working tree**

Run: `git status --short`
Expected: no output (or only untracked files unrelated to this feature).

---

## Task 1: Add `StatusBand` Pydantic model + two fields on `Race`

**Files:**
- Modify: `precompute/src/f1/models.py`
- Test: `precompute/tests/test_models.py`

- [ ] **Step 1: Write failing test for `StatusBand` validation**

Append to `precompute/tests/test_models.py`:

```python
from f1.models import StatusBand


def test_status_band_requires_positive_laps() -> None:
    with pytest.raises(ValidationError):
        StatusBand(status="Yellow", start_lap=0, end_lap=3)


def test_status_band_allows_equal_start_and_end() -> None:
    band = StatusBand(status="SCDeployed", start_lap=5, end_lap=5)
    assert band.start_lap == 5
    assert band.end_lap == 5


def test_status_band_rejects_unknown_code() -> None:
    with pytest.raises(ValidationError):
        StatusBand(status="Blue", start_lap=1, end_lap=2)  # type: ignore[arg-type]
```

Ensure the file already imports `pytest` and `ValidationError`; if not, add:
```python
import pytest
from pydantic import ValidationError
```

- [ ] **Step 2: Write failing test for `Race.race_status_bands` / `sprint_status_bands` defaults**

Find the existing test in `test_models.py` that constructs a `Race` (grep for `Race(` — there should be one). Add a new test beneath it:

```python
def test_race_has_empty_status_band_defaults() -> None:
    race = Race(
        slug="x",
        name="X GP",
        location="City",
        country="Country",
        season=2026,
        round=1,
        date="2026-01-01",
        sessions=[],
        drivers=[],
    )
    assert race.race_status_bands == []
    assert race.sprint_status_bands == []
```

- [ ] **Step 3: Run tests to verify they fail**

Run from `precompute/`: `uv run pytest tests/test_models.py -v`

Expected: three new tests fail (`StatusBand` not defined; `Race` has no such field).

- [ ] **Step 4: Implement the model changes**

Edit `precompute/src/f1/models.py`. Near the top where `Compound` and `SessionKey` are defined, add:

```python
TrackStatusCode = Literal["Yellow", "SCDeployed", "VSCDeployed", "Red"]
```

After the `TyreSet` class, before `RaceStint`, add a new class:

```python
class StatusBand(_StrictModel):
    """One continuous non-green track-status period within a session."""

    status: TrackStatusCode
    start_lap: int = Field(ge=1, description="Lap the status became active (inclusive)")
    end_lap: int = Field(ge=1, description="Last lap the status was active (inclusive)")
```

Inside `class Race(_StrictModel)`, after the `drivers` field, add:

```python
race_status_bands: list[StatusBand] = Field(default_factory=list)
sprint_status_bands: list[StatusBand] = Field(default_factory=list)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_models.py -v`
Expected: all tests green, including the three new ones.

- [ ] **Step 6: Run lint + mypy to catch strict-mode regressions**

Run: `uv run ruff check . && uv run mypy src`
Expected: no errors.

- [ ] **Step 7: Commit**

```bash
git add precompute/src/f1/models.py precompute/tests/test_models.py
git commit -m "feat(precompute): add StatusBand model and race_status_bands fields"
```

---

## Task 2: Implement `track_status.py` — `collect_status_transitions`

**Files:**
- Create: `precompute/src/f1/track_status.py`
- Create: `precompute/tests/test_track_status.py`

- [ ] **Step 1: Write failing test**

Create `precompute/tests/test_track_status.py`:

```python
"""Unit tests for precompute/src/f1/track_status.py."""
from __future__ import annotations

from f1.parse import Event
from f1.track_status import collect_status_transitions


def _ev(ts: int, payload: dict) -> Event:
    return Event(timestamp_ms=ts, data=payload)


def test_collect_status_transitions_extracts_all_codes() -> None:
    events = [
        _ev(0,    {"Status": "2", "Message": "Yellow"}),
        _ev(1000, {"Status": "1", "Message": "AllClear"}),
        _ev(2000, {"Status": "4", "Message": "SCDeployed"}),
        _ev(3000, {"Status": "1", "Message": "AllClear"}),
    ]
    assert collect_status_transitions(events) == [
        (0, "2"),
        (1000, "1"),
        (2000, "4"),
        (3000, "1"),
    ]


def test_collect_status_transitions_skips_malformed_payloads() -> None:
    events = [
        _ev(0, {"Message": "no-status"}),
        _ev(1, {"Status": 42, "Message": "not-a-string"}),
        _ev(2, {"Status": "4"}),
    ]
    assert collect_status_transitions(events) == [(2, "4")]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_track_status.py -v`
Expected: `ModuleNotFoundError: No module named 'f1.track_status'`.

- [ ] **Step 3: Implement the function**

Create `precompute/src/f1/track_status.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_track_status.py -v`
Expected: 2 tests pass.

- [ ] **Step 5: Commit**

```bash
git add precompute/src/f1/track_status.py precompute/tests/test_track_status.py
git commit -m "feat(precompute): add collect_status_transitions"
```

---

## Task 3: Implement `collect_lap_boundaries`

**Files:**
- Modify: `precompute/src/f1/track_status.py`
- Modify: `precompute/tests/test_track_status.py`

- [ ] **Step 1: Write failing test**

Append to `test_track_status.py`:

```python
from f1.track_status import collect_lap_boundaries


def test_collect_lap_boundaries_extracts_current_lap_changes() -> None:
    events = [
        _ev(0,     {"CurrentLap": 1, "TotalLaps": 53}),
        _ev(90000, {"CurrentLap": 2}),
        _ev(180000,{"CurrentLap": 3}),
    ]
    assert collect_lap_boundaries(events) == [
        (0, 1),
        (90000, 2),
        (180000, 3),
    ]


def test_collect_lap_boundaries_seeds_lap_one_if_first_event_is_later() -> None:
    # Defensive: if LapCount stream starts at CurrentLap=5 (partial archive),
    # seed (0, 1) so callers can resolve any early timestamp to lap 1.
    events = [
        _ev(120000, {"CurrentLap": 5}),
        _ev(180000, {"CurrentLap": 6}),
    ]
    assert collect_lap_boundaries(events) == [
        (0, 1),
        (120000, 5),
        (180000, 6),
    ]


def test_collect_lap_boundaries_ignores_non_int_and_missing_values() -> None:
    events = [
        _ev(0,  {"CurrentLap": 1}),
        _ev(1,  {"TotalLaps": 53}),       # no CurrentLap
        _ev(2,  {"CurrentLap": "two"}),   # not int
        _ev(3,  {"CurrentLap": 2}),
    ]
    assert collect_lap_boundaries(events) == [(0, 1), (3, 2)]


def test_collect_lap_boundaries_empty_input_returns_seed() -> None:
    # An empty stream still returns the (0, 1) seed so downstream code can
    # clamp early-session timestamps without a special case.
    assert collect_lap_boundaries([]) == [(0, 1)]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_track_status.py -v`
Expected: four new tests fail with `ImportError`.

- [ ] **Step 3: Implement**

Append to `precompute/src/f1/track_status.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_track_status.py -v`
Expected: all 6 tests pass.

- [ ] **Step 5: Lint + type check**

Run: `uv run ruff check . && uv run mypy src`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add precompute/src/f1/track_status.py precompute/tests/test_track_status.py
git commit -m "feat(precompute): add collect_lap_boundaries"
```

---

## Task 4: Implement `build_status_bands` — standard cycle

**Files:**
- Modify: `precompute/src/f1/track_status.py`
- Modify: `precompute/tests/test_track_status.py`

- [ ] **Step 1: Write failing test for the standard cycle**

Append to `test_track_status.py`:

```python
from f1.models import StatusBand
from f1.track_status import build_status_bands


def test_build_status_bands_standard_yellow_then_sc() -> None:
    # Status transitions at ms: Yellow opens at 0 (lap 1), AllClear at 180000 (lap 3),
    # SC at 2_400_000 (lap 26), AllClear at 3_000_000 (lap 32).
    transitions = [
        (0,       "2"),    # Yellow
        (180_000, "1"),    # AllClear
        (2_400_000, "4"),  # SCDeployed
        (3_000_000, "1"),  # AllClear
    ]
    # Lap boundaries: CurrentLap changes at 90s intervals (93s per lap ~ Japan).
    lap_boundaries = [(0, 1)]
    for lap in range(2, 55):
        lap_boundaries.append((93_000 * (lap - 1), lap))

    bands = build_status_bands(transitions, lap_boundaries, total_laps=53)
    assert bands == [
        StatusBand(status="Yellow",     start_lap=1,  end_lap=2),
        StatusBand(status="SCDeployed", start_lap=26, end_lap=32),
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_track_status.py::test_build_status_bands_standard_yellow_then_sc -v`
Expected: `ImportError` for `build_status_bands`.

- [ ] **Step 3: Implement**

Append to `precompute/src/f1/track_status.py`:

```python
import bisect

from f1.models import StatusBand, TrackStatusCode

# F1 live-timing TrackStatus code → our enum label. Codes not in this map
# (notably "1" AllClear and "7" VSCEnding) are treated as band closers.
_CODE_TO_STATUS: dict[str, TrackStatusCode] = {
    "2": "Yellow",
    "4": "SCDeployed",
    "5": "Red",
    "6": "VSCDeployed",
}


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
                bands.append(
                    StatusBand(status=open_status, start_lap=open_start_lap, end_lap=max(lap - 1, open_start_lap))
                )
                open_status = None
                open_start_lap = None
            continue

        if code == "7":  # VSCEnding closes only VSCDeployed
            if open_status == "VSCDeployed" and open_start_lap is not None:
                bands.append(
                    StatusBand(status="VSCDeployed", start_lap=open_start_lap, end_lap=max(lap - 1, open_start_lap))
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
            bands.append(
                StatusBand(status=open_status, start_lap=open_start_lap, end_lap=max(lap - 1, open_start_lap))
            )

        open_status = new_status
        open_start_lap = lap

    # Band still open at session end → clamp to total_laps.
    if open_status is not None and open_start_lap is not None:
        bands.append(StatusBand(status=open_status, start_lap=open_start_lap, end_lap=total_laps))

    return bands
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_track_status.py::test_build_status_bands_standard_yellow_then_sc -v`

Expected: PASS. (The `end_lap=2` for Yellow is correct: AllClear fired on lap 3, so the last lap under Yellow was lap 2.)

- [ ] **Step 5: Run entire test file**

Run: `uv run pytest tests/test_track_status.py -v`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add precompute/src/f1/track_status.py precompute/tests/test_track_status.py
git commit -m "feat(precompute): add build_status_bands for standard cycle"
```

---

## Task 5: `build_status_bands` edge cases

**Files:**
- Modify: `precompute/tests/test_track_status.py`

All five edge cases are already handled by the implementation in Task 4. This task adds regression tests to lock in the behaviour.

- [ ] **Step 1: Write tests for each edge case**

Append to `test_track_status.py`:

```python
def _linear_laps(n: int, per_lap_ms: int = 90_000) -> list[tuple[int, int]]:
    """Helper: generate lap boundaries at fixed pace."""
    return [(per_lap_ms * (lap - 1), lap) for lap in range(1, n + 1)]


def test_build_status_bands_status_at_session_start() -> None:
    # Yellow active from t=0 on lap 1.
    transitions = [(0, "2"), (300_000, "1")]
    bands = build_status_bands(transitions, _linear_laps(10), total_laps=10)
    assert bands == [StatusBand(status="Yellow", start_lap=1, end_lap=3)]


def test_build_status_bands_status_extends_to_session_end() -> None:
    # SC deployed at lap 5, never cleared — clamped to total_laps.
    transitions = [(5 * 90_000, "4")]
    bands = build_status_bands(transitions, _linear_laps(10), total_laps=10)
    assert bands == [StatusBand(status="SCDeployed", start_lap=6, end_lap=10)]


def test_build_status_bands_vsc_ending_closes_vsc() -> None:
    transitions = [
        (0,        "6"),  # VSCDeployed on lap 1
        (300_000,  "7"),  # VSCEnding on lap 4
    ]
    bands = build_status_bands(transitions, _linear_laps(10), total_laps=10)
    assert bands == [StatusBand(status="VSCDeployed", start_lap=1, end_lap=3)]


def test_build_status_bands_stray_vsc_ending_is_noop() -> None:
    # VSCEnding with no prior VSCDeployed — should produce no band.
    transitions = [(300_000, "7")]
    bands = build_status_bands(transitions, _linear_laps(10), total_laps=10)
    assert bands == []


def test_build_status_bands_duplicate_codes_do_not_split() -> None:
    transitions = [(0, "2"), (90_000, "2"), (180_000, "1")]
    bands = build_status_bands(transitions, _linear_laps(10), total_laps=10)
    assert bands == [StatusBand(status="Yellow", start_lap=1, end_lap=2)]


def test_build_status_bands_red_flag_band() -> None:
    transitions = [(0, "5"), (300_000, "1")]
    bands = build_status_bands(transitions, _linear_laps(10), total_laps=10)
    assert bands == [StatusBand(status="Red", start_lap=1, end_lap=3)]


def test_build_status_bands_empty_inputs_return_empty_list() -> None:
    assert build_status_bands([], _linear_laps(10), total_laps=10) == []
    assert build_status_bands([(0, "2")], [], total_laps=10) == []
    assert build_status_bands([(0, "2")], _linear_laps(10), total_laps=0) == []


def test_build_status_bands_non_green_to_non_green_without_allclear() -> None:
    # Yellow on lap 1, VSC deployed on lap 5 without AllClear in between —
    # close the Yellow at lap 4, open VSC on lap 5.
    transitions = [(0, "2"), (5 * 90_000 - 1000, "6"), (8 * 90_000, "1")]
    bands = build_status_bands(transitions, _linear_laps(15), total_laps=15)
    assert bands == [
        StatusBand(status="Yellow",      start_lap=1, end_lap=4),
        StatusBand(status="VSCDeployed", start_lap=5, end_lap=7),
    ]
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `uv run pytest tests/test_track_status.py -v`
Expected: all tests pass (the Task 4 implementation already covers every case).

- [ ] **Step 3: Check coverage stays ≥ 85%**

Run: `uv run pytest --cov=f1 --cov-report=term-missing`
Expected: coverage gate passes; in particular `f1/track_status.py` is ≥ 90%.

- [ ] **Step 4: Commit**

```bash
git add precompute/tests/test_track_status.py
git commit -m "test(precompute): cover edge cases for build_status_bands"
```

---

## Task 6: Add `TrackStatus.jsonStream` and `LapCount.jsonStream` to fetch list

**Files:**
- Modify: `seasons/fetch_race.py:22-28`

- [ ] **Step 1: Edit `MANIFEST_FILES`**

In `seasons/fetch_race.py`, change lines 22–28 from:

```python
MANIFEST_FILES: list[str] = [
    "SessionInfo.json",
    "DriverList.jsonStream",
    "TyreStintSeries.jsonStream",
    "TimingAppData.jsonStream",
    "TimingData.jsonStream",
]
```

to:

```python
MANIFEST_FILES: list[str] = [
    "SessionInfo.json",
    "DriverList.jsonStream",
    "TyreStintSeries.jsonStream",
    "TimingAppData.jsonStream",
    "TimingData.jsonStream",
    "TrackStatus.jsonStream",
    "LapCount.jsonStream",
]
```

- [ ] **Step 2: Fetch the new files for all featured races**

Run from the repo root: `make fetch-race`

Expected output: the totals line shows `ok` counts that include the new files. Each already-cached file is reported as `cached`; the six new fetches (2 files × 3 races × 1–5 sessions) should appear as `ok`. If any report `missing`, that means F1's archive doesn't have that specific session — acceptable for sessions that happened before or after TrackStatus was tracked.

- [ ] **Step 3: Verify fetched files are present for japan-2026 race**

Run:
```bash
ls seasons/2026/2026-03-29_Japanese_Grand_Prix/2026-03-29_Race/TrackStatus.jsonStream
ls seasons/2026/2026-03-29_Japanese_Grand_Prix/2026-03-29_Race/LapCount.jsonStream
```

Expected: both files exist. (These files are gitignored; they land on disk only.)

- [ ] **Step 4: Commit**

```bash
git add seasons/fetch_race.py
git commit -m "feat(fetch): pull TrackStatus and LapCount streams"
```

---

## Task 7: Extend mini-race fixture for integration test coverage

**Files:**
- Create: `precompute/fixtures/mini-race/2026/2026-03-08_Australian_Grand_Prix/2026-03-08_Race/TrackStatus.jsonStream`
- Create: `precompute/fixtures/mini-race/2026/2026-03-08_Australian_Grand_Prix/2026-03-08_Race/LapCount.jsonStream`
- Create: `precompute/fixtures/mini-race/2026/2026-03-15_Chinese_Grand_Prix/2026-03-15_Race/TrackStatus.jsonStream`
- Create: `precompute/fixtures/mini-race/2026/2026-03-15_Chinese_Grand_Prix/2026-03-15_Race/LapCount.jsonStream`
- Create: `precompute/fixtures/mini-race/2026/2026-03-15_Chinese_Grand_Prix/2026-03-14_Sprint/TrackStatus.jsonStream`
- Create: `precompute/fixtures/mini-race/2026/2026-03-15_Chinese_Grand_Prix/2026-03-14_Sprint/LapCount.jsonStream`

These are synthetic — enough to cover the three cases we want to lock in: a race with one SC band, a sprint with one yellow band, and a race with no bands at all.

- [ ] **Step 1: Write Australia TrackStatus (no non-green transitions)**

Create `precompute/fixtures/mini-race/2026/2026-03-08_Australian_Grand_Prix/2026-03-08_Race/TrackStatus.jsonStream`:

```
00:00:01.000{"Status":"1","Message":"AllClear"}
```

(The BOM is not strictly required by the parser because `parse_stream` uses `encoding="utf-8-sig"` — plain UTF-8 also works.)

- [ ] **Step 2: Write Australia LapCount (1→50)**

Create `precompute/fixtures/mini-race/2026/2026-03-08_Australian_Grand_Prix/2026-03-08_Race/LapCount.jsonStream`:

```
00:00:01.000{"CurrentLap":1,"TotalLaps":50}
```

(One event is enough — bands computation is driven by status transitions; without any non-green status, no bands are produced.)

- [ ] **Step 3: Write China Race TrackStatus (SC from lap 10 to lap 14)**

Create `precompute/fixtures/mini-race/2026/2026-03-15_Chinese_Grand_Prix/2026-03-15_Race/TrackStatus.jsonStream`:

```
00:00:01.000{"Status":"1","Message":"AllClear"}
00:15:00.000{"Status":"4","Message":"SCDeployed"}
00:22:30.000{"Status":"1","Message":"AllClear"}
```

- [ ] **Step 4: Write China Race LapCount (90s per lap up to lap 15)**

Create `precompute/fixtures/mini-race/2026/2026-03-15_Chinese_Grand_Prix/2026-03-15_Race/LapCount.jsonStream`:

```
00:00:01.000{"CurrentLap":1,"TotalLaps":56}
00:01:30.000{"CurrentLap":2}
00:03:00.000{"CurrentLap":3}
00:04:30.000{"CurrentLap":4}
00:06:00.000{"CurrentLap":5}
00:07:30.000{"CurrentLap":6}
00:09:00.000{"CurrentLap":7}
00:10:30.000{"CurrentLap":8}
00:12:00.000{"CurrentLap":9}
00:13:30.000{"CurrentLap":10}
00:15:00.000{"CurrentLap":11}
00:16:30.000{"CurrentLap":12}
00:18:00.000{"CurrentLap":13}
00:19:30.000{"CurrentLap":14}
00:21:00.000{"CurrentLap":15}
00:22:30.000{"CurrentLap":16}
```

(At `00:15:00.000` CurrentLap=11 → SC opens on lap 11. At `00:22:30.000` CurrentLap=16 → AllClear on lap 16, so last-lap-under-SC is lap 15. Expected band: `SCDeployed 11..15`.)

- [ ] **Step 5: Write China Sprint TrackStatus (Yellow from lap 1 to lap 2)**

Create `precompute/fixtures/mini-race/2026/2026-03-15_Chinese_Grand_Prix/2026-03-14_Sprint/TrackStatus.jsonStream`:

```
00:00:01.000{"Status":"2","Message":"Yellow"}
00:03:00.000{"Status":"1","Message":"AllClear"}
```

- [ ] **Step 6: Write China Sprint LapCount**

Create `precompute/fixtures/mini-race/2026/2026-03-15_Chinese_Grand_Prix/2026-03-14_Sprint/LapCount.jsonStream`:

```
00:00:01.000{"CurrentLap":1,"TotalLaps":19}
00:01:30.000{"CurrentLap":2}
00:03:00.000{"CurrentLap":3}
00:04:30.000{"CurrentLap":4}
```

(Expected band: `Yellow 1..2` — opened on lap 1, AllClear on lap 3.)

- [ ] **Step 7: Commit**

```bash
git add precompute/fixtures/mini-race/
git commit -m "test(fixtures): add TrackStatus and LapCount streams to mini-race"
```

---

## Task 8: Wire `track_status` into `build_race_manifest`

**Files:**
- Modify: `precompute/src/f1/build.py`
- Modify: `precompute/tests/test_build.py`

- [ ] **Step 1: Write failing integration test — Australia has no bands**

Append to `test_build.py`:

```python
def test_build_race_manifest_produces_empty_status_bands_for_australia(
    mini_race_root: Path,
) -> None:
    manifest = build_race_manifest(
        data_root=mini_race_root,
        race_dir="2026/2026-03-08_Australian_Grand_Prix",
        season=2026,
        round_number=1,
        slug="australia-2026",
    )
    assert manifest.race.race_status_bands == []
    assert manifest.race.sprint_status_bands == []
```

- [ ] **Step 2: Write failing integration test — China Race has one SC band**

Append to `test_build.py`:

```python
def test_build_race_manifest_produces_china_race_sc_band(
    mini_race_root: Path,
) -> None:
    manifest = build_race_manifest(
        data_root=mini_race_root,
        race_dir="2026/2026-03-15_Chinese_Grand_Prix",
        season=2026,
        round_number=2,
        slug="china-2026",
    )
    assert [(b.status, b.start_lap, b.end_lap) for b in manifest.race.race_status_bands] == [
        ("SCDeployed", 11, 15),
    ]
    assert [(b.status, b.start_lap, b.end_lap) for b in manifest.race.sprint_status_bands] == [
        ("Yellow", 1, 2),
    ]
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_build.py -v -k "status_bands or sprint"`
Expected: both new tests fail — current build doesn't populate status bands.

- [ ] **Step 4: Add a parse-only helper to `build.py`**

In `precompute/src/f1/build.py`, near `_reduce_stream`, add:

```python
def _parse_events(session_dir: Path, filename: str) -> list:
    """Parse events without reducing — we need transitions, not final state."""
    path = session_dir / filename
    if not path.exists():
        return []
    return parse_stream(path)
```

Also update the top-level imports in `build.py` if `parse_stream` is not already imported in this file's namespace (it is — line 32 already has `from f1.parse import parse_stream`).

- [ ] **Step 5: Import `track_status` and compute bands per session**

In `build.py`, add to the imports:

```python
from f1.track_status import (
    build_status_bands,
    collect_lap_boundaries,
    collect_status_transitions,
)
```

Inside `build_race_manifest`, after the loop that builds `stints_by_session` (around line 119, after the `for key, sess_dir in sessions:` block that populates `stints_by_session`), add:

```python
# Status bands per session (Race + Sprint only).
race_status_bands: list = []
sprint_status_bands: list = []
for key, sess_dir in sessions:
    if key not in ("R", "S"):
        continue
    stints_for_key = stints_by_session.get(key, [])
    if not stints_for_key:
        continue
    total_laps = max((s.end_lap for s in stints_for_key), default=0)
    if total_laps < 1:
        continue
    ts_events = _parse_events(sess_dir, "TrackStatus.jsonStream")
    lc_events = _parse_events(sess_dir, "LapCount.jsonStream")
    transitions = collect_status_transitions(ts_events)
    if transitions and not lc_events:
        # Rare: status data but no lap reference; log and skip rather than crash.
        print(
            f"warning: TrackStatus present but LapCount missing for {sess_dir.name}",
            file=sys.stderr,
        )
        continue
    bands = build_status_bands(
        transitions,
        collect_lap_boundaries(lc_events),
        total_laps=total_laps,
    )
    if key == "R":
        race_status_bands = bands
    else:
        sprint_status_bands = bands
```

- [ ] **Step 6: Pass the new lists into the `Race(...)` constructor**

Find the `race = Race(...)` construction near the bottom of `build_race_manifest` (around line 243–253). Add two fields to the call:

```python
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
    race_status_bands=race_status_bands,
    sprint_status_bands=sprint_status_bands,
)
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `uv run pytest tests/test_build.py -v`
Expected: all new tests pass, all pre-existing tests still pass.

- [ ] **Step 8: Lint + type check + coverage**

Run: `uv run ruff check . && uv run mypy src && uv run pytest --cov=f1 --cov-report=term-missing`
Expected: no lint / type errors; coverage ≥ 85%.

- [ ] **Step 9: Commit**

```bash
git add precompute/src/f1/build.py precompute/tests/test_build.py
git commit -m "feat(precompute): emit status bands on Race manifest"
```

---

## Task 9: Regenerate Zod schemas

**Files:**
- Modify: `precompute/out/schema.json` (regenerated)
- Modify: `site/src/lib/schemas.ts` (regenerated)

- [ ] **Step 1: Regenerate schemas**

Run from repo root: `make genzod`

Expected output: `precompute/out/schema.json` is rewritten, then `site/src/lib/schemas.ts` is regenerated from it. The diff on `schemas.ts` should include `StatusBand`, `TrackStatusCode`, `race_status_bands`, `sprint_status_bands`.

- [ ] **Step 2: Inspect the generated types**

Run: `git diff site/src/lib/schemas.ts | head -60`

Expected: `StatusBandSchema`, `TrackStatusCodeSchema`, and the two new fields appear. Defaults are `.default([])` or equivalent. If the enum literal order is unexpected, accept it — Pydantic's `Literal` iteration order is preserved.

- [ ] **Step 3: Type-check the site**

Run: `cd site && npx tsc -b --noEmit`
Expected: no errors. (The new fields flow into generated Zod types; call-sites that don't reference them are unaffected.)

- [ ] **Step 4: Commit**

```bash
git add precompute/out/schema.json site/src/lib/schemas.ts
git commit -m "chore(site): regenerate Zod schemas for status bands"
```

---

## Task 10: Add a `StatusBand` shape + label map to `StrategyChart.tsx`

**Files:**
- Modify: `site/src/components/StrategyChart.tsx`

- [ ] **Step 1: Add types and helpers near the top of the file**

In `site/src/components/StrategyChart.tsx`, after the existing `type Compound = ...` line (around line 9), add:

```ts
type TrackStatusCode = "Yellow" | "SCDeployed" | "VSCDeployed" | "Red";

type StatusBand = {
  status: TrackStatusCode;
  start_lap: number;
  end_lap: number;
};

const STATUS_LABEL: Record<TrackStatusCode, string> = {
  Yellow: "Yellow",
  SCDeployed: "Safety Car",
  VSCDeployed: "Virtual Safety Car",
  Red: "Red Flag",
};
```

- [ ] **Step 2: Add `statusBands` to the `Props` type**

Find the `type Props = { ... }` block (around line 36). Change it to:

```ts
type Props = {
  drivers: Driver[];
  sessionKey: "R" | "S";
  totalLaps: number;
  statusBands: StatusBand[];
};
```

- [ ] **Step 3: Destructure `statusBands` in the component signature**

Change the function signature (around line 110) from:

```ts
export function StrategyChart({ drivers, sessionKey, totalLaps }: Props) {
```

to:

```ts
export function StrategyChart({ drivers, sessionKey, totalLaps, statusBands }: Props) {
```

- [ ] **Step 4: Commit (scaffolding, renders not yet altered)**

```bash
git add site/src/components/StrategyChart.tsx
git commit -m "feat(site): accept statusBands prop on StrategyChart"
```

(Note: TypeScript will now require any `<StrategyChart>` call-site to pass `statusBands`. Task 11 fixes the call-site; keep Task 10 and Task 11 close together.)

---

## Task 11: `Strategy.tsx` passes `statusBands` prop

**Files:**
- Modify: `site/src/routes/Strategy.tsx:70`

- [ ] **Step 1: Pass the prop**

Change line 70 of `site/src/routes/Strategy.tsx` from:

```tsx
<StrategyChart drivers={drivers} sessionKey={active} totalLaps={totalLaps} />
```

to:

```tsx
<StrategyChart
  drivers={drivers}
  sessionKey={active}
  totalLaps={totalLaps}
  statusBands={active === "R" ? manifest.race.race_status_bands : manifest.race.sprint_status_bands}
/>
```

- [ ] **Step 2: Type-check the site**

Run: `cd site && npx tsc -b --noEmit`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add site/src/routes/Strategy.tsx
git commit -m "feat(site): wire Strategy route to pass statusBands"
```

---

## Task 12: Render `<defs>` patterns and background bands

**Files:**
- Modify: `site/src/components/StrategyChart.tsx`

- [ ] **Step 1: Add the pattern palette near `compoundColorVar`**

After `compoundTextColor` (around line 60), add:

```ts
// Status overlay palette. Hatch patterns for Yellow / Red avoid a
// colour collision with MEDIUM and SOFT compound bars; SC / VSC use
// solid orange.
const STATUS_FILL: Record<TrackStatusCode, { band: string; strip: string }> = {
  Yellow:       { band: "url(#statusYellowHatchLow)", strip: "url(#statusYellowHatch)" },
  SCDeployed:   { band: "#f97316",                    strip: "#f97316" },
  VSCDeployed:  { band: "#fb923c",                    strip: "#fb923c" },
  Red:          { band: "url(#statusRedHatchLow)",    strip: "url(#statusRedHatch)" },
};

const STATUS_BAND_OPACITY: Record<TrackStatusCode, number> = {
  Yellow:       1,    // pattern fill already low-opacity
  SCDeployed:   0.14,
  VSCDeployed:  0.14,
  Red:          1,    // pattern fill already low-opacity
};

const STATUS_STRIP_OPACITY: Record<TrackStatusCode, number> = {
  Yellow:       1,
  SCDeployed:   0.85,
  VSCDeployed:  0.7,
  Red:          1,
};
```

- [ ] **Step 2: Inside the `<svg>`, add a `<defs>` block**

Immediately after the `<svg width={width} height={height} ...>` opening tag (around line 146), add:

```tsx
<defs>
  <pattern id="statusYellowHatch" patternUnits="userSpaceOnUse" width={6} height={6} patternTransform="rotate(45)">
    <rect width={6} height={6} fill="#eab308" fillOpacity={0.55} />
    <rect width={3} height={6} fill="#ca8a04" fillOpacity={0.75} />
  </pattern>
  <pattern id="statusYellowHatchLow" patternUnits="userSpaceOnUse" width={6} height={6} patternTransform="rotate(45)">
    <rect width={6} height={6} fill="#eab308" fillOpacity={0.14} />
    <rect width={3} height={6} fill="#ca8a04" fillOpacity={0.2} />
  </pattern>
  <pattern id="statusRedHatch" patternUnits="userSpaceOnUse" width={6} height={6} patternTransform="rotate(45)">
    <rect width={6} height={6} fill="#dc2626" fillOpacity={0.55} />
    <rect width={3} height={6} fill="#991b1b" fillOpacity={0.75} />
  </pattern>
  <pattern id="statusRedHatchLow" patternUnits="userSpaceOnUse" width={6} height={6} patternTransform="rotate(45)">
    <rect width={6} height={6} fill="#dc2626" fillOpacity={0.14} />
    <rect width={3} height={6} fill="#991b1b" fillOpacity={0.18} />
  </pattern>
</defs>
```

- [ ] **Step 3: Render background bands before the existing `rows.map`**

Still inside the `<svg>`, find where `rows.map((row, i) => { ... })` begins. Immediately *before* that map, add:

```tsx
{statusBands.map((b, idx) => {
  const x0 = xScale(b.start_lap);
  const x1 = xScale(b.end_lap + 1);
  const y = PAD.top;
  const h = rows.length * ROW_H;
  const fill = STATUS_FILL[b.status];
  return (
    <rect
      key={`band-${idx}`}
      x={x0}
      y={y}
      width={Math.max(x1 - x0, 0)}
      height={h}
      fill={fill.band}
      fillOpacity={STATUS_BAND_OPACITY[b.status]}
      data-testid="status-band"
      data-status={b.status}
    />
  );
})}
```

- [ ] **Step 4: Type-check**

Run: `cd site && npx tsc -b --noEmit`
Expected: no errors.

- [ ] **Step 5: Visual spot-check**

Run: `make dev` and open `http://localhost:5173/race/japan-2026/strategy`. Expected:
- A faint yellow hatch behind lap-1..few laps.
- A faint orange band behind the SC window (look for the cluster of mid-race pit-stops).
- Compound colours still visible through the overlays.

If anything looks wrong, iterate on opacity / fill values before committing.

- [ ] **Step 6: Commit**

```bash
git add site/src/components/StrategyChart.tsx
git commit -m "feat(site): render status band overlay behind stints"
```

---

## Task 13: Render the top strip

**Files:**
- Modify: `site/src/components/StrategyChart.tsx`

- [ ] **Step 1: Add strip rendering immediately after background bands, before stint bars**

Directly after the `statusBands.map(...)` block from Task 12, append:

```tsx
{statusBands.length > 0 && (
  <>
    {/* Green AllClear baseline behind the strip, spanning the full chart. */}
    <rect
      x={leftCol}
      y={4}
      width={Math.max(width - PAD.right - leftCol, 0)}
      height={6}
      fill="#10b981"
      fillOpacity={0.28}
    />
    {statusBands.map((b, idx) => {
      const x0 = xScale(b.start_lap);
      const x1 = xScale(b.end_lap + 1);
      const fill = STATUS_FILL[b.status];
      return (
        <rect
          key={`strip-${idx}`}
          x={x0}
          y={4}
          width={Math.max(x1 - x0, 0)}
          height={6}
          fill={fill.strip}
          fillOpacity={STATUS_STRIP_OPACITY[b.status]}
          data-testid="status-strip-segment"
          data-status={b.status}
        />
      );
    })}
  </>
)}
```

- [ ] **Step 2: Type-check**

Run: `cd site && npx tsc -b --noEmit`
Expected: no errors.

- [ ] **Step 3: Visual spot-check**

Run the dev server again. Expect a thin coloured strip above all driver rows, with green baseline + yellow/orange segments at the same x-ranges as the background bands.

- [ ] **Step 4: Commit**

```bash
git add site/src/components/StrategyChart.tsx
git commit -m "feat(site): add top status strip above Strategy rows"
```

---

## Task 14: Add status-tooltip as a discriminated union on the existing `useTooltip`

**Files:**
- Modify: `site/src/components/StrategyChart.tsx`

- [ ] **Step 1: Widen the `TooltipData` type to a discriminated union**

Find the existing `type TooltipData = { ... }` block (around line 69). Replace it with:

```ts
type StintTooltipData = {
  kind: "stint";
  tla: string;
  stintIdx: number;
  totalStints: number;
  compound: Compound;
  startLap: number;
  endLap: number;
  laps: number;
  isNew: boolean;
  dnfAtLap: number | null;
  isLastStint: boolean;
};

type StatusTooltipData = {
  kind: "status";
  status: TrackStatusCode;
  startLap: number;
  endLap: number;
  laps: number;
};

type TooltipData = StintTooltipData | StatusTooltipData;
```

- [ ] **Step 2: Add `kind: "stint"` to the existing `showTooltip` call**

In `onMouseMove` of the stint `<Bar>` (around lines 176–195), change the `tooltipData: { ... }` object to include `kind: "stint"`:

```ts
tooltipData: {
  kind: "stint",
  tla: row.driver.tla,
  stintIdx: s.stint_idx,
  totalStints: row.stints.length,
  compound: s.compound,
  startLap: s.start_lap,
  endLap: s.end_lap,
  laps: s.laps,
  isNew: s.new,
  dnfAtLap: row.dnfAtLap,
  isLastStint,
},
```

- [ ] **Step 3: Wire `onMouseMove` / `onMouseLeave` on both band rects and strip segments**

Replace the background-band `<rect>` from Task 12 with a version that includes the tooltip handlers:

```tsx
{statusBands.map((b, idx) => {
  const x0 = xScale(b.start_lap);
  const x1 = xScale(b.end_lap + 1);
  const fill = STATUS_FILL[b.status];
  const onMove = (e: React.MouseEvent<SVGRectElement>) => {
    const svg = (e.currentTarget as SVGElement).ownerSVGElement;
    const rect = svg?.getBoundingClientRect();
    showTooltip({
      tooltipLeft: rect ? e.clientX - rect.left : e.clientX,
      tooltipTop:  rect ? e.clientY - rect.top  : e.clientY,
      tooltipData: {
        kind: "status",
        status: b.status,
        startLap: b.start_lap,
        endLap: b.end_lap,
        laps: b.end_lap - b.start_lap + 1,
      },
    });
  };
  return (
    <rect
      key={`band-${idx}`}
      x={x0}
      y={PAD.top}
      width={Math.max(x1 - x0, 0)}
      height={rows.length * ROW_H}
      fill={fill.band}
      fillOpacity={STATUS_BAND_OPACITY[b.status]}
      data-testid="status-band"
      data-status={b.status}
      onMouseMove={onMove}
      onMouseLeave={hideTooltip}
    />
  );
})}
```

Apply the same handlers to the strip segments — replace the corresponding inner `<rect>` from Task 13 with the same `onMove`/`onMouseLeave` attached. (Use the `onMove` defined in the closure above by hoisting the closure to wrap both bands and strip segments, or duplicate it — two small duplications are fine; don't factor it into a helper unless the compiler asks.)

- [ ] **Step 4: Widen the tooltip render block**

Find the `{tooltipOpen && tooltipData && ( ... )}` block near the bottom. Change it to:

```tsx
{tooltipOpen && tooltipData && (
  <TooltipWithBounds top={tooltipTop} left={tooltipLeft} style={TOOLTIP_STYLES}>
    {tooltipData.kind === "stint" ? (
      <>
        <div>
          {tooltipData.tla} · Stint {tooltipData.stintIdx + 1} / {tooltipData.totalStints}
        </div>
        <div>
          {tooltipData.compound} · laps {tooltipData.startLap}–{tooltipData.endLap} ({tooltipData.laps} laps)
        </div>
        <div>{tooltipData.isNew ? "New set" : "Used set"}</div>
        {tooltipData.dnfAtLap != null && tooltipData.isLastStint && (
          <div>Retired at lap {tooltipData.dnfAtLap}</div>
        )}
      </>
    ) : (
      <div>
        {STATUS_LABEL[tooltipData.status]} · lap {tooltipData.startLap}–{tooltipData.endLap} ({tooltipData.laps} laps)
      </div>
    )}
  </TooltipWithBounds>
)}
```

- [ ] **Step 5: Type-check**

Run: `cd site && npx tsc -b --noEmit`
Expected: no errors. Note that `isLastStint` is now only available on the narrowed `stint` branch; the compiler should enforce that.

- [ ] **Step 6: Manual hover smoke test**

Run `make dev` and hover both a stint and a status band / strip segment on the Japan race page. Expect two distinct tooltip layouts.

- [ ] **Step 7: Commit**

```bash
git add site/src/components/StrategyChart.tsx
git commit -m "feat(site): add status-band tooltip via discriminated union"
```

---

## Task 15: Vitest tests for `StrategyChart` overlay

**Files:**
- Create: `site/src/components/StrategyChart.test.tsx`

The site had no component-level vitest before this task; `site/tests/e2e/` is the only existing test location. This adds vitest coverage for the new overlay semantics.

- [ ] **Step 1: Write the test file**

Create `site/src/components/StrategyChart.test.tsx`:

```tsx
import { describe, test, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StrategyChart } from "./StrategyChart";

type RaceStint = Parameters<typeof StrategyChart>[0]["drivers"][number]["race_stints"][number];

const baseStints: RaceStint[] = [
  { stint_idx: 0, compound: "SOFT",   start_lap: 1,  end_lap: 15, laps: 15, new: true  },
  { stint_idx: 1, compound: "MEDIUM", start_lap: 16, end_lap: 30, laps: 15, new: false },
];

const driver = {
  racing_number: "1",
  tla: "VER",
  full_name: "Max Verstappen",
  team_name: "Red Bull Racing",
  team_color: "#1e3a8a",
  grid_position: 1,
  sets: [],
  race_stints: baseStints,
  sprint_stints: [],
  final_position: 1,
  dnf_at_lap: null,
  sprint_final_position: null,
  sprint_dnf_at_lap: null,
};

describe("StrategyChart status overlay", () => {
  test("renders no overlay elements when statusBands is empty", () => {
    render(<StrategyChart drivers={[driver]} sessionKey="R" totalLaps={30} statusBands={[]} />);
    expect(screen.queryByTestId("status-band")).toBeNull();
    expect(screen.queryByTestId("status-strip-segment")).toBeNull();
  });

  test("renders one band and one strip segment per StatusBand", () => {
    render(
      <StrategyChart
        drivers={[driver]}
        sessionKey="R"
        totalLaps={30}
        statusBands={[
          { status: "SCDeployed", start_lap: 10, end_lap: 14 },
          { status: "Yellow",     start_lap: 20, end_lap: 22 },
        ]}
      />,
    );
    expect(screen.getAllByTestId("status-band")).toHaveLength(2);
    expect(screen.getAllByTestId("status-strip-segment")).toHaveLength(2);
    expect(screen.getAllByTestId("status-band")[0].getAttribute("data-status")).toBe("SCDeployed");
    expect(screen.getAllByTestId("status-band")[1].getAttribute("data-status")).toBe("Yellow");
  });
});
```

- [ ] **Step 2: Verify vitest discovers and runs the file**

Run: `cd site && npm run test`
Expected: the new test file runs, all tests pass.

- [ ] **Step 3: Commit**

```bash
git add site/src/components/StrategyChart.test.tsx
git commit -m "test(site): cover StrategyChart status overlay with vitest"
```

---

## Task 16: Playwright E2E — overlay present on japan-2026 Strategy page

**Files:**
- Modify: `site/tests/e2e/strategy.spec.ts`

- [ ] **Step 1: Append a test**

Append to `site/tests/e2e/strategy.spec.ts`:

```ts
test("japan-2026 Strategy page shows status strip segments and a band tooltip", async ({ page }) => {
  await page.goto("/race/japan-2026/strategy");
  const chart = page.getByRole("img", { name: /Race strategy chart/i });
  await expect(chart).toBeVisible();

  const stripSegments = page.locator('[data-testid="status-strip-segment"]');
  await expect(stripSegments.first()).toBeVisible({ timeout: 5_000 });
  expect(await stripSegments.count()).toBeGreaterThanOrEqual(1);

  const first = stripSegments.first();
  await first.hover();
  await expect(
    page.getByText(/^(Yellow|Safety Car|Virtual Safety Car|Red Flag) · lap \d+–\d+ \(\d+ laps\)$/),
  ).toBeVisible();
});
```

- [ ] **Step 2: Run the E2E suite**

Run: `make test-e2e`
Expected: the new test passes along with the existing three.

- [ ] **Step 3: Commit**

```bash
git add site/tests/e2e/strategy.spec.ts
git commit -m "test(e2e): assert status overlay + tooltip on japan-2026"
```

---

## Task 17: Update data-feed-reference.md — TrackStatus and LapCount are now fetched

**Files:**
- Modify: `docs/data-feed-reference.md`

- [ ] **Step 1: Flip the Fetched flags in the summary table**

In the table inside section "## Summary table" (around line 46–50), change these two rows:

```
| `LapCount.jsonStream` | Current / total session laps. | ❌ | medium |
```
→
```
| `LapCount.jsonStream` | Current / total session laps. | ✅ | medium |
```

```
| `TrackStatus.jsonStream` | Current track status code (all-clear, yellow, SC, VSC, red). | ❌ | medium |
```
→
```
| `TrackStatus.jsonStream` | Current track status code (all-clear, yellow, SC, VSC, red). | ✅ | deep |
```

(We graduate `TrackStatus` from `medium` to `deep` because it now powers production features; leave `LapCount` at `medium`.)

- [ ] **Step 2: Flip the cross-reference icons**

In section "## Cross-reference" update:

```
- **Current / total session laps?** → `LapCount.jsonStream` ❌
```
→
```
- **Current / total session laps?** → `LapCount.jsonStream` ✅
```

```
- **Live track status (green/yellow/SC/VSC/red)?** → `TrackStatus.jsonStream` ❌
```
→
```
- **Live track status (green/yellow/SC/VSC/red)?** → `TrackStatus.jsonStream` ✅
```

- [ ] **Step 3: Update per-feed "Feeds these features" notes**

Inside the `### TrackStatus.jsonStream` section, change:

```
**Feeds these features** (current): none.
```
→
```
**Feeds these features** (current): Race Strategy chart status-band overlay (yellow / SC / VSC / red windows). See `site/src/components/StrategyChart.tsx`.
```

Inside the `### LapCount.jsonStream` section, change its analogous line to:

```
**Feeds these features** (current): Race Strategy chart status-band lap mapping (anchors TrackStatus transitions to lap numbers). See `precompute/src/f1/track_status.py`.
```

- [ ] **Step 4: Commit**

```bash
git add docs/data-feed-reference.md
git commit -m "docs(feed-reference): mark TrackStatus and LapCount as fetched"
```

---

## Task 18: Full regression pass + PR

**Files:** none (verification + PR)

- [ ] **Step 1: Run everything**

Run: `make test`
Expected: python, site, and e2e suites all pass. Coverage gate ≥ 85%.

- [ ] **Step 2: Full production build**

Run: `make build`
Expected: `site/dist/` rebuilt; no errors. Inspect `site/public/data/japan-2026.json` and confirm `race.race_status_bands` is populated.

- [ ] **Step 3: Push and open PR**

```bash
git push -u origin feat/track-status-overlay
gh pr create --title "feat: track status overlay on race strategy chart" --body "$(cat <<'EOF'
## Summary

- Adds a TrackStatus + LapCount pull to CI and a precompute pipeline that emits `race_status_bands` / `sprint_status_bands` on each manifest.
- Renders low-opacity full-height bands + a bright top strip on `StrategyChart`, with a hover tooltip sharing the chart's existing `useTooltip` via a discriminated union.
- Spec: `docs/superpowers/specs/2026-04-18-track-status-overlay-design.md`
- Plan: `docs/superpowers/plans/2026-04-18-track-status-overlay.md`

## Test plan

- [x] `make test` green (Python 85% coverage, vitest, Playwright)
- [x] `make build` produces `site/dist/` with populated `race_status_bands` in `japan-2026.json`
- [x] Manual QA — Japan 2026 Strategy page shows yellow hatch + SC band + tooltips
- [x] Australia 2026 and China 2026 Strategy pages render unchanged when the archive has no non-green transitions

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Expected: PR opens, URL returned. Do not merge here — await review.

---

## Self-Review Notes

- **Spec coverage:** every section of the spec maps to at least one task —
  § 3 Scope → Tasks 1–17; § 4 Visual → Tasks 12–14; § 5 Architecture → Tasks 1,
  2-5, 6, 8, 9; § 6 Data model → Task 1; § 7 Precompute → Tasks 2–5, 8; § 8 Site
  → Tasks 10–14; § 9 Edge cases → covered in Tasks 5 (unit) and 7 (fixture); § 10
  Testing → Tasks 1, 2–5, 8, 15, 16; § 11 Risks → validated through tests +
  fixtures; § 12 Rollout → single-branch, per Task 0.
- **Placeholder scan:** no TBDs; every code block is concrete; no "similar to".
- **Type consistency:** `TrackStatusCode`, `StatusBand`, and the label / fill
  maps all use identical enum-literal strings (`Yellow`, `SCDeployed`,
  `VSCDeployed`, `Red`) across Python and TypeScript.
- **Naming:** `race_status_bands` / `sprint_status_bands` consistent on model,
  build code, Zod output, and site call-sites.
