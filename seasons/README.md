# seasons/

Local mirror of Formula 1's public live-timing archive plus the download/verification scripts.

```
seasons/
├── download_f1.py   # mirror downloader (run once to populate a season)
├── verify_f1.py     # per-file verification + coverage report
├── 2018/ … 2026/    # one directory per season (mostly gitignored)
```

## What's checked in vs. gitignored

Only the small metadata files required by `make build` in CI are checked in — specifically, for the currently-featured race (**Australia 2026**):

- `SessionInfo.json`
- `DriverList.jsonStream`
- `TyreStintSeries.jsonStream`
- `TimingAppData.jsonStream`

Everything else (heavy telemetry like `CarData.z.jsonStream` and `Position.z.jsonStream`, plus all sessions for other races) is **gitignored**. It's fully regenerable via `download_f1.py`.

## Downloading

```bash
cd seasons
uv run python download_f1.py                  # all seasons 2018–2026 (except 2022)
uv run python download_f1.py 2024 2025        # specific seasons
```

The downloader is idempotent — files present on disk are skipped, so it's safe to interrupt and resume.

Expect several GB of `.jsonStream` files per season. The F1 archive returns 403 for seasons 2022 and pre-2018.

## Verifying

```bash
uv run python verify_f1.py
```

Walks every session on disk, probes for missing files, retries transient errors, and writes `coverage.json` with a `{session: {file: status}}` matrix. Statuses: `ok`, `fetched`, `absent`, `error`.

## Adding a new race to the committed set

The committed exceptions live in [`.gitignore`](../.gitignore). To commit a different race's metadata:

1. Download it: `uv run python download_f1.py <year>`.
2. Edit the `!/seasons/<year>/<meeting>/…` exception block in `.gitignore`.
3. Stage the new files: `git add seasons/<year>/<meeting>/`.

See [`../docs/data-pipeline.md`](../docs/data-pipeline.md) for how the data is consumed downstream.
