# Development guide

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.13+ | See `.python-version` |
| [`uv`](https://docs.astral.sh/uv/) | latest | Python package manager |
| Node.js | 22+ | See `site/package.json` `engines` |
| GNU Make | any | Orchestration |

No database, no backend. Everything builds to static files.

## First-time setup

```bash
git clone https://github.com/driversti/formula1.git
cd formula1
make install
```

`make install` runs `uv sync --extra dev` in `precompute/` and `npm ci` in `site/`.

## Common commands

All commands below are run from the repo root.

| Command | What it does |
|---------|--------------|
| `make dev` | Build manifest, copy to site, start Vite dev server at http://localhost:5173 |
| `make build` | Full production build (manifest + site/dist/) |
| `make test` | Python + site unit + Playwright E2E |
| `make test-py` | Python tests only (pytest, coverage ≥ 85%) |
| `make test-site` | Site unit tests only (vitest) |
| `make test-e2e` | Playwright E2E tests |
| `make precompute` | Rebuild just the race manifest |
| `make schema` | Regenerate JSON Schema (Zod sync) |
| `make genzod` | Regenerate Zod schemas in site/ from JSON Schema |
| `make clean` | Remove generated artefacts |

## Working on the Python pipeline

```bash
cd precompute
uv sync --extra dev
uv run pytest                          # 44 tests, 85% coverage threshold
uv run python -m f1.build              # builds the default (Australia 2026) race
uv run ruff check .                    # lint
uv run mypy src                        # strict type-check
```

## Working on the site

```bash
cd site
npm run dev                            # http://localhost:5173
npm run test:watch                     # vitest in watch mode
npm run test:e2e                       # Playwright (needs `make precompute` first)
```

If you change the Pydantic model, regenerate the Zod schemas:

```bash
make genzod
```

## Downloading more race data

Most contributors don't need to — the committed Australia 2026 metadata is enough for local dev. If you do need other weekends:

```bash
cd seasons
uv run python download_f1.py 2024      # or any year 2018–2026 except 2022
```

This can take a while and will write several GB of `.jsonStream` files under `seasons/<year>/`. Everything except the currently-featured race is gitignored.

## Tests, before opening a PR

```bash
make test
```

CI runs the same thing on every PR — if it's green locally, it should be green on GitHub.

## Code style

- **Python:** Ruff + strict mypy (see `precompute/pyproject.toml`). Type annotations required. Docstrings on public functions explain *why*, not *what*.
- **TypeScript:** strict mode. Prefer functional components, hooks. Keep components focused (see existing `DriverCard`, `UsageBar` for shape).
- **Tests:** any behaviour change needs a test. Python uses pytest; site uses vitest + Testing Library; E2E uses Playwright.

## Troubleshooting

- **`make install` fails on `uv`** → install `uv` first: `curl -LsSf https://astral.sh/uv/install.sh | sh`.
- **Site build fails with "cannot find data/australia-2026.json"** → run `make precompute` first. `make build` does this automatically.
- **Playwright tests hang** → run `npx playwright install --with-deps chromium` once.
- **Python tests fail with coverage < 85%** → that's the gate set in `pyproject.toml`. Add tests for the new code.
