# Architecture

High-level overview of how the three sub-projects fit together.

```
┌───────────────────────┐     ┌────────────────────────┐     ┌──────────────────────┐
│  seasons/             │     │  precompute/           │     │  site/               │
│                       │ →   │                        │ →   │                      │
│  Raw F1 live-timing   │     │  Parse + reduce        │     │  React dashboard     │
│  archive mirror       │     │  → race manifest JSON  │     │  (Vite + Tailwind)   │
│  (.jsonStream files)  │     │  (Pydantic-validated)  │     │  (Zod-validated)     │
└───────────────────────┘     └────────────────────────┘     └──────────────────────┘
        ↑                              ↑                              ↓
    download_f1.py                  make build              GitHub Pages (static)
```

## Components

### `seasons/`

A local mirror of [`livetiming.formula1.com/static/`](https://livetiming.formula1.com/static/), organised by year → meeting (Grand Prix weekend) → session (Practice 1/2/3, Qualifying, Sprint, Race).

- **`download_f1.py`** — full-archive downloader. Reads each season's `Index.json`, enumerates meetings and sessions, and fetches the full set of per-session files (timing, positions, driver list, tyre stints, etc.). Idempotent: files present on disk are skipped.
- **`verify_f1.py`** — per-file verification pass. Walks every cached session, confirms each expected file, retries missing ones, and writes `coverage.json`.

Only the small metadata files needed by the pipeline for the currently-featured race are committed; everything else is regenerable.

### `precompute/`

Python 3.13 package (`f1-precompute`) that turns the raw mirror into a single **race manifest** — one JSON file per race weekend, consumed by the site.

Pipeline stages (roughly):

1. **Parse** (`parse.py`) — stream-decode `.jsonStream` files into typed events.
2. **Reduce** (`reduce.py`) — collapse event streams into per-driver state.
3. **Inventory** (`inventory.py`) — derive each driver's available tyre sets across the weekend.
4. **Build** (`build.py`) — assemble the final `Manifest` Pydantic model and serialize it.

The output schema is mirrored to JSON Schema via `f1.schema` for the site's Zod validation.

### `site/`

React 19 + Vite + Tailwind + `@visx` dashboard deployed to GitHub Pages. Loads `data/australia-2026.json` at runtime and renders:

- **Home** — driver grid with tyre inventory at a glance.
- **Driver** — per-driver detail with a `UsageBar` visx chart of per-set lap usage.

Data validation is enforced by Zod schemas auto-generated from the Python-side JSON schema (`npm run gen:zod`).

## Build & deploy flow

```
make build
  ├─ precompute: uv run python -m f1.build
  │   └─ reads  seasons/2026/2026-03-08_Australian_Grand_Prix/
  │   └─ writes precompute/out/australia-2026.json
  ├─ copy manifest → site/public/data/australia-2026.json
  ├─ site: npm run gen:zod  (keeps Zod in sync with JSON Schema)
  └─ site: npm run build    → site/dist/

GitHub Actions .github/workflows/deploy.yml
  push: main
    └─ runs `make build`
    └─ uploads site/dist/ to GitHub Pages
```

## Why this split?

- **Data mirror is separate** so the expensive, slow download step never runs in CI.
- **Precompute is Python** because the raw `.jsonStream` format is quirky; Python's stream-parsing ergonomics and Pydantic validation are a good fit.
- **Site is static** so deployment is trivial (just HTML/JS on Pages) and contributors need no backend to preview changes.

## Further reading

- [`data-pipeline.md`](./data-pipeline.md) — detailed data flow and manifest schema.
- [`development.md`](./development.md) — local setup, commands, testing.
- [`history/`](./history/) — design specs and implementation plans for past features (archival).
