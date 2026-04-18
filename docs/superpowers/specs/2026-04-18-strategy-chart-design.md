# Race Strategy Chart — Design

**Date:** 2026-04-18
**Status:** Approved, ready for implementation plan.

## 1. Summary

Add a per-race strategy visualization: one horizontal row per driver showing
their tyre stints (compound, lap range, new/used) across the race — and,
on sprint weekends, the sprint. Rows are sorted by finishing position,
with DNF drivers at the bottom flagged as `RET L<lap>`. The chart lives
at `/race/<slug>/strategy`, reachable from a new `AnalyticsTile` on the
race page.

The data already needed for stints (`TyreStintSeries.jsonStream`) is
already in the pipeline. This spec adds one more source file
(`TimingData.jsonStream`) to derive canonical finishing order and
retirement flags.

## 2. Motivation

The site currently exposes pre-race tyre inventory only. Once the race
has run, the most informative view — the classic F1 strategy chart — is
absent. Given that `TyreStintSeries` is already parsed to derive
inventory, exposing the race-session stints themselves is a small
additive step that unlocks a well-understood, high-value visualization.

The chart answers questions like "what got the winner there", "who
undercut whom", "which one-stop strategies worked", at a glance.

## 3. User-visible behavior

- A new `AnalyticsTile` titled **Race Strategy** on `/race/<slug>` for
  each featured race.
- Clicking the tile opens `/race/<slug>/strategy`, which renders:
  - Breadcrumbs (auto, via `lib/breadcrumbs.ts`) including "Race Strategy".
  - Race header (reused `<RaceHeader>`).
  - On sprint weekends only: a `SPRINT / RACE` tab switcher.
  - The strategy chart.
- One row per driver who ran in the chosen session. Rows sorted:
  finishers by `final_position` ascending; DNF drivers appended below in
  descending `dnf_at_lap` order (the retiree who made it furthest shown
  first among DNFs).
- Each row:
  - Left: driver TLA (monospace, muted).
  - Centre: stint segments coloured by compound (solid fill from the
    existing `--color-compound-*` CSS variables). Segments sized by lap
    range over `[1, totalLaps]`. Inline label inside each segment ≥ 34px
    wide: `S · 14` (compound letter · laps). A small dot in the
    top-right of each segment denotes a new set.
  - Right: `P<n>` for finishers, `RET L<lap>` (in compound-soft red) for
    retirees.
- Hover over a segment: tooltip with driver TLA, stint index, compound,
  lap range, lap count, and new/used state (plus "Retired at lap N" for
  DNF drivers).
- Layout is responsive via `<ParentSize>`. Inline-label threshold:
  hide the label when the segment is narrower than 34px (desktop) or
  48px (widths < 480px — narrower screens demand more breathing room).
  On widths < 480px the TLA column also narrows from 52px to 38px.
  The segment stays visible in every case; full detail is in the tooltip.

DNF handling: short bar (length = laps completed) + `RET L<lap>` trailer.
No shaded ghost region — chosen for lower visual noise and simpler code.

## 4. Data model changes

`precompute/src/f1/models.py`:

```python
class RaceStint(_StrictModel):
    """One stint in a race or sprint session."""
    stint_idx: int
    compound: Compound
    start_lap: int
    end_lap: int
    laps: int
    new: bool

class DriverInventory(_StrictModel):
    # existing fields unchanged…
    race_stints:     list[RaceStint] = []
    sprint_stints:   list[RaceStint] = []
    final_position:  int | None = None
    dnf_at_lap:      int | None = None
```

Invariants:
- If `race_stints` (or `sprint_stints`) is non-empty for a driver, then
  for that session exactly one of `final_position` / `dnf_at_lap` is
  non-None.
- If the stint list is empty for a driver, both fields MAY be None.
  This covers three cases: (a) race not yet run; (b) DNS — driver did
  not start, so no stint was ever emitted; (c) the session is simply
  absent from the archive for this weekend. The site filters drivers
  with empty stint lists out of the chart regardless of reason.

For races that haven't been run yet (future featured weekends): all
stint lists empty, both position fields `None` for everyone. No crash,
no chart — the page shows a friendly "not run yet" message.

Zod schema regeneration: `make genzod` picks up the additions via
`f1.schema` → JSON Schema → `site/src/lib/schemas.ts`.

## 5. Precompute changes

### 5.1 Lap-indexed race stints

`inventory.py` already produces `SessionStint` records from
`TyreStintSeries.jsonStream`. These carry `start_laps` / `total_laps`
which describe **tyre wear**, not race laps. New helper:

```python
def build_race_stints(
    driver_number: str,
    stints_for_session: list[SessionStint],
) -> list[RaceStint]:
    ...
```

Logic: sort by `stint_idx`. For each stint, `start_lap` = previous
stint's `end_lap + 1` (or 1 for the first); `end_lap = start_lap +
total_laps - 1`; `laps = total_laps`. Stints whose compound is not
one of the canonical five are skipped (same rule already used in
`extract_session_stints`).

Wired into `build.py::build_race_manifest` alongside the existing
inventory pass.

### 5.2 `TimingData.jsonStream` ingest

Add `"TimingData.jsonStream"` to `seasons/fetch_race.py::MANIFEST_FILES`
(fifth file; ~1–5 MB gzip per race session; CI fetch stays well under
10 MB).

New function, in `driver_meta.py` (or a sibling `timing.py` if
`driver_meta.py` starts doing too much):

```python
def extract_final_positions_and_retirements(
    reduced_td: dict[str, object],
) -> dict[str, tuple[int | None, bool]]:
    """Return {driver_number: (final_line, retired)} for the race session.

    `final_line` is the last observed `Line` value for the driver;
    `retired` is True iff the last observed `Retired` is True.
    """
```

In `build.py`:
- If the driver has no race stints at all (DNS or pre-race manifest),
  both fields stay `None`.
- Else if `retired` is True → `dnf_at_lap = last_race_stint.end_lap`,
  `final_position = None`.
- Else → `final_position = final_line`, `dnf_at_lap = None`.

No lap-count heuristic for DNF — the canonical `Retired` flag is the
source of truth. This correctly handles red-flag-shortened races.

### 5.3 Tests

- `test_race_stints.py::test_single_stop` — 2 stints, correct start/end/laps.
- `::test_two_stop` — 3 stints, boundary continuity.
- `::test_unknown_compound_skipped` — non-canonical compound stripped.
- `test_timing_data.py::test_retired_flag_maps_to_dnf` — `Retired: true`
  in the feed produces `dnf_at_lap` filled and `final_position = None`.
- `::test_red_flag_shortened_race` — every driver completes fewer laps
  than planned, nobody has `Retired: true` → nobody is marked DNF.
- Existing 85% coverage gate in `pyproject.toml` must continue to pass.

## 6. Site changes

### 6.1 Route

`site/src/App.tsx`:

```tsx
{ path: "/race/:slug/strategy", element: <Strategy />, errorElement: <NotFound /> },
```

### 6.2 `site/src/routes/Strategy.tsx`

Pattern 1:1 with `Tyres.tsx`: `useParams`, `loadManifest`, featured-guard,
loading/error states. Owns `useState<"R" | "S">("R")`. Computes `hasRace`
/ `hasSprint` from the manifest; renders `SessionTabs` only when both
are present. Computes `totalLaps` as `max(end_lap)` across all drivers'
stints for the active session. Empty state: "Race not run yet — strategy
will appear after the chequered flag."

### 6.3 `site/src/components/StrategyChart.tsx`

Pure, router-free, tests cleanly in vitest.

```tsx
type Props = {
  drivers: DriverInventory[];
  sessionKey: "R" | "S";
  totalLaps: number;
};
```

Responsibilities:
- Filter to drivers who have stints for `sessionKey`.
- Sort: finishers by `final_position` asc; DNF appended by `dnf_at_lap` desc.
- Render SVG via `@visx` (`scaleLinear` for lap X, `scaleBand` for row Y,
  `<Bar>` for segments, `<AxisBottom>` for lap ticks), wrapped in
  `<ParentSize>` (same pattern as `UsageBar`).
- Compound colours from `var(--color-compound-*)`.
- New-set indicator: 5×5 px dot in each segment's top-right.
- Inline label shown when segment width ≥ 34px.
- Tooltip via `@visx/tooltip`.

Row height: 34px; top/bottom padding 16/24px; left col (TLA) 52px;
right col (trailer) 60px. No fixed total height — driven by row count
× 34.

### 6.4 `site/src/components/SessionTabs.tsx`

Minimal stateless button pair (`S` / `R`). Selection lives in the
route's React state, not URL. Adding `?session=` later is a trivial
change if it becomes desirable.

### 6.5 Race-page tile

Add a third `AnalyticsTile` to `site/src/routes/Race.tsx`:

```tsx
<AnalyticsTile
  title="Race Strategy"
  description="Tyre stints per driver with pit-stop timeline."
  to={`/race/${slug}/strategy`}
/>
```

### 6.6 Breadcrumbs

Extend `site/src/lib/breadcrumbs.ts` with `strategy → "Race Strategy"`
so the auto-generated crumbs read correctly.

### 6.7 Tests

- `StrategyChart.test.tsx`:
  - `renders_row_per_driver_with_stints`.
  - `sorts_finishers_before_dnf`.
  - `dnf_trailer_uses_compound_soft_color`.
  - `hides_inline_label_for_short_stint`.
  - `skips_driver_with_no_stints_for_session`.
- Playwright (`site/tests/e2e/strategy.spec.ts`):
  - `australia-2026`: Race page → tile → `/strategy` loads; chart visible.
  - `china-2026`: tabs visible; switching `SPRINT` changes row count and
    lap axis.
  - `/race/<bad-slug>/strategy` redirects to the race page.

## 7. Build sequence

Each step is a green-tree PR-sized unit.

1. **Precompute — race stints only.** Add `RaceStint`, populate
   `race_stints` + `sprint_stints` in `DriverInventory`. Regenerate Zod.
   Site ignores new fields.
2. **Precompute — TimingData.** Add file to fetch list, add
   `extract_final_positions_and_retirements`, populate `final_position`
   / `dnf_at_lap`. Regenerate Zod.
3. **Site — `StrategyChart` component in isolation.** Ship with unit
   tests. Not yet routed.
4. **Site — route, page, tile, breadcrumbs, e2e.** Feature live.
5. **Docs — `CLAUDE.md` updates** mentioning `TimingData` in the
   pipeline and `/strategy` in the routes.

Checkpoint after each step: green CI + user sign-off before the next.

## 8. Explicit non-goals for v1

- Per-lap position trace (separate potential feature using `TimingData`
  `Line` series, not just last value).
- Pit-stop duration annotations (would need
  `PitLaneTimeCollection.jsonStream`).
- Retirement reason (`RaceControlMessages.jsonStream`, not fetched yet).
- Shareable deep link to a session tab (no URL param in v1).
- FP / Q stint visualization (not meaningful under the same chart shape).
- Mobile-specific tap interactions beyond tooltip-on-hover.

Any of these are clean follow-ups; none is blocked by v1 decisions.

## 9. Risks

- **Zod drift.** Skipping `make genzod` between Precompute and Site
  steps will runtime-fail validation. `make build` and `make dev`
  already chain through `genzod`; direct `vite` does not. The build
  sequence treats regen as a required step in 1 and 2.
- **Future-featured races without race data.** If a featured race is
  added before it runs, `TimingData` and relevant stints are absent.
  `_reduce_stream` already returns `{}` for missing files; the model
  fields default to empty / None; the site renders the "not run yet"
  message. Covered by the empty-state path; worth an explicit test.
- **Coverage gate (85%).** New pipeline functions must be covered.
  Tests in §5.3 are sized to keep the gate.
- **`Line` field semantics for classified DNFs.** Stewards-assigned
  finishing positions for cars that retired but completed >90% of race
  distance live in `SessionData.jsonStream` / official classification,
  not in `TimingData`. For v1, retirees are presented as `RET` without
  a stewards-assigned position; if a concrete discrepancy surfaces,
  adding `SessionData` to fetch is a one-line follow-up.
