# precompute/

Python 3.13 pipeline that turns F1 live-timing `.jsonStream` files into a single validated JSON manifest per race weekend.

## Layout

```
precompute/
├── src/f1/
│   ├── parse.py        # .jsonStream → typed events
│   ├── reduce.py       # events → per-driver state
│   ├── inventory.py    # tyre set reconstruction
│   ├── driver_meta.py  # driver identity
│   ├── models.py       # Pydantic schema
│   ├── build.py        # orchestrator + CLI entry point
│   └── schema.py       # JSON Schema export (for site's Zod)
├── tests/              # pytest (44 tests, ≥ 85% coverage required)
├── fixtures/           # mini-race fixtures for tests
├── out/                # generated manifests (gitignored)
└── pyproject.toml
```

## Commands

```bash
uv sync --extra dev            # install deps (incl. pytest, mypy, ruff)
uv run python -m f1.build      # build the default race manifest → out/australia-2026.json
uv run pytest                  # tests + coverage gate
uv run ruff check .            # lint
uv run mypy src                # strict type-check
```

A console script is registered as `f1-build`:

```bash
uv run f1-build --race-dir 2024/2024-06-09_Canadian_Grand_Prix --season 2024 --round 9 --slug canada-2024 --out out/canada-2024.json
```

## CLI options

| Flag | Default | Notes |
|------|---------|-------|
| `--data-root` | `<repo>/seasons` | Root containing `<year>/<meeting>/<session>/` |
| `--race-dir` | `2026/2026-03-08_Australian_Grand_Prix` | Relative to `--data-root` |
| `--season` | `2026` | |
| `--round` | `1` | |
| `--slug` | `australia-2026` | Used in manifest and output filename |
| `--out` | `out/australia-2026.json` | Where to write the manifest |

## Output schema

See [`../docs/data-pipeline.md`](../docs/data-pipeline.md) for the full shape. In short: `{schema_version, generated_at, race: {meta…, sessions[], drivers: [{…, sets: […]}]}}`.

The same schema is exported as JSON Schema (`uv run python -m f1.schema`) so the site can validate manifests with Zod.

## Design notes

- **Stateless stages.** Each module exposes pure functions; nothing touches the filesystem outside `build.py`. Makes testing straightforward.
- **Pydantic-first.** The canonical source of truth for the manifest shape is `models.py`. JSON Schema and Zod are derived from it.
- **Coverage gate.** `pyproject.toml` fails `pytest` if coverage drops below 85%.
