# Track Status Overlay on Race Strategy Chart — Design

**Date:** 2026-04-18
**Status:** Awaiting user review.
**Branch:** `feat/track-status-overlay` (proposed)

## 1. Summary

Render a visual overlay on the Race Strategy chart that shows when each
session spent time under non-green conditions — yellow flags, Safety
Car, Virtual Safety Car, red flag. Every band is anchored to the same
lap axis the chart already uses, so viewers can immediately tie
pit-stop timing and stint length to track events.

The overlay appears on both the Race and Sprint tabs of the Strategy
page, for all three featured races (`australia-2026`, `china-2026`,
`japan-2026`). Sessions with no non-green transitions render exactly as
they do today — the overlay is additive and has no layout cost when the
band list is empty.

## 2. Motivation

Flag and Safety Car windows are the single largest exogenous driver of
race strategy. A cluster of pit-stops at lap 32 looks suspicious without
context; the same cluster under an SC banner is obvious and expected.
The current Strategy chart answers *what* compounds each driver ran and
*when* they pitted, but omits *why* the whole field reacted at the same
moment. This overlay closes that gap with one lightweight visual layer.

This is the first of several candidate overlays from
`docs/data-feed-reference.md` (weather, position trace, penalty log).
The design sets up the data-model and rendering pattern those later
overlays will reuse.

## 3. Scope

**In scope.**

- Fetch `TrackStatus.jsonStream` and `LapCount.jsonStream` per session
  in `seasons/fetch_race.py`.
- Compute per-session status bands in `precompute/` — a list of
  `(status, start_lap, end_lap)` tuples with status ∈
  {`Yellow`, `SCDeployed`, `VSCDeployed`, `Red`}.
- Emit `race_status_bands` and `sprint_status_bands` on
  `manifest.race`; re-gen Zod.
- Render bands and a thin top strip on `StrategyChart.tsx`, with a
  hover tooltip sharing the chart's existing tooltip infrastructure.
- Unit tests for band computation (including synthetic VSC/Red
  fixtures), integration test against Japan 2026 real data, site
  vitest for presence/absence based on `statusBands` prop, Playwright
  E2E that asserts the strip segment exists on `/race/japan-2026/strategy`.

**Out of scope.**

- Any feed other than `TrackStatus` and `LapCount`. The weather
  overlay, position trace, and penalty log each get their own spec.
- Sector-level yellow localization (`TrackStatus` code `"2"` fires on
  any yellow, regardless of scope). The overlay is session-wide only.
- Race control message text as tooltip content — comes from
  `RaceControlMessages.jsonStream`, which is out of scope here.
- Practice/qualifying sessions. The Strategy chart renders only Race
  and Sprint; qualifying has no stint structure to overlay.
- Visual polish for `VSCDeployed` and `Red` bands beyond the planned
  hatch/fill patterns — none of the three featured 2026 races recorded
  these states in their real data, so their design is validated only
  against synthetic fixtures in this iteration.

## 4. User-visible design

**Visual style: Option C (hybrid).** Low-opacity full-height
background bands behind the whole stint region + a thin bright strip
(6px) directly above the driver rows.

- **Background bands.** Fill-opacity ≈ 0.12–0.14 so the compound
  colours on each stint remain the primary signal. Yellow flags use a
  diagonal hatch pattern (`#eab308` + `#ca8a04`) rather than solid
  yellow, to avoid colour collision with `MEDIUM` compound stints
  (which are solid `#ffdd00`). Red flags use a red hatch pattern for
  the same reason vs. `SOFT` (`#ff3030`). SC and VSC use solid orange
  (`#f97316`, `#fb923c`) — no compound conflict.
- **Top strip.** 6px tall, spans the chart width. Acts as a
  persistent legend and ensures brief status periods remain visible
  even when the full-height band is too faint. The strip's default
  background is a faint green (`#10b981` ≈ 0.28) to represent
  `AllClear` as the baseline; non-green segments overlay the same
  colours as the full-height bands.
- **Tooltip.** Hovering a band or strip segment opens a tooltip with
  `<Status> · lap <start>–<end> (<N> laps)`. Shares the existing
  `TooltipWithBounds` via a discriminated union on the tooltip
  payload (`kind: "stint" | "status"`).

**Interactivity.** Tooltip on hover, no click behaviour. Matches the
existing stint tooltip. Empty `statusBands` array renders zero extra
SVG nodes.

## 5. Architecture

```
seasons/fetch_race.py (+TrackStatus.jsonStream, +LapCount.jsonStream)
                   │
                   ▼
precompute/src/f1/track_status.py   ← NEW module
                   │
                   ▼
precompute/src/f1/build.py          ← calls track_status for R + S
                   │
                   ▼
manifest.race.race_status_bands / sprint_status_bands
                   │
                   ▼ (Pydantic → JSON Schema → Zod, auto-regen)
                   │
site/src/routes/Strategy.tsx        ← passes bands prop
                   │
                   ▼
site/src/components/StrategyChart.tsx ← renders layers
```

No new runtime network dependencies on the site. The site keeps its
static-manifest model.

## 6. Data model

New types in `precompute/src/f1/models.py`:

```python
TrackStatusCode = Literal["Yellow", "SCDeployed", "VSCDeployed", "Red"]

class StatusBand(_StrictModel):
    """One continuous non-green status period within a session."""
    status: TrackStatusCode
    start_lap: int = Field(ge=1, description="Lap the status became active (inclusive)")
    end_lap: int   = Field(ge=1, description="Last lap the status was active (inclusive)")
```

`Race` gains two fields (both default empty so older behaviour is
preserved when source files are missing):

```python
race_status_bands:   list[StatusBand] = Field(default_factory=list)
sprint_status_bands: list[StatusBand] = Field(default_factory=list)
```

`AllClear` (`"1"`) is not materialised as a band — it's the implicit
background. `VSCEnding` (`"7"`) closes an active `VSCDeployed` band
rather than opening a new one.

Manifest `schema_version` bumps from `"1.0.0"` to `"1.1.0"`: the change
is additive and fully backwards-compatible (old manifests lack the
fields; Zod treats them as empty).

## 7. Precompute pipeline

**New module `precompute/src/f1/track_status.py`** with three pure
functions:

```python
def collect_status_transitions(events: Iterable[Event]) -> list[tuple[int, str]]:
    """Return (timestamp_ms, status_code) for every TrackStatus event,
    including AllClear (needed as a band-closer). Skips malformed payloads."""

def collect_lap_boundaries(events: Iterable[Event]) -> list[tuple[int, int]]:
    """Return (timestamp_ms, current_lap) from LapCount. Seeded with (0, 1)
    if the first event's lap > 1 or missing — ensures lap 1 can always be
    resolved."""

def build_status_bands(
    transitions: list[tuple[int, str]],
    lap_boundaries: list[tuple[int, int]],
    total_laps: int,
) -> list[StatusBand]:
    """Walk transitions in order; open a band on non-green codes, close on
    AllClear, on VSCEnding (for VSCDeployed only), or at session end.
    For each band, map its timestamps to the lap number that was current
    at that moment via lap_boundaries. Clamp end_lap to total_laps."""
```

**`build.py` changes.** Add a helper `_parse_only(session_dir, filename) →
list[Event]` that calls `parse_stream` without the reducer (we need
transitions, not terminal state). For each session where `key in {"R", "S"}`:

```python
ts_events = _parse_only(sess_dir, "TrackStatus.jsonStream")
lc_events = _parse_only(sess_dir, "LapCount.jsonStream")
bands = build_status_bands(
    collect_status_transitions(ts_events),
    collect_lap_boundaries(lc_events),
    total_laps=max_end_lap_for_session,
)
if key == "R": race_status_bands = bands
if key == "S": sprint_status_bands = bands
```

`max_end_lap_for_session` is derived the same way `Strategy.tsx`
derives `totalLaps` — `max(end_lap for stint in session)` — computed
once per session from `stints_by_session[key]`.

**Fetch-list change.** `MANIFEST_FILES` in `seasons/fetch_race.py`
gains two entries:

```python
"TrackStatus.jsonStream",
"LapCount.jsonStream",
```

Idempotent; per-session download grows by ≈5 KB (TrackStatus is ~5
events, LapCount is ~60 events for a race).

## 8. Site rendering

`StrategyChart` gains a `statusBands: StatusBand[]` prop (required;
empty array means overlay is off). Rendering layers, back to front,
inside the existing `<svg>`:

1. **Background bands** — one `<rect>` per band spanning
   `y = PAD.top` to `y = PAD.top + rows.length * ROW_H`, fill via
   `fill="url(#yellowHatchLow)"` / `fill="#f97316" fill-opacity="0.14"`
   / etc. These live *before* the existing `rows.map` so stint bars
   paint on top.
2. **Existing stint bars** — unchanged.
3. **Top strip** — 6px `<rect>` strip above `rows[0]`. Default green
   `AllClear` underlay across the full chart width, then per-band
   overlay rects with full opacity (for Yellow hatch is `yellowHatch`
   at ≈0.55 saturation; SC/VSC solid orange; Red hatch).
4. **Tooltip layer** — existing `TooltipWithBounds`, now rendering
   one of two payload shapes depending on `kind`.

```ts
type TooltipPayload =
  | { kind: "stint";  /* existing fields */ }
  | { kind: "status"; status: TrackStatusCode; startLap: number; endLap: number; laps: number };
```

`onMouseMove` on each band/strip rect calls `showTooltip({ kind: "status", ... })`.
The tooltip renderer switches on `kind`.

**Status-code → display-label mapping** (used in the tooltip and the
Playwright regex):

| Enum code      | Display label          |
|----------------|------------------------|
| `Yellow`       | `Yellow`               |
| `SCDeployed`   | `Safety Car`           |
| `VSCDeployed`  | `Virtual Safety Car`   |
| `Red`          | `Red Flag`             |

The mapping lives in one place (`const STATUS_LABEL` near the top of
`StrategyChart.tsx`), consumed by both tooltip rendering and — if
ever needed — a band-internal label.

**Pattern defs.** One `<defs>` block at the top of the SVG with
`yellowHatch`, `yellowHatchLow`, `redHatch`, `redHatchLow`
patterns. Scoped to the chart SVG, no global stylesheet changes.

**`Strategy.tsx` change.** One line:

```tsx
<StrategyChart
  drivers={drivers}
  sessionKey={active}
  totalLaps={totalLaps}
  statusBands={active === "R" ? manifest.race.race_status_bands : manifest.race.sprint_status_bands}
/>
```

## 9. Edge cases

- **Status active at session start** (Japan 2026 race opens under
  Yellow) → `start_lap = 1`.
- **Status still active at session end** → `end_lap = total_laps`.
- **Status transitions between lap boundaries** → resolved to the
  lap that was current at the transition timestamp (the lap the
  leader was running). `end_lap` is the last lap the status was still
  active, inclusive.
- **Source files missing** (race not yet run, archive unavailable) →
  both collector functions return `[]`, `build_status_bands` returns
  `[]`, manifest keeps the defaults. Chart renders as it does today.
- **`VSCEnding` without prior `VSCDeployed`** → no band opens or
  closes; treated as a no-op.
- **Duplicate consecutive codes** (`Yellow` → `Yellow`) → the second
  is ignored; doesn't split the band.
- **No Sprint session in weekend** → `sprint_status_bands = []`.
- **`LapCount` absent but `TrackStatus` present** → we cannot map
  timestamps to laps; `build_status_bands` returns `[]` and `build.py`
  prints a warning line to `stderr` (matching the existing
  `print(..., file=sys.stderr)` pattern in `_build_one`). Rare failure
  mode worth surfacing in CI output.

## 10. Testing

**Python (`precompute/tests/test_track_status.py`).**

- `collect_status_transitions`: filters malformed events, passes
  through all five codes.
- `collect_lap_boundaries`: seeds `(0, 1)` when first event is lap 2
  or later; preserves order.
- `build_status_bands`:
  - Standard cycle: Yellow → AllClear → SC → AllClear yields 2
    bands with correct laps.
  - Status-at-start: first event is Yellow at t=0, lap=1 → band
    `start_lap = 1`.
  - Status-at-end: SC still active at session close → band
    `end_lap = total_laps`.
  - VSCEnding closes only VSCDeployed; stray VSCEnding is no-op.
  - Red flag band with full hatch path exercised.

- Integration: `test_build_manifest_japan_race` (existing pattern)
  gains assertions on `race_status_bands` — expected sequence
  Yellow (1..x), SC (m..n) — values derived from actual archive data
  and pinned in the test.

- Coverage gate remains **≥85%**.

**Site vitest (`site/src/components/StrategyChart.test.tsx`).**

- Empty `statusBands` → no SVG element matches `data-testid="status-band"`
  or `data-testid="status-strip-segment"`.
- Non-empty `statusBands` → one `status-band` + one
  `status-strip-segment` per band, with `data-status` attribute set.
- Hover on a band dispatches `onMouseMove` with `kind: "status"` — verify
  via mock / tooltip render.

**Playwright E2E (`site/tests/e2e/strategy.spec.ts`).**

- Navigate to `/race/japan-2026/strategy`. Expect at least one
  element matching `[data-testid="status-strip-segment"]`.
- Hover a strip segment, expect tooltip text matching
  `/^(Yellow|Safety Car|Virtual Safety Car|Red Flag) · lap \d+–\d+/`.

## 11. Risks and mitigations

- **Colour clash with MEDIUM/SOFT compounds.** Mitigated by hatch
  patterns for Yellow and Red. Verified at mockup stage (see
  `.superpowers/brainstorm/.../visual-style.html`).
- **Lap-mapping off-by-one at lap-boundary transitions.** Anchoring
  on `LapCount.CurrentLap` resolves the ambiguity: `CurrentLap`
  updates when the leader *completes* the lap, so a status transition
  at `CurrentLap = N` belongs to lap N, not N+1. Covered by unit tests.
- **VSC/Red visuals untested against real data.** Unit fixtures
  cover the code paths, but visual QA only lands when a 2026 race
  actually produces these states. Acceptable for now; revisit if the
  visuals look off on first real occurrence.
- **Manifest size growth.** `StatusBand` is trivially small (~30
  bytes per entry). Worst-case 10 bands × 30 bytes × 2 sessions = 600
  bytes per manifest. Negligible.
- **CI fetch growth.** Two more small files × 5 sessions × 3 races =
  30 extra HTTP calls. Still well under the `fetch_race.py` MAX_WORKERS
  ceiling, ~100 KB total.

## 12. Rollout

1. Merge fetch/precompute changes first (behind empty default field
   on manifest); CI and the site stay green because the field
   defaults to `[]`.
2. Land site rendering next; Zod regen picks up the new field.
3. E2E lands with the second PR so the assertion has data to match.

All one branch if preferred — no feature-flag needed because the
overlay is silent when bands are empty.

## 13. Open questions

None blocking. The following were resolved during brainstorming and
recorded here for traceability:

- Visual style: **Option C** (low-opacity full-height bands + bright
  top strip).
- Session scope: **Race + Sprint**, all three featured races.
- Lap mapping: **fetch `LapCount.jsonStream`** (Approach 2 in the
  brainstorm) rather than derive leader laps from `TimingData`.
- Status bands placement on model: **flat on `Race`** (mirrors
  `race_stints` / `sprint_stints` pattern), not on `SessionRef`.
- Tooltip architecture: **single `useTooltip` with discriminated
  union payload** (`kind: "stint" | "status"`).
