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


def test_main_without_args_builds_races_with_fixtures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mini_race_root: Path,
) -> None:
    """FEATURED_RACES drives main(); running it should produce one json per entry."""
    from f1 import build as build_mod

    # Narrow FEATURED_RACES to those with mini-race fixtures present so the
    # test stays robust as new featured races are added without fixtures.
    races_with_fixtures = tuple(
        r for r in build_mod.FEATURED_RACES
        if (mini_race_root / r.race_dir).is_dir()
    )
    monkeypatch.setattr(build_mod, "FEATURED_RACES", races_with_fixtures)

    out_dir = tmp_path / "out"
    monkeypatch.setattr(build_mod, "_default_data_root", lambda: mini_race_root)
    monkeypatch.setattr(build_mod, "_default_out_dir", lambda: out_dir)

    rc = build_mod.main([])
    assert rc == 0
    for race in races_with_fixtures:
        assert (out_dir / f"{race.slug}.json").is_file()


def test_main_slug_with_out_writes_to_explicit_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mini_race_root: Path,
) -> None:
    """--slug + --out should write the manifest to the given path."""
    from f1 import build as build_mod

    monkeypatch.setattr(build_mod, "_default_data_root", lambda: mini_race_root)
    monkeypatch.setattr(build_mod, "_default_out_dir", lambda: tmp_path / "out")

    out_file = tmp_path / "custom" / "aus.json"
    rc = build_mod.main(["--slug", "australia-2026", "--out", str(out_file)])
    assert rc == 0
    assert out_file.is_file()


def test_main_slug_without_out_writes_to_out_dir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mini_race_root: Path,
) -> None:
    """--slug without --out should write slug.json in the default out dir."""
    from f1 import build as build_mod

    out_dir = tmp_path / "out"
    monkeypatch.setattr(build_mod, "_default_data_root", lambda: mini_race_root)
    monkeypatch.setattr(build_mod, "_default_out_dir", lambda: out_dir)

    rc = build_mod.main(["--slug", "china-2026"])
    assert rc == 0
    assert (out_dir / "china-2026.json").is_file()


def test_build_one_returns_1_on_runtime_error(tmp_path: Path) -> None:
    """_build_one should return 1 and print to stderr when build_race_manifest raises."""
    from f1 import build as build_mod

    out_dir = tmp_path / "out"
    # empty tmp_path → no drivers → RuntimeError inside build_race_manifest
    rc = build_mod._build_one(
        data_root=tmp_path,
        out_dir=out_dir,
        race=build_mod.FeaturedRace(
            slug="fake-race",
            race_dir="nonexistent",
            season=2026,
            round_number=99,
        ),
    )
    assert rc == 1


def test_main_unknown_slug_without_overrides_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mini_race_root: Path,
) -> None:
    """--slug unknown without --race-dir/--season/--round must parser.error (SystemExit)."""
    from f1 import build as build_mod

    monkeypatch.setattr(build_mod, "_default_data_root", lambda: mini_race_root)
    monkeypatch.setattr(build_mod, "_default_out_dir", lambda: tmp_path / "out")

    with pytest.raises(SystemExit):
        build_mod.main(["--slug", "imaginary-gp"])


def test_build_race_manifest_populates_race_stints(mini_race_root: Path) -> None:
    manifest = build_race_manifest(
        data_root=mini_race_root,
        race_dir="2026/2026-03-08_Australian_Grand_Prix",
        season=2026,
        round_number=1,
        slug="australia-2026",
    )
    ver = next(d for d in manifest.race.drivers if d.tla == "VER")
    assert len(ver.race_stints) > 0
    assert ver.sprint_stints == []  # Melbourne is not a sprint weekend
    # Race stints should be continuous.
    if len(ver.race_stints) > 1:
        for prev, curr in zip(ver.race_stints, ver.race_stints[1:], strict=False):
            assert curr.start_lap == prev.end_lap + 1


def test_build_race_manifest_populates_sprint_stints_on_sprint_weekend(
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
    assert len(ver.sprint_stints) > 0
    assert len(ver.race_stints) > 0


def test_build_race_manifest_marks_finishers(mini_race_root: Path) -> None:
    manifest = build_race_manifest(
        data_root=mini_race_root,
        race_dir="2026/2026-03-08_Australian_Grand_Prix",
        season=2026,
        round_number=1,
        slug="australia-2026",
    )
    ver = next(d for d in manifest.race.drivers if d.tla == "VER")
    assert ver.final_position == 1
    assert ver.dnf_at_lap is None


def test_build_race_manifest_marks_dnf_at_last_stint_end(mini_race_root: Path) -> None:
    manifest = build_race_manifest(
        data_root=mini_race_root,
        race_dir="2026/2026-03-08_Australian_Grand_Prix",
        season=2026,
        round_number=1,
        slug="australia-2026",
    )
    lec = next(d for d in manifest.race.drivers if d.tla == "LEC")
    assert lec.final_position is None
    assert lec.dnf_at_lap is not None
    assert lec.dnf_at_lap == lec.race_stints[-1].end_lap


def test_build_race_manifest_leaves_position_fields_none_when_no_race_stints(
    mini_race_root: Path,
) -> None:
    # Guard test: for drivers with no race stints (race not yet run / DNS),
    # both position fields stay None regardless of the TimingData feed.
    manifest = build_race_manifest(
        data_root=mini_race_root,
        race_dir="2026/2026-03-15_Chinese_Grand_Prix",
        season=2026,
        round_number=2,
        slug="china-2026",
    )
    for d in manifest.race.drivers:
        if not d.race_stints:
            assert d.final_position is None
            assert d.dnf_at_lap is None


def test_build_race_manifest_marks_sprint_finishers(mini_race_root: Path) -> None:
    manifest = build_race_manifest(
        data_root=mini_race_root,
        race_dir="2026/2026-03-15_Chinese_Grand_Prix",
        season=2026,
        round_number=2,
        slug="china-2026",
    )
    ver = next(d for d in manifest.race.drivers if d.tla == "VER")
    lec = next(d for d in manifest.race.drivers if d.tla == "LEC")
    assert ver.sprint_final_position == 1
    assert ver.sprint_dnf_at_lap is None
    assert lec.sprint_final_position == 2
    assert lec.sprint_dnf_at_lap is None


def test_build_race_manifest_leaves_sprint_fields_none_on_non_sprint_weekend(
    mini_race_root: Path,
) -> None:
    manifest = build_race_manifest(
        data_root=mini_race_root,
        race_dir="2026/2026-03-08_Australian_Grand_Prix",
        season=2026,
        round_number=1,
        slug="australia-2026",
    )
    for d in manifest.race.drivers:
        assert d.sprint_final_position is None
        assert d.sprint_dnf_at_lap is None
