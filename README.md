# F1 Tyre Inventory

Pre-race visualisation of each driver's **available tyre sets** for an upcoming Formula 1 Grand Prix. The dashboard reads Formula 1's public live-timing archive, reconstructs per-set stint histories across the race weekend's practice and qualifying sessions, and shows — for each driver — which compounds are still fresh, which are scrubbed, and how many laps each set has already seen.

🏁 **Live site:** [driversti.github.io/formula1](https://driversti.github.io/formula1/)

[![Deploy](https://github.com/driversti/formula1/actions/workflows/deploy.yml/badge.svg)](https://github.com/driversti/formula1/actions/workflows/deploy.yml)
[![CI](https://github.com/driversti/formula1/actions/workflows/ci.yml/badge.svg)](https://github.com/driversti/formula1/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

## What this repo contains

- **`seasons/`** — a local mirror of F1's public live-timing archive (`livetiming.formula1.com/static/`). Download scripts for seasons 2018–2026. Only the small metadata files needed to build the current race page are checked in; everything else is regenerable.
- **`precompute/`** — a Python 3.13 pipeline (Pydantic + pytest) that parses the raw `.jsonStream` files and emits a single validated JSON manifest per race.
- **`site/`** — a React 19 + TypeScript + Vite + Tailwind frontend that consumes the manifest and renders the dashboard. Charts use `@visx`. E2E tests with Playwright.

See [`docs/architecture.md`](./docs/architecture.md) for a deeper overview and [`docs/data-pipeline.md`](./docs/data-pipeline.md) for the data flow.

## Quick start

Prereqs: Python 3.13+ with [`uv`](https://docs.astral.sh/uv/), Node.js 22+, GNU Make.

```bash
# one-time setup
make install

# regenerate the committed race manifest and start the dev server
make dev
# → http://localhost:5173
```

Build for production (same as CI):

```bash
make build
```

Run the full test suite (Python + site unit + Playwright E2E):

```bash
make test
```

## Repo layout

```
formula1/
├── seasons/           # mirrored F1 live-timing archive + download scripts
│   ├── download_f1.py
│   ├── verify_f1.py
│   └── 2018…2026/
├── precompute/        # Python pipeline: raw .jsonStream → race manifest
│   ├── src/f1/
│   ├── tests/
│   └── fixtures/
├── site/              # React + Vite dashboard
│   ├── src/
│   ├── tests/
│   └── public/
├── docs/              # architecture, data pipeline, dev guide
├── Makefile           # top-level orchestration
└── .github/workflows/ # CI + Pages deploy
```

## Contributing

Issues and PRs are welcome! Before opening a PR:

1. Run `make test` locally.
2. Keep changes focused — smaller PRs are easier to review.
3. The race manifest format is validated by Pydantic in `precompute/` and mirrored by Zod in `site/` — changes to one usually require the other.

See [`docs/development.md`](./docs/development.md) for local setup details.

## Data & credits

Race data comes from Formula 1's publicly accessible live-timing archive at `livetiming.formula1.com/static/`. F1, FORMULA 1, and related marks are trademarks of Formula One Licensing BV — this project is not affiliated with, endorsed by, or associated with Formula 1.

## License

[MIT](./LICENSE) © Yurii Chekhotskyi
