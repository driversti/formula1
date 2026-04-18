# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project shape

Three-stage static pipeline for the Formula 1 Dashboard. Each stage lives in its own top-level directory and is orchestrated by the root `Makefile`:

```
seasons/      →   precompute/         →   site/
raw mirror        Python 3.13 pipeline    React 19 + Vite + Tailwind
(gitignored)      (Pydantic-validated)    (Zod-validated at runtime)
```

- **`seasons/`** — mirror of `livetiming.formula1.com/static/`. `seasons/20xx/` is gitignored. CI and fresh clones only fetch the metadata for the **currently-featured race** via `seasons/fetch_race.py`.
- **`precompute/`** (package `f1-precompute`) — streams `.jsonStream` files into typed events, reduces to per-driver state, derives tyre inventory, and emits one JSON manifest per weekend to `precompute/out/`. Pipeline stages live in `src/f1/`: `parse.py` → `reduce.py` → `inventory.py` → `build.py`. The schema is exported via `f1.schema`.
- **`site/`** — loads `public/data/<race>.json` at runtime and renders Home (driver grid) and Driver detail views with `@visx` charts. No backend.

## Currently-featured race(s)

`australia-2026` and `china-2026` are the two races currently built end-to-end. When adding, removing, or swapping a featured race, update all four sync points in lockstep — they drive fetch, build, packaging, and UI independently:

- `seasons/fetch_race.py` — `FEATURED_RACES`
- `precompute/src/f1/build.py` — `FEATURED_RACES`
- `Makefile` — `FEATURED_SLUGS`
- `site/src/config.ts` — `FEATURED_RACE_SLUGS`

Sprint weekends use `SessionKey` values `SQ` (Sprint Qualifying) and `S` (Sprint). Regular weekends use `FP1/FP2/FP3/Q/R`.

## Pydantic ↔ Zod sync

The Python manifest model is the source of truth. Zod schemas on the site are generated from it via JSON Schema:

```
precompute (Pydantic) ──f1.schema──▶ JSON Schema ──npm run gen:zod──▶ site/src (Zod)
```

If you change a Pydantic model in `precompute/src/f1/models.py`, run `make genzod` (or `make build`) before touching the site, otherwise the site's runtime validation will drift.

## Commands

Run everything from the repo root.

| Command | What it does |
|---|---|
| `make install` | `uv sync --extra dev` in `precompute/` + `npm ci` in `site/` |
| `make dev` | Fetch → precompute → genzod → copy manifest → `vite` dev server on :5173 |
| `make build` | Full production build → `site/dist/` (what CI runs) |
| `make precompute` | Just rebuild the race manifest |
| `make fetch-race` | Pull the 4 metadata files for the featured race (idempotent) |
| `make genzod` | Regenerate Zod schemas from Pydantic JSON Schema |
| `make test` | Python + site unit + Playwright E2E |
| `make test-py` | `pytest` in `precompute/` (coverage gate: **85%**, set in `pyproject.toml`) |
| `make test-site` | `vitest run` in `site/` |
| `make test-e2e` | Playwright (stages manifest automatically; one-time: `npx playwright install --with-deps chromium`) |
| `make clean` | Remove `precompute/out/`, `site/dist/`, staged manifests, caches |

### Sub-project commands

```bash
# precompute
cd precompute
uv run pytest tests/test_parse.py::test_name   # single test
uv run ruff check .
uv run mypy src                                # strict

# site
cd site
npm run test:watch
npx playwright test tests/e2e/home.spec.ts     # single E2E file
```

### Downloading full seasons (rare)

```bash
cd seasons && uv run python download_f1.py 2024   # years 2018–2026 except 2022; multi-GB
```

## Conventions

- **Python**: 3.13, strict `mypy`, `ruff`. Type annotations required on public APIs. Docstrings explain *why*, not *what*.
- **TypeScript**: strict mode. Functional components + hooks. Keep components focused (see `DriverCard`, `UsageBar`).
- **Tests**: any behaviour change needs a test. Don't drop below the 85% Python coverage gate.
- **Manifest-format changes** almost always require touching both Pydantic (`precompute/`) and regenerating Zod (`site/`).

## Deploy

GitHub Actions (`.github/workflows/deploy.yml`) runs `make build` on push to `main` and publishes `site/dist/` to GitHub Pages. A local `make deploy-local` target exists but requires explicit opt-in.
