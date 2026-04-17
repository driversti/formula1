# Pre-Race Tyre Inventory Viewer — Design Spec

**Date**: 2026-04-17
**Status**: Approved (pending user review of this document)
**Author**: Yurii Chekhotskyi

## 1. Product Overview

A static website that, for the **Australian Grand Prix 2026**, displays each driver's tyre inventory as it was at the moment the race began. The user lands on a grid of all 22 drivers. Clicking a driver opens a detail page showing every tyre set the driver had available, grouped by compound, with per-set lap counts and a usage timeline across weekend sessions.

This is the first vertical slice of a larger data-visualization platform for Formula 1 live-timing data. Subsequent slices (weather impact on lap times, driver season progression, tyre stint analysis, etc.) will be separate projects that reuse the parsing infrastructure built here.

## 2. Goals and Non-Goals

### In Scope

- One race: Australian Grand Prix 2026 (season opener, 5 sessions: FP1, FP2, FP3, Qualifying, Race)
- 22 drivers, reconstructed from raw `.jsonStream` data already mirrored locally
- Grid view (home page) + Driver detail (separate URL per driver, shareable)
- Dark F1-inspired theme, responsive across mobile / tablet / desktop
- Precomputed JSON artifact served as static site on GitHub Pages
- `Makefile` for local development, GitHub Actions for automatic deploy on push to `main`

### Out of Scope (for this slice)

- Strategy enumeration or "available strategies" generation
- Side-by-side driver comparison
- Additional races or seasons
- Weather, lap-time, telemetry, or positional analysis
- Backend API, database, or any runtime server logic
- Real-time data

### Success Criteria

1. **Accuracy**: For at least 20 of 22 drivers, the reconstructed inventory matches visual verification against F1 TV broadcasts or Pirelli press releases.
2. **Performance**: Lighthouse score ≥ 90 on the home page; driver detail loads in under 1 second on desktop.
3. **Developer experience**: Full data regeneration with one command (`make precompute`); full site build in under 30 seconds.
4. **Deploy**: A working public URL on GitHub Pages, updated automatically on every push to `main`.

### Non-Goals

- Not attempting to reconstruct the complete Pirelli allocation (typically 13 sets per driver). We display only the sets **observed in data**. Sets never used across the entire weekend will not appear. This is a deliberate simplification that avoids hardcoding Pirelli's year-specific allocation rules.

## 3. Architecture

Two independent sub-projects communicate via a JSON contract:

```
RAW DATA (existing)
/2026/2026-03-08_Australian_Grand_Prix/*/TyreStintSeries.jsonStream
         │
         ▼
🐍 PYTHON precompute/   (offline, run once)
   parse.py → reduce.py → inventory.py → build.py
         │
         ▼
📦 JSON ARTIFACT
   precompute/out/australia-2026.json  (Pydantic-validated)
         │
         ▼
⚡ TYPESCRIPT site/    (Vite + React + visx)
   loads JSON, Zod-validates, renders
         │
         ▼
🌐 STATIC SITE → GitHub Pages
```

### Architectural Principles

1. **Boundary via JSON**, not API or database. Python and TypeScript have no knowledge of each other beyond the JSON contract.
2. **Event sourcing reducer** at the parser level. The `.jsonStream` format is a log of patches; a single generic reducer replays them to final state. This is reusable across every file type (`WeatherData`, `RaceControlMessages`, etc.) for future slices.
3. **Static-first**. No runtime server, no database, no API. Everything in `dist/`.
4. **Type safety at both ends**. Pydantic (Python) and Zod (TS) mirror each other; JSON Schema is the single source of truth.

### Project Structure

```
formula1/
├── 2026/                          # Raw data (exists)
├── download_f1.py                 # Mirror script (exists)
├── verify_f1.py                   # Verify script (exists)
├── Makefile                       # NEW: one-command workflow
├── .gitignore                     # NEW: exclude .superpowers/, dist/, out/, node_modules
│
├── precompute/                    # Python package (uv-managed)
│   ├── pyproject.toml
│   ├── src/f1/
│   │   ├── __init__.py
│   │   ├── models.py              # Pydantic: TyreSet, DriverInventory, Race, Manifest
│   │   ├── parse.py               # jsonStream reader
│   │   ├── reduce.py              # event → state reducer
│   │   ├── inventory.py           # tyre set tracking algorithm
│   │   ├── build.py               # CLI entrypoint
│   │   └── schema.py              # exports JSON Schema for TS
│   ├── tests/
│   ├── fixtures/                  # minimal jsonStream samples
│   └── out/
│       ├── australia-2026.json
│       └── schema.json
│
├── site/                          # Vite + React + TS
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── lib/
│   │   │   ├── schemas.ts         # Zod schemas (mirror Pydantic)
│   │   │   └── data.ts            # JSON loader + validator
│   │   ├── routes/
│   │   │   ├── Home.tsx
│   │   │   ├── Driver.tsx
│   │   │   └── NotFound.tsx
│   │   ├── components/
│   │   │   ├── RaceHeader.tsx
│   │   │   ├── DriverGrid.tsx
│   │   │   ├── DriverCard.tsx
│   │   │   ├── TyreDot.tsx
│   │   │   ├── TyreSet.tsx
│   │   │   └── InventoryView.tsx
│   │   └── styles/index.css
│   ├── public/
│   │   ├── data/australia-2026.json  # copied from precompute/out
│   │   └── 404.html                   # SPA fallback for GH Pages
│   └── tests/
│       ├── unit/                   # Vitest
│       └── e2e/                    # Playwright
│
└── .github/workflows/deploy.yml   # precompute → build → Pages
```

### Build Pipeline

**Local**:
```
make install       # setup deps
make dev           # precompute + vite dev server
make test          # pytest + vitest + playwright
make build         # full static build
make deploy        # test + build + push to gh-pages (gh-pages package)
```

**CI/CD** (`.github/workflows/deploy.yml`):
- Trigger: push to `main` or manual dispatch
- Steps: checkout → setup Python+uv+Node → `make install` → `make test` → `make build` → deploy `site/dist` to GitHub Pages via `actions/deploy-pages@v4`

## 4. Data Model

Pydantic models in `precompute/src/f1/models.py`, mirrored by Zod schemas in `site/src/lib/schemas.ts`. JSON Schema exported by Pydantic is the canonical contract.

### TyreSet

One physical set of tyres identified across the weekend.

| Field | Type | Notes |
|-------|------|-------|
| `set_id` | string | Synthetic ID, format: `VER-MED-1`, `LEC-SOFT-3` |
| `compound` | `"SOFT" \| "MEDIUM" \| "HARD" \| "INTERMEDIATE" \| "WET"` | |
| `laps` | int ≥ 0 | Total laps accumulated on this set by end of weekend up to race start |
| `new_at_first_use` | bool | True if `New=true` when first observed |
| `first_seen_session` | string | `"FP1"`, `"FP2"`, `"FP3"`, `"Q"`, `"R"` |
| `last_seen_session` | string | Last session that used this set |

### DriverInventory

| Field | Type | Notes |
|-------|------|-------|
| `racing_number` | string | `"1"`, `"16"`, `"44"` |
| `tla` | string (exactly 3 chars) | `"VER"`, `"LEC"`, `"HAM"` |
| `full_name` | string | |
| `team_name` | string | |
| `team_color` | string (hex `#RRGGBB`) | From `DriverList.jsonStream` → `TeamColour` |
| `grid_position` | int \| null | 1..22 if known (from Qualifying `TimingAppData`), else null |
| `sets` | `list[TyreSet]` | All identified sets for this driver |

### Race

| Field | Type | Notes |
|-------|------|-------|
| `slug` | string | `"australia-2026"` |
| `name` | string | `"Australian Grand Prix"` |
| `location` | string | `"Melbourne"` |
| `country` | string | `"Australia"` |
| `season` | int | `2026` |
| `round` | int | `1` |
| `date` | string (ISO date) | `"2026-03-08"` |
| `sessions` | `list[SessionRef]` | FP1..R with paths and start times |
| `drivers` | `list[DriverInventory]` | 22 entries |

### Manifest (top-level)

| Field | Type | Notes |
|-------|------|-------|
| `schema_version` | string | `"1.0.0"`. Runtime-checked by TS |
| `generated_at` | string (ISO 8601) | Build timestamp |
| `source_commit` | string \| null | Git commit of raw data, if available |
| `race` | `Race` | |

### Data Flow for Schema Sync

```
Pydantic models (Python)
    ↓  model_json_schema()
JSON Schema  (precompute/out/schema.json)
    ↓  json-schema-to-zod (build step in site/)
Zod schemas  (TS auto-generated, committed for reproducibility)
    ↓  z.infer<>
TypeScript types
```

`make build` runs the Pydantic → Schema export, then `npm run build` runs `json-schema-to-zod` before `vite build`. Schema mismatches fail the build.

## 5. Algorithm: Tyre Set Tracking

The parser processes `.jsonStream` files with a generic event-sourcing reducer, then attributes stints to tyre sets by walking sessions chronologically.

### Step 1: Parse `.jsonStream`

Each line has the format `HH:MM:SS.mmm{json-patch}`. The parser strips the UTF-8 BOM, extracts the timestamp offset in milliseconds, and decodes the JSON payload. Malformed lines are logged and skipped.

### Step 2: Reduce Events to Final State

`deep_merge(base, patch)` applies a patch onto base state:
- Objects are merged recursively.
- Lists are replaced wholesale (not merged).
- An `_deleted` key in a patch removes the listed keys from base.
- Scalar values overwrite.

Applying all events in order yields the final state for a session.

This reducer is generic — it works for any `.jsonStream` file in the dataset. Future slices that need `WeatherData.jsonStream`, `TimingData.jsonStream`, etc., reuse it unchanged.

### Step 3: Extract Session-Level Stints Per Driver

For each session's reduced state, read `Stints[driver_number][stint_idx]` and build a list of `SessionStint` records:

```python
@dataclass(frozen=True)
class SessionStint:
    session_key: str        # "FP1", "FP2", "FP3", "Q", "R"
    driver_number: str
    stint_idx: int
    compound: Compound
    new_when_out: bool      # parsed from "New": "true"/"false"
    start_laps: int         # StartLaps
    total_laps: int         # TotalLaps

    @property
    def end_laps(self) -> int:
        return self.start_laps + self.total_laps
```

### Step 4: Match Stints to Tyre Sets Across Sessions

The inventory field `laps` represents the **pre-race state** — each set's lap count as it entered the race. This requires distinct handling for practice/qualifying sessions (where we fully track sets) and the race session (where we only discover saved-for-race sets, without mutating pre-race lap counts).

**Pass A — FP1, FP2, FP3, Q** (full tracking):

For each stint, in order:

- If `compound=UNKNOWN`: skip entirely — transitional pit-stop state.
- If `new_when_out=True`: create a fresh `TyreSet` with `laps=end_laps`.
- If `new_when_out=False`: search existing sets for one with `compound=stint.compound AND laps=stint.start_laps`. If found, update that set's `laps` to `stint.end_laps` and `last_seen_session` to current. If not found, create a new set anyway and log a warning (data inconsistency).

After Pass A, the inventory reflects each driver's state at the end of Qualifying — i.e., exactly what they had going into the race.

**Pass B — Race** (discovery only, no mutation):

For each race stint, in order:

- If `compound=UNKNOWN`: skip.
- If a matching set already exists in the inventory (same `compound AND laps=stint.start_laps`), do nothing — existing pre-race `laps` is preserved. Do not update `last_seen_session` either (the field refers to the last pre-race session).
- If `new_when_out=True` and no match exists: the driver saved this set for the race. Create a fresh `TyreSet` with `laps=0`, `first_seen_session="R"`, `last_seen_session="R"`, `new_at_first_use=True`. The UI will flag this as "saved for race".
- If `new_when_out=False` and no match exists: log a warning (we should have seen this set earlier) and create it with `laps=stint.start_laps` (its state entering the race), `first_seen_session="R"`.

**Why a two-pass approach**: Single-pass would either miss saved-for-race sets (if we stop at Q) or corrupt pre-race `laps` for matched sets (if we process R the same as earlier sessions). The two-pass design keeps the invariant: `TyreSet.laps` always represents state at race start.

### Worked Example

Hypothetical Verstappen at Australia GP 2026:

| Session | Stint | Compound | New | StartLaps | TotalLaps | EndLaps | Match | Known Sets |
|---------|-------|----------|-----|-----------|-----------|---------|-------|------------|
| FP1 | 0 | SOFT | yes | 0 | 8 | 8 | new | `[SOFT-1:8]` |
| FP1 | 1 | MED | yes | 0 | 5 | 5 | new | `[SOFT-1:8, MED-1:5]` |
| FP2 | 0 | SOFT | no | 8 | 2 | 10 | SOFT-1 | `[SOFT-1:10, MED-1:5]` |
| FP2 | 1 | HARD | yes | 0 | 12 | 12 | new | `[..., HARD-1:12]` |
| FP3 | 0 | MED | no | 5 | 3 | 8 | MED-1 | `[..., MED-1:8, ...]` |
| Q | 0,1,2 | SOFT | yes | 0 | 3,2,3 | 3,2,3 | new ×3 (Pass A) | `[..., SOFT-2, SOFT-3, SOFT-4]` |
| R | 0 | MED | yes | 0 | 25 | 25 | no match → new (Pass B): MED-2 saved for race, `laps=0` | `[..., MED-2:0]` |
| R | 1 | HARD | no | 12 | 33 | 45 | matches HARD-1 (Pass B): existing set preserved, no mutation | `[..., HARD-1:12]` |

`TyreSet.laps` always holds pre-race state: HARD-1 stays at 12 (its end-of-FP2 count), MED-2 is flagged as saved-for-race with `laps=0`. The race session contributes only the discovery of MED-2; existing sets are never mutated during Pass B.

### Edge Cases

| Case | Handling |
|------|----------|
| `Compound=UNKNOWN` | Skip the stint entirely |
| Ambiguous match (2 candidate sets with same compound and laps) | Pick first in creation order (deterministic) |
| `start_laps=0 AND new=false` (contradictory) | Log warning, treat as new |
| Driver absent from a session (DNS/injury) | Algorithm skips that session for that driver |
| Set with `laps=0` and `first_seen_session=R` | Flag `saved_for_race=True` in UI |
| Missing/malformed raw file | Log error, continue without that session |

## 6. UI Structure

### Routes

- `/` — Home page, grid of 22 drivers.
- `/driver/:tla` — Detail page for one driver (TLA = 3-letter code).
- `*` — `<NotFound />` with link back home.

**GitHub Pages note**: Client-side routing breaks on direct links to `/driver/VER` because GH Pages returns 404. Solution: `site/public/404.html` copies `index.html`'s bootstrap plus a small script that preserves the intended path before redirecting to the SPA. This keeps clean URLs (no `#` hashes).

### Component Tree

```
App
├── Home ("/")
│   ├── RaceHeader
│   └── DriverGrid
│       └── DriverCard × 22
│           ├── TyreDot × N (mini preview)
│           └── team-color left border (from data)
│
├── Driver ("/driver/:tla")
│   ├── RaceHeader
│   ├── DriverHeader (name, team, grid position)
│   └── InventoryView
│       └── TyreSet × N (grouped by compound: HARD, MEDIUM, SOFT)
│           ├── TyreDot (size="lg")
│           ├── lap counter ("3 laps" / "NEW")
│           ├── history badge ("FP1 → FP3" / "Saved for race")
│           └── UsageBar (visx): horizontal timeline across sessions
│
└── NotFound ("*")
```

### Per-Set Visual Timeline (visx)

Each `TyreSet` includes a small horizontal bar showing usage across sessions. Built from `@visx/scale` (scaleBand for sessions), `@visx/shape` (Bar per stint), `@visx/axis` (bottom axis with FP1/FP2/FP3/Q/R labels), `@visx/group`, `@visx/responsive` (parent-size tracker), `@visx/tooltip` (hover details).

### Styling

**Tailwind 4** with custom tokens in `tailwind.config.ts`:

- `f1-bg` `#0f1419`, `f1-panel` `#1b2330`, `f1-border` `#2a2f3a`, `f1-text` `#e6e6e6`, `f1-muted` `#8a8f99`
- Compound colors: soft `#ff3030`, medium `#ffdd00`, hard `#ffffff`, intermediate `#00b050`, wet `#0099ff`

Team colors are dynamic from JSON (`data.drivers[i].team_color`) applied via inline `style={{ borderLeftColor: ... }}`.

### Responsive Breakpoints

| Viewport | Grid columns |
|----------|--------------|
| < 640 px (mobile) | 2 |
| < 1024 px (tablet) | 3 |
| < 1280 px (laptop) | 4 |
| ≥ 1280 px (desktop) | 6 |

Driver detail: single column on mobile, two-column grid (set cards / metadata) on desktop.

## 7. Error Handling

### Python (precompute)

| Failure | Reaction |
|---------|----------|
| Missing raw data file | Warn, skip session |
| Malformed JSON line | Warn, skip line |
| Driver appears in some sessions but not others | Legal |
| Zero drivers found in any session | **Fail build** (sanity check) |
| Pydantic validation failure | **Fail build** with field-level error |

### TypeScript (runtime)

| Failure | Reaction |
|---------|----------|
| JSON 404 | Global error boundary: "Data not available" |
| Zod validation fails | Error boundary + `console.error` with details |
| TLA not found in `/driver/:tla` | `<NotFound />` with link home |
| Empty inventory for driver | Show "No tyre data available" inline |

## 8. Testing Strategy

### Python (Pytest)

```
precompute/tests/
├── test_parse.py          jsonStream parsing edge cases
├── test_reduce.py         deep_merge, _deleted, list replacement
├── test_inventory.py      tyre tracking algorithm (all edge cases)
└── test_build.py          end-to-end: fixtures → final JSON
```

Coverage target: ≥ 85% on `precompute/src/f1/`. Enforced in CI.

Fixtures in `precompute/fixtures/australia-2026-mini/`: minimal extracts from real `.jsonStream` files (10–20 events per file, 2–3 drivers), sufficient for each test.

### TypeScript (Vitest + Playwright)

```
site/tests/
├── unit/                  Vitest
│   ├── schemas.test.ts    Zod validation against sample JSON
│   ├── TyreDot.test.tsx   renders correct color per compound
│   ├── DriverCard.test.tsx hover, click navigation
│   └── data.test.ts       JSON loading + validation
└── e2e/                   Playwright
    ├── home.spec.ts       22 cards render, click → driver page
    ├── driver.spec.ts     inventory displays, correct lap counts
    └── routing.spec.ts    404, back navigation, deep links
```

Playwright runs against Vite preview (`npm run preview`, port 4173) in CI. Only one top-level snapshot test on Home to catch layout regressions; no component-level snapshots.

## 9. Performance Budget

| Metric | Target | Enforcement |
|--------|--------|-------------|
| Main bundle (gzipped) | < 250 KB | Lighthouse CI |
| LCP (home) | < 1.5 s | Lighthouse CI |
| CLS | < 0.1 | Lighthouse CI |
| JSON payload | < 100 KB | Manual check in CI step |
| `make build` wall time | < 30 s | CI job duration |

Techniques:
- `React.lazy` for `<InventoryView>` and visx imports (only needed on driver pages).
- `<link rel="preload" as="fetch">` for `/data/australia-2026.json` in `index.html`.
- System font stack; `font-mono` for numbers. No external font fetches.

## 10. Open Questions and Future Work

- **Weekend type handling**: Australia 2026 is a regular weekend. The algorithm already supports Sprint weekends (the session order list is configurable), but Sprint-specific tests will be added in the next slice that introduces a Sprint weekend.
- **Incomplete Pirelli allocation reveal**: A driver may end a weekend with sets entirely unused. Those will not appear in our data-derived inventory. A future enhancement could cross-reference a known Pirelli allocation table to mark "unseen but allocated" sets, at the cost of hardcoding per-year rules.
- **2026 C6 compound**: The data still labels tyres as SOFT/MEDIUM/HARD, but Pirelli introduces C6 as an additional soft option at selected races in 2026. For MVP we accept the three canonical labels; mapping to C-numbers can come later.
