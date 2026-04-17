"""Fetch the minimum per-session files needed to build one race's manifest.

Intended for CI (and for contributors who don't want the full multi-GB
archive): pulls just the four small files the precompute pipeline reads,
for every session in a given race weekend, directly from F1's live-timing
archive.

Defaults match ``precompute/src/f1/build.py`` — Australia 2026. When we
switch the featured race, update both default sets together.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from download_f1 import BASE_URL, ROOT, fetch, save

# The files precompute.build reads. Everything else (CarData, Position,
# Heartbeat, etc.) is ignored to keep CI fetches under a few MB.
MANIFEST_FILES: list[str] = [
    "SessionInfo.json",
    "DriverList.jsonStream",
    "TyreStintSeries.jsonStream",
    "TimingAppData.jsonStream",
]

DEFAULT_RACE_DIR = "2026/2026-03-08_Australian_Grand_Prix"
DEFAULT_SESSIONS: list[str] = [
    "2026-03-06_Practice_1",
    "2026-03-06_Practice_2",
    "2026-03-07_Practice_3",
    "2026-03-07_Qualifying",
    "2026-03-08_Race",
]

MAX_WORKERS = 8


def fetch_one(session_path: str, fname: str) -> str:
    """Fetch one file into the mirror. Returns a short status token."""
    dest = (ROOT / session_path / fname).resolve()
    if not dest.is_relative_to(ROOT):
        return "skip"
    if dest.exists() and dest.stat().st_size > 0:
        return "cached"
    data = fetch(f"{BASE_URL}/{session_path.rstrip('/')}/{fname}")
    if data is None:
        return "missing"
    save(dest, data)
    return "ok"


def fetch_session(session_path: str, filenames: list[str]) -> dict[str, int]:
    local_dir = (ROOT / session_path.rstrip("/")).resolve()
    if not local_dir.is_relative_to(ROOT):
        raise ValueError(f"path escapes mirror root: {session_path}")
    local_dir.mkdir(parents=True, exist_ok=True)

    counts: dict[str, int] = {"ok": 0, "cached": 0, "missing": 0, "skip": 0}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(fetch_one, session_path, f): f for f in filenames}
        for fut in as_completed(futures):
            counts[fut.result()] += 1
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--race-dir",
        default=DEFAULT_RACE_DIR,
        help=f"Meeting directory (default: {DEFAULT_RACE_DIR})",
    )
    parser.add_argument(
        "--sessions",
        nargs="+",
        default=DEFAULT_SESSIONS,
        help="Session directory names under --race-dir",
    )
    parser.add_argument(
        "--files",
        nargs="+",
        default=MANIFEST_FILES,
        help=f"Files to fetch per session (default: {MANIFEST_FILES})",
    )
    args = parser.parse_args()

    print(f"Fetching {args.race_dir}: {len(args.sessions)} sessions × {len(args.files)} files")
    totals: dict[str, int] = {"ok": 0, "cached": 0, "missing": 0, "skip": 0}
    for session in args.sessions:
        session_path = f"{args.race_dir.rstrip('/')}/{session}"
        counts = fetch_session(session_path, args.files)
        for k, v in counts.items():
            totals[k] += v
        print(f"  {session}: {counts}")

    print(f"\nTotals: {totals}")
    if totals["missing"]:
        print(f"warning: {totals['missing']} file(s) returned 404/403", end="")
        print(" — the race may not yet have run or the archive may be unavailable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
