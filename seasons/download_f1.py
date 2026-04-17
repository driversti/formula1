"""Mirror the F1 live-timing static archive locally.

Downloads Index.json per season, then for every meeting/session in that
index, probes and saves all known live-timing files. Files already present
on disk are skipped so the script is safely resumable.
"""
from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

BASE_URL = "https://livetiming.formula1.com/static"
ROOT = Path(__file__).parent.resolve()

# Real desktop Chrome UA — the archive returns 403 for bot-like agents.
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

# Seasons 2022 and pre-2018 return 403 at the time of writing.
SEASONS = [2018, 2019, 2020, 2021, 2023, 2024, 2025, 2026]

# Known per-session files. Older seasons / non-race sessions won't have
# every entry; 404s are treated as "missing, move on."
SESSION_FILES = [
    "SessionInfo.json",
    "ArchiveStatus.json",
    "Index.json",
    "SessionData.jsonStream",
    "TimingData.jsonStream",
    "TimingAppData.jsonStream",
    "TimingStats.jsonStream",
    "Position.z.jsonStream",
    "CarData.z.jsonStream",
    "DriverList.jsonStream",
    "WeatherData.jsonStream",
    "TrackStatus.jsonStream",
    "RaceControlMessages.jsonStream",
    "LapCount.jsonStream",
    "LapSeries.jsonStream",
    "ExtrapolatedClock.jsonStream",
    "Heartbeat.jsonStream",
    "TeamRadio.jsonStream",
    "TopThree.jsonStream",
    "TlaRcm.jsonStream",
    "CurrentTyres.jsonStream",
    "TyreStintSeries.jsonStream",
    "ChampionshipPrediction.jsonStream",
    "ContentStreams.jsonStream",
    "AudioStreams.jsonStream",
    "PitLaneTimeCollection.jsonStream",
    "SessionStatus.jsonStream",
]

TIMEOUT = 30
MAX_WORKERS = 12
RETRIES = 3

# Meetings that exist on disk (per-session files are reachable) but are
# absent from the season's Index.json. Discovered by probing:
#  - 2018 round 1 (Index range starts at #2)
#  - 2024 rounds 1-9 (Index range starts at #10)
# Each entry is a meeting folder + its session folder names relative to
# the season root. Sprint weekends in 2024 used Sprint_Qualifying / Sprint.
SUPPLEMENTAL_MEETINGS: dict[int, list[tuple[str, list[str]]]] = {
    2018: [
        ("2018-03-25_Australian_Grand_Prix", [
            "2018-03-23_Practice_1",
            "2018-03-23_Practice_2",
            "2018-03-24_Practice_3",
            "2018-03-24_Qualifying",
            "2018-03-25_Race",
        ]),
    ],
    2024: [
        ("2024-03-02_Bahrain_Grand_Prix", [
            "2024-02-29_Practice_1", "2024-02-29_Practice_2",
            "2024-03-01_Practice_3", "2024-03-01_Qualifying",
            "2024-03-02_Race",
        ]),
        ("2024-03-09_Saudi_Arabian_Grand_Prix", [
            "2024-03-07_Practice_1", "2024-03-07_Practice_2",
            "2024-03-08_Practice_3", "2024-03-08_Qualifying",
            "2024-03-09_Race",
        ]),
        ("2024-03-24_Australian_Grand_Prix", [
            "2024-03-22_Practice_1", "2024-03-22_Practice_2",
            "2024-03-23_Practice_3", "2024-03-23_Qualifying",
            "2024-03-24_Race",
        ]),
        ("2024-04-07_Japanese_Grand_Prix", [
            "2024-04-05_Practice_1", "2024-04-05_Practice_2",
            "2024-04-06_Practice_3", "2024-04-06_Qualifying",
            "2024-04-07_Race",
        ]),
        ("2024-04-21_Chinese_Grand_Prix", [
            "2024-04-19_Practice_1", "2024-04-19_Sprint_Qualifying",
            "2024-04-20_Sprint", "2024-04-20_Qualifying",
            "2024-04-21_Race",
        ]),
        ("2024-05-05_Miami_Grand_Prix", [
            "2024-05-03_Practice_1", "2024-05-03_Sprint_Qualifying",
            "2024-05-04_Sprint", "2024-05-04_Qualifying",
            "2024-05-05_Race",
        ]),
        ("2024-05-19_Emilia_Romagna_Grand_Prix", [
            "2024-05-17_Practice_1", "2024-05-17_Practice_2",
            "2024-05-18_Practice_3", "2024-05-18_Qualifying",
            "2024-05-19_Race",
        ]),
        ("2024-05-26_Monaco_Grand_Prix", [
            "2024-05-24_Practice_1", "2024-05-24_Practice_2",
            "2024-05-25_Practice_3", "2024-05-25_Qualifying",
            "2024-05-26_Race",
        ]),
        ("2024-06-09_Canadian_Grand_Prix", [
            "2024-06-07_Practice_1", "2024-06-07_Practice_2",
            "2024-06-08_Practice_3", "2024-06-08_Qualifying",
            "2024-06-09_Race",
        ]),
    ],
}


def fetch(url: str) -> bytes | None:
    """GET url with retries. Returns None when the resource is missing.

    The F1 archive uses 403 for files that simply weren't captured that
    season (e.g. compressed telemetry for 2018 rounds). After retries we
    treat a persistent 403 as "gone" so the mirror keeps moving; transient
    403/5xx still get the retry loop.
    """
    # urllib demands an ASCII-safe URL; percent-encode non-ASCII path
    # characters (e.g. "São" → "S%C3%A3o") without touching reserved chars.
    safe_url = quote(url, safe=":/?#[]@!$&'()*+,;=%")
    last_err: Exception | None = None
    for attempt in range(RETRIES):
        try:
            req = Request(safe_url, headers={"User-Agent": UA, "Accept": "*/*"})
            with urlopen(req, timeout=TIMEOUT) as resp:
                return resp.read()
        except HTTPError as e:
            if e.code == 404:
                return None
            last_err = e
            if e.code == 403 and attempt == RETRIES - 1:
                return None
        except URLError as e:
            last_err = e
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"fetch failed: {url} ({last_err})")


def save(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_bytes(data)
    tmp.replace(path)


def download_one(url: str, dest: Path) -> tuple[str, str]:
    """Download url into dest, returning (status, name) for logging."""
    if dest.exists() and dest.stat().st_size > 0:
        return ("skip", dest.name)
    data = fetch(url)
    if data is None:
        return ("404", dest.name)
    save(dest, data)
    return ("ok", dest.name)


def download_session(session_path: str) -> None:
    """Download every known file for a session path like '2024/.../2024-03-02_Race/'."""
    session_path = session_path.rstrip("/")
    local_dir = (ROOT / session_path).resolve()
    # Reject traversal — Index.json occasionally carries UAT paths like
    # "../uat/static/2022/..." that would escape the mirror root.
    if not local_dir.is_relative_to(ROOT):
        print(f"  skip (outside root): {session_path}")
        return
    local_dir.mkdir(parents=True, exist_ok=True)

    # Parallel download within a session; keep concurrency polite.
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {
            pool.submit(
                download_one,
                f"{BASE_URL}/{session_path}/{fname}",
                local_dir / fname,
            ): fname
            for fname in SESSION_FILES
        }
        counts = {"ok": 0, "skip": 0, "404": 0, "err": 0}
        for fut in as_completed(futures):
            try:
                status, _ = fut.result()
                counts[status] += 1
            except Exception as e:
                counts["err"] += 1
                print(f"  ! {futures[fut]}: {e}", file=sys.stderr)
    print(
        f"  session {session_path}: "
        f"{counts['ok']} new, {counts['skip']} cached, "
        f"{counts['404']} missing, {counts['err']} errors"
    )


def download_season(year: int) -> None:
    print(f"\n=== Season {year} ===")
    season_dir = ROOT / str(year)
    season_dir.mkdir(parents=True, exist_ok=True)

    index_url = f"{BASE_URL}/{year}/Index.json"
    index_path = season_dir / "Index.json"
    data = fetch(index_url)
    if data is None:
        print(f"  season {year}: no Index.json (404)")
        return
    save(index_path, data)

    # The server prefixes Index.json with a UTF-8 BOM; strip it before parsing.
    index = json.loads(data.decode("utf-8-sig"))
    meetings = index.get("Meetings", [])
    print(f"  {len(meetings)} meetings")

    for meeting in meetings:
        name = meeting.get("Name", "?")
        location = meeting.get("Location", "?")
        sessions = meeting.get("Sessions", [])
        print(f"- {name} ({location}) — {len(sessions)} sessions")
        for session in sessions:
            path = session.get("Path")
            if not path:
                continue
            download_session(path)

    for meeting_dir, session_names in SUPPLEMENTAL_MEETINGS.get(year, []):
        print(f"- [supplemental] {meeting_dir} — {len(session_names)} sessions")
        for session_name in session_names:
            download_session(f"{year}/{meeting_dir}/{session_name}/")


def main() -> None:
    years = [int(a) for a in sys.argv[1:]] or SEASONS
    print(f"Mirroring seasons: {years}")
    print(f"Target root: {ROOT}")
    for year in years:
        try:
            download_season(year)
        except Exception as e:
            print(f"!! season {year} aborted: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
