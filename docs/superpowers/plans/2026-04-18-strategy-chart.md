# Race Strategy Chart Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a `/race/<slug>/strategy` page that renders per-driver tyre stints across the race (and sprint on sprint weekends), sorted by finishing position, with DNF drivers flagged via a `RET L<lap>` trailer badge.

**Architecture:** Extend the Python precompute pipeline to emit `race_stints`, `sprint_stints`, `final_position`, and `dnf_at_lap` on every `DriverInventory`. Add one new source file (`TimingData.jsonStream`) to the fetch list for the canonical `Retired` flag and finishing `Line`. On the site, introduce a pure `<StrategyChart>` SVG component built on `@visx`, a thin route component `Strategy.tsx`, a `SessionTabs` widget for sprint weekends, and a third `AnalyticsTile` on the race page.

**Tech Stack:** Python 3.13 (Pydantic, `ruff`, `mypy` strict, `pytest` + 85% coverage), React 19 + Vite + TypeScript strict, Tailwind 4, `@visx`, `vitest`, `@testing-library/react`, Playwright.

**Project convention:** Every `git commit` step in this plan requires explicit user approval (per project's global CLAUDE.md "Always ask before creating commits"). Draft the commit message, show the `git status` / `git diff --stat` summary, and wait for sign-off.

**Spec reference:** `docs/superpowers/specs/2026-04-18-strategy-chart-design.md`

---

## Phase 1 — Precompute: race stints in the manifest

Goal: every `DriverInventory` gains `race_stints: list[RaceStint]` and `sprint_stints: list[RaceStint]`, derived from data already in the pipeline (`TyreStintSeries.jsonStream`). The site keeps ignoring the new fields — this phase is invisible to the user.

### Task 1.1: Add `RaceStint` Pydantic model and new fields on `DriverInventory`

**Files:**
- Modify: `precompute/src/f1/models.py`
- Test: `precompute/tests/test_models.py`

- [ ] **Step 1: Write failing tests**

Append to `precompute/tests/test_models.py`:

```python
def test_race_stint_accepts_valid_payload() -> None:
    from f1.models import RaceStint

    s = RaceStint(
        stint_idx=0,
        compound="MEDIUM",
        start_lap=1,
        end_lap=18,
        laps=18,
        new=True,
    )
    assert s.compound == "MEDIUM"
    assert s.end_lap == 18


def test_race_stint_rejects_unknown_compound() -> None:
    from f1.models import RaceStint

    with pytest.raises(ValidationError):
        RaceStint(
            stint_idx=0,
            compound="UNKNOWN",  # type: ignore[arg-type]
            start_lap=1,
            end_lap=2,
            laps=2,
            new=True,
        )


def test_race_stint_rejects_start_lap_below_one() -> None:
    from f1.models import RaceStint

    with pytest.raises(ValidationError):
        RaceStint(
            stint_idx=0,
            compound="SOFT",
            start_lap=0,
            end_lap=3,
            laps=3,
            new=True,
        )


def test_driver_inventory_has_empty_stint_lists_by_default() -> None:
    inv = DriverInventory(
        racing_number="1",
        tla="VER",
        full_name="Max Verstappen",
        team_name="Red Bull Racing",
        team_color="#4781D7",
        grid_position=1,
        sets=[],
    )
    assert inv.race_stints == []
    assert inv.sprint_stints == []
```

- [ ] **Step 2: Run tests — they should fail on import**

```bash
cd precompute && uv run pytest tests/test_models.py -v
```

Expected: `ImportError: cannot import name 'RaceStint'` and/or `AttributeError: no field 'race_stints'`.

- [ ] **Step 3: Implement the model**

In `precompute/src/f1/models.py`, add `RaceStint` after `TyreSet`:

```python
class RaceStint(_StrictModel):
    """One stint inside a race or sprint session, in lap-index space."""

    stint_idx: int = Field(ge=0, description="0-based stint index within the session")
    compound: Compound
    start_lap: int = Field(ge=1, description="Lap the driver exited the pit on (1 for first stint)")
    end_lap: int = Field(ge=1, description="Last lap on this set (inclusive)")
    laps: int = Field(ge=1, description="end_lap - start_lap + 1")
    new: bool = Field(description="True if the set was mounted new for this stint")
```

Extend `DriverInventory` with the two new lists (before the `@property`):

```python
    race_stints: list[RaceStint] = Field(default_factory=list)
    sprint_stints: list[RaceStint] = Field(default_factory=list)
```

- [ ] **Step 4: Run tests — should pass**

```bash
cd precompute && uv run pytest tests/test_models.py -v
```

Expected: all new tests pass. Existing ones still pass.

- [ ] **Step 5: Run the full Python suite to confirm no regression**

```bash
cd precompute && uv run pytest
```

Expected: all green. Coverage stays ≥85%.

---

### Task 1.2: Implement `build_race_stints` in `inventory.py`

**Files:**
- Modify: `precompute/src/f1/inventory.py`
- Test: `precompute/tests/test_race_stints.py` (new file)

- [ ] **Step 1: Write failing tests**

Create `precompute/tests/test_race_stints.py`:

```python
"""Tests for race/sprint stint derivation from SessionStint records."""
from __future__ import annotations

from f1.inventory import SessionStint, build_race_stints
from f1.models import RaceStint


def test_build_race_stints_single_stop_strategy() -> None:
    # Two stints: MEDIUM for 18 laps, then HARD for 39 laps.
    session = [
        SessionStint("R", "1", 0, "MEDIUM", True, 0, 18),
        SessionStint("R", "1", 1, "HARD",   True, 0, 39),
    ]
    stints = build_race_stints(driver_number="1", stints_for_session=session)
    assert stints == [
        RaceStint(stint_idx=0, compound="MEDIUM", start_lap=1,  end_lap=18, laps=18, new=True),
        RaceStint(stint_idx=1, compound="HARD",   start_lap=19, end_lap=57, laps=39, new=True),
    ]


def test_build_race_stints_two_stop_strategy_preserves_continuity() -> None:
    session = [
        SessionStint("R", "1", 0, "SOFT",   True,  0, 14),
        SessionStint("R", "1", 1, "MEDIUM", True,  0, 18),
        SessionStint("R", "1", 2, "HARD",   True,  0, 25),
    ]
    stints = build_race_stints(driver_number="1", stints_for_session=session)
    assert [s.start_lap for s in stints] == [1, 15, 33]
    assert [s.end_lap   for s in stints] == [14, 32, 57]
    assert [s.laps      for s in stints] == [14, 18, 25]


def test_build_race_stints_filters_other_drivers() -> None:
    session = [
        SessionStint("R", "1",  0, "MEDIUM", True, 0, 18),
        SessionStint("R", "16", 0, "HARD",   True, 0, 57),
    ]
    stints = build_race_stints(driver_number="16", stints_for_session=session)
    assert len(stints) == 1
    assert stints[0].compound == "HARD"
    assert stints[0].laps == 57


def test_build_race_stints_skips_zero_lap_stints() -> None:
    # A stint recorded with TotalLaps=0 means the driver never completed a lap
    # on it — treat as not-yet-run (or dropout mid-pit). Filter out.
    session = [
        SessionStint("R", "1", 0, "MEDIUM", True, 0, 18),
        SessionStint("R", "1", 1, "HARD",   True, 0, 0),
    ]
    stints = build_race_stints(driver_number="1", stints_for_session=session)
    assert len(stints) == 1
    assert stints[0].compound == "MEDIUM"


def test_build_race_stints_empty_input_returns_empty_list() -> None:
    assert build_race_stints(driver_number="1", stints_for_session=[]) == []


def test_build_race_stints_sorted_by_stint_idx_even_when_input_is_not() -> None:
    session = [
        SessionStint("R", "1", 1, "HARD",   True, 0, 39),
        SessionStint("R", "1", 0, "MEDIUM", True, 0, 18),
    ]
    stints = build_race_stints(driver_number="1", stints_for_session=session)
    assert [s.stint_idx for s in stints] == [0, 1]
    assert stints[0].start_lap == 1
    assert stints[1].start_lap == 19
```

- [ ] **Step 2: Run tests — should fail**

```bash
cd precompute && uv run pytest tests/test_race_stints.py -v
```

Expected: `ImportError: cannot import name 'build_race_stints'`.

- [ ] **Step 3: Implement `build_race_stints`**

Append to `precompute/src/f1/inventory.py`:

```python
def build_race_stints(
    *,
    driver_number: str,
    stints_for_session: list[SessionStint],
) -> list["RaceStint"]:
    """Turn this driver's ``SessionStint`` records into lap-indexed ``RaceStint``s.

    ``stints_for_session`` is all stints for this driver in the session.
    Zero-lap stints are skipped (they represent in-progress states the feed
    sometimes emits at pit exit/entry). Output is sorted by ``stint_idx`` and
    stints are laid end-to-end: stint N starts at the lap after stint N-1 ends.
    """
    from f1.models import RaceStint  # local import to keep inventory.py model-light

    mine = [s for s in stints_for_session if s.driver_number == driver_number and s.total_laps > 0]
    mine.sort(key=lambda s: s.stint_idx)

    result: list[RaceStint] = []
    next_start = 1
    for s in mine:
        end = next_start + s.total_laps - 1
        result.append(
            RaceStint(
                stint_idx=s.stint_idx,
                compound=s.compound,
                start_lap=next_start,
                end_lap=end,
                laps=s.total_laps,
                new=s.new_when_out,
            )
        )
        next_start = end + 1
    return result
```

- [ ] **Step 4: Run tests — should pass**

```bash
cd precompute && uv run pytest tests/test_race_stints.py -v
```

Expected: 6 passes.

- [ ] **Step 5: Run the full suite + type check**

```bash
cd precompute && uv run pytest && uv run ruff check . && uv run mypy src
```

Expected: all green.

---

### Task 1.3: Populate `race_stints` / `sprint_stints` in `build.py`

**Files:**
- Modify: `precompute/src/f1/build.py`
- Test: `precompute/tests/test_build.py`

- [ ] **Step 1: Write a failing integration test**

Append to `precompute/tests/test_build.py`:

```python
def test_build_race_manifest_populates_race_stints(mini_race_root: Path) -> None:
    manifest = build_race_manifest(
        data_root=mini_race_root,
        race_dir="2026/2026-03-08_Australian_Grand_Prix",
        season=2026,
        round_number=1,
        slug="australia-2026",
    )
    ver = next(d for d in manifest.race.drivers if d.tla == "VER")
    assert len(ver.race_stints) > 0
    assert ver.sprint_stints == []  # Melbourne is not a sprint weekend
    # Race stints should be continuous.
    for prev, curr in zip(ver.race_stints, ver.race_stints[1:]):
        assert curr.start_lap == prev.end_lap + 1


def test_build_race_manifest_populates_sprint_stints_on_sprint_weekend(
    mini_race_root: Path,
) -> None:
    manifest = build_race_manifest(
        data_root=mini_race_root,
        race_dir="2026/2026-03-15_Chinese_Grand_Prix",
        season=2026,
        round_number=2,
        slug="china-2026",
    )
    ver = next(d for d in manifest.race.drivers if d.tla == "VER")
    assert len(ver.sprint_stints) > 0
    assert len(ver.race_stints) > 0
```

- [ ] **Step 2: Run — should fail**

```bash
cd precompute && uv run pytest tests/test_build.py -v -k "race_stints or sprint_stints"
```

Expected: assertions fail because `race_stints` / `sprint_stints` are still `[]`.

- [ ] **Step 3: Wire `build_race_stints` into `build_race_manifest`**

In `precompute/src/f1/build.py`, update the imports:

```python
from f1.inventory import (
    SessionStint,
    build_inventory,
    build_race_stints,
    extract_session_stints,
)
```

Inside the driver loop in `build_race_manifest` (where `DriverInventory(...)` is constructed), replace the existing construction with:

```python
    for racing_number, meta in driver_meta.items():
        sets: list[TyreSet] = build_inventory(
            driver_number=racing_number,
            driver_tla=meta.tla,
            stints_by_session=stints_by_session,
        )
        race_stints = build_race_stints(
            driver_number=racing_number,
            stints_for_session=stints_by_session.get("R", []),
        )
        sprint_stints = build_race_stints(
            driver_number=racing_number,
            stints_for_session=stints_by_session.get("S", []),
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
                race_stints=race_stints,
                sprint_stints=sprint_stints,
            )
        )
```

- [ ] **Step 4: Run — should pass**

```bash
cd precompute && uv run pytest tests/test_build.py -v -k "race_stints or sprint_stints"
```

Expected: both new tests pass.

- [ ] **Step 5: Full suite + types**

```bash
cd precompute && uv run pytest && uv run mypy src
```

Expected: green. Coverage unchanged or higher.

---

### Task 1.4: Regenerate Zod + extend hand-written `FullManifestSchema`

**Files:**
- Regenerate: `site/src/lib/schemas.ts` (auto-generated)
- Modify: `site/src/lib/data.ts`

- [ ] **Step 1: Regenerate Zod from Pydantic**

Run from repo root:

```bash
make genzod
```

Expected: `site/src/lib/schemas.ts` updated. The `race` field stays `z.any()` (that's deliberate — the top-level schema is auto-gen, deep shape lives in `data.ts`).

- [ ] **Step 2: Extend the hand-written `FullManifestSchema`**

In `site/src/lib/data.ts`, add a Zod `RaceStintSchema` above `DriverInventorySchema`:

```ts
const RaceStintSchema = z.object({
  stint_idx: z.number().int().min(0),
  compound: z.enum(["SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"]),
  start_lap: z.number().int().min(1),
  end_lap: z.number().int().min(1),
  laps: z.number().int().min(1),
  new: z.boolean(),
});
```

Then add the two new fields to `DriverInventorySchema`:

```ts
const DriverInventorySchema = z.object({
  racing_number: z.string().min(1),
  tla: z.string().min(3).max(3),
  full_name: z.string(),
  team_name: z.string(),
  team_color: z.string().regex(/^#[0-9A-Fa-f]{6}$/),
  grid_position: z.union([z.number().int().min(1).max(22), z.null()]).default(null),
  sets: z.array(TyreSetSchema),
  race_stints:   z.array(RaceStintSchema).default([]),
  sprint_stints: z.array(RaceStintSchema).default([]),
});
```

- [ ] **Step 3: Rebuild the featured race manifests**

```bash
cd precompute && uv run python -m f1.build
```

Expected: three JSON files in `precompute/out/` now contain `race_stints` / `sprint_stints` arrays for every driver.

- [ ] **Step 4: Verify site still loads without validation errors**

```bash
make dev
# In a second terminal, open http://localhost:5173 and click through
# / → /season/2026 → /race/australia-2026 → /race/australia-2026/tyres
# and confirm the console is clean.
```

Expected: no Zod parse error banner. Stop dev server.

- [ ] **Step 5: Site unit tests still pass**

```bash
cd site && npm run test
```

Expected: all green (no test touches the new fields yet).

---

### Task 1.5: Commit phase 1

- [ ] **Step 1: Draft commit**

```bash
git add precompute/src/f1/models.py \
        precompute/src/f1/inventory.py \
        precompute/src/f1/build.py \
        precompute/tests/test_models.py \
        precompute/tests/test_race_stints.py \
        precompute/tests/test_build.py \
        site/src/lib/schemas.ts \
        site/src/lib/data.ts
git status
git diff --cached --stat
```

- [ ] **Step 2: Request user approval for commit**

Show the stat output to the user. Wait for approval. Then:

```bash
git commit -m "$(cat <<'EOF'
feat(precompute): add race_stints and sprint_stints to DriverInventory

Derives lap-indexed stint records for the Race session (and the Sprint
on sprint weekends) from the TyreStintSeries stream we already ingest.
Site does not yet render them — validator schemas are updated in lockstep.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Phase 2 — Precompute: TimingData for finishing position & DNF

Goal: add `final_position: int | None` and `dnf_at_lap: int | None` to `DriverInventory`, sourced from `TimingData.jsonStream`. Add that file to the CI fetch list and to the mini-race fixture.

### Task 2.1: Add `TimingData.jsonStream` to the fetch list

**Files:**
- Modify: `seasons/fetch_race.py`

- [ ] **Step 1: Edit `MANIFEST_FILES`**

In `seasons/fetch_race.py`, change:

```python
MANIFEST_FILES: list[str] = [
    "SessionInfo.json",
    "DriverList.jsonStream",
    "TyreStintSeries.jsonStream",
    "TimingAppData.jsonStream",
    "TimingData.jsonStream",
]
```

Update the comment on the line above to drop `TimingData` from the "Everything else … is ignored" clause — the updated comment:

```python
# The files precompute.build reads. Everything else (CarData, Position,
# Heartbeat, etc.) is ignored to keep CI fetches under a few MB.
```

(already accurate since `TimingData` is no longer in the "everything else" set — just verify the comment still makes sense.)

- [ ] **Step 2: Fetch the new file for all featured races**

```bash
cd seasons && uv run python fetch_race.py
```

Expected: three new `TimingData.jsonStream` files appear under `seasons/2026/<race>/<race_session>/`, one per featured race. Each should be 1–5 MB.

- [ ] **Step 3: Sanity-check the fetched data**

```bash
ls -lh seasons/2026/2026-03-08_Australian_Grand_Prix/2026-03-08_Race/TimingData.jsonStream
```

Expected: non-empty file. (Don't commit — `seasons/20xx/` is gitignored.)

---

### Task 2.2: Add a `TimingData` fixture to `mini-race`

**Files:**
- Create: `precompute/fixtures/mini-race/2026/2026-03-08_Australian_Grand_Prix/2026-03-08_Race/TimingData.jsonStream`
- Create: `precompute/fixtures/mini-race/2026/2026-03-15_Chinese_Grand_Prix/2026-03-15_Race/TimingData.jsonStream`
- Create: `precompute/fixtures/mini-race/2026/2026-03-15_Chinese_Grand_Prix/2026-03-14_Sprint/TimingData.jsonStream` (if the Sprint session dir exists — verify with `ls precompute/fixtures/mini-race/2026/2026-03-15_Chinese_Grand_Prix/`)

The Australian fixture has two drivers — VER finishes P1, LEC DNFs at lap 12. Fixture content:

```
00:00:00.000{"Lines":{"1":{"Line":2,"Retired":false},"16":{"Line":1,"Retired":false}}}
00:30:00.000{"Lines":{"1":{"Line":1,"Retired":false}}}
02:00:00.000{"Lines":{"16":{"Retired":true}}}
02:30:00.000{"Lines":{"1":{"Line":1,"Retired":false}}}
```

- [ ] **Step 1: Write the Australian fixture**

Use the `Write` tool to create the file with exactly the four lines above (no leading BOM — `parse_stream` tolerates its absence).

- [ ] **Step 2: Write the Chinese race fixture**

The China race-session fixture should put VER P1 / LEC P2, both retired=false:

```
00:00:00.000{"Lines":{"1":{"Line":1,"Retired":false},"16":{"Line":2,"Retired":false}}}
02:00:00.000{"Lines":{"1":{"Line":1,"Retired":false},"16":{"Line":2,"Retired":false}}}
```

- [ ] **Step 3: Write the Chinese Sprint fixture (if that dir exists)**

Put VER P1, LEC P2 in the sprint too:

```
00:00:00.000{"Lines":{"1":{"Line":1,"Retired":false},"16":{"Line":2,"Retired":false}}}
```

- [ ] **Step 4: Quick verification**

```bash
ls precompute/fixtures/mini-race/2026/*/2026-03-*_Race/TimingData.jsonStream
```

Expected: both race-session files exist and are non-empty.

---

### Task 2.3: Implement `extract_final_positions_and_retirements`

**Files:**
- Modify: `precompute/src/f1/driver_meta.py`
- Test: `precompute/tests/test_driver_meta.py`

- [ ] **Step 1: Write failing tests**

Append to `precompute/tests/test_driver_meta.py`:

```python
def test_extract_final_positions_and_retirements_reads_line_and_retired() -> None:
    from f1.driver_meta import extract_final_positions_and_retirements

    state: dict[str, object] = {
        "Lines": {
            "1":  {"Line": 1, "Retired": False},
            "16": {"Line": 5, "Retired": True},
            "44": {"Line": 3, "Retired": False},
        }
    }
    result = extract_final_positions_and_retirements(state)
    assert result["1"]  == (1, False)
    assert result["16"] == (5, True)
    assert result["44"] == (3, False)


def test_extract_final_positions_and_retirements_handles_missing_fields() -> None:
    from f1.driver_meta import extract_final_positions_and_retirements

    state: dict[str, object] = {
        "Lines": {
            "1":  {"Retired": False},                  # no Line
            "16": {"Line": 5},                         # no Retired → default False
            "44": {"Line": "2", "Retired": "true"},    # string forms (feed can send either)
        }
    }
    result = extract_final_positions_and_retirements(state)
    assert result["1"]  == (None, False)
    assert result["16"] == (5, False)
    assert result["44"] == (2, True)


def test_extract_final_positions_and_retirements_empty_state_returns_empty() -> None:
    from f1.driver_meta import extract_final_positions_and_retirements

    assert extract_final_positions_and_retirements({}) == {}
    assert extract_final_positions_and_retirements({"Lines": {}}) == {}
```

- [ ] **Step 2: Run — should fail**

```bash
cd precompute && uv run pytest tests/test_driver_meta.py -v
```

Expected: `ImportError: cannot import name 'extract_final_positions_and_retirements'`.

- [ ] **Step 3: Implement**

Append to `precompute/src/f1/driver_meta.py`:

```python
def _to_bool_loose(value: object) -> bool:
    """The feed encodes booleans as either Python bool or the strings 'true'/'false'."""
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


def _to_int_optional(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def extract_final_positions_and_retirements(
    timing_data_state: dict[str, object],
) -> dict[str, tuple[int | None, bool]]:
    """Read final ``Line`` position and ``Retired`` flag per driver.

    ``Line`` is the driver's last observed position; ``Retired`` is True
    iff their last observed ``Retired`` value was truthy. Both fields
    may be absent from the feed for a given driver; the tuple slot stays
    ``None``/``False`` in that case.
    """
    lines = timing_data_state.get("Lines")
    if not isinstance(lines, dict):
        return {}
    result: dict[str, tuple[int | None, bool]] = {}
    for racing_number, raw in lines.items():
        if not isinstance(raw, dict):
            continue
        final_line = _to_int_optional(raw.get("Line"))
        retired = _to_bool_loose(raw.get("Retired", False))
        result[str(racing_number)] = (final_line, retired)
    return result
```

- [ ] **Step 4: Run — should pass**

```bash
cd precompute && uv run pytest tests/test_driver_meta.py -v
```

Expected: 6 tests pass (3 old, 3 new).

- [ ] **Step 5: Ruff + mypy**

```bash
cd precompute && uv run ruff check . && uv run mypy src
```

Expected: green.

---

### Task 2.4: Add `final_position` / `dnf_at_lap` fields to `DriverInventory`

**Files:**
- Modify: `precompute/src/f1/models.py`
- Test: `precompute/tests/test_models.py`

- [ ] **Step 1: Write failing tests**

Append to `precompute/tests/test_models.py`:

```python
def test_driver_inventory_defaults_for_final_position_and_dnf() -> None:
    inv = DriverInventory(
        racing_number="1",
        tla="VER",
        full_name="Max Verstappen",
        team_name="Red Bull Racing",
        team_color="#4781D7",
        grid_position=1,
        sets=[],
    )
    assert inv.final_position is None
    assert inv.dnf_at_lap is None


def test_driver_inventory_accepts_final_position() -> None:
    inv = DriverInventory(
        racing_number="1",
        tla="VER",
        full_name="Max Verstappen",
        team_name="Red Bull Racing",
        team_color="#4781D7",
        grid_position=1,
        sets=[],
        final_position=3,
    )
    assert inv.final_position == 3


def test_driver_inventory_rejects_final_position_out_of_range() -> None:
    with pytest.raises(ValidationError):
        DriverInventory(
            racing_number="1",
            tla="VER",
            full_name="Max Verstappen",
            team_name="Red Bull Racing",
            team_color="#4781D7",
            grid_position=1,
            sets=[],
            final_position=0,
        )
```

- [ ] **Step 2: Run — should fail**

```bash
cd precompute && uv run pytest tests/test_models.py -v -k "final_position or dnf"
```

Expected: `AttributeError` / `ValidationError: extra_forbidden` when constructing with `final_position`.

- [ ] **Step 3: Add fields to the model**

In `precompute/src/f1/models.py`, extend `DriverInventory` after `sprint_stints`:

```python
    final_position: int | None = Field(
        default=None,
        ge=1,
        le=22,
        description="Finishing Line in the Race session; None if the driver retired or the race has not run",
    )
    dnf_at_lap: int | None = Field(
        default=None,
        ge=1,
        description="Lap the final race stint ended on, when the driver retired",
    )
```

- [ ] **Step 4: Run — should pass**

```bash
cd precompute && uv run pytest tests/test_models.py -v
```

Expected: all green.

---

### Task 2.5: Populate `final_position` / `dnf_at_lap` in `build.py`

**Files:**
- Modify: `precompute/src/f1/build.py`
- Test: `precompute/tests/test_build.py`

- [ ] **Step 1: Write failing integration tests**

Append to `precompute/tests/test_build.py`:

```python
def test_build_race_manifest_marks_finishers(mini_race_root: Path) -> None:
    manifest = build_race_manifest(
        data_root=mini_race_root,
        race_dir="2026/2026-03-08_Australian_Grand_Prix",
        season=2026,
        round_number=1,
        slug="australia-2026",
    )
    ver = next(d for d in manifest.race.drivers if d.tla == "VER")
    assert ver.final_position == 1
    assert ver.dnf_at_lap is None


def test_build_race_manifest_marks_dnf_at_last_stint_end(mini_race_root: Path) -> None:
    manifest = build_race_manifest(
        data_root=mini_race_root,
        race_dir="2026/2026-03-08_Australian_Grand_Prix",
        season=2026,
        round_number=1,
        slug="australia-2026",
    )
    lec = next(d for d in manifest.race.drivers if d.tla == "LEC")
    assert lec.final_position is None
    assert lec.dnf_at_lap is not None
    assert lec.dnf_at_lap == lec.race_stints[-1].end_lap


def test_build_race_manifest_leaves_position_fields_none_when_no_race_stints(
    mini_race_root: Path,
) -> None:
    # Synthesize by pointing at a race whose fixture has race stints but
    # filter is easy: use china-2026 and ensure if a driver has no race
    # stint, neither field is set. (With our fixture both drivers have
    # stints; this test is a guard for future fixtures.)
    manifest = build_race_manifest(
        data_root=mini_race_root,
        race_dir="2026/2026-03-15_Chinese_Grand_Prix",
        season=2026,
        round_number=2,
        slug="china-2026",
    )
    for d in manifest.race.drivers:
        if not d.race_stints:
            assert d.final_position is None
            assert d.dnf_at_lap is None
```

**Fixture precondition** (check now): the Australian-GP `TyreStintSeries.jsonStream` fixture should have LEC retiring mid-race. Inspect:

```bash
cat precompute/fixtures/mini-race/2026/2026-03-08_Australian_Grand_Prix/2026-03-08_Race/TyreStintSeries.jsonStream
```

If LEC only has a short final stint (e.g. TotalLaps=12) and the file ends with that value, the test will pass. If the current fixture has LEC finishing, either (a) extend the fixture so LEC's final stint is short and the `TimingData` fixture from Task 2.2 flags Retired, or (b) simplify the test to only check VER (the finisher) — but that weakens coverage. **Preferred:** adjust the fixture so the DNF flow is covered. If the test fails at step 2 because LEC's stint list is longer than 12 or `dnf_at_lap` is None, edit both stream fixtures so that LEC's last race stint has `TotalLaps=12` and `TimingData` ends with `{"16":{"Retired":true}}`.

- [ ] **Step 2: Run — should fail**

```bash
cd precompute && uv run pytest tests/test_build.py -v -k "finishers or dnf or position_fields_none"
```

Expected: assertion failures because `final_position` / `dnf_at_lap` are still `None`.

- [ ] **Step 3: Wire `TimingData` into `build_race_manifest`**

In `precompute/src/f1/build.py`:

1. Update imports:

```python
from f1.driver_meta import (
    DriverMeta,
    build_driver_meta,
    extract_final_positions_and_retirements,
    extract_grid_positions,
)
```

2. After the block that reads grid positions from the Race session, add a parallel extraction of `TimingData`:

```python
    # Final race classification from TimingData: last Line value + Retired flag.
    final_pos_and_retired: dict[str, tuple[int | None, bool]] = {}
    for key, sess_dir in sessions:
        if key == "R":
            td = _reduce_stream(sess_dir, "TimingData.jsonStream")
            final_pos_and_retired = extract_final_positions_and_retirements(td)
            break
```

3. In the driver-construction loop, compute the two new fields before building `DriverInventory`:

```python
        final_line, retired = final_pos_and_retired.get(racing_number, (None, False))
        if not race_stints:
            final_position = None
            dnf_at_lap = None
        elif retired:
            final_position = None
            dnf_at_lap = race_stints[-1].end_lap
        else:
            final_position = final_line
            dnf_at_lap = None
```

4. Pass them into `DriverInventory(...)`:

```python
        drivers.append(
            DriverInventory(
                racing_number=meta.racing_number,
                tla=meta.tla,
                full_name=meta.full_name,
                team_name=meta.team_name,
                team_color=meta.team_color,
                grid_position=grid_positions.get(racing_number),
                sets=sets,
                race_stints=race_stints,
                sprint_stints=sprint_stints,
                final_position=final_position,
                dnf_at_lap=dnf_at_lap,
            )
        )
```

- [ ] **Step 4: Run — should pass**

```bash
cd precompute && uv run pytest tests/test_build.py -v
```

Expected: all green.

- [ ] **Step 5: Full suite + types**

```bash
cd precompute && uv run pytest && uv run ruff check . && uv run mypy src
```

Expected: green. Coverage still ≥85%.

---

### Task 2.6: Regenerate Zod + extend `FullManifestSchema`

**Files:**
- Regenerate: `site/src/lib/schemas.ts`
- Modify: `site/src/lib/data.ts`

- [ ] **Step 1: Regenerate**

```bash
make genzod
```

Expected: `schemas.ts` updated.

- [ ] **Step 2: Extend `DriverInventorySchema` in `data.ts`**

Add to the Zod object (after `sprint_stints`):

```ts
  final_position: z.union([z.number().int().min(1).max(22), z.null()]).default(null),
  dnf_at_lap:     z.union([z.number().int().min(1), z.null()]).default(null),
```

- [ ] **Step 3: Rebuild featured manifests**

```bash
cd precompute && uv run python -m f1.build
```

Expected: JSON artifacts in `precompute/out/` now contain `final_position` / `dnf_at_lap` on each driver.

- [ ] **Step 4: Site unit tests still pass**

```bash
cd site && npm run test
```

Expected: green.

- [ ] **Step 5: Manual visual smoke**

```bash
make dev
```

Click through Home → Race → Tyres. Confirm no schema errors. Stop dev server.

---

### Task 2.7: Commit phase 2

- [ ] **Step 1: Draft commit**

```bash
git add seasons/fetch_race.py \
        precompute/src/f1/models.py \
        precompute/src/f1/driver_meta.py \
        precompute/src/f1/build.py \
        precompute/tests/test_models.py \
        precompute/tests/test_driver_meta.py \
        precompute/tests/test_build.py \
        precompute/fixtures/mini-race/2026/2026-03-08_Australian_Grand_Prix/2026-03-08_Race/TimingData.jsonStream \
        precompute/fixtures/mini-race/2026/2026-03-15_Chinese_Grand_Prix/2026-03-15_Race/TimingData.jsonStream \
        site/src/lib/schemas.ts \
        site/src/lib/data.ts
```

If the Chinese Sprint `TimingData.jsonStream` was created in Task 2.2 Step 3, add it too.

```bash
git status && git diff --cached --stat
```

- [ ] **Step 2: Request user approval, then commit**

```bash
git commit -m "$(cat <<'EOF'
feat(precompute): add final_position and dnf_at_lap via TimingData

Adds TimingData.jsonStream to the fetch list and reads the last Line
value plus the canonical Retired flag per driver. DriverInventory gains
final_position (int | None) and dnf_at_lap (int | None). A race stint
is treated as DNF iff Retired is true; no lap-count heuristic, so
red-flag-shortened races don't falsely flag finishers.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Phase 3 — Site: `StrategyChart` component in isolation

Goal: a pure, route-free React component that renders the chart. Unit-tested via `vitest` + Testing Library. Not yet wired into a page.

### Task 3.1: `SessionTabs` component

**Files:**
- Create: `site/src/components/SessionTabs.tsx`
- Test: `site/tests/unit/SessionTabs.test.tsx`

- [ ] **Step 1: Write failing tests**

Create `site/tests/unit/SessionTabs.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SessionTabs } from "../../src/components/SessionTabs";

describe("<SessionTabs />", () => {
  it("renders SPRINT and RACE buttons", () => {
    render(<SessionTabs value="R" onChange={() => {}} />);
    expect(screen.getByRole("button", { name: /SPRINT/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /RACE/ })).toBeInTheDocument();
  });

  it("marks the active button as selected", () => {
    render(<SessionTabs value="S" onChange={() => {}} />);
    const sprintBtn = screen.getByRole("button", { name: /SPRINT/ });
    expect(sprintBtn).toHaveAttribute("aria-pressed", "true");
    const raceBtn = screen.getByRole("button", { name: /RACE/ });
    expect(raceBtn).toHaveAttribute("aria-pressed", "false");
  });

  it("calls onChange with the clicked key", () => {
    const spy = vi.fn();
    render(<SessionTabs value="R" onChange={spy} />);
    fireEvent.click(screen.getByRole("button", { name: /SPRINT/ }));
    expect(spy).toHaveBeenCalledWith("S");
  });
});
```

- [ ] **Step 2: Run — should fail**

```bash
cd site && npx vitest run tests/unit/SessionTabs.test.tsx
```

Expected: file-not-found for `SessionTabs`.

- [ ] **Step 3: Implement**

Create `site/src/components/SessionTabs.tsx`:

```tsx
type SessionKey = "R" | "S";

type Props = {
  value: SessionKey;
  onChange: (v: SessionKey) => void;
};

const KEYS: ReadonlyArray<{ k: SessionKey; label: string }> = [
  { k: "S", label: "SPRINT" },
  { k: "R", label: "RACE" },
];

export function SessionTabs({ value, onChange }: Props) {
  return (
    <div
      role="tablist"
      aria-label="Session"
      className="mb-4 inline-flex rounded-md border border-f1-border bg-f1-panel p-1"
    >
      {KEYS.map(({ k, label }) => {
        const active = value === k;
        return (
          <button
            key={k}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(k)}
            className={`rounded px-3 py-1 font-mono text-xs font-semibold tracking-widest transition ${
              active ? "bg-f1-border text-f1-text" : "text-f1-muted hover:text-f1-text"
            }`}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 4: Run — should pass**

```bash
cd site && npx vitest run tests/unit/SessionTabs.test.tsx
```

Expected: 3 pass.

---

### Task 3.2: `StrategyChart` component (TDD, tests first)

**Files:**
- Create: `site/tests/unit/StrategyChart.test.tsx`
- Create: `site/src/components/StrategyChart.tsx`

- [ ] **Step 1: Write failing tests**

Create `site/tests/unit/StrategyChart.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StrategyChart } from "../../src/components/StrategyChart";

type Driver = Parameters<typeof StrategyChart>[0]["drivers"][number];

function makeDriver(overrides: Partial<Driver> & { tla: string }): Driver {
  return {
    racing_number: "99",
    tla: overrides.tla,
    full_name: overrides.tla + " Fullname",
    team_name: "Team",
    team_color: "#888888",
    grid_position: null,
    sets: [],
    race_stints: [],
    sprint_stints: [],
    final_position: null,
    dnf_at_lap: null,
    ...overrides,
  };
}

const VER = makeDriver({
  tla: "VER",
  final_position: 1,
  race_stints: [
    { stint_idx: 0, compound: "MEDIUM", start_lap: 1,  end_lap: 18, laps: 18, new: true  },
    { stint_idx: 1, compound: "HARD",   start_lap: 19, end_lap: 57, laps: 39, new: true  },
  ],
});

const LEC_DNF = makeDriver({
  tla: "LEC",
  final_position: null,
  dnf_at_lap: 12,
  race_stints: [
    { stint_idx: 0, compound: "MEDIUM", start_lap: 1, end_lap: 12, laps: 12, new: true },
  ],
});

const HAM = makeDriver({
  tla: "HAM",
  final_position: 2,
  race_stints: [
    { stint_idx: 0, compound: "HARD", start_lap: 1, end_lap: 57, laps: 57, new: true },
  ],
});

describe("<StrategyChart />", () => {
  it("renders one row per driver with race_stints", () => {
    render(<StrategyChart drivers={[VER, HAM, LEC_DNF]} sessionKey="R" totalLaps={57} />);
    expect(screen.getAllByTestId("strategy-row")).toHaveLength(3);
  });

  it("sorts finishers ahead of DNFs and by final_position asc", () => {
    render(<StrategyChart drivers={[LEC_DNF, HAM, VER]} sessionKey="R" totalLaps={57} />);
    const rows = screen.getAllByTestId("strategy-row");
    expect(rows.map((r) => r.getAttribute("data-tla"))).toEqual(["VER", "HAM", "LEC"]);
  });

  it("skips drivers with no stints for the requested session", () => {
    const GAS = makeDriver({ tla: "GAS", final_position: 8, race_stints: [], sprint_stints: [] });
    render(<StrategyChart drivers={[VER, GAS]} sessionKey="R" totalLaps={57} />);
    const rows = screen.getAllByTestId("strategy-row");
    expect(rows.map((r) => r.getAttribute("data-tla"))).toEqual(["VER"]);
  });

  it("renders a RET trailer for DNF drivers", () => {
    render(<StrategyChart drivers={[VER, LEC_DNF]} sessionKey="R" totalLaps={57} />);
    expect(screen.getByText("RET L12")).toBeInTheDocument();
  });

  it("renders a finishing position trailer for finishers", () => {
    render(<StrategyChart drivers={[VER, HAM]} sessionKey="R" totalLaps={57} />);
    expect(screen.getByText("P1")).toBeInTheDocument();
    expect(screen.getByText("P2")).toBeInTheDocument();
  });

  it("uses sprint_stints when sessionKey=S", () => {
    const sprinter = makeDriver({
      tla: "NOR",
      final_position: 3,
      race_stints: [],
      sprint_stints: [
        { stint_idx: 0, compound: "MEDIUM", start_lap: 1, end_lap: 19, laps: 19, new: true },
      ],
    });
    render(<StrategyChart drivers={[sprinter]} sessionKey="S" totalLaps={19} />);
    expect(screen.getAllByTestId("strategy-row")).toHaveLength(1);
  });
});
```

- [ ] **Step 2: Run — should fail**

```bash
cd site && npx vitest run tests/unit/StrategyChart.test.tsx
```

Expected: module not found.

- [ ] **Step 3: Implement `StrategyChart`**

Create `site/src/components/StrategyChart.tsx`:

```tsx
import { Fragment } from "react";
import { Group } from "@visx/group";
import { scaleLinear, scaleBand } from "@visx/scale";
import { Bar } from "@visx/shape";
import { ParentSize } from "@visx/responsive";
import { AxisBottom } from "@visx/axis";

type Compound = "SOFT" | "MEDIUM" | "HARD" | "INTERMEDIATE" | "WET";

type RaceStint = {
  stint_idx: number;
  compound: Compound;
  start_lap: number;
  end_lap: number;
  laps: number;
  new: boolean;
};

type Driver = {
  racing_number: string;
  tla: string;
  full_name: string;
  team_name: string;
  team_color: string;
  grid_position: number | null;
  sets: unknown[];
  race_stints: RaceStint[];
  sprint_stints: RaceStint[];
  final_position: number | null;
  dnf_at_lap: number | null;
};

type Props = {
  drivers: Driver[];
  sessionKey: "R" | "S";
  totalLaps: number;
};

const ROW_H = 34;
const PAD = { top: 16, right: 60, bottom: 24, left: 52 };

const COMPOUND_LETTER: Record<Compound, string> = {
  SOFT: "S",
  MEDIUM: "M",
  HARD: "H",
  INTERMEDIATE: "I",
  WET: "W",
};

function compoundColorVar(c: Compound): string {
  const slug = c === "INTERMEDIATE" ? "inter" : c.toLowerCase();
  return `var(--color-compound-${slug})`;
}

function compoundTextColor(c: Compound): string {
  return c === "MEDIUM" || c === "HARD" ? "#111" : "#fff";
}

type Row = {
  driver: Driver;
  stints: RaceStint[];
  finalPos: number | null;
  dnfAtLap: number | null;
};

function prepareRows(drivers: Driver[], sessionKey: "R" | "S"): Row[] {
  return drivers
    .map<Row>((d) => ({
      driver: d,
      stints: sessionKey === "R" ? d.race_stints : d.sprint_stints,
      finalPos: d.final_position,
      dnfAtLap: d.dnf_at_lap,
    }))
    .filter((r) => r.stints.length > 0)
    .sort((a, b) => {
      if (a.finalPos != null && b.finalPos != null) return a.finalPos - b.finalPos;
      if (a.finalPos != null) return -1;
      if (b.finalPos != null) return 1;
      return (b.dnfAtLap ?? 0) - (a.dnfAtLap ?? 0);
    });
}

export function StrategyChart({ drivers, sessionKey, totalLaps }: Props) {
  const rows = prepareRows(drivers, sessionKey);
  if (rows.length === 0) {
    return <p className="text-sm text-f1-muted">No stints recorded for this session.</p>;
  }
  const height = PAD.top + rows.length * ROW_H + PAD.bottom;

  return (
    <ParentSize>
      {({ width }) => {
        if (width === 0) return null;

        const narrow = width < 480;
        const leftCol = narrow ? 38 : PAD.left;
        const xScale = scaleLinear<number>({
          domain: [1, Math.max(totalLaps, 1)],
          range: [leftCol, width - PAD.right],
        });
        const yScale = scaleBand<number>({
          domain: rows.map((_, i) => i),
          range: [PAD.top, PAD.top + rows.length * ROW_H],
          padding: 0.15,
        });
        const labelThreshold = narrow ? 48 : 34;

        return (
          <svg width={width} height={height} role="img" aria-label="Race strategy chart">
            {rows.map((row, i) => {
              const y = yScale(i)!;
              return (
                <Group key={row.driver.tla} data-testid="strategy-row" data-tla={row.driver.tla}>
                  <text
                    x={leftCol - 10}
                    y={y + ROW_H / 2}
                    textAnchor="end"
                    dominantBaseline="middle"
                    className="fill-f1-muted font-mono text-xs font-semibold tracking-widest"
                  >
                    {row.driver.tla}
                  </text>
                  {row.stints.map((s) => {
                    const x0 = xScale(s.start_lap);
                    const x1 = xScale(s.end_lap + 1);
                    const w = Math.max(x1 - x0 - 2, 0); // 2px gap = pit marker
                    const showLabel = w >= labelThreshold;
                    return (
                      <Fragment key={s.stint_idx}>
                        <Bar
                          x={x0}
                          y={y + 4}
                          width={w}
                          height={ROW_H - 8}
                          fill={compoundColorVar(s.compound)}
                          rx={3}
                        />
                        {s.new && (
                          <circle
                            cx={x0 + w - 5}
                            cy={y + 8}
                            r={2.5}
                            fill={s.compound === "HARD" ? "#333" : "rgba(255,255,255,0.85)"}
                          />
                        )}
                        {showLabel && (
                          <text
                            x={x0 + 6}
                            y={y + ROW_H / 2 + 1}
                            dominantBaseline="middle"
                            fontFamily="ui-monospace, monospace"
                            fontSize={11}
                            fontWeight={700}
                            fill={compoundTextColor(s.compound)}
                          >
                            {COMPOUND_LETTER[s.compound]} · {s.laps}
                          </text>
                        )}
                      </Fragment>
                    );
                  })}
                  <text
                    x={width - PAD.right + 8}
                    y={y + ROW_H / 2}
                    dominantBaseline="middle"
                    fontFamily="ui-monospace, monospace"
                    fontSize={11}
                    fontWeight={700}
                    className={row.dnfAtLap != null ? "fill-compound-soft" : "fill-f1-muted"}
                  >
                    {row.dnfAtLap != null ? `RET L${row.dnfAtLap}` : `P${row.finalPos}`}
                  </text>
                </Group>
              );
            })}
            <AxisBottom
              scale={xScale}
              top={PAD.top + rows.length * ROW_H + 4}
              numTicks={Math.min(7, totalLaps)}
              tickFormat={(v) => String(v)}
              tickLabelProps={() => ({
                fontFamily: "ui-monospace, monospace",
                fontSize: 10,
                fill: "var(--color-f1-muted)",
                textAnchor: "middle",
              })}
              stroke="var(--color-f1-border)"
              tickStroke="var(--color-f1-border)"
            />
          </svg>
        );
      }}
    </ParentSize>
  );
}
```

- [ ] **Step 4: Run — should pass**

```bash
cd site && npx vitest run tests/unit/StrategyChart.test.tsx
```

Expected: all 6 pass.

- [ ] **Step 5: Full unit suite**

```bash
cd site && npm run test
```

Expected: all green.

---

### Task 3.3: Commit phase 3

- [ ] **Step 1: Draft commit**

```bash
git add site/src/components/SessionTabs.tsx \
        site/src/components/StrategyChart.tsx \
        site/tests/unit/SessionTabs.test.tsx \
        site/tests/unit/StrategyChart.test.tsx
git status && git diff --cached --stat
```

- [ ] **Step 2: Request user approval, then commit**

```bash
git commit -m "$(cat <<'EOF'
feat(site): add StrategyChart and SessionTabs components

Pure, route-free components rendering a per-driver stint timeline in
SVG via @visx. Sorted by finishing position with DNF drivers flagged
via a RET L<lap> trailer. Not yet wired into the router.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Phase 4 — Site: route, page, tile, breadcrumbs, e2e

Goal: the feature becomes reachable by the user via `/race/<slug>/strategy`.

### Task 4.1: Extend breadcrumbs for the new route

**Files:**
- Modify: `site/src/lib/breadcrumbs.ts`
- Test: `site/tests/unit/breadcrumbs.test.ts`

- [ ] **Step 1: Write failing tests**

Append to `site/tests/unit/breadcrumbs.test.ts`:

```ts
it("builds a trail for /race/<slug>/strategy", () => {
  const trail = buildTrail("/race/australia-2026/strategy", SCHEDULE);
  expect(trail.map((c) => c.label)).toEqual([
    "Home",
    "2026",
    expect.any(String), // race label
    "Strategy",
  ]);
  expect(trail[trail.length - 1].current).toBe(true);
  expect(trail[trail.length - 1].href).toBe("/race/australia-2026/strategy");
});
```

- [ ] **Step 2: Run — should fail**

```bash
cd site && npx vitest run tests/unit/breadcrumbs.test.ts
```

Expected: last crumb label is undefined / trail is short because the regex in `buildTrail` doesn't match `strategy`.

- [ ] **Step 3: Update the regex and branch**

In `site/src/lib/breadcrumbs.ts`, change the race regex and add the new branch:

```ts
  const raceMatch = pathname.match(
    /^\/race\/([^/]+)(?:\/(tyres|strategy|driver\/([A-Za-z0-9]+)))?\/?$/
  );
```

and inside the `raceMatch` block, after the existing `tyres` branch:

```ts
    if (leaf === "tyres") {
      trail.push({ label: "Tyres", href: `/race/${slug}/tyres`, current: true });
    } else if (leaf === "strategy") {
      trail.push({ label: "Strategy", href: `/race/${slug}/strategy`, current: true });
    } else if (leaf?.startsWith("driver/")) {
      // … unchanged …
    }
```

- [ ] **Step 4: Run — should pass**

```bash
cd site && npx vitest run tests/unit/breadcrumbs.test.ts
```

Expected: new test passes, existing breadcrumb tests still pass.

---

### Task 4.2: `Strategy.tsx` route component

**Files:**
- Create: `site/src/routes/Strategy.tsx`

- [ ] **Step 1: Implement**

Create `site/src/routes/Strategy.tsx`:

```tsx
import { useEffect, useState } from "react";
import { Navigate, useParams } from "react-router-dom";
import { RaceHeader } from "../components/RaceHeader";
import { SessionTabs } from "../components/SessionTabs";
import { StrategyChart } from "../components/StrategyChart";
import { loadManifest } from "../lib/data";
import type { Manifest } from "../lib/schemas";
import { isFeatured } from "../config";
import { SCHEDULE } from "../data/schedule";
import NotFound from "./NotFound";

export default function Strategy() {
  const { slug = "" } = useParams<{ slug: string }>();
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [session, setSession] = useState<"R" | "S">("R");

  const known = SCHEDULE.some((s) => s.races.some((r) => r.slug === slug));

  useEffect(() => {
    if (!isFeatured(slug)) return;
    loadManifest(`${import.meta.env.BASE_URL}data/${slug}.json`)
      .then(setManifest)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)));
  }, [slug]);

  if (!known) return <NotFound />;
  if (!isFeatured(slug)) return <Navigate to={`/race/${slug}`} replace />;

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

  const drivers = manifest.race.drivers as Parameters<typeof StrategyChart>[0]["drivers"];
  const hasSprint = drivers.some((d) => d.sprint_stints.length > 0);
  const hasRace   = drivers.some((d) => d.race_stints.length > 0);

  if (!hasRace && !hasSprint) {
    return (
      <main className="mx-auto max-w-6xl p-6">
        <RaceHeader race={manifest.race} />
        <p className="mt-4 rounded-md border border-f1-border bg-f1-panel p-4 text-sm text-f1-muted">
          Race not run yet — strategy will appear after the chequered flag.
        </p>
      </main>
    );
  }

  const active: "R" | "S" = hasRace ? session : "S";
  const stints = drivers.flatMap((d) => (active === "R" ? d.race_stints : d.sprint_stints));
  const totalLaps = stints.length > 0 ? Math.max(...stints.map((s) => s.end_lap)) : 0;

  return (
    <main className="mx-auto max-w-6xl p-6">
      <RaceHeader race={manifest.race} />
      {hasSprint && hasRace && (
        <SessionTabs value={session} onChange={setSession} />
      )}
      <StrategyChart drivers={drivers} sessionKey={active} totalLaps={totalLaps} />
    </main>
  );
}
```

- [ ] **Step 2: Type-check**

```bash
cd site && npx tsc --noEmit
```

Expected: clean.

---

### Task 4.3: Register the route

**Files:**
- Modify: `site/src/App.tsx`

- [ ] **Step 1: Add the import**

At the top of `site/src/App.tsx`:

```tsx
import Strategy from "./routes/Strategy";
```

- [ ] **Step 2: Add the route entry**

Inside the children array, after the `tyres` entry:

```tsx
        { path: "/race/:slug/strategy", element: <Strategy />, errorElement: <NotFound /> },
```

- [ ] **Step 3: Type-check**

```bash
cd site && npx tsc --noEmit
```

Expected: clean.

---

### Task 4.4: Add the "Race Strategy" tile

**Files:**
- Modify: `site/src/routes/Race.tsx`

- [ ] **Step 1: Add the tile**

In the Analytics grid inside `site/src/routes/Race.tsx`, after the existing `Tyre Inventory` tile:

```tsx
            <AnalyticsTile
              title="Race Strategy"
              description="Tyre stints per driver with pit-stop timeline."
              to={`/race/${slug}/strategy`}
            />
```

- [ ] **Step 2: Type-check + unit tests**

```bash
cd site && npx tsc --noEmit && npm run test
```

Expected: green.

- [ ] **Step 3: Manual smoke**

```bash
make dev
```

Visit http://localhost:5173 → `/race/australia-2026` → click **Race Strategy** → verify the chart. Switch to `/race/china-2026/strategy` → verify SPRINT/RACE tabs appear and clicking SPRINT updates the chart. Stop the dev server.

---

### Task 4.5: Playwright e2e

**Files:**
- Create: `site/tests/e2e/strategy.spec.ts`

- [ ] **Step 1: Write the e2e spec**

Create `site/tests/e2e/strategy.spec.ts`:

```ts
import { test, expect } from "@playwright/test";

test("Race Strategy tile is reachable from race page", async ({ page }) => {
  await page.goto("/race/australia-2026");
  await page.getByRole("link", { name: /Race Strategy/i }).click();
  await expect(page).toHaveURL(/\/race\/australia-2026\/strategy$/);
  await expect(page.getByRole("img", { name: /Race strategy chart/i })).toBeVisible();
});

test("sprint weekend shows SPRINT/RACE tabs and switching updates the chart", async ({ page }) => {
  await page.goto("/race/china-2026/strategy");
  const raceTab = page.getByRole("button", { name: /^RACE$/ });
  const sprintTab = page.getByRole("button", { name: /^SPRINT$/ });
  await expect(raceTab).toBeVisible();
  await expect(sprintTab).toBeVisible();
  await expect(raceTab).toHaveAttribute("aria-pressed", "true");

  const chart = page.getByRole("img", { name: /Race strategy chart/i });
  await expect(chart).toBeVisible();
  const svgBefore = await chart.innerHTML();

  await sprintTab.click();
  await expect(sprintTab).toHaveAttribute("aria-pressed", "true");
  const svgAfter = await chart.innerHTML();
  expect(svgAfter).not.toEqual(svgBefore);
});

test("non-featured race redirects away from /strategy", async ({ page }) => {
  // Pick a race that's in SCHEDULE but not in FEATURED_RACE_SLUGS.
  await page.goto("/race/bahrain-2026/strategy");
  await expect(page).toHaveURL(/\/race\/bahrain-2026$/);
});
```

If `bahrain-2026` isn't in `SCHEDULE`, pick any scheduled-but-not-featured slug — check with: `grep "slug:" site/src/data/schedule.ts | head -20`.

- [ ] **Step 2: Install Playwright browsers if not already**

```bash
cd site && npx playwright install --with-deps chromium
```

(One-time; skip if the team already has it.)

- [ ] **Step 3: Run the e2e**

```bash
make test-e2e
```

Expected: the three new specs pass alongside existing ones.

---

### Task 4.6: Commit phase 4

- [ ] **Step 1: Draft commit**

```bash
git add site/src/App.tsx \
        site/src/routes/Strategy.tsx \
        site/src/routes/Race.tsx \
        site/src/lib/breadcrumbs.ts \
        site/tests/unit/breadcrumbs.test.ts \
        site/tests/e2e/strategy.spec.ts
git status && git diff --cached --stat
```

- [ ] **Step 2: Request user approval, then commit**

```bash
git commit -m "$(cat <<'EOF'
feat(site): add /race/<slug>/strategy page

Per-driver tyre-stint timeline sorted by finishing position with a
SPRINT/RACE tab switcher on sprint weekends. Reachable via a new
AnalyticsTile on the race page. Covered by unit tests for breadcrumbs
and by Playwright e2e for the full navigation flow.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Phase 5 — Documentation touch-ups

### Task 5.1: Update `CLAUDE.md` to reflect the added data file and route

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update the route list (if present)**

Search `CLAUDE.md` for mentions of `/race/:slug/tyres`:

```bash
grep -n "race/" CLAUDE.md || echo "no matches"
```

If there's a list of known site routes, append `/race/<slug>/strategy` with a one-line description (e.g., "per-driver race-strategy timeline"). If the file doesn't enumerate routes, skip.

- [ ] **Step 2: Update the files-read-by-precompute list (if present)**

Search for `TyreStintSeries` in `CLAUDE.md`:

```bash
grep -n "TyreStintSeries\|TimingAppData" CLAUDE.md || echo "no matches"
```

If the file lists ingested files, add `TimingData.jsonStream — final race classification and retired flag` next to the others.

- [ ] **Step 3: Type-check docs are markdown-correct (no linter needed; eyeball it)**

Read the edited file and confirm structure is unbroken.

---

### Task 5.2: Commit phase 5

- [ ] **Step 1: Draft commit (only if CLAUDE.md changed)**

```bash
git status
```

If `CLAUDE.md` was modified:

```bash
git add CLAUDE.md
git diff --cached --stat
```

- [ ] **Step 2: Request user approval, then commit**

```bash
git commit -m "$(cat <<'EOF'
docs(claude): note TimingData and /strategy route in project guide

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

If `CLAUDE.md` needed no changes, skip this task.

---

## Final verification

- [ ] **All tests**

```bash
make test
```

Expected: Python tests green (coverage ≥85%), site unit tests green, Playwright specs green.

- [ ] **Full production build**

```bash
make build
```

Expected: `site/dist/` regenerated cleanly, no warnings about missing data.

- [ ] **Quick visual smoke against the built site**

```bash
cd site && npx vite preview --port 5180 --strictPort
```

Open http://localhost:5180, navigate Home → 2026 → Australia → Race Strategy; then Home → 2026 → China → Race Strategy → toggle SPRINT/RACE. Stop the preview.

---

## Spec coverage matrix

| Spec section | Implementing tasks |
|---|---|
| §3 user-visible behaviour | Task 3.2 (chart), Task 4.2 (page), Task 4.4 (tile), Task 4.1 (breadcrumbs) |
| §4 data model | Task 1.1, Task 2.4 |
| §5.1 lap-indexed stints | Task 1.2, Task 1.3 |
| §5.2 TimingData ingest | Task 2.1, Task 2.3, Task 2.5 |
| §5.3 precompute tests | Tasks 1.1, 1.2, 1.3, 2.3, 2.4, 2.5 |
| §6.1 route | Task 4.3 |
| §6.2 route component | Task 4.2 |
| §6.3 chart component | Task 3.2 |
| §6.4 session tabs | Task 3.1 |
| §6.5 race-page tile | Task 4.4 |
| §6.6 breadcrumbs | Task 4.1 |
| §6.7 tests | Tasks 3.1, 3.2, 4.5 |
| §7 build sequence | Phases 1–5 |
| §8 non-goals | (intentionally omitted from implementation) |
| §9 risks | Schema drift: Tasks 1.4 & 2.6; DNF future-featured races: Task 2.5 Step 1 third test; coverage gate: §5.3 tests |
