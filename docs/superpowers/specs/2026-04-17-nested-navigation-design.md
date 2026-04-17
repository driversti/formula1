# Nested Navigation: Seasons → Races → Analytics

> "Race" and "Grand Prix" refer to the same entity throughout this spec. `/season/:year` is the list view of a season's races; `/race/:slug` is the landing page for one race.

**Status:** Draft · **Date:** 2026-04-17

## Problem

Today the site's home route (`/`) opens the tyre inventory for the hardwired featured race (`australia-2026`). This conflates "the app" with "one view of one race" and leaves no place to grow additional analytics or historical seasons.

## Goal

Reshape the site into a browsable hierarchy:

```
Seasons (/)  →  Races in a season (/season/:year)  →  Race landing (/race/:slug)  →  Analytics (/race/:slug/tyres, …)
```

Three conceptual levels — seasons, races, analytics. `/season/:year` and `/race/:slug` are the list and detail views of the same "race" entity.

All seasons (2018–2026, excluding 2022 per the repo) and all their races are rendered. Only the currently-featured race (`australia-2026`) is fully enabled end-to-end. Everything else renders as a disabled tile with a **"Coming soon"** label.

## Scope

In scope:

- New routes and views for seasons, races, and a per-race landing page.
- A committed schedule catalog (seasons + races + season metadata) so the site has data to render without relying on the gitignored `seasons/` mirror.
- Move existing driver-grid / tyre-inventory content behind `/race/:slug/tyres`; move the driver detail behind `/race/:slug/driver/:tla`.
- A site-level config module exposing `FEATURED_RACE_SLUG` + `isFeatured(slug)` helper, replacing the string literal currently used in the site layer.

Out of scope:

- Fetching or precomputing additional race manifests. Only `australia-2026.json` is present; other GP landings render disabled.
- Any new analytics beyond the existing tyre inventory (the landing page is structured to accept more tiles later, but we ship with one).
- Changes to the Python pipeline, Pydantic models, or Zod schema generation.
- Refreshing the schedule catalog automatically in CI (a one-shot script suffices; refresh is a manual action).

## Non-goals

- Backfilling champions for seasons where the user has not supplied data.
- Deep-linking into sessions (P1/Quali/Race) — the landing page surfaces the schedule but the analytics tile still targets the existing all-weekend inventory view.

## Architecture

### Routes

| Path | View | Notes |
|---|---|---|
| `/` | `SeasonsView` | Grid of season tiles, 2018–2026 (no 2022). |
| `/season/:year` | `SeasonView` | Grid of race tiles for that year. |
| `/race/:slug` | `RaceLanding` | Race header + metadata + analytics tile grid. Disabled state shows "Coming soon" and no tiles. |
| `/race/:slug/tyres` | `TyresView` (renamed from today's `Home`) | Existing `InventoryView` + `DriverGrid`. |
| `/race/:slug/driver/:tla` | `Driver` | Existing driver detail, parameterised by race. |
| `*` | `NotFound` | Unchanged. |

`App.tsx` gets the new route table. The `basename` handling for the GitHub Pages subpath stays as-is.

### Featured-race gate

`site/src/config.ts` exports:

```ts
export const FEATURED_RACE_SLUG = "australia-2026";
export const isFeatured = (slug: string) => slug === FEATURED_RACE_SLUG;
```

All tile components use `isFeatured(slug)` to decide click behaviour and visual state. This replaces the literal currently embedded in the site layer. The precompute-side default (`precompute/src/f1/build.py`) and `seasons/fetch_race.py` remain the source of truth for *which* race is built, but the site no longer has to know the Python-side details — only the slug.

### Schedule catalog

The `seasons/` mirror is gitignored, and CI only fetches the four per-session files for the featured race. The site therefore cannot read `Index.json` at build or runtime.

We add a committed, static catalog:

- **`site/src/data/schedule.ts`** — TypeScript module exporting a typed array of `Season` records:

  ```ts
  export type Race = {
    slug: string;           // e.g. "australia-2026"
    round: number;          // 1..N within the season; testing rounds excluded
    name: string;           // "Australian Grand Prix"
    countryCode: string;    // ISO alpha-3 or F1 3-letter (AUS, BRN, …)
    countryName: string;
    circuitShortName: string;
    startDate: string;      // ISO date (weekend start)
    endDate: string;        // ISO date (race day)
  };

  export type Season = {
    year: number;
    races: Race[];
    driversChampion: string | null;        // null if unknown / in progress
    constructorsChampion: string | null;
    raceCount: number;                      // len(races); denormalised for tiles
  };

  export const SCHEDULE: Season[] = [ /* 2018..2026 except 2022 */ ];
  ```

- **`scripts/gen-schedule.ts`** (run manually via `npm run gen:schedule`) — reads each local `seasons/<year>/Index.json`, strips pre-season testing, derives `slug` from the GP directory name (`2026-03-08_Australian_Grand_Prix` → `australia-2026`), and writes `schedule.ts`. Champion fields are preserved across regenerations by merging with the existing file (the script never clobbers non-null champion entries it doesn't know about).

- Champions for 2018–2025 are hardcoded in the catalog (user-supplied). 2026 champions stay `null` until the season ends.

Slugging rule: lowercase, country+year with underscores collapsed to hyphens; e.g. `São Paulo` → `sao-paulo-2025`. The precompute-side slug (`australia-2026`) must match; the script's test ensures collision-free mapping.

### Components

New:

- `SeasonsView` — renders a responsive grid of `SeasonTile`s.
- `SeasonTile` — year, race count, drivers' + constructors' champion (or "TBD" when null), subtle hover. Always clickable.
- `SeasonView` — header with year + champions, grid of `RaceTile`s.
- `RaceTile` — round number, GP name, country flag/code, weekend date range. `isFeatured(slug) ? clickable : disabled + "Coming soon" badge`.
- `RaceLanding` — reuses `RaceHeader`, adds a session-schedule panel (from the manifest or catalog) and an `AnalyticsTile` grid. When the race is not featured the tile grid is replaced with a "No analytics available yet" placeholder.
- `AnalyticsTile` — generic tile component; initially one entry: `{ title: "Tyre Inventory", to: "/race/:slug/tyres", icon: … }`.

Renamed / moved:

- `routes/Home.tsx` → `routes/Tyres.tsx` (same body; reads `:slug` from params, loads `/data/<slug>.json`).
- `routes/Driver.tsx` — adjust to read `:slug` from params; manifest path becomes `/data/${slug}.json`.

Unchanged: `DriverCard`, `DriverGrid`, `DriverHeader`, `InventoryView`, `RaceHeader`, `TyreDot`, `TyreSet`, `UsageBar`.

### Data flow

- **Seasons / Races views:** pure render over `SCHEDULE` — no network.
- **Race landing:** reads `SCHEDULE` for metadata + session schedule. If `isFeatured(slug)`, also fetches `/data/<slug>.json` lazily (or links to `/tyres` without prefetching — lazy is simpler and keeps the landing instant).
- **Tyres / Driver views:** unchanged loader, just parameterised by `:slug`.

### Error handling

- Unknown `:year` → `NotFound`.
- Unknown `:slug` in catalog → `NotFound`.
- Known-but-not-featured `:slug` at `/race/:slug/tyres` or `/race/:slug/driver/:tla` → redirect to `/race/:slug` landing (single source of "coming soon" messaging).
- `/data/<slug>.json` fetch failure on the featured race → existing error UI from `Tyres.tsx`.

## Testing

- **Unit (Vitest)**:
  - `isFeatured` returns true only for the configured slug.
  - Schedule catalog invariants: every `race.slug` unique, round numbers contiguous within each season, no testing rounds included.
  - `SeasonTile`, `RaceTile` render disabled state correctly when `isFeatured` is false.
- **E2E (Playwright)**:
  - Home shows 8 season tiles (2018–2026 minus 2022).
  - Navigating `/` → 2026 tile → Australia tile → "Tyre Inventory" tile lands on the existing driver grid, identical to today's home.
  - Clicking a non-featured race tile is a no-op (or: clicking is disabled / cursor not-allowed).
  - `/race/japan-2026` renders the landing with "Coming soon" messaging and no analytics tiles.
- **Python**: unchanged — the precompute pipeline is untouched.
- Coverage gate stays at 85% for Python; site unit tests cover new components.

## Migration

- Any bookmark to `/` still works (new Seasons view).
- Old `/driver/:tla` is removed with no redirect. The project is early and active URL changes are expected; stale bookmarks 404 to `NotFound`.
- `make dev`, `make build` flows are unchanged — `npm run gen:schedule` is manual.

## Open questions

None — champion fields for 2018–2025 to be supplied by the user when populating the catalog (the user has stated the 2025 season is complete and data is available).

## Rollout

Single PR: routing + config + catalog + components + tests. Feature is inert without manifests for additional races, so there's no staged rollout needed.
