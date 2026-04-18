"""Fetch the minimum per-session files needed to build each featured race's manifest.

Intended for CI (and for contributors who don't want the full multi-GB
archive): pulls just the four small files the precompute pipeline reads,
for every session in a given race weekend, directly from F1's live-timing
archive.

Defaults match ``precompute/src/f1/build.py``'s FEATURED_RACES. When we
change the featured lineup, keep both in sync.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from download_f1 import BASE_URL, ROOT, fetch, save

# The files precompute.build reads. Everything else (CarData, Position,
# Heartbeat, etc.) is ignored to keep CI fetches under a few MB.
MANIFEST_FILES: list[str] = [
    "SessionInfo.json",
    "DriverList.jsonStream",
    "TyreStintSeries.jsonStream",
    "TimingAppData.jsonStream",
    "TimingData.jsonStream",
]


@dataclass(frozen=True)
class FeaturedRace:
    race_dir: str
    sessions: tuple[str, ...]


FEATURED_RACES: tuple[FeaturedRace, ...] = (
    FeaturedRace(
        race_dir="2026/2026-03-08_Australian_Grand_Prix",
        sessions=(
            "2026-03-06_Practice_1",
            "2026-03-06_Practice_2",
            "2026-03-07_Practice_3",
            "2026-03-07_Qualifying",
            "2026-03-08_Race",
        ),
    ),
    FeaturedRace(
        race_dir="2026/2026-03-15_Chinese_Grand_Prix",
        sessions=(
            "2026-03-13_Practice_1",
            "2026-03-13_Sprint_Qualifying",
            "2026-03-14_Sprint",
            "2026-03-14_Qualifying",
            "2026-03-15_Race",
        ),
    ),
    FeaturedRace(
        race_dir="2026/2026-03-29_Japanese_Grand_Prix",
        sessions=(
            "2026-03-27_Practice_1",
            "2026-03-27_Practice_2",
            "2026-03-28_Practice_3",
            "2026-03-28_Qualifying",
            "2026-03-29_Race",
        ),
    ),
)

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
        default=None,
        help="Meeting directory. If omitted, fetches every race in FEATURED_RACES.",
    )
    parser.add_argument(
        "--sessions",
        nargs="+",
        default=None,
        help="Session directory names under --race-dir. Required when --race-dir is set.",
    )
    parser.add_argument(
        "--files",
        nargs="+",
        default=MANIFEST_FILES,
        help=f"Files to fetch per session (default: {MANIFEST_FILES})",
    )
    args = parser.parse_args()

    if args.race_dir:
        if not args.sessions:
            parser.error("--sessions is required when --race-dir is given")
        races: tuple[FeaturedRace, ...] = (
            FeaturedRace(race_dir=args.race_dir, sessions=tuple(args.sessions)),
        )
    else:
        races = FEATURED_RACES

    totals: dict[str, int] = {"ok": 0, "cached": 0, "missing": 0, "skip": 0}
    for race in races:
        print(
            f"Fetching {race.race_dir}: "
            f"{len(race.sessions)} sessions × {len(args.files)} files"
        )
        for session in race.sessions:
            session_path = f"{race.race_dir.rstrip('/')}/{session}"
            counts = fetch_session(session_path, args.files)
            for k, v in counts.items():
                totals[k] += v
            print(f"  {session}: {counts}")

    print(f"\nTotals: {totals}")
    if totals["missing"]:
        print(f"warning: {totals['missing']} file(s) returned 404/403", end="")
        print(" — the race(s) may not yet have run or the archive may be unavailable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
