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

## Summary table

Every per-session feed F1 publishes, at a glance. **Fetched** means the file is pulled by `seasons/fetch_race.py` (i.e. available in CI and to fresh clones). **Depth** reflects how much this doc knows about the feed: `deep` = used in production, `medium` = investigated here with real data, `shallow` = opened and skimmed.

| Feed | Summary | Fetched by CI | Depth |
|------|---------|---------------|-------|
| `SessionInfo.json` | Session metadata: meeting, circuit, type, UTC start/end. | ✅ | deep |
| `Index.json` | Per-session file manifest; lists what's available in the archive. | ❌ | medium |
| `ArchiveStatus.json` | Archive completion flag for the session. | ❌ | medium |
| `SessionData.jsonStream` | Lap-boundary timestamps (Series) and session/track-status transitions (StatusSeries). | ❌ | medium |
| `SessionStatus.jsonStream` | Running session state: Inactive / Started / Finished / Finalised / Ends. | ❌ | medium |
| `TimingData.jsonStream` | Per-driver live timing: lap times, sector times, position, Retired. | ✅ | deep |
| `TimingAppData.jsonStream` | Per-driver tyre sets, stints, pit-in/out state, grid position. | ✅ | deep |
| `TimingStats.jsonStream` | Personal-best / session-best splits and speeds. | ❌ | medium |
| `TopThree.jsonStream` | Top-3-on-track summary (position-order, gaps). | ❌ | medium |
| `LapCount.jsonStream` | Current / total session laps. | ❌ | medium |
| `LapSeries.jsonStream` | Per-driver lap-by-lap position series. | ❌ | medium |
| `ExtrapolatedClock.jsonStream` | Extrapolated session clock (remaining time, running flag). | ❌ | medium |
| `TyreStintSeries.jsonStream` | Per-driver tyre stint series (compound, new/used, lap counters). | ✅ | deep |
| `CurrentTyres.jsonStream` | Currently-fitted tyre per driver (compound + new/used snapshot, updates on pit exit). | ❌ | medium |
| `PitLaneTimeCollection.jsonStream` | Per-pit-stop duration and lap number; insert/delete pair per stop, final state always empty. | ❌ | medium |
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

TBD placeholders in this table are intentional: they get filled in by the Phase 2 task that investigates each group, which keeps each commit self-contained.

## Cross-reference: "I want X — which feed(s)?"

Organized by the question you're likely to ask, not by filename. Feeds already fetched by CI are marked ✅; feeds available only via the full-archive download are marked ❌.

- **Driver identity (TLA, number, name, team, colour)?** → `DriverList.jsonStream` ✅
- **Session metadata (name, start time, circuit)?** → `SessionInfo.json` ✅
- **Official finishing classification?** → _unresolved_ — `SessionData.jsonStream` was expected to carry it but investigation (see Session & weekend metadata section) shows it does not. `TimingData.Line` ✅ is the current last-known-position proxy.
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

## Session & weekend metadata

Feeds in this group describe the session's overall shape — when it runs, what's in it, whether it's running, and whether the archive is complete.

### `SessionInfo.json`

**Fetched by CI:** ✅ yes (via `seasons/fetch_race.py`)
**Compressed:** no
**Investigation depth:** deep — used in production

**Summary.** A single static JSON object (UTF-8 BOM) containing nested meeting and session metadata: the meeting key, official name, round number, country, circuit short name, session type (`Race`, `Qualifying`, etc.), local start/end times, GMT offset, and the relative archive path. This is the canonical source for the race name, location, country, and session start time used throughout the precompute pipeline.

**Example event** (truncated, from Japan 2026 Race):
```json
{
  "Meeting": {
    "Key": 1281,
    "Name": "Japanese Grand Prix",
    "OfficialName": "FORMULA 1 ARAMCO JAPANESE GRAND PRIX 2026",
    "Location": "Suzuka",
    "Number": 3,
    "Country": { "Key": 4, "Code": "JPN", "Name": "Japan" },
    "Circuit": { "Key": 46, "ShortName": "Suzuka" }
  },
  "Key": 11253,
  "Type": "Race",
  "StartDate": "2026-03-29T14:00:00",
  "GmtOffset": "09:00:00",
  "Path": "2026/2026-03-29_Japanese_Grand_Prix/2026-03-29_Race/"
}
```

**Known quirks.**
- `StartDate` and `EndDate` are local time, not UTC; use `GmtOffset` to convert. The pipeline stores `StartDate` as-is and the site displays it without conversion.
- `SessionStatus` and `ArchiveStatus` fields appear in this file (mirroring their dedicated feeds) but the pipeline ignores them here.

**Feeds these features** (current): race name, location, country, session start date, GMT offset, and session path — all consumed by `precompute/src/f1/build.py::_load_session_info` and `build_race_manifest`.

**Could power** (speculative): session-type display labels, countdown timers, multi-round schedule pages.

### `Index.json`

**Fetched by CI:** ❌ no
**Compressed:** no
**Investigation depth:** medium — opened and inspected

**Summary.** A single static JSON object with one key, `Feeds`, whose value is a map from feed name to an object containing `KeyFramePath` (the static `.json` snapshot) and `StreamPath` (the live `.jsonStream` file). The Japan 2026 Race lists 32 feeds including several not seen in the archive directory (`TimingDataF1`, `DriverTracker`, `OvertakeSeries`, `PitStop`, `PitStopSeries`, `WeatherDataSeries`).

**Example event** (truncated, from Japan 2026 Race):
```json
{
  "Feeds": {
    "SessionInfo":   { "KeyFramePath": "SessionInfo.json",   "StreamPath": "SessionInfo.jsonStream" },
    "SessionData":   { "KeyFramePath": "SessionData.json",   "StreamPath": "SessionData.jsonStream" },
    "TimingData":    { "KeyFramePath": "TimingData.json",     "StreamPath": "TimingData.jsonStream" },
    "CarData.z":     { "KeyFramePath": "CarData.z.json",      "StreamPath": "CarData.z.jsonStream" }
  }
}
```

**Known quirks.**
- `Index.json` lists feeds that may not be present in the local archive (e.g. `TimingDataF1`, `OvertakeSeries`). Treat it as a discovery hint, not a guarantee of local availability.
- The keyframe `.json` files listed here (e.g. `SessionData.json`) are not downloaded by the current fetch script and may not exist on disk.

**Feeds these features** (current): none.

**Could power** (speculative): dynamic feed-availability checks, CI fetch-list generation, feed-completeness audits.

### `ArchiveStatus.json`

**Fetched by CI:** ❌ no
**Compressed:** no
**Investigation depth:** medium — opened and inspected

**Summary.** A minimal single-field JSON object whose `Status` value signals whether the session archive is finalized. In practice only `"Complete"` has been observed for finished sessions.

**Example event** (from Japan 2026 Race):
```json
{ "Status": "Complete" }
```

**Known quirks.**
- The complete set of possible values is unconfirmed from this session alone. `"Generating"` or similar intermediate values likely appear for in-progress or recently-finished sessions.
- A corresponding `ArchiveStatus` key also appears inside `SessionInfo.json` — they appear to be identical once the session is finalised.

**Feeds these features** (current): none.

**Could power** (speculative): CI gate to verify a session is fully archived before running a precompute job, health-check dashboards.

### `SessionData.jsonStream`

**Fetched by CI:** ❌ no
**Compressed:** no
**Investigation depth:** medium — all 62 events inspected

**Summary.** A stream of 62 events carrying two parallel series: `Series` (lap-boundary timestamps keyed by lap index, emitted once per lap as the race leader crosses the line) and `StatusSeries` (session and track status transitions, including `TrackStatus` — `Yellow`, `AllClear`, `SCDeployed` — and `SessionStatus` — `Started`, `Finished`, `Finalised`, `Ends`). The stream does NOT carry per-driver finishing positions; those come from `TimingData.Line`.

**Example event** (from Japan 2026 Race):
```json
{ "Series": { "5": { "Utc": "2026-03-29T05:21:57.825Z", "Lap": 6 } } }
{ "StatusSeries": { "2": { "Utc": "2026-03-29T05:14:02.078Z", "SessionStatus": "Started" } } }
```

**Known quirks.**
- The very first event has `Series` as a JSON array (`[]`) before switching to an object keyed by index for all subsequent events — a bootstrap artifact that the merge-patch reducer handles gracefully.
- `StatusSeries` mixes two distinct event types (`TrackStatus` and `SessionStatus`) in the same series with no discriminator field; callers must check which key is present.
- `TimingData.Line` (last-known on-track position) is what the pipeline currently uses for final finishing order. `SessionData` has no per-driver result field, so it cannot serve as the official classification source in this archive format. Pre-known quirk #4 note: the assumption that "the canonical classification lives in SessionData" is not supported by this feed's observed schema — `TimingData.Line` remains the best available proxy.

**Feeds these features** (current): none — lap boundaries and status transitions are not yet consumed by the pipeline.

**Could power** (speculative): lap-by-lap timeline axis, safety-car and yellow-flag overlays on the race strategy chart, session-clock reconstruction.

### `SessionStatus.jsonStream`

**Fetched by CI:** ❌ no
**Compressed:** no
**Investigation depth:** medium — all 5 events inspected

**Summary.** A very sparse stream (5 events for a full race) that carries a single `Status` field plus a redundant `Started` field tracking the current lifecycle state of the session. Observed values in Japan 2026 Race: `Inactive` → `Started` → `Finished` → `Finalised` → `Ends`.

**Example event** (from Japan 2026 Race):
```json
{ "Status": "Finalised", "Started": "Finished" }
```

**Known quirks.**
- The `Started` field does not reset to `"Inactive"` when the session ends; its last value was `"Finished"` even when `Status` became `"Finalised"` and `"Ends"`, making it an unreliable end-of-session signal on its own.
- `SessionData.StatusSeries` carries a superset of this information (including `TrackStatus` events) with UTC timestamps for each transition. Prefer `SessionData` for any timeline analysis.
- The set of `Status` values observed here overlaps with the `SessionStatus` field inside `SessionInfo.json` but the two feeds are independent.

**Feeds these features** (current): none.

**Could power** (speculative): live-session state banner, gating precompute jobs until a session reaches `"Finalised"`.

## Timing & classification

Feeds in this group carry per-driver lap and sector timing, on-track running order, and the signals used to derive final classification. Two of the seven feeds — `TimingData` and `TimingAppData` — are already consumed by the production precompute pipeline.

### `TimingData.jsonStream`

**Fetched by CI:** ✅ yes (via `seasons/fetch_race.py`, added by the race-strategy-chart PR)
**Compressed:** no
**Investigation depth:** deep — used in production

**Summary.** The main real-time per-driver timing stream. Each event is a merge-patch against a `Lines` dict keyed by racing number. A full driver record carries: `Line` (on-track running order), `Position` (string), `GapToLeader`, `IntervalToPositionAhead` (`{Value, Catching}`), `LastLapTime` (`{Value, Status, OverallFastest, PersonalFastest}`), `BestLapTime` (`{Value, Lap}`), `NumberOfLaps`, `NumberOfPitStops`, `Retired`, `InPit`, `PitOut`, `Stopped`, `Status` (bitmask), `Sectors` (array/dict of `{Value, Status, OverallFastest, PersonalFastest, Segments}`), and `Speeds` (`I1`, `I2`, `FL`, `ST` speed traps). Most events are sparse patches updating only changed fields.

**Example event** (Japan 2026 Race, ts 4020220 ms):
```json
{ "Lines": { "10": {
    "LastLapTime": { "Value": "1:35.436", "PersonalFastest": true },
    "BestLapTime":  { "Value": "1:35.436", "Lap": 2 },
    "Sectors": { "2": { "Value": "18.023", "PersonalFastest": true } },
    "NumberOfLaps": 2
} } }
```

**Known quirks.**
- **Quirk #3 (canonical DNF flag):** `Retired` is the authoritative DNF signal. Do not infer retirement from lap counts, stint truncation, or gaps; only `Retired: true` is reliable.
- **Quirk #4 (finishing classification):** `Line` is the last-known on-track position number, not the official stewards' classification. Drivers who are DNF but later awarded a finishing position by stewards will have `Retired: true` and a stale `Line` value. No field in this archive format carries the official final classification; `Line` is the best available proxy. (See `SessionData.jsonStream` note in the Session & weekend metadata section.)
- `Retired` arrives as Python `bool` in this feed; normalize defensively anyway.
- The bootstrap event (timestamp ~2839 ms) emits `Lines: {}` with an empty object before any driver data populates.
- Sector sub-fields use both array (in the first full-state event) and dict (in subsequent patches) shapes for the `Sectors` key — the merge reducer handles this transparently.
- `BestLapTime` carries a `Lap` field (lap number of the personal best) which is absent from `LastLapTime`.

**Feeds these features** (current): final finishing position (`Line`) and DNF flag (`Retired`) for the race strategy chart, consumed by `precompute/src/f1/driver_meta.py::extract_final_positions_and_retirements`. Lap count per driver (`NumberOfLaps`) consumed by `driver_meta.py::extract_lap_counts` for stint reconciliation.

**Could power** (speculative): live lap-time leaderboard, sector-by-sector timing breakdowns, gap-to-leader trace, pit-stop detection overlay.

### `TimingAppData.jsonStream`

**Fetched by CI:** ✅ yes (via `seasons/fetch_race.py`)
**Compressed:** no
**Investigation depth:** deep — used in production

**Summary.** Per-driver supplemental timing data focused on tyre stint tracking and grid position. `Lines` dict keyed by racing number. Before race start: each driver entry carries `GridPos` (string, their starting grid slot) and `RacingNumber`. Once on-track: a `Stints` structure appears — initially a list in the first event, then updated as a dict keyed by stint index. Each stint object contains `Compound`, `New` (string `"true"`/`"false"`), `TyresNotChanged`, `StartLaps`, `TotalLaps`, `LapFlags`, and (once the stint accumulates laps) `LapTime` and `LapNumber`. Between stint patches the feed also emits `Line` position updates.

**Example event** (Japan 2026 Race, ts 3303189 ms — race start):
```json
{ "Lines": { "12": { "Stints": [
    { "Compound": "MEDIUM", "New": "true", "TyresNotChanged": "0",
      "TotalLaps": 0, "StartLaps": 0, "LapFlags": 0 }
] } } }
```

**Known quirks.**
- `Stints` is a **list** in the first full-state event, then a **dict** keyed by stint index string (`"0"`, `"1"`, …) in all subsequent patches. The merge reducer promotes list→dict, so the reduced state is always dict-indexed. `precompute/src/f1/inventory.py::extract_session_stints` sorts by these integer-keyed indices.
- `New` is a string (`"true"` / `"false"`), not a bool. `inventory.py::_to_bool` normalizes it.
- `GridPos` is present only in the very first broadcast event (before the session starts). If the pre-race initialization event is missing, `GridPos` will be absent from the reduced state. `driver_meta.py::extract_grid_positions` handles the `""` empty-string case.
- Stints with non-canonical `Compound` values (e.g. an in-progress pit-stop state) are skipped by `extract_session_stints`.

**Feeds these features** (current): tyre inventory across the full weekend (`precompute/src/f1/inventory.py`), starting grid positions for the race (`driver_meta.py::extract_grid_positions`).

**Could power** (speculative): live tyre-change detection, pit-stop lap annotation, used-vs-new tyre indicator on the race strategy chart.

### `TimingStats.jsonStream`

**Fetched by CI:** ❌ no
**Compressed:** no
**Investigation depth:** medium

**Summary.** Per-driver session-best statistics stream. `Lines` dict keyed by racing number. Each driver record holds: `PersonalBestLapTime` (`{Value, Lap, Position}` — position is their session rank for that metric), `BestSectors` (dict of sector index → `{Value, Position}`), and `BestSpeeds` (speed trap keys `I1`, `I2`, `FL`, `ST` → `{Value, Position}`). Updates arrive immediately after each driver completes a lap, overwriting only the improved fields. The top-level state also carries `SessionType` (`"Race"`) and `Withheld` flag.

**Example event** (Japan 2026 Race, ts 3860205 ms):
```json
{ "Lines": { "81": { "BestSpeeds": { "I1": { "Position": 1, "Value": "280" } } } } }
```

Reduced state example for driver 1:
```json
{ "PersonalBestLapTime": { "Value": "1:33.208", "Lap": 52, "Position": 6 },
  "BestSectors": { "0": { "Position": 6, "Value": "33.929" }, "1": { "Position": 7, "Value": "41.281" }, "2": { "Position": 7, "Value": "17.739" } },
  "BestSpeeds": { "I1": { "Value": "289", "Position": 2 }, "FL": { "Value": "287", "Position": 5 }, "ST": { "Value": "304", "Position": 4 } } }
```

**Known quirks.**
- `Position` within each stat object is a session-wide rank (1 = fastest in session), not the on-track running position. It updates live as faster times are set.
- `BestSectors` keys are zero-indexed strings (`"0"`, `"1"`, `"2"`) in the reduced dict (promoted from an initial list, same list→dict pattern as `TimingAppData.Stints`).
- The bootstrap event emits all fields with empty `Value` strings before any real timing data arrives.

**Feeds these features** (current): none.

**Could power** (speculative): fastest-sector and speed-trap leaderboards, "purple / green / yellow" sector colour logic for a timing tower UI.

### `TopThree.jsonStream`

**Fetched by CI:** ❌ no
**Compressed:** no
**Investigation depth:** medium

**Summary.** A cut-down view of the top three cars on track, updated in real time. The `Lines` field starts as a list of three full driver objects (in position order), then subsequent patches arrive as a dict keyed by index string (`"0"`, `"1"`, `"2"`). Each entry carries: `RacingNumber`, `Tla`, `BroadcastName`, `FullName`, `Team`, `TeamColour`, `LapTime`, `LapState` (status bitmask), `DiffToAhead`, `DiffToLeader`, `OverallFastest`, `PersonalFastest`. Exactly 3 positions in the reduced state.

**Example event** (Japan 2026 Race, ts 3973882 ms):
```json
{ "Lines": { "1": { "DiffToAhead": "+1.821", "DiffToLeader": "+1.821" } } }
```

Reduced state (position 2, final):
```json
{ "RacingNumber": "16", "Tla": "LEC", "Team": "Ferrari", "TeamColour": "ED1131",
  "DiffToAhead": "+1.548", "DiffToLeader": "+15.270", "LapTime": "1:32.634",
  "LapState": 1089, "OverallFastest": false, "PersonalFastest": true }
```

**Known quirks.**
- `Lines` bootstrap is a list (3 elements); subsequent updates are dict-indexed. Same list→dict merge pattern as `TimingAppData.Stints` and `TimingStats.BestSectors`.
- `TeamColour` here is a hex string **without** the leading `#` (e.g. `"ED1131"`). The pipeline normalizes this in `driver_meta.py::_normalize_color` for `DriverList`, but `TopThree` is not currently consumed.
- `LapState` is a bitmask integer whose individual bit meanings are undocumented in this archive.

**Feeds these features** (current): none.

**Could power** (speculative): a broadcast-style top-3 overlay widget, live gap-to-leader display.

### `LapCount.jsonStream`

**Fetched by CI:** ❌ no
**Compressed:** no
**Investigation depth:** medium

**Summary.** A very small stream (53 events for a 53-lap race) carrying two fields: `CurrentLap` and `TotalLaps`. The first event sets both; all subsequent events update only `CurrentLap` once per lap. The reduced state is a flat dict `{"CurrentLap": 53, "TotalLaps": 53}`.

**Example events** (Japan 2026 Race):
```json
{ "CurrentLap": 1, "TotalLaps": 53 }
{ "CurrentLap": 2 }
```

**Known quirks.**
- `TotalLaps` is only present in the first event; it is not repeated on subsequent updates.
- Event count equals `TotalLaps` exactly (one event per lap). The stream ends as soon as `CurrentLap` reaches `TotalLaps`.

**Feeds these features** (current): none. (The per-driver lap count comes from `TimingData.NumberOfLaps`, not this feed.)

**Could power** (speculative): progress bar / lap counter widget, axis labels on the race strategy chart.

### `LapSeries.jsonStream`

**Fetched by CI:** ❌ no
**Compressed:** no
**Investigation depth:** medium

**Summary.** Per-driver position-by-lap series. Top-level keys of the stream are **driver racing numbers** (not wrapped in a `Lines` dict). Each driver object holds `RacingNumber` and `LapPosition`, a dict keyed by lap number (string) whose value is the driver's position (also a string). Updates arrive per-driver per-lap as each driver completes a lap. The reduced state has one entry per driver, each with a fully-populated `LapPosition` dict covering every lap they completed.

**Example events** (Japan 2026 Race):
```json
{ "12": { "RacingNumber": "12", "LapPosition": ["1"] } }
{ "81": { "LapPosition": { "1": "1" } } }
{ "14": { "LapPosition": { "1": "20" } } }
```

Reduced example for driver 12 (Antonelli, race winner):
```json
{ "RacingNumber": "12", "LapPosition": { "1": "6", "2": "5", ..., "49": "1", "53": "1" } }
```

**Known quirks.**
- The first event emits `LapPosition` as a list (bootstrap, index 0 = lap 1); subsequent patches are dict-keyed by lap number string. The merge reducer promotes list→dict, but the resulting key `"0"` corresponds to lap 1 in the list bootstrap. Callers must handle this off-by-one if consuming the raw reduced state directly.
- Position values are strings, not integers (`"1"` not `1`).
- Driver 12 started lap 1 in position `"6"` (grid position was 1 but the bootstrap reflects on-track order after the start rather than before). The first-lap figure may not match grid position.

**Feeds these features** (current): none.

**Could power** (speculative): position-trace chart (position vs lap for every driver), gap-to-leader animation, overtake-count statistics. This is the natural data source for a position-trace / "racing lines" visualization.

### `ExtrapolatedClock.jsonStream`

**Fetched by CI:** ❌ no
**Compressed:** no
**Investigation depth:** medium

**Summary.** A tiny stream (3 events for the Japan 2026 Race) carrying the session clock: `Utc` (ISO-8601 timestamp of the reference point), `Remaining` (`HH:MM:SS` string), and `Extrapolating` (bool). The first event is emitted when the session is initialized (well before the race starts); the third event marks when the clock transitions to actively counting down.

**All events** (Japan 2026 Race):
```json
{ "Utc": "2026-03-29T04:10:20.01Z", "Remaining": "02:00:00", "Extrapolating": false }
{ "Utc": "2026-03-29T05:14:03.011Z", "Remaining": "01:59:58" }
{ "Utc": "2026-03-29T05:14:04.01Z", "Remaining": "01:59:57", "Extrapolating": true }
```

**Known quirks.**
- **Quirk #5:** `Extrapolating` is a Python **bool** (`true`/`false`) in this feed — not a string. This is unlike many other boolean fields in the timing archive (e.g. `TimingAppData.Stints[n].New` which is the string `"true"`). Normalize defensively if consuming alongside other feeds.
- The second event omits `Extrapolating`, meaning the merge-patch state retains the previous `false` value until the third event sets it `true`.
- With only 3 events, the stream carries no lap-by-lap ticks — the clock must be extrapolated client-side from `Utc` + `Remaining` + the `Extrapolating` flag.
- `Remaining` format is `HH:MM:SS` (whole seconds only); sub-second precision is not provided.

**Feeds these features** (current): none.

**Could power** (speculative): session countdown timer, race-start detection (transition from `Extrapolating: false` to `true`), race-end time estimation.

## Tyres & pit

Feeds in this group describe per-driver tyre history and pit-lane activity. One of the three — `TyreStintSeries` — is already consumed by the production precompute pipeline as the source for the pre-race tyre inventory.

### `TyreStintSeries.jsonStream`

**Fetched by CI:** ✅ yes (via `seasons/fetch_race.py`)
**Compressed:** no
**Investigation depth:** deep — used in production

**Summary.** The authoritative tyre-stint record. State is keyed `Stints → {driver_number → {stint_idx → {Compound, New, TotalLaps, StartLaps, TyresNotChanged}}}`. The stream opens with a bootstrap that initialises all drivers to stint index `"0"`, then emits incremental patches approximately once per lap as `TotalLaps` increments. A new stint index appears at pit exit with `Compound` and `New` reset; a brief transitional entry with `Compound: "UNKNOWN"` precedes the definitive compound name for some pit stops. Japan 2026 Race: 539 events, 22 drivers, 2–7 stints per driver.

**Example events** (Japan 2026 Race):
```json
{"Stints": {"1": {"0": {"Compound": "MEDIUM", "New": "true", "TyresNotChanged": "0", "TotalLaps": 0, "StartLaps": 0}}}}
{"Stints": {"1": {"0": {"TotalLaps": 1}}, "16": {"0": {"TotalLaps": 1}}, "63": {"0": {"TotalLaps": 1}}}}
{"Stints": {"1": {"1": {"Compound": "HARD", "New": "true", "TyresNotChanged": "0", "TotalLaps": 0, "StartLaps": 0}}}}
```

**Known quirks.**
- **Quirk #1 — `TotalLaps` is cumulative tyre wear, not stint laps.** `TotalLaps` counts total laps on the physical tyre set across all sessions it has run, including any prior use before this weekend session. `StartLaps` is the wear when the set was fitted for this stint. **Stint length = `TotalLaps − StartLaps`**. The in-repo property is `SessionStint.stint_laps` in `precompute/src/f1/inventory.py`. This was mis-handled until PR #7; `_derive_stint_from_session_stints` (renamed to `extract_session_stints`) is the primary consumer.
- **Quirk #2 — feed can silently stop updating mid-session after a pit stop.** Observed concretely: RUS in China Sprint 2026 — after his pit stop the feed emitted no further `TotalLaps` increments for his new stint. Reconciliation is done in `build_race_stints` (`inventory.py`) using `TimingData.NumberOfLaps` lap counts sourced via `driver_meta.py::extract_lap_counts`: if the sum of stint laps from this feed is less than the authoritative lap count, the final stint's `end_lap` is extended by the gap.
- `New`, `TyresNotChanged`, and numeric fields (`TotalLaps`, `StartLaps`) all arrive as **strings**, not native types. Use `_to_bool` / `_to_int` helpers in `inventory.py`.
- Stint indices are string keys (`"0"`, `"1"`, …), not integers.
- Stints with `Compound: "UNKNOWN"` represent transient in-pit states and are filtered out in `extract_session_stints`.

**Feeds these features** (current): tyre inventory (`precompute/src/f1/inventory.py` → `DriverInventory.sets`); race strategy chart (`DriverInventory.race_stints` / `sprint_stints` via `build_race_stints` in `inventory.py`).

**Could power** (speculative): animated tyre-wear gauge, compound-usage heat map.

### `CurrentTyres.jsonStream`

**Fetched by CI:** ❌ no
**Compressed:** no
**Investigation depth:** medium

**Summary.** A "right-now" snapshot stream, parallel to `TyreStintSeries` but much lighter. State is keyed `Tyres → {driver_number → {Compound, New}}` — only the currently-fitted compound and whether it is still classified as new. Updates fire on pit-exit events (roughly 1–3 events per stop per driver). Japan 2026 Race: only 36 events total (vs 539 for `TyreStintSeries`). The `New` field uses native Python booleans (`True`/`False`) unlike the string `"true"`/`"false"` in `TyreStintSeries`. Some pit events emit two updates — first `Compound: "UNKNOWN", New: False` (tyres off), then the definitive compound (tyres on).

**Example events** (Japan 2026 Race):
```json
{"Tyres": {"1": {"Compound": "MEDIUM", "New": true}, ..., "77": {"Compound": "HARD", "New": true}}}
{"Tyres": {"1": {"Compound": "UNKNOWN", "New": false}}}
{"Tyres": {"1": {"Compound": "HARD", "New": true}}}
{"Tyres": {"16": {"Compound": "HARD"}}}
```

**Known quirks.**
- `New` uses native `bool` here, not string — unlike `TyreStintSeries`. Normalize defensively when consuming alongside other feeds.
- Some updates include only `Compound` without `New` (e.g. driver 16 above); the merge-patch state retains the prior `New` value.
- A mid-stop `UNKNOWN` state appears for some but not all drivers (present for drivers 1, 87, 41, 10, 5, 30, 55, 27; absent for 16, 43, 81, 6, 31, etc.), so callers must not assume UNKNOWN always precedes the definitive compound.

**Feeds these features** (current): none — `TyreStintSeries` is used instead for all production tyre logic.

**Could power** (speculative): real-time "current tyre" indicator overlay, pit-stop compound-detection without needing to diff `TyreStintSeries` stint indices.

### `PitLaneTimeCollection.jsonStream`

**Fetched by CI:** ❌ no
**Compressed:** no
**Investigation depth:** medium

**Summary.** Records individual pit-stop durations keyed by driver number. State is keyed `PitTimes → {driver_number → {RacingNumber, Duration, Lap}}`. Each pit-stop produces exactly two events: an insert (duration + lap number appears) followed by a `_deleted` removal a few seconds later when the car exits. The final reduced state is always empty `{}`. Japan 2026 Race: 58 events covering 29 pit stops across all drivers. Driver 23 (Albon) appears repeatedly in the late-race sequence — consecutive entries on laps 45–49 — due to repeated penalty pit stops.

**Example events** (Japan 2026 Race):
```json
{"PitTimes": {"1": {"RacingNumber": "1", "Duration": "23.3", "Lap": "16"}}}
{"PitTimes": {"_deleted": ["1"]}}
{"PitTimes": {"87": {"RacingNumber": "87", "Duration": "25.0", "Lap": "16"}}}
{"PitTimes": {"_deleted": ["87"]}}
```

**Pit-stop-timeline feature analysis.**
- **Pit-stop duration:** provided directly as `Duration` (string, decimal seconds, e.g. `"23.3"`). No derivation needed.
- **Lap number:** `Lap` (string integer) identifies which lap the driver pitted on. Matches the `StartLaps` boundary in `TyreStintSeries` (lap 16 pit = `TyreStintSeries` stint index 0 shows `TotalLaps: 16`).
- **Pit entry / exit timestamps:** not carried explicitly. The insert event's `timestamp_ms` corresponds to approximately pit entry (the stop timer starting); the `_deleted` event's `timestamp_ms` is approximately pit exit. Gap between the two is ~30–40 s (consistent with `Duration` + a margin).
- **Per-driver vs per-event:** the key is driver number, but only one driver per key at a time. Multiple simultaneous stops appear as separate keys in the same event or consecutive events (see laps 21–22 in Japan where 8 drivers pitted in 2 laps).
- **Alignment with `TyreStintSeries`:** `Lap` values align with `TyreStintSeries` `TotalLaps` at the end of the previous stint. The feeds can be joined on `(driver_number, lap)` to enrich stints with stop durations.
- **Limitation:** because `_deleted` wipes the entry on pit exit, there is no historical accumulation in the reduced state. To build a per-driver pit-stop history, callers must collect insert events before they are deleted (i.e. consume the raw event stream, not the terminal state).

**Known quirks.**
- `Duration` and `Lap` are strings, not numbers.
- The final reduced `PitTimes` state is always `{}` — a reduce-then-read approach yields nothing. The raw event stream must be walked.
- Driver 23 in Japan 2026 logged 5 pit stops on laps 45–49 with `TyresNotChanged: "1"` in `TyreStintSeries` — penalty visits. `Duration` values were 23.0, 24.1, 26.0, 32.7, 24.3 s respectively; the 32.7 s stop likely involved a wheel-gun issue.

**Feeds these features** (current): none.

**Could power** (speculative): pit-stop-duration bar chart, undercut/overcut analysis (pair with `TyreStintSeries` stint laps and `TimingData` lap times), pit-stop heat map across the field.
