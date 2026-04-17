# Data pipeline

How a Grand Prix weekend's raw live-timing files become the JSON the site renders.

## Sources

Formula 1 publishes per-session live-timing data at:

```
https://livetiming.formula1.com/static/<year>/<meeting>/<session>/<file>
```

Each session directory contains ~27 files — small JSON (metadata, driver list, session info) plus `.jsonStream` files, which are **newline-delimited event streams** prefixed with a monotonically-increasing timestamp. Some files are compressed (`.z.jsonStream`). Seasons 2022 and pre-2018 return 403 at the time of writing.

## Step 1 — Mirror (`seasons/download_f1.py`)

```bash
cd seasons
uv run python download_f1.py 2024 2025    # or: python download_f1.py (all seasons)
```

- Fetches each season's `Index.json` to enumerate meetings and sessions.
- For every session, tries all 27 known files in parallel (12 workers).
- 404/403 treated as "not captured that season" — not fatal.
- Files already on disk are skipped, so the script is safely resumable.
- A few 2018/2024 meetings are missing from `Index.json` but exist on disk; these are listed in `SUPPLEMENTAL_MEETINGS`.

After a full run you'll have tens of gigabytes of raw archive under `seasons/<year>/`. **Nothing under `seasons/20xx/` is checked into git.** CI and fresh clones call `seasons/fetch_race.py` (via `make fetch-race`) to pull just the four files per session the precompute pipeline needs for the currently-featured race — a few MB total.

## Step 2 — Verify (`seasons/verify_f1.py`)

```bash
cd seasons
uv run python verify_f1.py
```

Walks every session directory, probes each expected file, retries transient failures, and writes `coverage.json` with a `{file: status}` matrix (`ok`, `fetched`, `absent`, `error`). Useful as a "what did we actually end up with" report.

## Step 3 — Precompute (`precompute/src/f1/build.py`)

```bash
cd precompute
uv run python -m f1.build                 # defaults: Australia 2026
# or specify a race:
uv run python -m f1.build \
  --data-root ../seasons \
  --race-dir  2024/2024-06-09_Canadian_Grand_Prix \
  --season 2024 --round 9 --slug canada-2024 \
  --out out/canada-2024.json
```

Pipeline (each step is a pure function; see module-level docstrings):

1. **`parse.py`** — decodes `.jsonStream` files into typed events. Handles the timestamp prefix and stream quirks (duplicate keys, out-of-order updates).
2. **`reduce.py`** — walks the event stream and folds it into terminal per-driver state (current tyre set, lap count, etc.).
3. **`inventory.py`** — derives each driver's **available tyre sets** across the weekend from `TyreStintSeries` + `TimingAppData`: compound, lap count, first-seen session.
4. **`driver_meta.py`** — pulls driver identity (TLA, team, number) from `DriverList`.
5. **`build.py`** — composes everything into a `Manifest` Pydantic model and writes JSON.

## Output — the race manifest

```json
{
  "schema_version": 1,
  "generated_at": "2026-04-17T14:00:00Z",
  "race": {
    "slug": "australia-2026",
    "season": 2026,
    "round": 1,
    "name": "Australian Grand Prix",
    "location": "Melbourne",
    "country": "Australia",
    "date": "2026-03-08",
    "sessions": [
      { "key": "P1", "name": "Practice 1", "path": "2026/…/2026-03-06_Practice_1/", "start_utc": "…" }
    ],
    "drivers": [
      {
        "tla": "VER",
        "name": "Max Verstappen",
        "team": "Red Bull Racing",
        "number": 1,
        "grid_position": 3,
        "sets": [
          { "set_id": "…", "compound": "SOFT", "laps": 4, "first_seen_session": "FP2" }
        ]
      }
    ]
  }
}
```

The schema is validated by Pydantic on write (`precompute/src/f1/models.py`) and by Zod on read (`site/src/lib/schemas.ts`, generated from JSON Schema via `npm run gen:zod`).

## Fixtures

`precompute/fixtures/mini-race/` contains trimmed `.jsonStream` extracts (10–20 events per file, 2–3 drivers) used by `pytest`. Small enough to commit; large enough to exercise the full pipeline.

## Adding a new race

1. Mirror the weekend's sessions: `cd seasons && uv run python download_f1.py <year>`.
2. Confirm the metadata files are present: `uv run python verify_f1.py`.
3. Build its manifest: `cd ../precompute && uv run python -m f1.build --race-dir <year>/<meeting> --season <year> --round <n> --slug <slug> --out out/<slug>.json`.
4. Wire it into the site (currently hard-coded to `australia-2026.json` in `site/src/routes/Home.tsx`).
