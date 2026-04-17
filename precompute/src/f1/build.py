"""CLI entry point that assembles the final Manifest JSON artifact."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from f1.driver_meta import DriverMeta, build_driver_meta, extract_grid_positions
from f1.inventory import (
    SessionStint,
    build_inventory,
    extract_session_stints,
)
from f1.models import (
    DriverInventory,
    Manifest,
    Race,
    SessionKey,
    SessionRef,
    TyreSet,
)
from f1.parse import parse_stream
from f1.reduce import reduce_events

# Folder-name fragment -> SessionKey used internally
_SESSION_FOLDER_HINTS: list[tuple[str, SessionKey]] = [
    ("Practice_1", "FP1"),
    ("Practice_2", "FP2"),
    ("Practice_3", "FP3"),
    ("Qualifying", "Q"),
    ("Race", "R"),
]

_SESSION_DISPLAY_NAME: dict[SessionKey, str] = {
    "FP1": "Practice 1",
    "FP2": "Practice 2",
    "FP3": "Practice 3",
    "Q": "Qualifying",
    "R": "Race",
}


def _discover_sessions(race_abs_dir: Path) -> list[tuple[SessionKey, Path]]:
    """Return session key + absolute directory for every session we recognise."""
    if not race_abs_dir.is_dir():
        return []
    discovered: list[tuple[SessionKey, Path]] = []
    for child in sorted(race_abs_dir.iterdir()):
        if not child.is_dir():
            continue
        for hint, key in _SESSION_FOLDER_HINTS:
            if hint in child.name:
                discovered.append((key, child))
                break
    return discovered


def _load_session_info(session_dir: Path) -> dict[str, object]:
    info_path = session_dir / "SessionInfo.json"
    if not info_path.exists():
        return {}
    try:
        return json.loads(info_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}


def _reduce_stream(session_dir: Path, filename: str) -> dict[str, object]:
    path = session_dir / filename
    if not path.exists():
        return {}
    events = parse_stream(path)
    return reduce_events(events)


def build_race_manifest(
    *,
    data_root: Path,
    race_dir: str,
    season: int,
    round_number: int,
    slug: str,
) -> Manifest:
    """Assemble a validated Manifest from raw archive files under ``data_root``."""
    race_abs = (data_root / race_dir).resolve()
    sessions = _discover_sessions(race_abs)

    # Aggregate driver metadata from whichever session first provides DriverList.
    driver_meta: dict[str, DriverMeta] = {}
    for _, sess_dir in sessions:
        reduced = _reduce_stream(sess_dir, "DriverList.jsonStream")
        if reduced:
            driver_meta.update(build_driver_meta(reduced))
            if driver_meta:
                break

    if not driver_meta:
        raise RuntimeError(f"no drivers found under {race_abs}")

    # Stints per session key.
    stints_by_session: dict[SessionKey, list[SessionStint]] = {}
    for key, sess_dir in sessions:
        reduced = _reduce_stream(sess_dir, "TyreStintSeries.jsonStream")
        stints_by_session[key] = extract_session_stints(key, reduced)

    # Grid positions from the Race session's TimingAppData (set right before
    # race start). Qualifying's TimingAppData does not carry GridPos.
    grid_positions: dict[str, int] = {}
    for key, sess_dir in sessions:
        if key == "R":
            ta = _reduce_stream(sess_dir, "TimingAppData.jsonStream")
            grid_positions = extract_grid_positions(ta)
            break

    # Session refs (metadata + path relative to data_root).
    session_refs: list[SessionRef] = []
    race_info: dict[str, object] = {}
    location = "Unknown"
    country = "Unknown"
    race_name = "Unknown Grand Prix"
    for key, sess_dir in sessions:
        info = _load_session_info(sess_dir)
        rel_path = sess_dir.resolve().relative_to(data_root.resolve()).as_posix() + "/"
        session_refs.append(
            SessionRef(
                key=key,
                name=_SESSION_DISPLAY_NAME[key],
                path=rel_path,
                start_utc=str(info.get("StartDate", "")),
            )
        )
        if key == "R":
            race_info = info

    meeting = race_info.get("Meeting") if isinstance(race_info.get("Meeting"), dict) else {}
    if isinstance(meeting, dict):
        race_name = str(meeting.get("Name", race_name))
        location = str(meeting.get("Location", location))
        country_obj = meeting.get("Country")
        if isinstance(country_obj, dict):
            country = str(country_obj.get("Name", country))

    # Assemble drivers.
    drivers: list[DriverInventory] = []
    for racing_number, meta in driver_meta.items():
        sets: list[TyreSet] = build_inventory(
            driver_number=racing_number,
            driver_tla=meta.tla,
            stints_by_session=stints_by_session,
        )
        drivers.append(
            DriverInventory(
                racing_number=meta.racing_number,
                tla=meta.tla,
                full_name=meta.full_name,
                team_name=meta.team_name,
                team_color=meta.team_color,
                grid_position=grid_positions.get(racing_number),
                sets=sets,
            )
        )
    drivers.sort(key=lambda d: d.tla)

    race = Race(
        slug=slug,
        name=race_name,
        location=location,
        country=country,
        season=season,
        round=round_number,
        date=str(race_info.get("StartDate", ""))[:10],
        sessions=session_refs,
        drivers=drivers,
    )

    return Manifest(
        schema_version="1.0.0",
        generated_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        race=race,
    )


def write_manifest(manifest: Manifest, out_path: Path) -> None:
    """Serialize ``manifest`` to ``out_path`` as pretty JSON."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        manifest.model_dump_json(indent=2, exclude_none=False),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build race tyre inventory JSON")
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
        help="Root directory containing year folders (defaults to repo root)",
    )
    parser.add_argument(
        "--race-dir",
        default="2026/2026-03-08_Australian_Grand_Prix",
    )
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--round", type=int, default=1, dest="round_number")
    parser.add_argument("--slug", default="australia-2026")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "out" / "australia-2026.json",
    )
    args = parser.parse_args(argv)

    try:
        manifest = build_race_manifest(
            data_root=args.data_root,
            race_dir=args.race_dir,
            season=args.season,
            round_number=args.round_number,
            slug=args.slug,
        )
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    write_manifest(manifest, args.out)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
