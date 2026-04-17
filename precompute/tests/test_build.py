"""End-to-end tests for the build CLI."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from f1.build import build_race_manifest
from f1.models import Manifest


@pytest.fixture
def mini_race_root(fixtures_dir: Path) -> Path:
    return fixtures_dir / "mini-race"


def test_build_race_manifest_produces_validated_model(mini_race_root: Path) -> None:
    manifest = build_race_manifest(
        data_root=mini_race_root,
        race_dir="2026/2026-03-08_Australian_Grand_Prix",
        season=2026,
        round_number=1,
        slug="australia-2026",
    )
    assert isinstance(manifest, Manifest)
    assert manifest.race.slug == "australia-2026"
    assert manifest.race.name == "Australian Grand Prix"
    assert manifest.race.location == "Melbourne"
    assert manifest.race.country == "Australia"
    assert manifest.race.season == 2026
    assert manifest.race.round == 1


def test_build_race_manifest_includes_all_drivers(mini_race_root: Path) -> None:
    manifest = build_race_manifest(
        data_root=mini_race_root,
        race_dir="2026/2026-03-08_Australian_Grand_Prix",
        season=2026,
        round_number=1,
        slug="australia-2026",
    )
    tlas = sorted(d.tla for d in manifest.race.drivers)
    assert tlas == ["LEC", "VER"]


def test_build_race_manifest_attaches_grid_positions(mini_race_root: Path) -> None:
    manifest = build_race_manifest(
        data_root=mini_race_root,
        race_dir="2026/2026-03-08_Australian_Grand_Prix",
        season=2026,
        round_number=1,
        slug="australia-2026",
    )
    by_tla = {d.tla: d for d in manifest.race.drivers}
    assert by_tla["LEC"].grid_position == 1
    assert by_tla["VER"].grid_position == 2


def test_build_race_manifest_discovers_saved_for_race_sets(mini_race_root: Path) -> None:
    manifest = build_race_manifest(
        data_root=mini_race_root,
        race_dir="2026/2026-03-08_Australian_Grand_Prix",
        season=2026,
        round_number=1,
        slug="australia-2026",
    )
    ver = next(d for d in manifest.race.drivers if d.tla == "VER")
    # VER used MEDIUM new in the race and SOFT new in Q.
    saved_for_race = [s for s in ver.sets if s.first_seen_session == "R"]
    assert len(saved_for_race) == 1
    assert saved_for_race[0].compound == "MEDIUM"
    assert saved_for_race[0].laps == 0


def test_build_race_manifest_fails_if_zero_drivers(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="no drivers"):
        build_race_manifest(
            data_root=tmp_path,
            race_dir="2026/empty",
            season=2026,
            round_number=1,
            slug="empty",
        )


def test_build_race_manifest_json_round_trip(mini_race_root: Path, tmp_path: Path) -> None:
    from f1.build import write_manifest

    manifest = build_race_manifest(
        data_root=mini_race_root,
        race_dir="2026/2026-03-08_Australian_Grand_Prix",
        season=2026,
        round_number=1,
        slug="australia-2026",
    )
    out = tmp_path / "out.json"
    write_manifest(manifest, out)
    loaded = json.loads(out.read_text())
    assert loaded["race"]["slug"] == "australia-2026"
    # Re-validate through Pydantic.
    Manifest.model_validate(loaded)


def test_build_race_manifest_for_sprint_weekend_produces_validated_model(
    mini_race_root: Path,
) -> None:
    manifest = build_race_manifest(
        data_root=mini_race_root,
        race_dir="2026/2026-03-15_Chinese_Grand_Prix",
        season=2026,
        round_number=2,
        slug="china-2026",
    )
    assert isinstance(manifest, Manifest)
    assert manifest.race.slug == "china-2026"
    assert manifest.race.name == "Chinese Grand Prix"
    assert manifest.race.location == "Shanghai"
    assert manifest.race.country == "China"
    assert manifest.race.season == 2026
    assert manifest.race.round == 2


def test_build_race_manifest_discovers_all_five_session_keys(
    mini_race_root: Path,
) -> None:
    manifest = build_race_manifest(
        data_root=mini_race_root,
        race_dir="2026/2026-03-15_Chinese_Grand_Prix",
        season=2026,
        round_number=2,
        slug="china-2026",
    )
    assert [s.key for s in manifest.race.sessions] == ["FP1", "SQ", "S", "Q", "R"]


def test_build_race_manifest_sprint_session_stints_participate_in_pass_a(
    mini_race_root: Path,
) -> None:
    manifest = build_race_manifest(
        data_root=mini_race_root,
        race_dir="2026/2026-03-15_Chinese_Grand_Prix",
        season=2026,
        round_number=2,
        slug="china-2026",
    )
    ver = next(d for d in manifest.race.drivers if d.tla == "VER")
    soft = next(s for s in ver.sets if s.compound == "SOFT")
    assert soft.first_seen_session == "SQ"
    assert soft.last_seen_session == "Q"
    assert soft.laps == 5  # 3 from SQ + 2 from Q


def test_build_race_manifest_sprint_session_does_not_falsely_discover_in_pass_b(
    mini_race_root: Path,
) -> None:
    manifest = build_race_manifest(
        data_root=mini_race_root,
        race_dir="2026/2026-03-15_Chinese_Grand_Prix",
        season=2026,
        round_number=2,
        slug="china-2026",
    )
    ver = next(d for d in manifest.race.drivers if d.tla == "VER")
    hard_sets = [s for s in ver.sets if s.compound == "HARD"]
    assert len(hard_sets) == 1
    assert hard_sets[0].first_seen_session == "S"
    # The MEDIUM saved for the race:
    medium_sets = [s for s in ver.sets if s.compound == "MEDIUM"]
    assert len(medium_sets) == 1
    assert medium_sets[0].first_seen_session == "R"
    assert medium_sets[0].laps == 0


def test_build_race_manifest_attaches_sprint_grid_positions(
    mini_race_root: Path,
) -> None:
    manifest = build_race_manifest(
        data_root=mini_race_root,
        race_dir="2026/2026-03-15_Chinese_Grand_Prix",
        season=2026,
        round_number=2,
        slug="china-2026",
    )
    by_tla = {d.tla: d for d in manifest.race.drivers}
    assert by_tla["VER"].grid_position == 1
    assert by_tla["LEC"].grid_position == 2
