# seasons/

Local mirror of Formula 1's public live-timing archive plus the download/verification scripts.

```
seasons/
├── download_f1.py    # full-archive downloader (one-time or per-season)
├── fetch_race.py     # minimal fetch for the currently-featured race (CI + fresh clones)
├── verify_f1.py      # per-file verification + coverage report
├── 2018/ … 2026/     # gitignored — regenerated on demand
```

## Nothing here is checked into git

All race data is gitignored (`.gitignore:/seasons/20??/`). That keeps the repo lean — the full multi-GB archive stays on whoever downloads it, and CI pulls just what it needs on every run.

`fetch_race.py` fetches **only the four files `precompute` reads**, for every session in the currently-featured race weekend (Australia 2026). In total that's ~20 files, a few MB. It's idempotent — files already on disk are skipped.

```bash
cd seasons
uv run python fetch_race.py                     # defaults: Australia 2026
uv run python fetch_race.py --race-dir 2024/2024-06-09_Canadian_Grand_Prix --sessions 2024-06-07_Practice_1 2024-06-09_Race
```

You normally don't need to invoke this yourself — `make build` / `make dev` / `make test-e2e` all depend on the `fetch-race` make target.

## Downloading a full season (optional)

If you want everything — telemetry, weather, race-control messages, you name it:

```bash
cd seasons
uv run python download_f1.py 2024 2025          # specific seasons
uv run python download_f1.py                    # all seasons 2018–2026 (except 2022)
```

Expect several GB of `.jsonStream` files per season. Idempotent and resumable. The F1 archive returns 403 for seasons 2022 and pre-2018.

## Verifying

```bash
uv run python verify_f1.py
```

Walks every session on disk, probes for missing files, retries transient errors, and writes `coverage.json` with a `{session: {file: status}}` matrix. Statuses: `ok`, `fetched`, `absent`, `error`.

## Switching the featured race

The default race is configured in two places that must stay in sync:

- `seasons/fetch_race.py` — `DEFAULT_RACE_DIR` + `DEFAULT_SESSIONS`
- `precompute/src/f1/build.py` — `--race-dir` / `--season` / `--round` / `--slug` defaults

Update both, drop a new `<slug>.json` filename in `Makefile` (`cp precompute/out/<slug>.json site/public/data/`), and adjust the site routes that load the manifest.

See [`../docs/data-pipeline.md`](../docs/data-pipeline.md) for the downstream pipeline.
