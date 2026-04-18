# Data Feed Reference Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `docs/data-feed-reference.md` — a single-file grounded menu of every `.jsonStream`/`.json` feed F1 publishes per session, with real examples drawn from the Japanese GP 2026 Race on disk, known quirks, and speculative feature opportunities.

**Architecture:** Pure documentation. No code under `precompute/`, `site/`, `seasons/`, or `Makefile` changes. Content is built section-by-section on branch `docs/data-feed-reference` (already created), with the user signing off after each section before the next commit.

**Tech Stack:** Markdown. Real-data investigation uses `parse_stream` from `precompute/src/f1/parse.py` and `reduce_events` from `precompute/src/f1/reduce.py`; compressed feeds decoded with `zlib.decompress(base64.b64decode(blob), -zlib.MAX_WBITS)`.

**Project convention:** Every `git commit` step in this plan requires explicit user approval (per project's global CLAUDE.md "Always ask before creating commits"). Draft the commit message, show the `git status` / `git diff --stat` summary, and wait for sign-off.

**Section-by-section cadence:** After each phase writes a section and before committing, pause to let the user review the rendered markdown. Do NOT batch multiple sections into one commit.

**Spec reference:** `docs/superpowers/specs/2026-04-18-data-feed-reference-design.md`

**Reference session for all example events:** `seasons/2026/2026-03-29_Japanese_Grand_Prix/2026-03-29_Race/`

**Per-feed template (used in every Phase 2 task):**

````markdown
## <FeedName>.jsonStream

**Fetched by CI:** ✅ yes (via `seasons/fetch_race.py`) · or · ❌ no (full-archive only)
**Compressed:** yes / no
**Investigation depth:** deep / medium / shallow

**Summary.** One-paragraph description of what the feed contains and whether it accumulates state via `deep_merge` or is emitted event-wise.

**Example event** (truncated, from Japan 2026 Race):
```json
{ "example": "payload, ~5 lines max" }
```

**Known quirks.**
- Bullet list. Pre-known quirks from the spec are captured verbatim. Observational quirks note their session context ("seen in Japan 2026 Race") when generalization is unclear.

**Feeds these features** (current): list of features currently using this feed, or "none" if unused.

**Could power** (speculative): comma-separated list of plausible features.
````

**Pre-known quirks mapping** (from NEXT-TASK-PROMPT.md / spec §5.6). Every phase MUST attach these to the listed feed:

| # | Quirk | Target feed(s) |
|---|-------|-----------------|
| 1 | `TyreStintSeries.TotalLaps` is cumulative tyre wear (not stint length) | TyreStintSeries |
| 2 | TyreStintSeries can stop emitting mid-session (esp. post-pit) | TyreStintSeries |
| 3 | `TimingData.Retired` is the canonical DNF flag | TimingData |
| 4 | `TimingData.Line` is last-known track position, not official classification | TimingData + note in SessionData |
| 5 | Booleans arrive as bool OR `"true"`/`"false"` string; normalize | Stream format primer |
| 6 | `.z.` suffix → base64 zlib-deflated JSON; decode with `zlib.decompress(data, -zlib.MAX_WBITS)` | Stream format primer + CarData.z + Position.z |
| 7 | Line format `HH:MM:SS.mmm{<json>}`, UTF-8 BOM on first line | Stream format primer |

---

## File structure

**Target file:** `docs/data-feed-reference.md` (single file, ~400–600 lines).

**Working directory:** Repository root `/Users/driversti/Projects/formula1`.

**Branch:** `docs/data-feed-reference` (already checked out; spec already committed).

**Commit cadence:** One commit per phase task (12 commits total across Phases 1–3, plus the spec commit that already landed).

---

## Phase 1 — Top matter

Goal: create the file with its intro, stream-format primer, summary table (all 27 feeds), and cross-reference index. No feed sections yet.

### Task 1.1: Create the file with intro and stream-format primer

**Files:**
- Create: `docs/data-feed-reference.md`

- [ ] **Step 1: Confirm the reference session has all 27 feeds**

Run:
```bash
ls seasons/2026/2026-03-29_Japanese_Grand_Prix/2026-03-29_Race/ | wc -l
ls seasons/2026/2026-03-29_Japanese_Grand_Prix/2026-03-29_Race/
```

Expected: at least 26 files present. Note any missing files — they will be flagged per-feed in Phase 2 with a "not emitted in this session" note.

- [ ] **Step 2: Create `docs/data-feed-reference.md` with intro and primer**

Write the file with exactly these sections (the rest get appended in later tasks):

```markdown
# F1 Live-Timing Data Feeds — Reference

A grounded menu of every `.jsonStream` / `.json` file F1 publishes per session. For each feed we capture: what it contains, a real truncated example event, known quirks, and the features it powers or could power.

**This doc is not:** a full code-level analysis, a field-by-field dictionary, or a cross-season schema audit. Examples describe the **Japanese GP 2026 Race** session. Quirks generalize only when explicitly noted.

**Use this doc when:** you're asking "can we build feature X?" — scan the summary table below and the cross-reference index to find which feeds you need and whether we already fetch them in CI.

## Stream format primer

Every `.jsonStream` file has this shape: one line per event, each line prefixed by a session-relative timestamp.

```
HH:MM:SS.mmm{<json-patch>}
```

The first line carries a UTF-8 BOM. Events are JSON Merge Patches against an accumulating state dict — objects merge recursively, lists replace wholesale, and a special `_deleted` key at the current level removes named sub-keys. See `precompute/src/f1/reduce.py::deep_merge`.

**Parsing.** Use `parse_stream` from `precompute/src/f1/parse.py`; it handles the BOM, timestamp prefix, and skips malformed lines. To get the terminal state of a stream, pipe events through `reduce_events` from `precompute/src/f1/reduce.py`.

**Booleans.** Some fields arrive as Python `bool` (`true`/`false`), others as string (`"true"`/`"false"`). Always normalize before comparing.

**Compressed feeds.** Files ending in `.z.jsonStream` (currently `CarData.z.jsonStream` and `Position.z.jsonStream`) wrap each event's payload in base64-encoded zlib-deflated JSON. Decode with:

```python
import base64, zlib
decoded = zlib.decompress(base64.b64decode(blob), -zlib.MAX_WBITS)
```

The `-zlib.MAX_WBITS` argument is required — the payloads are raw DEFLATE without a zlib header.
```

- [ ] **Step 3: Verify the file opens and renders**

Run:
```bash
wc -l docs/data-feed-reference.md
head -40 docs/data-feed-reference.md
```

Expected: file exists, ~40–60 lines, markdown headings render correctly.

- [ ] **Step 4: Checkpoint — ask user to review**

Show the user: "Intro + primer drafted in `docs/data-feed-reference.md`. Please review before I commit." Wait for sign-off. If changes requested, apply them and re-show.

- [ ] **Step 5: Commit**

After sign-off:
```bash
git add docs/data-feed-reference.md
git commit -m "$(cat <<'EOF'
docs: seed data-feed-reference with intro and stream format primer

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task 1.2: Append the summary table (all 27 feeds)

**Files:**
- Modify: `docs/data-feed-reference.md` (append)

- [ ] **Step 1: Draft the summary table**

Append to `docs/data-feed-reference.md`:

```markdown

## Summary table

Every per-session feed F1 publishes, at a glance. **Fetched** means the file is pulled by `seasons/fetch_race.py` (i.e. available in CI and to fresh clones). **Depth** reflects how much this doc knows about the feed: `deep` = used in production, `medium` = investigated here with real data, `shallow` = opened and skimmed.

| Feed | Summary | Fetched by CI | Depth |
|------|---------|---------------|-------|
| `SessionInfo.json` | Session metadata: meeting, circuit, type, UTC start/end. | ✅ | deep |
| `Index.json` | Per-session file manifest; lists what's available in the archive. | ❌ | _TBD — Phase 2 group 1_ |
| `ArchiveStatus.json` | Archive completion flag for the session. | ❌ | _TBD — Phase 2 group 1_ |
| `SessionData.jsonStream` | Official classification, lap counts, session-boundary events. | ❌ | _TBD — Phase 2 group 1_ |
| `SessionStatus.jsonStream` | Running session state: green / red / yellow / finished. | ❌ | _TBD — Phase 2 group 1_ |
| `TimingData.jsonStream` | Per-driver live timing: lap times, sector times, position, Retired. | ✅ | deep |
| `TimingAppData.jsonStream` | Per-driver tyre sets, stints, pit-in/out state, grid position. | ✅ | deep |
| `TimingStats.jsonStream` | Personal-best / session-best splits and speeds. | ❌ | _TBD — Phase 2 group 2_ |
| `TopThree.jsonStream` | Top-3-on-track summary (position-order, gaps). | ❌ | _TBD — Phase 2 group 2_ |
| `LapCount.jsonStream` | Current / total session laps. | ❌ | _TBD — Phase 2 group 2_ |
| `LapSeries.jsonStream` | Per-driver lap-by-lap position series. | ❌ | _TBD — Phase 2 group 2_ |
| `ExtrapolatedClock.jsonStream` | Extrapolated session clock (remaining time, running flag). | ❌ | _TBD — Phase 2 group 2_ |
| `TyreStintSeries.jsonStream` | Per-driver tyre stint series (compound, new/used, lap counters). | ✅ | deep |
| `CurrentTyres.jsonStream` | Currently-fitted tyre per driver. | ❌ | _TBD — Phase 2 group 3_ |
| `PitLaneTimeCollection.jsonStream` | Pit-lane timing per pit event. | ❌ | _TBD — Phase 2 group 3_ |
| `CarData.z.jsonStream` | Compressed per-car telemetry (throttle, brake, RPM, gear, speed, DRS). | ❌ | _TBD — Phase 2 group 4_ |
| `Position.z.jsonStream` | Compressed per-car XYZ positions on track. | ❌ | _TBD — Phase 2 group 4_ |
| `RaceControlMessages.jsonStream` | Race Control messages: flags, investigations, penalties. | ❌ | _TBD — Phase 2 group 5_ |
| `TrackStatus.jsonStream` | Current track status code (all-clear, yellow, SC, VSC, red). | ❌ | _TBD — Phase 2 group 5_ |
| `TlaRcm.jsonStream` | Per-driver abbreviated race-control messages (TLA-indexed). | ❌ | _TBD — Phase 2 group 5_ |
| `DriverList.jsonStream` | Driver identity: TLA, number, name, team, team colour. | ✅ | deep |
| `WeatherData.jsonStream` | Air/track temperature, humidity, wind speed/direction, rainfall. | ❌ | _TBD — Phase 2 group 7_ |
| `Heartbeat.jsonStream` | Feed connection keep-alive. | ❌ | _TBD — Phase 2 group 7_ |
| `TeamRadio.jsonStream` | Team radio clip metadata (driver, URL, timestamp). | ❌ | _TBD — Phase 2 group 8_ |
| `AudioStreams.jsonStream` | Available audio stream URLs (commentary feeds). | ❌ | _TBD — Phase 2 group 8_ |
| `ContentStreams.jsonStream` | Available video/content stream URLs. | ❌ | _TBD — Phase 2 group 8_ |
| `ChampionshipPrediction.jsonStream` | Live championship-standings prediction. | ❌ | _TBD — Phase 2 group 9_ |
```

_TBD placeholders in this table are intentional: they get filled in by the Phase 2 task that investigates each group, which keeps each commit self-contained._

- [ ] **Step 2: Sanity-check the table**

Run:
```bash
grep -c '^| `' docs/data-feed-reference.md
```

Expected: `27` (one row per feed). If not 27, fix missing/extra rows before committing.

- [ ] **Step 3: Checkpoint — ask user to review**

Wait for sign-off.

- [ ] **Step 4: Commit**

```bash
git add docs/data-feed-reference.md
git commit -m "$(cat <<'EOF'
docs: add all-27-feeds summary table to data feed reference

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task 1.3: Append the cross-reference index

**Files:**
- Modify: `docs/data-feed-reference.md` (append)

- [ ] **Step 1: Draft the cross-reference index**

Append to `docs/data-feed-reference.md`:

```markdown

## Cross-reference: "I want X — which feed(s)?"

Organized by the question you're likely to ask, not by filename. Feeds already fetched by CI are marked ✅; feeds available only via the full-archive download are marked ❌.

- **Driver identity (TLA, number, name, team, colour)?** → `DriverList.jsonStream` ✅
- **Session metadata (name, start time, circuit)?** → `SessionInfo.json` ✅
- **Official finishing classification?** → `SessionData.jsonStream` ❌ (see also `TimingData.Line` as a last-known proxy ✅)
- **Live retirement / DNF flag?** → `TimingData.Retired` ✅
- **Per-lap lap times, sector times, gaps?** → `TimingData.jsonStream` ✅
- **Personal bests / session bests?** → `TimingStats.jsonStream` ❌
- **Per-driver tyre history (compound, new/used, laps)?** → `TyreStintSeries.jsonStream` ✅
- **Currently-fitted tyre?** → `CurrentTyres.jsonStream` ❌
- **Pit-stop timing?** → `PitLaneTimeCollection.jsonStream` ❌ + `TimingData` ✅
- **Live track status (green/yellow/SC/VSC/red)?** → `TrackStatus.jsonStream` ❌
- **Race Control decisions (investigations, penalties, flags)?** → `RaceControlMessages.jsonStream` ❌
- **Weather (temp, wind, rainfall)?** → `WeatherData.jsonStream` ❌
- **Per-car telemetry (throttle/brake/RPM/gear/DRS/speed)?** → `CarData.z.jsonStream` ❌ (compressed)
- **Per-car position on track (XYZ)?** → `Position.z.jsonStream` ❌ (compressed)
- **Team radio clips?** → `TeamRadio.jsonStream` ❌
- **Current / total session laps?** → `LapCount.jsonStream` ❌
- **Championship predictions?** → `ChampionshipPrediction.jsonStream` ❌
```

- [ ] **Step 2: Sanity-check**

Run:
```bash
grep -c '^- \*\*' docs/data-feed-reference.md
```

Expected: ≥ 15 cross-reference bullets. Visually confirm the index reads smoothly.

- [ ] **Step 3: Checkpoint — ask user to review**

Wait for sign-off.

- [ ] **Step 4: Commit**

```bash
git add docs/data-feed-reference.md
git commit -m "$(cat <<'EOF'
docs: add cross-reference index to data feed reference

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Phase 2 — Feed groups

Nine tasks, one per group. Each task: investigate every feed in the group with real data, write its section using the per-feed template (top of this plan), update the summary table's `Depth` column for those feeds from `_TBD — Phase 2 group N_` to the appropriate label, checkpoint, commit.

**Investigation recipe (run at the top of every Phase 2 task):**

1. Start an ephemeral Python session:
   ```bash
   cd precompute && uv run python
   ```
2. For each feed file in the group:
   ```python
   from pathlib import Path
   import sys; sys.path.insert(0, "src")
   from f1.parse import parse_stream
   from f1.reduce import reduce_events

   p = Path("../seasons/2026/2026-03-29_Japanese_Grand_Prix/2026-03-29_Race/<FeedName>.jsonStream")
   events = parse_stream(p)
   print(f"{len(events)} events")
   for e in events[:5]:
       print(e.timestamp_ms, e.data)

   state = reduce_events(events)
   print("reduced keys:", list(state.keys())[:10])
   ```
3. For compressed feeds only (`CarData.z`, `Position.z`):
   ```python
   import base64, zlib, json
   blob = events[0].data["Entries"][0]["Data"]  # or similar — adjust per actual key
   decoded = zlib.decompress(base64.b64decode(blob), -zlib.MAX_WBITS)
   print(json.loads(decoded))
   ```
4. For the 3 static `.json` files (`SessionInfo.json`, `Index.json`, `ArchiveStatus.json`) use `json.loads(Path(...).read_text(encoding="utf-8-sig"))` directly — they are not streams.
5. Skim 20–50 events looking for: string vs bool inconsistencies, empty/no-op updates, `_deleted` usage, late bursts past session end, per-driver silence mid-session.
6. Record one truncated example event per feed (~5 lines max after truncation).

**After investigating, every Phase 2 task must:**
- Write a `## <FeedName>` section per feed using the per-feed template.
- Update the corresponding row(s) in the summary table (`_TBD — Phase 2 group N_` → `deep`/`medium`/`shallow`).
- Attach pre-known quirks to the correct feed per the mapping at the top of this plan.
- Keep each feed section within 6–25 lines (trim "Could power" first if too long).
- Checkpoint with the user before committing.

### Task 2.1: Group 1 — Session & weekend metadata (5 feeds)

**Feeds:** `SessionInfo.json`, `Index.json`, `ArchiveStatus.json`, `SessionData.jsonStream`, `SessionStatus.jsonStream`.

**Files:**
- Modify: `docs/data-feed-reference.md` (append group section; update summary table rows)

- [ ] **Step 1: Investigate all 5 feeds**

Follow the investigation recipe for each of the 5 files in `seasons/2026/2026-03-29_Japanese_Grand_Prix/2026-03-29_Race/`. Note which fields look most useful, which look noisy.

**Special attention for this group:**
- `SessionData` — confirm whether it carries the official classification field (relevant to pre-known quirk #4: stewards-reclassified DNFs). If yes, note it in `SessionData`'s "Known quirks" as the official-classification source.
- `SessionStatus` — observe how red-flag / finished transitions look; this is a secondary-example candidate from a different session type, but for now document what's in the Japan 2026 Race.

- [ ] **Step 2: Draft the group header and 5 feed sections**

Append to `docs/data-feed-reference.md`:

```markdown

## Session & weekend metadata

Feeds in this group describe the session's overall shape — when it runs, what's in it, whether it's running, and whether the archive is complete.

### `SessionInfo.json`

**Fetched by CI:** ✅ yes (via `seasons/fetch_race.py`)
**Compressed:** no
**Investigation depth:** deep — used in production

[Follow template from plan header; fill in Summary, Example, Known quirks, Feeds these features, Could power.]

### `Index.json`

[Same template. Observed from investigation. Not stream — single JSON object.]

### `ArchiveStatus.json`

[Same template.]

### `SessionData.jsonStream`

[Same template. **Include quirk #4 note:** the official classification for stewards-reclassified DNFs likely lives here, per spec §9 risk note.]

### `SessionStatus.jsonStream`

[Same template.]
```

- [ ] **Step 3: Update summary table**

For each of the 5 feeds, change the Depth column from `_TBD — Phase 2 group 1_` to the appropriate label (`deep` for `SessionInfo`; `medium` for the other 4 after this investigation).

- [ ] **Step 4: Sanity-check**

Run:
```bash
grep -c '^### `' docs/data-feed-reference.md
grep -c '_TBD — Phase 2 group 1_' docs/data-feed-reference.md
```

Expected: first command shows 5 (one per group-1 feed). Second command shows 0 (all group-1 TBDs resolved).

Also confirm quirk #4 is attached to at least one feed:
```bash
grep -n 'classification' docs/data-feed-reference.md
```

- [ ] **Step 5: Checkpoint — ask user to review the group**

Show the user the 5 new sections + the updated table rows. Wait for sign-off on both content quality and the per-feed template as applied in practice. If the template itself needs adjusting, apply the fix consistently to all 5 entries before committing.

- [ ] **Step 6: Commit**

```bash
git add docs/data-feed-reference.md
git commit -m "$(cat <<'EOF'
docs: document session & weekend metadata feeds (group 1/9)

Covers SessionInfo, Index, ArchiveStatus, SessionData, SessionStatus.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task 2.2: Group 2 — Timing & classification (7 feeds)

**Feeds:** `TimingData.jsonStream`, `TimingAppData.jsonStream`, `TimingStats.jsonStream`, `TopThree.jsonStream`, `LapCount.jsonStream`, `LapSeries.jsonStream`, `ExtrapolatedClock.jsonStream`.

**Files:**
- Modify: `docs/data-feed-reference.md` (append; update summary table)

- [ ] **Step 1: Investigate all 7 feeds**

Follow the investigation recipe. `TimingData` and `TimingAppData` are already in production, so the summary and example should match what `precompute/src/f1/build.py` and `inventory.py` use — cross-check with those files.

**Special attention:**
- `TimingData` — attach pre-known quirks #3 and #4 (canonical `Retired`, `Line` ≠ classification). Mention that this feed was added to CI fetch in the strategy-chart PR.
- `TimingAppData` — confirm its role in driver/stint derivation; reference `precompute/src/f1/inventory.py` as the in-repo consumer.
- `LapSeries` — inspect whether it's per-lap position per driver; if so, flag this in "Could power" as the basis for a position trace.

- [ ] **Step 2: Draft the group section**

Append a `## Timing & classification` header with 7 feed sections, each using the template.

- [ ] **Step 3: Update summary table**

Change `_TBD — Phase 2 group 2_` to the appropriate label for each of the 7 feeds (`deep` for `TimingData` and `TimingAppData`; `medium` for the other 5).

- [ ] **Step 4: Sanity-check**

Run:
```bash
grep -c '_TBD — Phase 2 group 2_' docs/data-feed-reference.md
grep -n 'Retired' docs/data-feed-reference.md | head
```

Expected: first command shows 0. Second confirms quirk #3 is attached to `TimingData`.

- [ ] **Step 5: Checkpoint — ask user to review**

- [ ] **Step 6: Commit**

```bash
git add docs/data-feed-reference.md
git commit -m "$(cat <<'EOF'
docs: document timing & classification feeds (group 2/9)

Covers TimingData, TimingAppData, TimingStats, TopThree, LapCount,
LapSeries, ExtrapolatedClock.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task 2.3: Group 3 — Tyres & pit (3 feeds)

**Feeds:** `TyreStintSeries.jsonStream`, `CurrentTyres.jsonStream`, `PitLaneTimeCollection.jsonStream`.

**Files:**
- Modify: `docs/data-feed-reference.md` (append; update summary table)

- [ ] **Step 1: Investigate all 3 feeds**

Follow the investigation recipe. `TyreStintSeries` is in production; cross-check with `precompute/src/f1/inventory.py` for the `SessionStint` derivation.

**Special attention:**
- `TyreStintSeries` — attach pre-known quirks #1 (`TotalLaps` is cumulative) and #2 (mid-session silence after pit, observed RUS China Sprint 2026). Quote exactly: "Stint length = `TotalLaps - StartLaps`" from the spec.
- `PitLaneTimeCollection` — check whether it carries pit-entry/exit timestamps and whether those align with `TyreStintSeries` stint boundaries. This is a key appendix candidate (pit-stop timeline feature).
- `CurrentTyres` — disambiguate from `TyreStintSeries`: likely a "right now" snapshot vs. historical series.

- [ ] **Step 2: Draft the group section**

Append a `## Tyres & pit` header with 3 feed sections.

- [ ] **Step 3: Update summary table**

Change `_TBD — Phase 2 group 3_` to `deep` for `TyreStintSeries`, `medium` for the other two.

- [ ] **Step 4: Sanity-check**

Run:
```bash
grep -c '_TBD — Phase 2 group 3_' docs/data-feed-reference.md
grep -n 'cumulative' docs/data-feed-reference.md
```

Expected: first command shows 0. Second confirms quirk #1 attached to `TyreStintSeries`.

- [ ] **Step 5: Checkpoint — ask user to review**

- [ ] **Step 6: Commit**

```bash
git add docs/data-feed-reference.md
git commit -m "$(cat <<'EOF'
docs: document tyres & pit feeds (group 3/9)

Covers TyreStintSeries, CurrentTyres, PitLaneTimeCollection.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task 2.4: Group 4 — Telemetry (2 feeds, compressed)

**Feeds:** `CarData.z.jsonStream`, `Position.z.jsonStream`.

**Files:**
- Modify: `docs/data-feed-reference.md` (append; update summary table)

- [ ] **Step 1: Investigate both feeds (decode required)**

Follow the compressed-feed investigation sub-step. For each file:
- Parse the stream with `parse_stream`.
- The payload structure will look roughly like `{"Entries": [{"Utc": "...", "Cars": {...}}]}` or `{"Position": [...]}`. Open one event, base64-decode the wrapped blob, decompress, and `json.loads` the result.
- Capture one decoded example event for each feed (~5 lines). Note sample rate — observe how frequent events are (expect ~4 Hz for CarData, ~10 Hz for Position, but verify).

- [ ] **Step 2: Draft the group section**

Append a `## Telemetry` header with 2 feed sections. Both entries explicitly note the `.z.` format + decode snippet (referencing the primer). Attach pre-known quirk #6 to both.

- [ ] **Step 3: Update summary table**

Change `_TBD — Phase 2 group 4_` to `medium` for both.

- [ ] **Step 4: Sanity-check**

Run:
```bash
grep -c '_TBD — Phase 2 group 4_' docs/data-feed-reference.md
grep -n 'zlib' docs/data-feed-reference.md | head
```

Expected: first command shows 0. Second confirms decode reference appears in telemetry entries.

- [ ] **Step 5: Checkpoint — ask user to review**

- [ ] **Step 6: Commit**

```bash
git add docs/data-feed-reference.md
git commit -m "$(cat <<'EOF'
docs: document telemetry feeds (group 4/9)

Covers CarData.z, Position.z — compressed payloads, decode sample
included.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task 2.5: Group 5 — Race control (3 feeds)

**Feeds:** `RaceControlMessages.jsonStream`, `TrackStatus.jsonStream`, `TlaRcm.jsonStream`.

**Files:**
- Modify: `docs/data-feed-reference.md` (append; update summary table)

- [ ] **Step 1: Investigate all 3 feeds**

Follow the recipe.

**Special attention:**
- `RaceControlMessages` — look at message categories (flags, investigations, penalties, pit-lane closures). Note whether `Category` is an enum-like field.
- `TlaRcm` — appears to be TLA-indexed race-control messages. Disambiguate from `RaceControlMessages`: likely a driver-addressed subset (e.g. per-driver penalty notifications).
- `TrackStatus` — expect a small enum of status codes. Note the observed codes with their meanings (1 = all clear, 2 = yellow, 4 = SC, 5 = red, 6 = VSC — verify from the data).

- [ ] **Step 2: Draft the group section**

Append a `## Race control` header with 3 feed sections.

- [ ] **Step 3: Update summary table**

Change `_TBD — Phase 2 group 5_` to `medium` for all three.

- [ ] **Step 4: Sanity-check**

Run:
```bash
grep -c '_TBD — Phase 2 group 5_' docs/data-feed-reference.md
```

Expected: 0.

- [ ] **Step 5: Checkpoint — ask user to review**

- [ ] **Step 6: Commit**

```bash
git add docs/data-feed-reference.md
git commit -m "$(cat <<'EOF'
docs: document race control feeds (group 5/9)

Covers RaceControlMessages, TrackStatus, TlaRcm.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task 2.6: Group 6 — Drivers (1 feed)

**Feed:** `DriverList.jsonStream`.

**Files:**
- Modify: `docs/data-feed-reference.md` (append; update summary table)

- [ ] **Step 1: Investigate the feed**

Follow the recipe. `DriverList` is in production — cross-check with `precompute/src/f1/driver_meta.py`.

- [ ] **Step 2: Draft the section**

Append a `## Drivers` header with `DriverList` section. Single-feed group so keep the header lead short.

- [ ] **Step 3: Update summary table**

Change `_TBD — Phase 2 group 6_` to `deep` for `DriverList`.

- [ ] **Step 4: Sanity-check**

Run:
```bash
grep -c '_TBD — Phase 2 group 6_' docs/data-feed-reference.md
```

Expected: 0.

- [ ] **Step 5: Checkpoint — ask user to review**

- [ ] **Step 6: Commit**

```bash
git add docs/data-feed-reference.md
git commit -m "$(cat <<'EOF'
docs: document drivers feed (group 6/9)

Covers DriverList.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task 2.7: Group 7 — Environment (2 feeds)

**Feeds:** `WeatherData.jsonStream`, `Heartbeat.jsonStream`.

**Files:**
- Modify: `docs/data-feed-reference.md` (append; update summary table)

- [ ] **Step 1: Investigate both feeds**

Follow the recipe.

**Special attention:**
- `WeatherData` — observe sample rate. Field names likely include `AirTemp`, `TrackTemp`, `Humidity`, `WindSpeed`, `WindDirection`, `Rainfall`. Note if `Rainfall` is a boolean, a count, or mm/hr.
- `Heartbeat` — tiny feed. Just a connection keep-alive. Note its minimal role — probably useless for features but present in every session. If the "Environment" grouping feels forced at this point, mention in the group lead that Heartbeat lives here by elimination, not topical fit.

- [ ] **Step 2: Draft the group section**

Append a `## Environment` header with 2 feed sections.

- [ ] **Step 3: Update summary table**

Change `_TBD — Phase 2 group 7_` to `medium` for both.

- [ ] **Step 4: Sanity-check**

Run:
```bash
grep -c '_TBD — Phase 2 group 7_' docs/data-feed-reference.md
```

Expected: 0.

- [ ] **Step 5: Checkpoint — ask user to review**

- [ ] **Step 6: Commit**

```bash
git add docs/data-feed-reference.md
git commit -m "$(cat <<'EOF'
docs: document environment feeds (group 7/9)

Covers WeatherData and Heartbeat.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task 2.8: Group 8 — Audio / video (3 feeds)

**Feeds:** `TeamRadio.jsonStream`, `AudioStreams.jsonStream`, `ContentStreams.jsonStream`.

**Files:**
- Modify: `docs/data-feed-reference.md` (append; update summary table)

- [ ] **Step 1: Investigate all 3 feeds**

Follow the recipe.

**Special attention:**
- `TeamRadio` — captures are per-clip metadata with URLs (likely to F1's CDN). Note whether URLs are absolute or relative, whether they require authentication, and whether they persist post-race.
- `AudioStreams` / `ContentStreams` — likely commentary / video stream manifests. Note structure (URL, language, format). These are unlikely to power a feature in this static-site project (no backend to proxy streams), but document faithfully.

- [ ] **Step 2: Draft the group section**

Append a `## Audio / video` header with 3 feed sections.

- [ ] **Step 3: Update summary table**

Change `_TBD — Phase 2 group 8_` to `medium` for all three.

- [ ] **Step 4: Sanity-check**

Run:
```bash
grep -c '_TBD — Phase 2 group 8_' docs/data-feed-reference.md
```

Expected: 0.

- [ ] **Step 5: Checkpoint — ask user to review**

- [ ] **Step 6: Commit**

```bash
git add docs/data-feed-reference.md
git commit -m "$(cat <<'EOF'
docs: document audio/video feeds (group 8/9)

Covers TeamRadio, AudioStreams, ContentStreams.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task 2.9: Group 9 — Predictions (1 feed)

**Feed:** `ChampionshipPrediction.jsonStream`.

**Files:**
- Modify: `docs/data-feed-reference.md` (append; update summary table)

- [ ] **Step 1: Investigate the feed**

Follow the recipe. Expect a live-updated prediction of championship standings based on the current session. Note update cadence and shape.

- [ ] **Step 2: Draft the section**

Append a `## Predictions` header with `ChampionshipPrediction` section.

- [ ] **Step 3: Update summary table**

Change `_TBD — Phase 2 group 9_` to `medium` for `ChampionshipPrediction`.

- [ ] **Step 4: Sanity-check**

Run:
```bash
grep -c '_TBD — Phase 2 group 9_' docs/data-feed-reference.md
grep -c '_TBD' docs/data-feed-reference.md
```

Expected: both 0 (the whole table is now filled in).

- [ ] **Step 5: Checkpoint — ask user to review**

- [ ] **Step 6: Commit**

```bash
git add docs/data-feed-reference.md
git commit -m "$(cat <<'EOF'
docs: document predictions feed (group 9/9)

Covers ChampionshipPrediction. Completes the per-feed inventory.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Phase 3 — Cross-feed opportunities appendix and final review

### Task 3.1: Draft the cross-feed opportunities appendix

**Files:**
- Modify: `docs/data-feed-reference.md` (append)

- [ ] **Step 1: Collect opportunities surfaced during Phase 2**

Re-read the `Could power` entries across all 27 feeds. Group by theme — anything that needs 2+ feeds is an appendix candidate. Discard trivially-already-possible ideas.

- [ ] **Step 2: Draft the appendix section**

Append to `docs/data-feed-reference.md`:

```markdown

## Cross-feed opportunities

Feature ideas that need two or more feeds. Each entry: pitch, feeds required (with ✅/❌ for currently-fetched), and one "verify first" note that prevents premature implementation.

**None of these is committed work** — they are the menu the user scans when deciding what to build next.

### Per-lap position trace

[1-line pitch + feeds required + verify-first note.]

### Pit-stop timeline annotations

[...]

### Weather-vs-lap-time overlay

[...]

### Red-flag / SC / VSC overlay on lap timeline

[...]

### Live gap-to-leader chart (historical)

[...]

### Stewards-reclassified finishing positions

[...]

[Add more entries as surfaced during Phase 2. Aim for 5–10 total; trim if padding.]
```

- [ ] **Step 3: Sanity-check**

Run:
```bash
grep -c '^### ' docs/data-feed-reference.md
wc -l docs/data-feed-reference.md
```

Expected: number of `### ` headings = 27 feed sections + N appendix entries + 0 others (from top-matter). Line count within 400–700 range.

- [ ] **Step 4: Checkpoint — ask user to review**

Wait for sign-off.

- [ ] **Step 5: Commit**

```bash
git add docs/data-feed-reference.md
git commit -m "$(cat <<'EOF'
docs: add cross-feed opportunities appendix to data feed reference

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task 3.2: Self-review pass

**Files:**
- Modify: `docs/data-feed-reference.md` (inline fixes if needed)

- [ ] **Step 1: Run the success-criteria checks**

Success criteria from spec §8. Run each:

```bash
# All 27 feeds present
grep -c '^## \|^### ' docs/data-feed-reference.md
# No residual TBDs
grep -c '_TBD' docs/data-feed-reference.md
grep -c 'TODO\|FIXME' docs/data-feed-reference.md
# No `minimal` depth labels (every feed should have been investigated)
grep -n 'depth:** minimal\|depth: minimal' docs/data-feed-reference.md
# File length in range
wc -l docs/data-feed-reference.md
```

Expected: third + fourth grep commands produce nothing; file length between 400 and 700 lines.

- [ ] **Step 2: Pre-known quirks cross-check**

For each of the 7 pre-known quirks, confirm it's present somewhere in the doc:

```bash
grep -n 'cumulative\|total laps\|stint length' docs/data-feed-reference.md    # #1
grep -n 'silence\|stop emitting\|RUS' docs/data-feed-reference.md               # #2
grep -n 'canonical DNF\|Retired' docs/data-feed-reference.md                     # #3
grep -n 'classification\|stewards' docs/data-feed-reference.md                   # #4
grep -n 'normalize\|"true"\|bool' docs/data-feed-reference.md                    # #5
grep -n 'zlib\|base64' docs/data-feed-reference.md                               # #6
grep -n 'BOM\|HH:MM:SS' docs/data-feed-reference.md                              # #7
```

Each command must return at least one match. If any returns nothing, add the missing quirk to the relevant feed.

- [ ] **Step 3: Placeholder scan**

Look for: placeholder language from the plan template ("[Same template.]", "[...]"), incomplete sentences, dangling TODO/TBD/FIXME. Fix inline.

- [ ] **Step 4: Internal consistency pass**

Read through once, looking for:
- Contradictions between the summary table and per-feed sections (e.g. table says "deep", section says "shallow").
- Feeds mentioned in the cross-reference index but missing from the table.
- Features in "Could power" that are already implemented (should be in "Feeds these features" instead).

Fix inline.

- [ ] **Step 5: If any fixes were applied, commit**

Only commit if Step 2–4 produced edits. Otherwise, skip to Task 3.3.

```bash
git add docs/data-feed-reference.md
git commit -m "$(cat <<'EOF'
docs: self-review polish on data feed reference

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task 3.3: Open the PR

- [ ] **Step 1: Confirm branch state**

Run:
```bash
git log --oneline main..HEAD
git status
```

Expected: 12–13 commits ahead of main, working tree clean.

- [ ] **Step 2: Push the branch**

Ask the user for explicit approval, then:
```bash
git push -u origin docs/data-feed-reference
```

- [ ] **Step 3: Open the PR**

```bash
gh pr create --title "docs: add data feed reference" --body "$(cat <<'EOF'
## Summary
- Adds `docs/data-feed-reference.md` — a grounded menu of all 27 live-timing feeds with real examples from Japan 2026 Race, known quirks, and cross-feed opportunity ideas.
- Captures all pre-known quirks from the brainstorming prompt (TyreStintSeries cumulative-laps gotcha, TimingData.Retired semantics, `.z.` decode recipe, etc.).
- Pure documentation — no code, no fetch-list, no pipeline, no site changes.

## Test plan
- [ ] Summary table lists all 27 feeds with non-TBD depth labels.
- [ ] Cross-reference index answers the common "I want X, which feed?" questions.
- [ ] Each feed section fits the template: fetched-by-CI flag, compressed flag, depth label, summary, example, quirks, features.
- [ ] Pre-known quirks #1–#7 from NEXT-TASK-PROMPT.md all appear in the doc.
- [ ] Cross-feed opportunities appendix has 5–10 feature ideas, each with required feeds and a "verify first" note.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 4: Report the PR URL to the user**

Done.

---

## Self-review check (planner-side, applied to this plan document)

- **Spec coverage:** Every spec section has a task. §1/§2 motivation → covered in the file's intro (Task 1.1). §3 scope & non-goals → enforced throughout (no-code constraint stated in plan header + each commit). §4 file location + structure → Task 1.1 (create + primer), Task 1.2 (summary table), Task 1.3 (cross-reference index), Phase 2 tasks (feed sections), Task 3.1 (appendix). §4.3 per-feed template → Phase 2 tasks all reference the template at top of plan. §5 investigation methodology → bundled into Phase 2 "investigation recipe" at top of Phase 2. §6 build sequence → matches Phase 1 → Phase 2 (one task per group) → Phase 3. §7 risks → mitigations baked into tasks (length check in 3.2 success criteria; quirks cross-check in 3.2 Step 2; season-drift framing in Task 1.1 primer). §8 success criteria → Task 3.2 Step 1 runs each check as a shell command.
- **Placeholders:** The Phase 2 task bodies use bracketed shorthand like `[Same template.]` for the per-section content — this is intentional because the template is defined once at the top of the plan and the actual content is a factual writeup of the investigation output, which can't be pre-written. The per-feed template itself is fully spelled out.
- **Type/name consistency:** "Japan 2026 Race" as the reference session is used consistently. Depth labels (`deep`/`medium`/`shallow`/`minimal`) match the spec. Quirk numbering (#1–#7) matches the spec and NEXT-TASK-PROMPT.md. The summary-table sentinel `_TBD — Phase 2 group N_` is used identically in Task 1.2 and resolved in the matching Phase 2 task.

No gaps found. Proceeding to execution choice.
