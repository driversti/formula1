# Data Feed Reference — Design

**Date:** 2026-04-18
**Status:** Approved, ready for implementation plan.
**Branch:** `docs/data-feed-reference`

## 1. Summary

Produce `docs/data-feed-reference.md`: a single-file, grounded menu of
every `.jsonStream` / `.json` file F1 publishes per session. Each feed
gets a short entry with a real example event drawn from on-disk data,
known quirks, and the features it already powers or could power.

The goal is a reference, not an exhaustive code analysis. When the user
asks "can we build X?", we open this doc, see which feeds X needs,
whether we trust them, and whether `seasons/fetch_race.py` needs
extending.

## 2. Motivation

Today, feed knowledge is scattered: partly in `seasons/download_f1.py`
(the canonical list), partly in existing precompute code (the five feeds
we already use), partly in the user's head, and partly nowhere — most of
the 22 non-production feeds have never been opened in anger. Each new
feature brainstorm re-discovers the landscape.

A single grounded reference front-loads that discovery once. Future
brainstorms cite the doc ("check `data-feed-reference.md#timing-data`")
rather than starting from scratch.

## 3. Scope & non-goals

**In scope:**
- Every feed in `download_f1.py::SESSION_FILES` (27 feeds).
- Real example events drawn from **Japanese GP 2026 Race** on disk
  (`seasons/2026/2026-03-29_Japanese_Grand_Prix/2026-03-29_Race/`).
- Known quirks from the current session's task prompt, captured verbatim
  in the relevant feeds.
- Speculative "could power" entries per feed, plus a cross-feed
  opportunities appendix.

**Explicit non-goals:**
- **No code.** No changes to precompute, site, fetch script, or Makefile
  as part of this task. If a "quick win" feature becomes obvious during
  investigation, it gets noted in the appendix — not implemented.
- **No season-drift audit.** The doc describes Japan 2026 Race behaviour.
  Known schema differences across seasons get flagged briefly (e.g. "not
  emitted in 2018") but we don't systematically regression-test each
  feed across every on-disk season.
- **No exhaustive field dictionary.** We capture the shape and the
  "gotcha" fields, not every leaf. A reader who needs every field opens
  the file.

## 4. Output file

**Location:** `docs/data-feed-reference.md` (single file).
**Target length:** ~400–600 lines. Each feed entry 6–25 lines; top-matter
and appendix add ~80–120 lines.

### 4.1 Top-matter structure

1. **Intro** (≤1 short paragraph). Purpose of the doc + one sentence on
   what it is NOT (no code analysis, no season-drift audit).
2. **Stream format primer** (~15 lines). Explains once:
   - Line format: `HH:MM:SS.mmm{<json>}`, BOM-prefixed.
   - `parse_stream` / `reduce_events` helper locations.
   - `.z.` suffix → base64-encoded zlib-deflated JSON; decode via
     `zlib.decompress(base64.b64decode(blob), -zlib.MAX_WBITS)`.
   - Boolean normalization (sometimes string, sometimes bool).
   - `_deleted` key semantics in the reducer.
3. **Summary table** — single table, 27 rows. Columns:
   `Feed | One-line summary | Fetched by CI | Depth`.
   This is the scan-in-30-seconds menu.
4. **Cross-reference index** — organized by question, not filename.
   Example:
   - "Driver identity (TLA, team, number)?" → `DriverList`.
   - "Per-lap lap times?" → `TimingData` + `TimingAppData`.
   - "Pit stop timing?" → `PitLaneTimeCollection` + `TimingData`.
   - Aim for ~10–15 of the most common questions.

### 4.2 Feed grouping (ordering)

Grouped by role, in this order:

1. **Session & weekend metadata.** `SessionInfo`, `Index`, `SessionData`,
   `SessionStatus`, `ArchiveStatus`.
2. **Timing & classification.** `TimingData`, `TimingAppData`,
   `TimingStats`, `TopThree`, `LapCount`, `LapSeries`, `ExtrapolatedClock`.
3. **Tyres & pit.** `TyreStintSeries`, `CurrentTyres`,
   `PitLaneTimeCollection`.
4. **Telemetry.** `CarData.z`, `Position.z`.
5. **Race control.** `RaceControlMessages`, `TrackStatus`, `TlaRcm`.
6. **Drivers.** `DriverList`.
7. **Environment.** `WeatherData`, `Heartbeat`.
8. **Audio / video.** `TeamRadio`, `AudioStreams`, `ContentStreams`.
9. **Predictions.** `ChampionshipPrediction`.

Each group starts with a 1-sentence lead ("Feeds in this group describe
the session's overall shape — when it runs, what's in it, whether it's
complete.") then lists its feeds.

### 4.3 Per-feed template

```markdown
## TimingData.jsonStream

**Fetched by CI:** ✅ yes (via `seasons/fetch_race.py`)
**Compressed:** no
**Investigation depth:** deep — used in production

**Summary.** One-paragraph description of what the feed contains and
whether it's stateful (accumulated via `deep_merge`) or event-wise.

**Example event** (truncated, from Japan 2026 Race):
​```json
{"Lines": {"1": {"Line": 3, "NumberOfLaps": 45, "Retired": false,
 "LastLapTime": {"Value": "1:32.456", "PersonalFastest": false}}}}
​```

**Known quirks.**
- Bullet list. Include pre-known quirks from NEXT-TASK-PROMPT verbatim
  where they apply to this feed. Add anything observed during
  investigation. Quirks should note their observation context ("seen
  in Japan 2026 Race") when they can't be generalized.

**Feeds these features** (current): Race Strategy Chart — finishing
order, DNF flag.

**Could power** (speculative): per-lap position trace, gap-to-leader
chart, sector-time heatmap, personal-best timeline.
```

**Depth labels** (top of each entry):
- `deep` — feed is used in production code; we understand it thoroughly.
- `medium` — investigated thoroughly here via real data + reducer.
- `shallow` — opened and summarized but quirks may be incomplete.
- `minimal` — not examined on disk. Target state for this task: zero
  feeds land here (Japan 2026 has all 27).

### 4.4 Cross-feed opportunities appendix

A short section at the end listing feature ideas that need two or more
feeds. Each idea is 3–5 lines: feature name, one-line pitch, feeds
required (with ✅/❌ for currently-fetched), a "what we'd need to verify
first" note.

Examples of the flavour (not commitments):
- **Per-lap position trace.** `TimingData` (Line history) +
  `LapCount` (session lap boundaries). Verify: does `TimingData`
  emit `Line` updates every lap, or only on change?
- **Pit-stop timeline annotations.** `PitLaneTimeCollection` +
  `TyreStintSeries` + `TimingData`. Verify: does
  `PitLaneTimeCollection` carry stint-boundary timestamps we can
  align to stint start/end laps?
- **Weather-vs-lap-time overlay.** `WeatherData` + `TimingData`.
  Verify: sample rate of `WeatherData` updates during a race.

## 5. Investigation methodology

For each feed:

1. **Open the file** from
   `seasons/2026/2026-03-29_Japanese_Grand_Prix/2026-03-29_Race/`
   using `parse_stream` from `precompute/src/f1/parse.py`.
2. **Reduce if stateful.** For most feeds, apply `reduce_events` and
   confirm the reduced shape matches what a consumer would see.
3. **Decode compressed feeds.** For `CarData.z` and `Position.z`,
   base64-decode one payload then `zlib.decompress(data, -zlib.MAX_WBITS)`.
4. **Skim for quirks.** Read 20–50 events looking for: string vs bool
   inconsistencies, empty or no-op updates, `_deleted` usage, late
   bursts (many events after the session ends), mid-session silence
   (feed stops emitting for a driver), schema differences across event
   types.
5. **Capture one example.** Pick a representative event, truncate to
   ~5 lines, include in the entry.
6. **Record pre-known quirks.** Items 1–7 from `NEXT-TASK-PROMPT.md`
   are incorporated verbatim into the relevant feeds' Known Quirks
   sections. Mapping:
   - #1 cumulative `TotalLaps` → `TyreStintSeries`.
   - #2 mid-session silence after pit → `TyreStintSeries`.
   - #3 `Retired` is canonical DNF → `TimingData`.
   - #4 `Line` ≠ classification → `TimingData` + note in `SessionData`.
   - #5 bool-as-string → stream format primer (applies everywhere).
   - #6 `.z.` decode → stream format primer + each compressed feed.
   - #7 line format + BOM → stream format primer.

## 6. Build sequence

Section-by-section cadence to match user preference:

1. **Branch created** (done: `docs/data-feed-reference`).
2. **Draft intro + stream format primer + summary table + cross-reference
   index.** Commit. User sign-off.
3. **Draft group 1** (Session & weekend metadata, 5 feeds). Commit. User
   sign-off on the per-feed template applied in practice. Adjust if the
   template feels off.
4. **Draft remaining groups** (2 through 9), one group per commit, with
   sign-off after each. Eight more commits. If two small groups feel
   natural to bundle, bundle them and mention the bundling in the commit.
5. **Draft cross-feed opportunities appendix.** Commit. Sign-off.
6. **Spec self-review pass on the reference itself** — placeholders,
   internal contradictions, feed count = 27, all quirks from the prompt
   are attached to at least one feed.
7. **Open PR.** User squash-merges at their discretion.

Each commit: ask first, follow the user's workflow preference.

## 7. Risks

- **Season-specific schema drift.** A feed's shape in 2026 may not
  match its shape in 2018. Mitigation: the doc explicitly frames itself
  as "Japan 2026 Race behaviour" and flags schema deltas only when we
  stumble into them, not systematically.
- **"Could power" inflation.** Speculative features are easy to
  over-list and then drift into commitments. Mitigation: the appendix
  labels them as brainstorming fodder; each appendix entry carries a
  "verify first" note to prevent premature implementation.
- **Quirks drift.** A quirk observed in Japan 2026 Race may already
  have been fixed or might be specific to that session. Mitigation:
  quirks note their observation context when generalization is unclear.
- **Scope creep into investigation rabbit holes.** Each feed has a
  6–25-line ceiling. If a feed is pulling toward more, it's a signal
  to stop and add "investigate further" to the appendix.
- **Length ceiling overrun.** 27 × 25 = 675 lines at the worst case,
  plus top-matter and appendix. If the doc trends past ~700 lines,
  trim "could power" sections first.

## 8. Success criteria

- One committed file: `docs/data-feed-reference.md`.
- All 27 feeds from `SESSION_FILES` present with complete entries (no
  `minimal` depth labels remaining).
- All seven pre-known quirks from `NEXT-TASK-PROMPT.md` appear in at
  least one feed's Known Quirks (or in the stream format primer).
- Summary table and cross-reference index are scannable without
  scrolling to individual feed sections.
- Zero lines of code changed outside `docs/`.
- PR opened against `main` from `docs/data-feed-reference`.
