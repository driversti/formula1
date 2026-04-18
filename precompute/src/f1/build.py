"""CLI entry point that assembles the final Manifest JSON artifact."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from f1.driver_meta import (
    DriverMeta,
    build_driver_meta,
    extract_final_positions_and_retirements,
    extract_grid_positions,
    extract_lap_counts,
)
from f1.inventory import (
    SessionStint,
    build_inventory,
    build_race_stints,
    extract_session_stints,
)
from f1.models import (
    DriverInventory,
    Manifest,
    Race,
    SessionKey,
    SessionRef,
    StatusBand,
    TyreSet,
)
from f1.parse import Event, parse_stream
from f1.reduce import reduce_events
from f1.track_status import (
    build_status_bands,
    collect_lap_boundaries,
    collect_status_transitions,
)

# Most-specific first: "Sprint_Qualifying" MUST be checked before both
# "Sprint" and "Qualifying" to avoid a substring collision.
_SESSION_FOLDER_HINTS: list[tuple[str, SessionKey]] = [
    ("Practice_1",        "FP1"),
    ("Practice_2",        "FP2"),
    ("Practice_3",        "FP3"),
    ("Sprint_Qualifying", "SQ"),
    ("Sprint",            "S"),
    ("Qualifying",        "Q"),
    ("Race",              "R"),
]

_SESSION_DISPLAY_NAME: dict[SessionKey, str] = {
    "FP1": "Practice 1",
    "FP2": "Practice 2",
    "FP3": "Practice 3",
    "SQ":  "Sprint Qualifying",
    "S":   "Sprint",
    "Q":   "Qualifying",
    "R":   "Race",
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


def _parse_events(session_dir: Path, filename: str) -> list[Event]:
    """Parse events without reducing — we need transitions, not final state."""
    path = session_dir / filename
    if not path.exists():
        return []
    return parse_stream(path)


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

    # Status bands per session (Race + Sprint only).
    race_status_bands: list[StatusBand] = []
    sprint_status_bands: list[StatusBand] = []
    for key, sess_dir in sessions:
        if key not in ("R", "S"):
            continue
        stints_for_key = stints_by_session.get(key, [])
        if not stints_for_key:
            continue
        ts_events = _parse_events(sess_dir, "TrackStatus.jsonStream")
        lc_events = _parse_events(sess_dir, "LapCount.jsonStream")
        lap_boundaries = collect_lap_boundaries(lc_events)
        total_laps = max((lap for _, lap in lap_boundaries), default=0)
        if total_laps < 1:
            continue
        transitions = collect_status_transitions(ts_events)
        if transitions and not lc_events:
            # Rare: status data but no lap reference; log and skip rather than crash.
            print(
                f"warning: TrackStatus present but LapCount missing for {sess_dir.name}",
                file=sys.stderr,
            )
            continue
        bands = build_status_bands(
            transitions,
            lap_boundaries,
            total_laps=total_laps,
        )
        if key == "R":
            race_status_bands = bands
        else:
            sprint_status_bands = bands

    # Grid positions from the Race session's TimingAppData (set right before
    # race start). Qualifying's TimingAppData does not carry GridPos.
    grid_positions: dict[str, int] = {}
    for key, sess_dir in sessions:
        if key == "R":
            ta = _reduce_stream(sess_dir, "TimingAppData.jsonStream")
            grid_positions = extract_grid_positions(ta)
            break

    # Final race classification and lap counts from TimingData.
    race_final_pos_and_retired: dict[str, tuple[int | None, bool]] = {}
    race_lap_counts: dict[str, int] = {}
    for key, sess_dir in sessions:
        if key == "R":
            td = _reduce_stream(sess_dir, "TimingData.jsonStream")
            race_final_pos_and_retired = extract_final_positions_and_retirements(td)
            race_lap_counts = extract_lap_counts(td)
            break

    # Sprint classification and lap counts from TimingData (when a sprint session is present).
    sprint_pos_and_retired: dict[str, tuple[int | None, bool]] = {}
    sprint_lap_counts: dict[str, int] = {}
    for key, sess_dir in sessions:
        if key == "S":
            td_s = _reduce_stream(sess_dir, "TimingData.jsonStream")
            sprint_pos_and_retired = extract_final_positions_and_retirements(td_s)
            sprint_lap_counts = extract_lap_counts(td_s)
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

    # Folder names don't always sort chronologically on sprint weekends
    # (e.g. 2026-03-14_Qualifying sorts before 2026-03-14_Sprint even
    # though Sprint runs first). Re-order by StartDate so the manifest's
    # session list matches what actually happened on track.
    session_refs.sort(key=lambda ref: ref.start_utc)

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
        race_stints = build_race_stints(
            driver_number=racing_number,
            stints_for_session=stints_by_session.get("R", []),
            driver_lap_count=race_lap_counts.get(racing_number),
        )
        sprint_stints = build_race_stints(
            driver_number=racing_number,
            stints_for_session=stints_by_session.get("S", []),
            driver_lap_count=sprint_lap_counts.get(racing_number),
        )
        final_line, retired = race_final_pos_and_retired.get(racing_number, (None, False))
        if not race_stints:
            final_position = None
            dnf_at_lap = None
        elif retired:
            final_position = None
            dnf_at_lap = race_stints[-1].end_lap
        else:
            final_position = final_line
            dnf_at_lap = None

        sprint_line, sprint_retired = sprint_pos_and_retired.get(racing_number, (None, False))
        if not sprint_stints:
            sprint_final_position = None
            sprint_dnf_at_lap = None
        elif sprint_retired:
            sprint_final_position = None
            sprint_dnf_at_lap = sprint_stints[-1].end_lap
        else:
            sprint_final_position = sprint_line
            sprint_dnf_at_lap = None

        drivers.append(
            DriverInventory(
                racing_number=meta.racing_number,
                tla=meta.tla,
                full_name=meta.full_name,
                team_name=meta.team_name,
                team_color=meta.team_color,
                grid_position=grid_positions.get(racing_number),
                sets=sets,
                race_stints=race_stints,
                sprint_stints=sprint_stints,
                final_position=final_position,
                dnf_at_lap=dnf_at_lap,
                sprint_final_position=sprint_final_position,
                sprint_dnf_at_lap=sprint_dnf_at_lap,
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
        race_status_bands=race_status_bands,
        sprint_status_bands=sprint_status_bands,
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


@dataclass(frozen=True)
class FeaturedRace:
    slug: str
    race_dir: str
    season: int
    round_number: int


FEATURED_RACES: tuple[FeaturedRace, ...] = (
    FeaturedRace(
        slug="australia-2026",
        race_dir="2026/2026-03-08_Australian_Grand_Prix",
        season=2026,
        round_number=1,
    ),
    FeaturedRace(
        slug="china-2026",
        race_dir="2026/2026-03-15_Chinese_Grand_Prix",
        season=2026,
        round_number=2,
    ),
    FeaturedRace(
        slug="japan-2026",
        race_dir="2026/2026-03-29_Japanese_Grand_Prix",
        season=2026,
        round_number=3,
    ),
)


def _default_data_root() -> Path:
    return Path(__file__).resolve().parents[3] / "seasons"


def _default_out_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "out"


def _build_one(
    *,
    data_root: Path,
    out_dir: Path,
    race: FeaturedRace,
) -> int:
    try:
        manifest = build_race_manifest(
            data_root=data_root,
            race_dir=race.race_dir,
            season=race.season,
            round_number=race.round_number,
            slug=race.slug,
        )
    except RuntimeError as exc:
        print(f"error building {race.slug}: {exc}", file=sys.stderr)
        return 1
    out_path = out_dir / f"{race.slug}.json"
    write_manifest(manifest, out_path)
    print(f"wrote {out_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build race tyre inventory JSON")
    parser.add_argument("--data-root", type=Path, default=_default_data_root())
    parser.add_argument("--slug", default=None,
                        help="Build only the race with this slug; default is all FEATURED_RACES.")
    parser.add_argument("--race-dir", default=None,
                        help="Override race_dir for --slug (ignored without --slug).")
    parser.add_argument("--season", type=int, default=None)
    parser.add_argument("--round", type=int, default=None, dest="round_number")
    parser.add_argument("--out", type=Path, default=None,
                        help="Output path; only meaningful with --slug.")
    args = parser.parse_args(argv)

    if args.slug:
        base = next((r for r in FEATURED_RACES if r.slug == args.slug), None)
        race_dir = args.race_dir if args.race_dir else (base.race_dir if base else None)
        season = args.season if args.season is not None else (base.season if base else None)
        round_number = (
            args.round_number
            if args.round_number is not None
            else (base.round_number if base else None)
        )
        if race_dir is None or season is None or round_number is None:
            parser.error(
                f"--slug {args.slug!r} not in FEATURED_RACES; "
                f"supply --race-dir, --season, --round."
            )
        race = FeaturedRace(
            slug=args.slug,
            race_dir=race_dir,
            season=season,
            round_number=round_number,
        )
        if args.out:
            write_manifest(
                build_race_manifest(
                    data_root=args.data_root,
                    race_dir=race.race_dir,
                    season=race.season,
                    round_number=race.round_number,
                    slug=race.slug,
                ),
                args.out,
            )
            print(f"wrote {args.out}")
            return 0
        return _build_one(data_root=args.data_root, out_dir=_default_out_dir(), race=race)

    # No --slug: build every featured race.
    rc = 0
    out_dir = _default_out_dir()
    for race in FEATURED_RACES:
        rc |= _build_one(data_root=args.data_root, out_dir=out_dir, race=race)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
