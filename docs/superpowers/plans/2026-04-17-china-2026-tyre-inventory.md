# China 2026 Tyre Inventory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship tyre-inventory pages for the Chinese Grand Prix (`china-2026`) alongside the existing Australian GP, with first-class support for sprint-weekend sessions (Sprint Qualifying, Sprint).

**Architecture:** Widen the Python `SessionKey` enum to cover `SQ` and `S`, teach the build pipeline to resolve Sprint_Qualifying vs Qualifying correctly and sort sessions chronologically, extend the inventory Pass-A loop to cover sprint sessions, then generalise the single-featured-race plumbing (`fetch_race.py`, `build.py`, `Makefile`, `site/src/config.ts`) to drive two races in lockstep.

**Tech Stack:** Python 3.13 (Pydantic, pytest, mypy strict, ruff), TypeScript / Vite / React 19 / Zod on the site, Playwright for E2E.

**Reference spec:** `docs/superpowers/specs/2026-04-17-china-2026-tyre-inventory-design.md` — read it before starting any task.

**Commit discipline:** One commit per task (small, reviewable). Conventional-commits style, same as recent history (`feat(site):`, `fix(site):`, `docs:`, `chore:`, `test:`). Every commit ends with:

```
Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

Always ask the user before committing — per their global `CLAUDE.md`, commits are never autonomous.

---

## Task 1: Widen `SessionKey` and extend inventory Pass-A

**Why first:** The enum change is invisible at runtime (Python `Literal` is type-only) but required by every downstream step. Pair it with the Pass-A loop extension in a single commit so the change has a real behavioural test covering it.

**Files:**
- Modify: `precompute/src/f1/models.py:13`
- Modify: `precompute/src/f1/inventory.py:8,124`
- Test: `precompute/tests/test_inventory.py` (append a new test)

- [ ] **Step 1: Append a failing Pass-A ordering test to `test_inventory.py`**

Open `precompute/tests/test_inventory.py` and append at the end of the file:

```python
def test_pass_a_includes_sprint_sessions_in_chronological_order() -> None:
    from f1.inventory import build_inventory

    stints = {
        "FP1": [],
        "SQ": [SessionStint("SQ", "1", 0, "MEDIUM", True, 0, 2)],
        "S":  [SessionStint("S",  "1", 0, "HARD",   True, 0, 8)],
        "Q":  [SessionStint("Q",  "1", 0, "MEDIUM", False, 2, 1)],
    }
    sets = build_inventory(driver_number="1", driver_tla="VER", stints_by_session=stints)

    # One MEDIUM (continued SQ → Q) and one HARD (only S).
    assert len(sets) == 2
    med = next(s for s in sets if s.compound == "MEDIUM")
    assert med.first_seen_session == "SQ"
    assert med.last_seen_session == "Q"
    assert med.laps == 3           # 2 (SQ) + 1 (Q)
    hard = next(s for s in sets if s.compound == "HARD")
    assert hard.first_seen_session == "S"
    assert hard.last_seen_session == "S"
    assert hard.laps == 8
```

- [ ] **Step 2: Run the new test — expect failure**

```bash
cd precompute
uv run pytest tests/test_inventory.py::test_pass_a_includes_sprint_sessions_in_chronological_order -v
```

Expected: fails on `len(sets) == 2` with `sets == []` because the current Pass-A loop skips `SQ` and `S`.

- [ ] **Step 3: Widen `SessionKey` literal**

In `precompute/src/f1/models.py`, replace line 13:

```python
SessionKey = Literal["FP1", "FP2", "FP3", "Q", "R"]
```

with:

```python
SessionKey = Literal["FP1", "FP2", "FP3", "SQ", "S", "Q", "R"]
```

- [ ] **Step 4: Extend `_SESSION_ORDER` and the Pass-A loop**

In `precompute/src/f1/inventory.py`:

Line 8 — change:

```python
_SESSION_ORDER: list[SessionKey] = ["FP1", "FP2", "FP3", "Q", "R"]
```

to:

```python
_SESSION_ORDER: list[SessionKey] = ["FP1", "FP2", "FP3", "SQ", "S", "Q", "R"]
```

Line 124 — change:

```python
    for session in ("FP1", "FP2", "FP3", "Q"):
```

to:

```python
    for session in ("FP1", "FP2", "FP3", "SQ", "S", "Q"):
```

- [ ] **Step 5: Run the new test — expect pass**

```bash
cd precompute
uv run pytest tests/test_inventory.py::test_pass_a_includes_sprint_sessions_in_chronological_order -v
```

Expected: PASS.

- [ ] **Step 6: Run the full Python test + lint suite**

```bash
cd precompute
uv run pytest
uv run mypy src
uv run ruff check .
```

Expected: all green. Coverage gate (85 %) should still hold — no code deletion.

- [ ] **Step 7: Commit**

Ask the user before committing. On approval:

```bash
git add precompute/src/f1/models.py precompute/src/f1/inventory.py precompute/tests/test_inventory.py
git commit -m "$(cat <<'EOF'
feat(precompute): extend SessionKey for sprint-weekend sessions

Adds SQ (Sprint Qualifying) and S (Sprint) to the SessionKey literal
and expands the inventory Pass-A loop to process them chronologically
(FP1 → FP2 → FP3 → SQ → S → Q). Pass B (Race, discovery-only) is
unchanged.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Create the China mini-race fixture

**Why second:** Tasks 3 + 6 need a working fixture tree. Build it once, referenced everywhere.

**Files — all new:**
- Create: `precompute/fixtures/mini-race/2026/2026-03-15_Chinese_Grand_Prix/2026-03-13_Practice_1/SessionInfo.json`
- Create: `precompute/fixtures/mini-race/2026/2026-03-15_Chinese_Grand_Prix/2026-03-13_Sprint_Qualifying/SessionInfo.json`
- Create: `precompute/fixtures/mini-race/2026/2026-03-15_Chinese_Grand_Prix/2026-03-13_Sprint_Qualifying/TyreStintSeries.jsonStream`
- Create: `precompute/fixtures/mini-race/2026/2026-03-15_Chinese_Grand_Prix/2026-03-14_Sprint/SessionInfo.json`
- Create: `precompute/fixtures/mini-race/2026/2026-03-15_Chinese_Grand_Prix/2026-03-14_Sprint/TyreStintSeries.jsonStream`
- Create: `precompute/fixtures/mini-race/2026/2026-03-15_Chinese_Grand_Prix/2026-03-14_Qualifying/SessionInfo.json`
- Create: `precompute/fixtures/mini-race/2026/2026-03-15_Chinese_Grand_Prix/2026-03-14_Qualifying/TyreStintSeries.jsonStream`
- Create: `precompute/fixtures/mini-race/2026/2026-03-15_Chinese_Grand_Prix/2026-03-15_Race/SessionInfo.json`
- Create: `precompute/fixtures/mini-race/2026/2026-03-15_Chinese_Grand_Prix/2026-03-15_Race/TyreStintSeries.jsonStream`
- Create: `precompute/fixtures/mini-race/2026/2026-03-15_Chinese_Grand_Prix/2026-03-15_Race/DriverList.jsonStream`
- Create: `precompute/fixtures/mini-race/2026/2026-03-15_Chinese_Grand_Prix/2026-03-15_Race/TimingAppData.jsonStream`

**Stint design (two drivers, VER=1, LEC=16; grid VER=1, LEC=2):**

| Session | VER (1) | LEC (16) |
|---|---|---|
| FP1 | — | — |
| SQ  | new SOFT, 3 laps | new MEDIUM, 4 laps |
| S   | new HARD, 8 laps | new SOFT, 6 laps |
| Q   | SOFT start=3, total=2 (continues SQ) | new SOFT, 3 laps |
| R   | HARD start=8, total=0 (continues S) + new MEDIUM, 0 laps | SOFT start=3, total=0 (continues Q) |

This exercises all three paths the design spec calls out: Path A (SQ → Q continuation), Path B (S → R continuation), Path C (saved-for-race new set in R).

- [ ] **Step 1: Write `2026-03-13_Practice_1/SessionInfo.json`**

```json
{"Meeting":{"Key":1280,"Name":"Chinese Grand Prix","Location":"Shanghai","Number":2,"Country":{"Key":53,"Code":"CHN","Name":"China"}},"Key":11235,"Type":"Practice","Number":1,"Name":"Practice 1","StartDate":"2026-03-13T11:30:00","EndDate":"2026-03-13T12:30:00","GmtOffset":"08:00:00","Path":"2026/2026-03-15_Chinese_Grand_Prix/2026-03-13_Practice_1/"}
```

- [ ] **Step 2: Write `2026-03-13_Sprint_Qualifying/SessionInfo.json`**

```json
{"Meeting":{"Key":1280,"Name":"Chinese Grand Prix","Location":"Shanghai","Number":2,"Country":{"Key":53,"Code":"CHN","Name":"China"}},"Key":11236,"Type":"Qualifying","Number":-1,"Name":"Sprint Qualifying","StartDate":"2026-03-13T15:30:00","EndDate":"2026-03-13T16:14:00","GmtOffset":"08:00:00","Path":"2026/2026-03-15_Chinese_Grand_Prix/2026-03-13_Sprint_Qualifying/"}
```

- [ ] **Step 3: Write `2026-03-13_Sprint_Qualifying/TyreStintSeries.jsonStream`**

Single line, no trailing newline:

```
00:00:00.000{"Stints":{"1":{"0":{"Compound":"SOFT","New":"true","TotalLaps":3,"StartLaps":0}},"16":{"0":{"Compound":"MEDIUM","New":"true","TotalLaps":4,"StartLaps":0}}}}
```

- [ ] **Step 4: Write `2026-03-14_Sprint/SessionInfo.json`**

```json
{"Meeting":{"Key":1280,"Name":"Chinese Grand Prix","Location":"Shanghai","Number":2,"Country":{"Key":53,"Code":"CHN","Name":"China"}},"Key":11240,"Type":"Race","Number":-1,"Name":"Sprint","StartDate":"2026-03-14T11:00:00","EndDate":"2026-03-14T12:00:00","GmtOffset":"08:00:00","Path":"2026/2026-03-15_Chinese_Grand_Prix/2026-03-14_Sprint/"}
```

- [ ] **Step 5: Write `2026-03-14_Sprint/TyreStintSeries.jsonStream`**

```
00:00:00.000{"Stints":{"1":{"0":{"Compound":"HARD","New":"true","TotalLaps":8,"StartLaps":0}},"16":{"0":{"Compound":"SOFT","New":"true","TotalLaps":6,"StartLaps":0}}}}
```

- [ ] **Step 6: Write `2026-03-14_Qualifying/SessionInfo.json`**

```json
{"Meeting":{"Key":1280,"Name":"Chinese Grand Prix","Location":"Shanghai","Number":2,"Country":{"Key":53,"Code":"CHN","Name":"China"}},"Key":11241,"Type":"Qualifying","Name":"Qualifying","StartDate":"2026-03-14T15:00:00","EndDate":"2026-03-14T16:00:00","GmtOffset":"08:00:00","Path":"2026/2026-03-15_Chinese_Grand_Prix/2026-03-14_Qualifying/"}
```

- [ ] **Step 7: Write `2026-03-14_Qualifying/TyreStintSeries.jsonStream`**

```
00:00:00.000{"Stints":{"1":{"0":{"Compound":"SOFT","New":"false","TotalLaps":2,"StartLaps":3}},"16":{"0":{"Compound":"SOFT","New":"true","TotalLaps":3,"StartLaps":0}}}}
```

- [ ] **Step 8: Write `2026-03-15_Race/SessionInfo.json`**

```json
{"Meeting":{"Key":1280,"Name":"Chinese Grand Prix","OfficialName":"FORMULA 1 HEINEKEN CHINESE GRAND PRIX 2026","Location":"Shanghai","Number":2,"Country":{"Key":53,"Code":"CHN","Name":"China"},"Circuit":{"Key":49,"ShortName":"Shanghai"}},"SessionStatus":"Finalised","Key":11245,"Type":"Race","Name":"Race","StartDate":"2026-03-15T15:00:00","EndDate":"2026-03-15T17:00:00","GmtOffset":"08:00:00","Path":"2026/2026-03-15_Chinese_Grand_Prix/2026-03-15_Race/"}
```

- [ ] **Step 9: Write `2026-03-15_Race/TyreStintSeries.jsonStream`**

```
00:00:00.000{"Stints":{"1":{"0":{"Compound":"HARD","New":"false","TotalLaps":0,"StartLaps":8},"1":{"Compound":"MEDIUM","New":"true","TotalLaps":0,"StartLaps":0}},"16":{"0":{"Compound":"SOFT","New":"false","TotalLaps":0,"StartLaps":3}}}}
```

- [ ] **Step 10: Write `2026-03-15_Race/DriverList.jsonStream`**

```
00:00:00.000{"1":{"RacingNumber":"1","Tla":"VER","FullName":"Max Verstappen","TeamName":"Red Bull Racing","TeamColour":"4781D7"},"16":{"RacingNumber":"16","Tla":"LEC","FullName":"Charles Leclerc","TeamName":"Ferrari","TeamColour":"ED1131"}}
```

- [ ] **Step 11: Write `2026-03-15_Race/TimingAppData.jsonStream`**

```
00:00:00.000{"Lines":{"1":{"RacingNumber":"1","GridPos":"1"},"16":{"RacingNumber":"16","GridPos":"2"}}}
```

- [ ] **Step 12: Commit**

Ask the user before committing. On approval:

```bash
git add precompute/fixtures/mini-race/2026/2026-03-15_Chinese_Grand_Prix
git commit -m "$(cat <<'EOF'
test(precompute): add China 2026 sprint-weekend mini-race fixture

Two-driver fixture (VER, LEC) with all five session folders.
Stints exercise: SQ → Q continuation, S → R continuation, and a
saved-for-race new set in R.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Session discovery — folder hints + chronological sort + display names

**Why now:** We have the fixture; next we need the build code to discover the five sessions correctly and sort them chronologically (`FP1, SQ, S, Q, R`) rather than lexicographically (`FP1, SQ, Q, S, R`).

**Files:**
- Modify: `precompute/src/f1/build.py:28-42,118-144`
- Test: `precompute/tests/test_build.py` (append new tests)

- [ ] **Step 1: Append a failing integration test to `test_build.py`**

Open `precompute/tests/test_build.py` and append at the end:

```python
@pytest.fixture
def mini_race_china_root(fixtures_dir: Path) -> Path:
    return fixtures_dir / "mini-race"


def test_build_race_manifest_for_sprint_weekend_produces_validated_model(
    mini_race_china_root: Path,
) -> None:
    manifest = build_race_manifest(
        data_root=mini_race_china_root,
        race_dir="2026/2026-03-15_Chinese_Grand_Prix",
        season=2026,
        round_number=2,
        slug="china-2026",
    )
    assert manifest.race.slug == "china-2026"
    assert manifest.race.name == "Chinese Grand Prix"
    assert manifest.race.location == "Shanghai"
    assert manifest.race.country == "China"
    assert manifest.race.season == 2026
    assert manifest.race.round == 2


def test_build_race_manifest_discovers_all_five_session_keys(
    mini_race_china_root: Path,
) -> None:
    manifest = build_race_manifest(
        data_root=mini_race_china_root,
        race_dir="2026/2026-03-15_Chinese_Grand_Prix",
        season=2026,
        round_number=2,
        slug="china-2026",
    )
    assert [s.key for s in manifest.race.sessions] == ["FP1", "SQ", "S", "Q", "R"]


def test_build_race_manifest_sprint_session_stints_participate_in_pass_a(
    mini_race_china_root: Path,
) -> None:
    manifest = build_race_manifest(
        data_root=mini_race_china_root,
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
    mini_race_china_root: Path,
) -> None:
    manifest = build_race_manifest(
        data_root=mini_race_china_root,
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
    mini_race_china_root: Path,
) -> None:
    manifest = build_race_manifest(
        data_root=mini_race_china_root,
        race_dir="2026/2026-03-15_Chinese_Grand_Prix",
        season=2026,
        round_number=2,
        slug="china-2026",
    )
    by_tla = {d.tla: d for d in manifest.race.drivers}
    assert by_tla["VER"].grid_position == 1
    assert by_tla["LEC"].grid_position == 2
```

- [ ] **Step 2: Run the new tests — expect failures**

```bash
cd precompute
uv run pytest tests/test_build.py -k "sprint or chinese or china or discovers_all_five" -v
```

Expected failures: `KeyError: 'SQ'` from `_SESSION_DISPLAY_NAME[key]` when the discovery mis-labels `Sprint_Qualifying` as `Q` but actually, because current hints list puts "Qualifying" check before we add "Sprint_Qualifying", both `2026-03-13_Sprint_Qualifying` and `2026-03-14_Qualifying` get label `Q` and we get duplicate session keys; also session order will be wrong. Either way the test reports a concrete mismatch.

- [ ] **Step 3: Reorder `_SESSION_FOLDER_HINTS` and extend `_SESSION_DISPLAY_NAME`**

In `precompute/src/f1/build.py`, replace the `_SESSION_FOLDER_HINTS` block (currently lines 28-34) with:

```python
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
```

Replace the `_SESSION_DISPLAY_NAME` block (currently lines 36-42) with:

```python
_SESSION_DISPLAY_NAME: dict[SessionKey, str] = {
    "FP1": "Practice 1",
    "FP2": "Practice 2",
    "FP3": "Practice 3",
    "SQ":  "Sprint Qualifying",
    "S":   "Sprint",
    "Q":   "Qualifying",
    "R":   "Race",
}
```

- [ ] **Step 4: Sort `session_refs` chronologically in `build_race_manifest`**

In `precompute/src/f1/build.py`, find the block that builds `session_refs` (starts around line 118). After the `for key, sess_dir in sessions: ... session_refs.append(...)` loop but BEFORE the `meeting = race_info.get("Meeting") ...` block, insert:

```python
    # Folder names don't always sort chronologically on sprint weekends
    # (e.g. 2026-03-14_Qualifying sorts before 2026-03-14_Sprint even
    # though Sprint runs first). Re-order by StartDate so the manifest's
    # session list matches what actually happened on track.
    session_refs.sort(key=lambda ref: ref.start_utc)
```

So that block becomes:

```python
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
```

- [ ] **Step 5: Run the new tests — expect pass**

```bash
cd precompute
uv run pytest tests/test_build.py -k "sprint or chinese or china or discovers_all_five" -v
```

Expected: all 5 new tests PASS.

- [ ] **Step 6: Run the full Python suite**

```bash
cd precompute
uv run pytest
uv run mypy src
uv run ruff check .
```

Expected: all green. Australia tests still pass (chronological order for Australia matches lexicographic so the sort is a no-op).

- [ ] **Step 7: Commit**

Ask the user before committing. On approval:

```bash
git add precompute/src/f1/build.py precompute/tests/test_build.py
git commit -m "$(cat <<'EOF'
feat(precompute): resolve sprint sessions + sort by StartDate

Reorder _SESSION_FOLDER_HINTS so Sprint_Qualifying wins against its
substring Qualifying. Extend _SESSION_DISPLAY_NAME for SQ and S. Sort
session_refs by start_utc so sprint weekends are chronologically
correct (Saturday's Sprint sorts before Saturday's Qualifying).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: `FEATURED_RACES` list in `build.py`, with default multi-build

**Why now:** With the sprint support working, we can have `build.py` produce both manifests when invoked without args.

**Files:**
- Modify: `precompute/src/f1/build.py:194-230` (the `main()` function + argparse defaults)

- [ ] **Step 1: Replace `main()` with a multi-race loop**

Open `precompute/src/f1/build.py`. Replace the `main()` function (current lines 194-230) with:

```python
FEATURED_RACES: list[dict[str, object]] = [
    {
        "slug": "australia-2026",
        "race_dir": "2026/2026-03-08_Australian_Grand_Prix",
        "season": 2026,
        "round": 1,
    },
    {
        "slug": "china-2026",
        "race_dir": "2026/2026-03-15_Chinese_Grand_Prix",
        "season": 2026,
        "round": 2,
    },
]


def _default_data_root() -> Path:
    return Path(__file__).resolve().parents[3] / "seasons"


def _default_out_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "out"


def _build_one(
    *,
    data_root: Path,
    out_dir: Path,
    race: dict[str, object],
) -> int:
    try:
        manifest = build_race_manifest(
            data_root=data_root,
            race_dir=str(race["race_dir"]),
            season=int(race["season"]),  # type: ignore[arg-type]
            round_number=int(race["round"]),  # type: ignore[arg-type]
            slug=str(race["slug"]),
        )
    except RuntimeError as exc:
        print(f"error building {race['slug']}: {exc}", file=sys.stderr)
        return 1
    out_path = out_dir / f"{race['slug']}.json"
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

    out_dir = args.out.parent if args.out else _default_out_dir()

    if args.slug:
        matches = [r for r in FEATURED_RACES if r["slug"] == args.slug]
        race = matches[0] if matches else {"slug": args.slug}
        # CLI overrides take precedence over FEATURED_RACES defaults.
        race = dict(race)
        if args.race_dir:
            race["race_dir"] = args.race_dir
        if args.season is not None:
            race["season"] = args.season
        if args.round_number is not None:
            race["round"] = args.round_number
        if "race_dir" not in race or "season" not in race or "round" not in race:
            parser.error(
                f"--slug {args.slug!r} not in FEATURED_RACES; supply --race-dir, --season, --round."
            )
        if args.out:
            write_manifest(
                build_race_manifest(
                    data_root=args.data_root,
                    race_dir=str(race["race_dir"]),
                    season=int(race["season"]),  # type: ignore[arg-type]
                    round_number=int(race["round"]),  # type: ignore[arg-type]
                    slug=str(race["slug"]),
                ),
                args.out,
            )
            print(f"wrote {args.out}")
            return 0
        return _build_one(data_root=args.data_root, out_dir=out_dir, race=race)

    # No --slug: build every featured race.
    rc = 0
    for race in FEATURED_RACES:
        rc |= _build_one(data_root=args.data_root, out_dir=out_dir, race=race)
    return rc
```

- [ ] **Step 2: Add a test that `main()` without args builds both manifests**

Append to `precompute/tests/test_build.py`:

```python
def test_main_without_args_builds_both_featured_races(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mini_race_root: Path,
) -> None:
    """FEATURED_RACES drives main(); running it should produce one json per entry."""
    from f1 import build as build_mod

    out_dir = tmp_path / "out"
    monkeypatch.setattr(build_mod, "_default_data_root", lambda: mini_race_root)
    monkeypatch.setattr(build_mod, "_default_out_dir", lambda: out_dir)

    rc = build_mod.main([])
    assert rc == 0
    assert (out_dir / "australia-2026.json").is_file()
    assert (out_dir / "china-2026.json").is_file()
```

This uses the existing `mini_race_root` fixture (Australia) plus the China fixture from Task 2, both under `precompute/fixtures/mini-race/`.

- [ ] **Step 3: Run the new test — expect pass**

```bash
cd precompute
uv run pytest tests/test_build.py::test_main_without_args_builds_both_featured_races -v
```

Expected: PASS.

- [ ] **Step 4: Run the full Python suite**

```bash
cd precompute
uv run pytest
uv run mypy src
uv run ruff check .
```

Expected: all green.

- [ ] **Step 5: Commit**

Ask the user before committing. On approval:

```bash
git add precompute/src/f1/build.py precompute/tests/test_build.py
git commit -m "$(cat <<'EOF'
feat(precompute): build all FEATURED_RACES by default

Replaces single-race argparse defaults with a FEATURED_RACES list so
'python -m f1.build' produces every featured manifest in one run.
--slug still filters to one race for debugging; --race-dir / --season
/ --round / --out remain valid overrides.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: `FEATURED_RACES` list in `fetch_race.py`, with default multi-fetch

**Files:**
- Modify: `seasons/fetch_race.py` (replace `DEFAULT_RACE_DIR` + `DEFAULT_SESSIONS`, rework `main()`)

- [ ] **Step 1: Replace the defaults and `main()`**

Open `seasons/fetch_race.py`. Replace lines 28-35 (the current `DEFAULT_*` constants) with:

```python
FEATURED_RACES: list[dict[str, list[str] | str]] = [
    {
        "race_dir": "2026/2026-03-08_Australian_Grand_Prix",
        "sessions": [
            "2026-03-06_Practice_1",
            "2026-03-06_Practice_2",
            "2026-03-07_Practice_3",
            "2026-03-07_Qualifying",
            "2026-03-08_Race",
        ],
    },
    {
        "race_dir": "2026/2026-03-15_Chinese_Grand_Prix",
        "sessions": [
            "2026-03-13_Practice_1",
            "2026-03-13_Sprint_Qualifying",
            "2026-03-14_Sprint",
            "2026-03-14_Qualifying",
            "2026-03-15_Race",
        ],
    },
]
```

Then replace the `main()` function (currently lines 68-102) with:

```python
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
        races: list[dict[str, list[str] | str]] = [
            {"race_dir": args.race_dir, "sessions": args.sessions},
        ]
    else:
        races = FEATURED_RACES

    grand_totals: dict[str, int] = {"ok": 0, "cached": 0, "missing": 0, "skip": 0}
    for race in races:
        race_dir = str(race["race_dir"])
        sessions = list(race["sessions"])  # type: ignore[arg-type]
        print(f"Fetching {race_dir}: {len(sessions)} sessions × {len(args.files)} files")
        for session in sessions:
            session_path = f"{race_dir.rstrip('/')}/{session}"
            counts = fetch_session(session_path, args.files)
            for k, v in counts.items():
                grand_totals[k] += v
            print(f"  {session}: {counts}")

    print(f"\nTotals: {grand_totals}")
    if grand_totals["missing"]:
        print(f"warning: {grand_totals['missing']} file(s) returned 404/403", end="")
        print(" — the race(s) may not yet have run or the archive may be unavailable.")
    return 0
```

- [ ] **Step 2: Sanity-check by running `make fetch-race`**

This is idempotent and fast (files are already cached under `seasons/2026/`):

```bash
cd /Users/driversti/Projects/formula1
make fetch-race
```

Expected: logs "Fetching 2026/2026-03-08_Australian_Grand_Prix: 5 sessions × 4 files" followed by "Fetching 2026/2026-03-15_Chinese_Grand_Prix: 5 sessions × 4 files", and `Totals:` line with no `missing` count. All files should report as `cached` because they already exist on disk.

- [ ] **Step 3: Commit**

Ask the user before committing. On approval:

```bash
git add seasons/fetch_race.py
git commit -m "$(cat <<'EOF'
feat(seasons): fetch all FEATURED_RACES by default

Replaces DEFAULT_RACE_DIR / DEFAULT_SESSIONS with a FEATURED_RACES list
and makes main() loop over it when --race-dir is not given. CI and
fresh clones now pull metadata for both Australia and China in one go.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Makefile — `FEATURED_SLUGS` variable + copy loop

**Files:**
- Modify: `Makefile:29-37,47-52`

- [ ] **Step 1: Add `FEATURED_SLUGS` at the top and replace the three hardcoded `cp` lines**

Open `Makefile`. Between the `.PHONY:` line and the `# -------- setup --------` comment block, insert:

```makefile
# Source of truth for which race manifests the site consumes. Keep in
# sync with FEATURED_RACES in precompute/src/f1/build.py, with
# FEATURED_RACES in seasons/fetch_race.py, and with FEATURED_RACE_SLUGS
# in site/src/config.ts.
FEATURED_SLUGS := australia-2026 china-2026
```

Replace the `build:` target (current lines 29-32):

```makefile
build: precompute genzod
	mkdir -p site/public/data
	cp precompute/out/australia-2026.json site/public/data/
	cd site && npm run build
```

with:

```makefile
build: precompute genzod
	mkdir -p site/public/data
	for s in $(FEATURED_SLUGS); do cp precompute/out/$$s.json site/public/data/; done
	cd site && npm run build
```

Replace the `dev:` target (current lines 34-37):

```makefile
dev: precompute genzod
	mkdir -p site/public/data
	cp precompute/out/australia-2026.json site/public/data/
	cd site && npm run dev
```

with:

```makefile
dev: precompute genzod
	mkdir -p site/public/data
	for s in $(FEATURED_SLUGS); do cp precompute/out/$$s.json site/public/data/; done
	cd site && npm run dev
```

Replace the `test-e2e:` target (current lines 47-52):

```makefile
test-e2e: precompute genzod
	# Playwright's webServer.command builds with VITE_BASE=/ so tests can
	# hit page.goto("/") without a subpath. We only need data staged here.
	mkdir -p site/public/data
	cp precompute/out/australia-2026.json site/public/data/
	cd site && npm run test:e2e
```

with:

```makefile
test-e2e: precompute genzod
	# Playwright's webServer.command builds with VITE_BASE=/ so tests can
	# hit page.goto("/") without a subpath. We only need data staged here.
	mkdir -p site/public/data
	for s in $(FEATURED_SLUGS); do cp precompute/out/$$s.json site/public/data/; done
	cd site && npm run test:e2e
```

- [ ] **Step 2: Dry-run `make build` target locally up to the copy**

```bash
cd /Users/driversti/Projects/formula1
make precompute
ls precompute/out/
```

Expected: `precompute/out/` contains `australia-2026.json`, `china-2026.json`, `schema.json`.

Then:

```bash
mkdir -p site/public/data
for s in australia-2026 china-2026; do cp precompute/out/$s.json site/public/data/; done
ls site/public/data/
```

Expected: `site/public/data/` contains `australia-2026.json` and `china-2026.json`.

- [ ] **Step 3: Commit**

Ask the user before committing. On approval:

```bash
git add Makefile
git commit -m "$(cat <<'EOF'
chore: drive manifest copy with FEATURED_SLUGS variable

Replaces three hardcoded 'cp precompute/out/australia-2026.json' lines
in build:/dev:/test-e2e: with a for-loop over FEATURED_SLUGS so adding
a new featured race only touches the variable, not each target.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Site config — `FEATURED_RACE_SLUGS` list + unit test update

**Files:**
- Modify: `site/src/config.ts`
- Modify: `site/tests/unit/config.test.ts`

- [ ] **Step 1: Rewrite the failing config test**

Replace the whole content of `site/tests/unit/config.test.ts` with:

```ts
import { describe, it, expect } from "vitest";
import { FEATURED_RACE_SLUGS, isFeatured } from "../../src/config";

describe("featured-race config", () => {
  it("lists australia-2026 and china-2026 as the featured slugs", () => {
    expect(FEATURED_RACE_SLUGS).toEqual(["australia-2026", "china-2026"]);
  });

  it("isFeatured returns true for each featured slug", () => {
    expect(isFeatured("australia-2026")).toBe(true);
    expect(isFeatured("china-2026")).toBe(true);
  });

  it("isFeatured returns false for slugs not in the list", () => {
    expect(isFeatured("japan-2026")).toBe(false);
    expect(isFeatured("")).toBe(false);
  });
});
```

- [ ] **Step 2: Run the test — expect failure (FEATURED_RACE_SLUG not defined yet as array)**

```bash
cd site
npx vitest run tests/unit/config.test.ts
```

Expected: fail to import `FEATURED_RACE_SLUGS` from `../../src/config`.

- [ ] **Step 3: Rewrite `site/src/config.ts`**

Replace the whole content with:

```ts
/**
 * Races built end-to-end (manifest + UI analytics). Every other race in
 * the catalogue renders as a "Coming soon" tile until a manifest is
 * produced.
 *
 * Keep in sync with:
 *   - FEATURED_RACES in seasons/fetch_race.py
 *   - FEATURED_RACES in precompute/src/f1/build.py
 *   - FEATURED_SLUGS in the root Makefile
 */
export const FEATURED_RACE_SLUGS: readonly string[] = [
  "australia-2026",
  "china-2026",
] as const;

export function isFeatured(slug: string): boolean {
  return FEATURED_RACE_SLUGS.includes(slug);
}
```

- [ ] **Step 4: Run the test — expect pass**

```bash
cd site
npx vitest run tests/unit/config.test.ts
```

Expected: PASS.

- [ ] **Step 5: Run the full unit-test suite and the TypeScript build**

```bash
cd site
npm run test
npx tsc -b --noEmit
```

Expected: all green. `npx tsc -b` must not fail — if any other file imports `FEATURED_RACE_SLUG` (the old singular name), update that import site. Spot-check with:

```bash
cd site
grep -rn FEATURED_RACE_SLUG src tests || echo "no singular references"
```

Expected: `no singular references`. (Spec verified only `Race.tsx` and `Tyres.tsx` import `isFeatured`; if the grep surfaces something else, fix it.)

- [ ] **Step 6: Commit**

Ask the user before committing. On approval:

```bash
git add site/src/config.ts site/tests/unit/config.test.ts
git commit -m "$(cat <<'EOF'
feat(site): generalise featured-race config to a list

Replaces the single FEATURED_RACE_SLUG scalar with FEATURED_RACE_SLUGS
(readonly tuple). isFeatured() becomes a membership check so Race,
Tyres, and any new race route accept both australia-2026 and
china-2026 without further changes.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Site `data.ts` — widen the hand-rolled `SessionKeySchema`

**Why separate:** `site/src/lib/schemas.ts` is auto-generated by `gen-zod.mjs`, but `site/src/lib/data.ts` hand-rolls a stricter Zod schema for nested validation. The auto-generated one will pick up `SQ`/`S` once `make schema` is rerun; the hand-rolled one needs a manual edit.

**Files:**
- Modify: `site/src/lib/data.ts:10`
- Modify: `site/tests/unit/data.test.ts` (append a new test)

- [ ] **Step 1: Append a failing test to `data.test.ts`**

Append to `site/tests/unit/data.test.ts`, before the final `});` of the `describe` block:

```ts
  it("accepts sprint-weekend session keys (SQ, S)", async () => {
    const sprintFixture = {
      ...validFixture,
      race: {
        ...validFixture.race,
        slug: "china-2026",
        name: "Chinese Grand Prix",
        location: "Shanghai",
        country: "China",
        round: 2,
        sessions: [
          { key: "FP1", name: "Practice 1",        path: "p1/", start_utc: "2026-03-13T11:30:00" },
          { key: "SQ",  name: "Sprint Qualifying", path: "sq/", start_utc: "2026-03-13T15:30:00" },
          { key: "S",   name: "Sprint",            path: "s/",  start_utc: "2026-03-14T11:00:00" },
          { key: "Q",   name: "Qualifying",        path: "q/",  start_utc: "2026-03-14T15:00:00" },
          { key: "R",   name: "Race",              path: "r/",  start_utc: "2026-03-15T15:00:00" },
        ],
      },
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => sprintFixture }));
    const m = await loadManifest("/data/china-2026.json");
    expect(m.race.sessions.map((s) => s.key)).toEqual(["FP1", "SQ", "S", "Q", "R"]);
  });
```

- [ ] **Step 2: Run it — expect failure (Zod rejects "SQ" / "S")**

```bash
cd site
npx vitest run tests/unit/data.test.ts
```

Expected: fails inside `FullManifestSchema.parse(raw)` complaining about invalid enum values for `sessions[*].key`.

- [ ] **Step 3: Extend `SessionKeySchema` in `data.ts`**

In `site/src/lib/data.ts` line 10, change:

```ts
const SessionKeySchema = z.enum(["FP1", "FP2", "FP3", "Q", "R"]);
```

to:

```ts
const SessionKeySchema = z.enum(["FP1", "FP2", "FP3", "SQ", "S", "Q", "R"]);
```

- [ ] **Step 4: Run it — expect pass**

```bash
cd site
npx vitest run tests/unit/data.test.ts
```

Expected: PASS.

- [ ] **Step 5: Run the full unit-test suite**

```bash
cd site
npm run test
```

Expected: all green.

- [ ] **Step 6: Commit**

Ask the user before committing. On approval:

```bash
git add site/src/lib/data.ts site/tests/unit/data.test.ts
git commit -m "$(cat <<'EOF'
feat(site): accept SQ and S in the hand-rolled SessionKeySchema

The auto-generated schemas.ts picks up new enum values from the Zod
generator, but the stricter nested schema in data.ts is hand-maintained
and needs a manual bump. Adds SQ (Sprint Qualifying) and S (Sprint) so
the China manifest validates.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: E2E — China drill-in Playwright test

**Files:**
- Modify: `site/tests/e2e/home.spec.ts`

- [ ] **Step 1: Add the China drill-in test**

Open `site/tests/e2e/home.spec.ts`. After the existing Australia drill-in test (currently lines 9-22) and before the "non-featured race tile" test, insert:

```ts
test("drill into 2026 → Chinese GP → Tyre Inventory", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: /2026/ }).click();
  await expect(page).toHaveURL(/\/season\/2026$/);

  await page.getByRole("link", { name: /Chinese Grand Prix/ }).click();
  await expect(page).toHaveURL(/\/race\/china-2026$/);
  await expect(page.getByRole("heading", { name: /Chinese Grand Prix/ })).toBeVisible();

  await page.getByRole("link", { name: /Tyre Inventory/ }).click();
  await expect(page).toHaveURL(/\/race\/china-2026\/tyres$/);
  const cards = page.locator('a[href^="/race/china-2026/driver/"]');
  await expect(cards).toHaveCount(22);
});
```

- [ ] **Step 2: Run the E2E suite**

From repo root (this runs the Makefile dependencies — fetch, precompute, genzod, stage manifests):

```bash
cd /Users/driversti/Projects/formula1
make test-e2e
```

Expected: all three home-spec tests pass (Australia drill-in, China drill-in, non-featured tile assertion), plus the other E2E files unchanged. If Playwright's browser isn't installed, run `npx playwright install --with-deps chromium` first (one-off).

Note: the `toHaveCount(22)` on China assumes the live-timing archive contains all 22 drivers for the Chinese GP. If that count is off, check `seasons/2026/2026-03-15_Chinese_Grand_Prix/2026-03-15_Race/DriverList.jsonStream` and adjust the assertion to match the driver count.

- [ ] **Step 3: Commit**

Ask the user before committing. On approval:

```bash
git add site/tests/e2e/home.spec.ts
git commit -m "$(cat <<'EOF'
test(site): add China 2026 drill-in E2E

Mirrors the existing Australia flow: Seasons → 2026 → Chinese Grand
Prix → Tyre Inventory, asserting 22 driver cards on the Tyres page.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: Update `CLAUDE.md` sync warning

**Files:**
- Modify: `CLAUDE.md` (the "Currently-featured race" section)

- [ ] **Step 1: Read and replace the section**

Open `CLAUDE.md` at the repo root. Find the section `## Currently-featured race`. Replace its body with:

```markdown
## Currently-featured race(s)

`australia-2026` and `china-2026` are the two races currently built
end-to-end. When adding, removing, or swapping a featured race, update
all four sync points in lockstep — they drive fetch, build, packaging,
and UI independently:

- `seasons/fetch_race.py` — `FEATURED_RACES`
- `precompute/src/f1/build.py` — `FEATURED_RACES`
- `Makefile` — `FEATURED_SLUGS`
- `site/src/config.ts` — `FEATURED_RACE_SLUGS`

Sprint weekends use `SessionKey` values `SQ` (Sprint Qualifying) and
`S` (Sprint). Regular weekends use `FP1/FP2/FP3/Q/R`.
```

- [ ] **Step 2: Commit**

Ask the user before committing. On approval:

```bash
git add CLAUDE.md
git commit -m "$(cat <<'EOF'
docs: update CLAUDE.md for multiple featured races

Enumerates the four sync points (fetch_race, build, Makefile, config.ts)
instead of the old two-file warning, and notes the new SQ/S session
keys for sprint weekends.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: Full verification pass

- [ ] **Step 1: Clean slate build**

```bash
cd /Users/driversti/Projects/formula1
make clean
make install
make build
```

Expected: no errors; `site/dist/data/` contains `australia-2026.json` and `china-2026.json`.

- [ ] **Step 2: Full test suite**

```bash
cd /Users/driversti/Projects/formula1
make test
```

Expected: `test-py`, `test-site`, `test-e2e` all green. Python coverage ≥ 85 %.

- [ ] **Step 3: Manual smoke check**

```bash
cd /Users/driversti/Projects/formula1
make dev
```

Then open `http://localhost:5173/`:

- Seasons → 2026 → Chinese Grand Prix tile should be clickable (not "Coming soon").
- `/race/china-2026` shows the Analytics section with a "Tyre Inventory" tile.
- `/race/china-2026/tyres` shows 22 driver cards with their tyre dots.
- `/race/australia-2026/tyres` still renders correctly (regression check).
- Drill into any driver → the driver page renders without console errors.

Stop the dev server (`Ctrl-C`).

- [ ] **Step 4: No commit for this task — verification only.**

---

## Appendix — Troubleshooting

- **Test `test_build_race_manifest_discovers_all_five_session_keys` fails with `['FP1','SQ','Q','S','R']`:** the chronological `session_refs.sort(...)` call in `build.py` was missed or placed before `session_refs` is fully populated.
- **Test fails with `KeyError: 'SQ'` in `_SESSION_DISPLAY_NAME[key]`:** Task 3 Step 3 was only partially applied — ensure the new display map includes both `SQ` and `S` entries.
- **`npx tsc -b` fails with "Cannot find name 'FEATURED_RACE_SLUG'":** a route file still imports the singular name; change to `FEATURED_RACE_SLUGS` or the `isFeatured` helper as appropriate.
- **`make test-e2e` fails with `toHaveCount(22)` mismatch for China:** inspect the driver count in `seasons/2026/2026-03-15_Chinese_Grand_Prix/2026-03-15_Race/DriverList.jsonStream` and update the assertion to match reality.
- **`ruff` or `mypy` flags the new Python code:** re-read the diff — the `FEATURED_RACES` dict uses `list[dict[str, object]]` deliberately; `# type: ignore[arg-type]` is acceptable on the `int(race["season"])` casts to avoid over-typing the list literal.

---

## Spec-to-task coverage map

| Spec requirement | Task(s) |
|---|---|
| SessionKey gains SQ, S | Task 1 |
| Pass A includes SQ + S in chronological order | Task 1 |
| Folder hints resolve Sprint_Qualifying specifically | Task 3 |
| session_refs sorted by StartDate | Task 3 |
| FEATURED_RACES drives build.py | Task 4 |
| FEATURED_RACES drives fetch_race.py | Task 5 |
| Makefile loops over FEATURED_SLUGS | Task 6 |
| site/src/config.ts uses FEATURED_RACE_SLUGS | Task 7 |
| site/src/lib/data.ts SessionKeySchema widened | Task 8 |
| China mini-race fixture | Task 2 |
| 5 build integration tests | Task 3 (+ fixture from Task 2) |
| Inventory unit test for Pass-A ordering | Task 1 |
| Site config unit test updated | Task 7 |
| Site data.ts unit test (new SQ/S case) | Task 8 |
| China drill-in E2E | Task 9 |
| CLAUDE.md enumeration of 4 sync points | Task 10 |
| Verification: `make build`, `make test`, manual smoke | Task 11 |
