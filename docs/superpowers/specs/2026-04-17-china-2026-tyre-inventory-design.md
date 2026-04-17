# China 2026 Tyre Inventory — Design

**Status**: Approved for planning
**Date**: 2026-04-17
**Scope**: Add the Chinese Grand Prix (`china-2026`, round 2) as a second featured race alongside Australia, including first-class support for sprint-format sessions in the precompute pipeline.

## Goal

A user browsing the site can open `/race/china-2026/tyres` and see pre-race tyre inventory for every driver — exactly like the existing Australia experience. Under the hood, the precompute pipeline must understand sprint-weekend session structure (FP1 → Sprint Qualifying → Sprint → Qualifying → Race) and produce a validated manifest that tracks tyre sets across all five sessions.

## Non-goals

- Sprint-weekend tyre *allocation rules* (12 sets vs 13). The inventory is data-driven; it only observes what ran on track.
- UI treatment of sprint weekends (e.g., a "Sprint" badge on race tiles or Tyres pages). Visual parity with Australia is the target.
- Generalising the featured-race list into an external config file. That refactor is deferred until there are more featured races.

## Context

### Current single-race plumbing

"Featured race" is scattered across four layers, each single-valued:

- `seasons/fetch_race.py` — `DEFAULT_RACE_DIR` + `DEFAULT_SESSIONS` hardcode Australia.
- `precompute/src/f1/build.py` — argparse defaults hardcode Australia.
- `Makefile` — `build:`, `dev:`, `test-e2e:` hardcode `cp … australia-2026.json`.
- `site/src/config.ts` — `FEATURED_RACE_SLUG = "australia-2026"` scalar string; `isFeatured(slug)` does equality.

### Sprint weekend structure

The Chinese GP live-timing archive exposes these session folders under `seasons/2026/2026-03-15_Chinese_Grand_Prix/`:

- `2026-03-13_Practice_1`
- `2026-03-13_Sprint_Qualifying`
- `2026-03-14_Sprint`
- `2026-03-14_Qualifying`
- `2026-03-15_Race`

The current code models neither **Sprint Qualifying** nor the **Sprint** itself. `SessionKey = Literal["FP1","FP2","FP3","Q","R"]` has no entries for them, and `build.py`'s folder-name heuristic (`"Qualifying" in child.name`) mis-classifies `Sprint_Qualifying` as `Q`, colliding with the real Qualifying session.

## Decisions

### D1 — Full sprint-session support (not minimal awareness)

Extend `SessionKey` to include `SQ` (Sprint Qualifying) and `S` (Sprint). Tyre stints from SQ and S participate in the inventory algorithm so we don't miss sets that only appeared during the sprint portion of the weekend.

### D2 — List of featured slugs (not an external config file)

The featured-race list becomes a small Python constant in each of the three producers (`fetch_race.py`, `build.py`) and a sibling TypeScript readonly array on the site. A single shared JSON config is a cleaner long-term answer but is out of scope; the `CLAUDE.md` drift warning is updated to enumerate all four sites instead.

### D3 — Sprint stints join Pass A of the inventory algorithm

`build_inventory`'s Pass A loop (full tracking, mutation allowed) becomes `FP1 → FP2 → FP3 → SQ → S → Q`. Pass B (Race, discovery-only) is unchanged: only the actual Grand Prix is still treated as "set the pre-race snapshot in stone". Sprint sessions happen before the Grand Prix, so stints there can legitimately change a set's lap count.

## Architecture

### Layer 1 — Models (`precompute/src/f1/models.py`)

```python
SessionKey = Literal["FP1", "FP2", "FP3", "SQ", "S", "Q", "R"]
```

No other model changes. `SessionRef`, `TyreSet.first_seen_session`, and `TyreSet.last_seen_session` flow through the broader enum unchanged.

### Layer 2 — Session discovery (`precompute/src/f1/build.py`)

On a sprint weekend the folder-sort order is not chronological: Saturday has both `2026-03-14_Qualifying` and `2026-03-14_Sprint`, and lexicographic sort puts Qualifying before Sprint even though Sprint runs first. Today's `_discover_sessions` uses `sorted(race_abs_dir.iterdir())` — alphabetical. We keep that as the discovery primitive (deterministic, no file reads) but add a post-hoc chronological sort of `session_refs` by `start_utc` inside `build_race_manifest` before assigning to `Race.sessions`. The Australia case is unaffected: alphabetical and chronological coincide.

Order `_SESSION_FOLDER_HINTS` most-specific-first so a substring check still works:

```python
_SESSION_FOLDER_HINTS: list[tuple[str, SessionKey]] = [
    ("Practice_1",        "FP1"),
    ("Practice_2",        "FP2"),
    ("Practice_3",        "FP3"),
    ("Sprint_Qualifying", "SQ"),   # MUST precede both "Sprint" and "Qualifying"
    ("Sprint",            "S"),
    ("Qualifying",        "Q"),
    ("Race",              "R"),
]
```

Extend display names:

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

Replace argparse defaults with a module-level list and build-all main:

```python
FEATURED_RACES: list[dict[str, object]] = [
    {"slug": "australia-2026",
     "race_dir": "2026/2026-03-08_Australian_Grand_Prix",
     "season": 2026, "round": 1},
    {"slug": "china-2026",
     "race_dir": "2026/2026-03-15_Chinese_Grand_Prix",
     "season": 2026, "round": 2},
]
```

`main()` iterates `FEATURED_RACES` by default, writing `out/<slug>.json` per entry. `--slug <name>` filters to a single race. `--race-dir` + `--season` + `--round` + `--out` remain valid for one-off custom builds and take precedence when provided.

### Layer 3 — Inventory (`precompute/src/f1/inventory.py`)

```python
_SESSION_ORDER: list[SessionKey] = ["FP1", "FP2", "FP3", "SQ", "S", "Q", "R"]
...
for session in ("FP1", "FP2", "FP3", "SQ", "S", "Q"):
    session_key: SessionKey = session  # type: ignore[assignment]
    for stint in stints_by_session.get(session_key, []):
        ...
```

Regular (non-sprint) weekends are unaffected: `stints_by_session.get("SQ", [])` returns `[]` for Australia and the loop skips them silently.

### Layer 4 — Data fetcher (`seasons/fetch_race.py`)

Replace `DEFAULT_RACE_DIR` + `DEFAULT_SESSIONS` with:

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

`main()` iterates `FEATURED_RACES` by default. `--race-dir` and `--sessions` still work for one-off fetches (they override the loop).

### Layer 5 — Makefile

Add a source-of-truth variable for which manifests the site consumes:

```makefile
FEATURED_SLUGS := australia-2026 china-2026
```

Replace the three hardcoded `cp … australia-2026.json` lines (in `build:`, `dev:`, `test-e2e:`) with:

```makefile
mkdir -p site/public/data
for s in $(FEATURED_SLUGS); do cp precompute/out/$$s.json site/public/data/; done
```

`make precompute` already calls `python -m f1.build` once, which now iterates `FEATURED_RACES` internally and writes both manifests. No other target changes.

### Layer 6 — Site config (`site/src/config.ts`)

```ts
export const FEATURED_RACE_SLUGS: readonly string[] = [
  "australia-2026",
  "china-2026",
] as const;

export function isFeatured(slug: string): boolean {
  return FEATURED_RACE_SLUGS.includes(slug);
}
```

`FEATURED_RACE_SLUG` (singular) is removed. Callers in `Race.tsx` and `Tyres.tsx` only use `isFeatured(slug)` and are unchanged.

## Data flow (unchanged)

```
seasons/<year>/<race>/<session>/*.jsonStream
   │
   ▼  f1.build._discover_sessions() + f1.parse + f1.reduce
per-driver stints keyed by SessionKey
   │
   ▼  f1.inventory.build_inventory() — two-pass
TyreSet[] per driver, with first_seen / last_seen session tags
   │
   ▼  f1.models.Manifest (Pydantic-validated)
precompute/out/<slug>.json
   │
   ▼  Makefile cp
site/public/data/<slug>.json
   │
   ▼  lib/data.loadManifest + Zod
Tyres route renders DriverGrid
```

Sprint support shows up inside step 1 (session discovery) and step 2 (per-session stint extraction + inventory Pass A). Everything downstream is enum-widening only.

## Testing

### Python (`precompute/tests/`)

New fixture tree at `precompute/fixtures/mini-race/2026/2026-03-15_Chinese_Grand_Prix/` with five session dirs. Two drivers (LEC + VER), small hand-crafted `.jsonStream` + `SessionInfo.json` files. Stints designed to exercise:

- **Path A** — a set first seen new in SQ and reused with non-zero `StartLaps` in Q. Asserts SQ is included in Pass A and the set's lap count is mutated.
- **Path B** — a set first seen new in S (Sprint) and later reused in R with matching `StartLaps`. Asserts S is included in Pass A (otherwise Pass B's discovery-only would double-count it) and the set still reports `first_seen_session == "S"`.
- **Path C** — a set new in R that never appeared in any prior session. Asserts Pass B still works on a sprint weekend.

New tests in `tests/test_build.py`:

1. `test_build_race_manifest_for_sprint_weekend_produces_validated_model` — slug, round, country, location assertions for `china-2026`.
2. `test_build_race_manifest_discovers_all_five_session_keys` — `manifest.race.sessions` has keys `["FP1","SQ","S","Q","R"]` in chronological order. Covers both regressions: the Sprint_Qualifying / Qualifying folder-hint collision **and** the lexicographic-vs-chronological ordering quirk on Saturday.
3. `test_build_race_manifest_sprint_session_stints_participate_in_pass_a` — a `TyreSet` exists with `first_seen_session == "SQ"` and its laps were updated by a later Q stint.
4. `test_build_race_manifest_sprint_session_does_not_falsely_discover_in_pass_b` — for a set first used new in Sprint and reused in R with matching `StartLaps`, the set appears exactly once in the driver's final `sets` list **and** has `first_seen_session == "S"`. If S were omitted from Pass A the set would still appear once but mis-tagged as `first_seen_session == "R"` — the assertion on `first_seen_session` is what actually catches the regression.

New test in `tests/test_inventory.py`:

- `test_build_inventory_processes_sprint_sessions_in_order` — calls `build_inventory` with a hand-built `stints_by_session` containing only SQ and S keys (no real fixture needed); asserts `first_seen_session` respects the FP1→SQ→S→Q order.

The existing Australia-based tests are untouched; coverage stays ≥ 85 %.

### Site (`site/tests/`)

`tests/unit/config.test.ts` — rewrite around `FEATURED_RACE_SLUGS`:

- Asserts the list contains both `"australia-2026"` and `"china-2026"`.
- `isFeatured("australia-2026")` is `true`, `isFeatured("china-2026")` is `true`, `isFeatured("japan-2026")` is `false`, `isFeatured("")` is `false`.

`tests/e2e/home.spec.ts` — add a new test mirroring the existing Australia drill-in:

```ts
test("drill into 2026 → Chinese GP → Tyre Inventory", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: /2026/ }).click();
  await page.getByRole("link", { name: /Chinese Grand Prix/ }).click();
  await expect(page).toHaveURL(/\/race\/china-2026$/);
  await page.getByRole("link", { name: /Tyre Inventory/ }).click();
  await expect(page).toHaveURL(/\/race\/china-2026\/tyres$/);
  const cards = page.locator('a[href^="/race/china-2026/driver/"]');
  await expect(cards).toHaveCount(22);
});
```

The existing Australia drill-in and the Japan "non-featured" tile assertion remain unchanged (Japan is still not featured).

## Documentation

`CLAUDE.md` — rewrite the "Currently-featured race" section. Replace the current two-file sync warning with an enumeration of the four update sites:

- `seasons/fetch_race.py` — `FEATURED_RACES`
- `precompute/src/f1/build.py` — `FEATURED_RACES`
- `Makefile` — `FEATURED_SLUGS`
- `site/src/config.ts` — `FEATURED_RACE_SLUGS`

## File-change summary

| File | Change |
|---|---|
| `precompute/src/f1/models.py` | `SessionKey` literal gains `"SQ"`, `"S"` |
| `precompute/src/f1/build.py` | Reorder folder hints; extend display-name map; sort `session_refs` by `start_utc` before assigning to `Race.sessions`; replace argparse defaults with `FEATURED_RACES` list + loop in `main()` |
| `precompute/src/f1/inventory.py` | Extend `_SESSION_ORDER`; Pass A loop iterates FP1, FP2, FP3, SQ, S, Q |
| `precompute/tests/test_build.py` | 4 new sprint-weekend tests |
| `precompute/tests/test_inventory.py` | 1 new Pass-A ordering test |
| `precompute/fixtures/mini-race/2026/2026-03-15_Chinese_Grand_Prix/**` | New fixture tree, 5 session dirs |
| `seasons/fetch_race.py` | Replace `DEFAULT_RACE_DIR`/`DEFAULT_SESSIONS` with `FEATURED_RACES` list; loop in `main()` |
| `Makefile` | Add `FEATURED_SLUGS`; replace 3 hardcoded `cp` commands with a loop |
| `site/src/config.ts` | Replace `FEATURED_RACE_SLUG` with `FEATURED_RACE_SLUGS`; `isFeatured` membership check |
| `site/tests/unit/config.test.ts` | Rewrite for new shape |
| `site/tests/e2e/home.spec.ts` | Add China drill-in test |
| `site/src/lib/data.ts` | Extend the hand-rolled `SessionKeySchema` enum with `"SQ"`, `"S"` — this schema is not auto-generated |
| `CLAUDE.md` | Rewrite "Currently-featured race" section |

### Files deliberately untouched

- `site/src/data/schedule.ts` — already has `china-2026`.
- Any route file — routes are slug-parametric and work as-is.
- `precompute/src/f1/schema.py`, `driver_meta.py`, `parse.py`, `reduce.py` — unaffected by enum widening.
- `site/src/lib/schemas.ts` — regenerated by `make genzod` from the Pydantic JSON Schema. (The sibling `data.ts` enum, by contrast, is hand-rolled and listed above.)

## Verification steps (post-implementation)

1. `make install` if needed.
2. `make precompute` → both `precompute/out/australia-2026.json` and `precompute/out/china-2026.json` exist.
3. `make genzod` → site Zod accepts `SQ` and `S`.
4. `make test-py` → coverage ≥ 85 %.
5. `make test-site` → unit tests green.
6. `make test-e2e` → Australia and China drill-in specs both pass.
7. `make build` → `site/dist/data/` contains both manifests.
