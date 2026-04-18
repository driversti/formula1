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
| `LapCount.jsonStream` | Current / total session laps. | ✅ | medium |
| `LapSeries.jsonStream` | Per-driver lap-by-lap position series. | ❌ | medium |
| `ExtrapolatedClock.jsonStream` | Extrapolated session clock (remaining time, running flag). | ❌ | medium |
| `TyreStintSeries.jsonStream` | Per-driver tyre stint series (compound, new/used, lap counters). | ✅ | deep |
| `CurrentTyres.jsonStream` | Currently-fitted tyre per driver (compound + new/used snapshot, updates on pit exit). | ❌ | medium |
| `PitLaneTimeCollection.jsonStream` | Per-pit-stop duration and lap number; insert/delete pair per stop, final state always empty. | ❌ | medium |
| `CarData.z.jsonStream` | Compressed per-car telemetry (throttle, brake, RPM, gear, speed). | ❌ | medium |
| `Position.z.jsonStream` | Compressed per-car XYZ positions on track. | ❌ | medium |
| `RaceControlMessages.jsonStream` | Race Control messages: flags, investigations, penalties. | ❌ | medium |
| `TrackStatus.jsonStream` | Current track status code (all-clear, yellow, SC, VSC, red). | ✅ | deep |
| `TlaRcm.jsonStream` | Plain-text mirror of RaceControlMessages — message text only, no metadata. | ❌ | medium |
| `DriverList.jsonStream` | Driver identity: TLA, number, name, team, team colour. | ✅ | deep |
| `WeatherData.jsonStream` | Air/track temperature, humidity, wind speed/direction, rainfall. | ❌ | medium |
| `Heartbeat.jsonStream` | Feed connection keep-alive. | ❌ | medium |
| `TeamRadio.jsonStream` | Team radio clip metadata (driver, URL, timestamp). | ❌ | medium |
| `AudioStreams.jsonStream` | Available audio stream URLs (commentary feeds). | ❌ | medium |
| `ContentStreams.jsonStream` | Available video/content stream URLs. | ❌ | medium |
| `ChampionshipPrediction.jsonStream` | Live championship-standings prediction. | ❌ | medium |

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
- **Live track status (green/yellow/SC/VSC/red)?** → `TrackStatus.jsonStream` ✅
- **Race Control decisions (investigations, penalties, flags)?** → `RaceControlMessages.jsonStream` ❌
- **Weather (temp, wind, rainfall)?** → `WeatherData.jsonStream` ❌
- **Per-car telemetry (throttle/brake/RPM/gear/DRS/speed)?** → `CarData.z.jsonStream` ❌ (compressed)
- **Per-car position on track (XYZ)?** → `Position.z.jsonStream` ❌ (compressed)
- **Team radio clips?** → `TeamRadio.jsonStream` ❌
- **Current / total session laps?** → `LapCount.jsonStream` ✅
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

**Fetched by CI:** ✅ yes
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

**Feeds these features** (current): Race Strategy chart status-band lap mapping (anchors TrackStatus transitions to lap numbers). See `precompute/src/f1/track_status.py`.

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

## Telemetry

High-rate per-car streams. Both feeds are compressed (`.z.jsonStream`) — each event payload is a base64-encoded zlib-deflated JSON blob; see the Stream format primer for the decode recipe. Neither is currently fetched in CI.

### `CarData.z.jsonStream`

**Fetched by CI:** ❌ no
**Compressed:** yes (base64 + zlib; `zlib.decompress(base64.b64decode(blob), -zlib.MAX_WBITS)`)
**Investigation depth:** medium — payload decoded and sampled

**Summary.** The outer `.jsonStream` lines do not follow the standard JSON-patch format; `parse_stream` returns 0 events for this file. Each line is `HH:MM:SS.mmm"<base64-blob>"` where the blob decompresses to a JSON object with a single `Entries` key. `Entries` is a list of 1–5 telemetry snapshots, each carrying a `Utc` timestamp and a `Cars` dict keyed by racing number. Every car entry contains a `Channels` dict with integer string keys. Across 9,315 outer lines, the file contains 34,761 inner snapshots covering a session spanning ~156 minutes, yielding ~3.7 inner snapshots per second across the full field (approximately 4 Hz). All 22 racing numbers appear in every snapshot.

**Channel key mapping** (confirmed by full file scan — only these five keys are present):

| Channel | Signal | Range (observed) |
|---------|--------|-----------------|
| `"0"` | RPM | 0–13,000 |
| `"2"` | Speed (km/h) | 0–341 |
| `"3"` | Gear (0 = neutral) | 0–8 |
| `"4"` | Throttle (%) | 0–100 |
| `"5"` | Brake (0 = none, 100 = applied) | 0 / 100 |

Channel `"1"` (DRS) is **absent** from this dataset; no DRS signal is present in the Japan 2026 Race archive.

**Decoded example event** (outer line ts `01:08:41.907`, one inner snapshot, two cars shown):
```json
{
  "Entries": [
    {
      "Utc": "2026-03-29T05:18:58.4345718Z",
      "Cars": {
        "1":  { "Channels": { "0": 11320, "2": 272, "3": 8, "4":   0, "5": 100 } },
        "3":  { "Channels": { "0": 10825, "2": 302, "3": 6, "4": 100, "5":   0 } }
      }
    }
  ]
}
```

**Known quirks.**
- **Quirk #6 (compressed payload):** Payload is base64-encoded zlib-deflated JSON — decode with `zlib.decompress(base64.b64decode(blob), -zlib.MAX_WBITS)` (raw DEFLATE, no zlib header). See Stream format primer.
- **`parse_stream` does not parse this file.** The line format is `HH:MM:SS.mmm"<base64>"` (a JSON string, not a JSON object). `parse_stream` discards these lines silently; callers must parse the outer format manually before decompressing.
- **Sentinel value 104** appears simultaneously on both `"4"` (throttle) and `"5"` (brake) when the telemetry snapshot is frozen — i.e., the feed is repeating the last-known values with no fresh update. Treat any reading where both channels equal 104 as stale data.
- **Multiple entries per outer event.** Each outer compressed blob bundles 1–5 inner snapshots. The per-snapshot `Utc` timestamps are the authoritative time base; the outer line's session-relative timestamp is the delivery time, not the measurement time.

**Feeds these features** (current): none.

**Could power** (speculative): lap-time-vs-telemetry overlay, throttle trace by lap or corner, brake-point marker on track map, engine RPM histogram.

### `Position.z.jsonStream`

**Fetched by CI:** ❌ no
**Compressed:** yes (base64 + zlib; `zlib.decompress(base64.b64decode(blob), -zlib.MAX_WBITS)`)
**Investigation depth:** medium — payload decoded and sampled

**Summary.** Same outer line format as `CarData.z.jsonStream` (`parse_stream` also returns 0 events). Each blob decompresses to `{"Position": [...]}` where `Position` is a list of 1–5 snapshots. Each snapshot has a `Timestamp` (UTC string) and an `Entries` dict keyed by racing number. Every entry carries `Status` (`"OnTrack"` or `"OffTrack"`) and integer `X`, `Y`, `Z` coordinates. Across 9,322 outer lines the file holds 35,733 inner snapshots (~3.8 Hz). All 22 drivers appear in each snapshot; `OffTrack` entries have `X=Y=Z=0`.

**Decoded example event** (outer line ts `01:07:01.038`, one inner snapshot, two cars shown):
```json
{
  "Position": [
    {
      "Timestamp": "2026-03-29T05:17:17.6452505Z",
      "Entries": {
        "1":  { "Status": "OnTrack", "X":  3235, "Y": -2444, "Z": 673 },
        "3":  { "Status": "OnTrack", "X":   252, "Y":   650, "Z": 809 }
      }
    }
  ]
}
```

**Coordinate space.** X ranges roughly −13,800 to +5,960; Y ranges roughly −7,000 to +3,100; Z ranges 0–945 (Japan 2026 Race). The unit is not officially documented. The XY bounding box of ~19,800 × 10,100 units is consistent with Suzuka's circuit footprint (~2.5 km × 1.5 km) if each unit is approximately 0.1–0.15 m, though the Z axis (elevation) yields a different ratio (~0.04 m/unit for Suzuka's ~40 m elevation change). Treat coordinates as relative positions normalized to a proprietary track-map grid; apply per-circuit normalization before rendering.

**Known quirks.**
- **Quirk #6 (compressed payload):** Payload is base64-encoded zlib-deflated JSON — decode with `zlib.decompress(base64.b64decode(blob), -zlib.MAX_WBITS)` (raw DEFLATE, no zlib header). See Stream format primer.
- **`parse_stream` does not parse this file** — same reason as `CarData.z.jsonStream`: outer line payload is a JSON string, not a JSON object.
- **Top-level key is `Position`, not `Entries`.** The decoded shape differs from `CarData`: `CarData` uses `{"Entries": [...]}` while `Position` uses `{"Position": [...]}`.
- **`OffTrack` entries carry zeros.** When `Status` is `"OffTrack"`, X, Y, Z are all 0. Filter before rendering to avoid spurious origin spikes.
- **Frozen-snapshot intervals.** Like `CarData`, consecutive snapshots sometimes repeat identical X/Y/Z values across several milliseconds, indicating a telemetry gap rather than a stationary car.

**Feeds these features** (current): none.

**Could power** (speculative): animated track-map with all 22 cars, on-track position visualization, overtake-detection heuristics (position crossings), safety-car bunching analysis.

## Race control

Feeds in this group carry Race Control decisions — flags, safety-car / VSC calls, investigations, and penalties. None is currently fetched in CI; all three are core candidates for any feature involving race-timeline overlays, flag states, or penalty analysis.

### `RaceControlMessages.jsonStream`

**Fetched by CI:** no
**Compressed:** no
**Investigation depth:** medium

**Summary.** The primary Race Control feed. `parse_stream` returns one event per on-screen RC message (47 in Japan 2026 Race). The outer payload shape varies by event type: the first event wraps messages in a JSON array (`{"Messages": [...]}`); subsequent events wrap messages in a numbered JSON object (`{"Messages": {"1": {...}, "2": {...}}}`). Each inner message always carries `Utc`, `Lap`, `Category`, and `Message` (human-readable text); optional fields depend on category.

**Fields per message.**
- `Category` — `"Flag"` | `"SafetyCar"` | `"Other"` (Japan 2026: 24 / 2 / 21)
- `Flag` — flag type when `Category = "Flag"`: `GREEN`, `YELLOW`, `DOUBLE YELLOW`, `CLEAR`, `CHEQUERED`, `BLACK AND WHITE`, `BLUE`
- `Scope` — `"Track"` | `"Sector"` | `"Driver"` (present for flag messages)
- `Sector` — integer sector number (1–N) when `Scope = "Sector"`
- `RacingNumber` — car number string when `Scope = "Driver"` (11 driver-specific messages in Japan 2026, all blue flags or black-and-white flags)
- `Status` — SafetyCar state string: `"DEPLOYED"` or `"IN THIS LAP"` (SafetyCar messages only)
- `Mode` — `"SAFETY CAR"` or `"VIRTUAL SAFETY CAR"` (SafetyCar messages only; Japan 2026 had no VSC)
- `Utc`, `Lap` — wall-clock time (UTC) and lap number at time of message

**No penalty-specific category.** Penalty and investigation messages fall under `Category: "Other"` as free-text strings (e.g. `"TURN 13 INCIDENT INVOLVING CARS 43 (COL) AND 87 (BEA) NOTED"`, `"FIA STEWARDS: ... REVIEWED NO FURTHER INVESTIGATION"`). Lap deletion notices also appear in `"Other"`.

**Example messages (Japan 2026 Race).**

Flag — sector yellow (Lap 22):
```json
{
  "Utc": "2026-03-29T05:47:54", "Lap": 22,
  "Category": "Flag", "Flag": "YELLOW", "Scope": "Sector", "Sector": 21,
  "Message": "YELLOW IN TRACK SECTOR 21"
}
```

SafetyCar deployed (Lap 22):
```json
{
  "Utc": "2026-03-29T05:48:11", "Lap": 22,
  "Category": "SafetyCar", "Status": "DEPLOYED", "Mode": "SAFETY CAR",
  "Message": "SAFETY CAR DEPLOYED"
}
```

Driver-specific flag (Lap 15):
```json
{
  "Utc": "2026-03-29T05:37:09", "Lap": 15,
  "Category": "Flag", "Flag": "BLACK AND WHITE", "Scope": "Driver",
  "RacingNumber": "41", "Message": "BLACK AND WHITE FLAG FOR CAR 41 (LIN) - MOVING UNDER BRAKING"
}
```

**Known quirks.**
- **Quirk #7 (inconsistent outer wrapper):** The very first event uses a JSON array as the `Messages` value; all subsequent events use a numbered-key object. Parsers must handle both shapes.
- Penalties and investigations are free-text in `Category: "Other"` — there is no structured penalty field or dedicated penalty category.

**Feeds these features** (current): none.

**Could power** (speculative): flag/SC/VSC overlay on race strategy chart, penalty audit log, live race-control banner, investigation timeline.

### `TrackStatus.jsonStream`

**Fetched by CI:** ✅ yes
**Compressed:** no
**Investigation depth:** deep

**Summary.** A small enum feed that records transitions in overall track status. `parse_stream` returns one event per status change (5 in Japan 2026 Race). Each event payload is `{"Status": "<code>", "Message": "<label>"}`.

**Observed status codes (Japan 2026 Race):**
| Code | `Message` | Meaning |
|------|-----------|---------|
| `"1"` | `AllClear` | Track fully clear; green-flag racing |
| `"2"` | `Yellow` | At least one sector under yellow |
| `"4"` | `SCDeployed` | Safety Car deployed |

VSC codes (`"6"` = `VSCDeployed`, `"7"` = `VSCEnding`) and red flag (`"5"` = `Red`) are part of the known enum but did not appear in Japan 2026 Race.

**Status sequence for Japan 2026 Race** (5 transitions):
`Yellow` → `AllClear` → `Yellow` → `SCDeployed` → `AllClear`

**Known quirks.**
- Status transitions can fire before the corresponding `RaceControlMessages` event is broadcast; treat `TrackStatus` as the authoritative machine-readable flag state and `RaceControlMessages` as the human-readable annotation.
- `"2"` (Yellow) fires even for a single-sector yellow; it does not distinguish local from widespread yellows. Use `RaceControlMessages` with `Scope/Sector` to determine which sectors are affected.

**Feeds these features** (current): Race Strategy chart status-band overlay (yellow / SC / VSC / red windows). See `site/src/components/StrategyChart.tsx`.

**Could power** (speculative): flag/SC/VSC overlay on race strategy chart, flag-state background colouring on any time-series chart.

### `TlaRcm.jsonStream`

**Fetched by CI:** no
**Compressed:** no
**Investigation depth:** medium

**Summary.** A stripped-down plain-text mirror of `RaceControlMessages`. `parse_stream` returns one event per RC message (47 in Japan 2026 Race — exactly matching `RaceControlMessages`). Every event payload contains exactly two fields: `Timestamp` (local wall-clock time as a UTC-format ISO string) and `Message` (the identical human-readable text from `RaceControlMessages`).

**Disambiguation from `RaceControlMessages`.**
- `TlaRcm` has **no** `Category`, `Flag`, `Scope`, `Sector`, `RacingNumber`, `Status`, `Mode`, or `Lap` fields. It carries only message text.
- The name suggests TLA (Three-Letter Abbreviation) indexing, but in practice all 47 events in Japan 2026 Race are flat `{Timestamp, Message}` objects — not keyed by TLA or racing number.
- Timestamps differ slightly: `RaceControlMessages` uses `Utc` (just date + time, no milliseconds); `TlaRcm` uses `Timestamp` (full ISO string in local/JST time).
- Use `RaceControlMessages` for any structured analysis. `TlaRcm` is suitable only if you need a simple ordered log of RC message text without parsing category-specific fields.

**Example event:**
```json
{ "Timestamp": "2026-03-29T14:48:11", "Message": "SAFETY CAR DEPLOYED" }
```

**Feeds these features** (current): none.

**Could power** (speculative): simple race-control banner (text only), human-readable RC log export.

## Drivers

### `DriverList.jsonStream`

**Fetched by CI:** ✅ yes (via `seasons/fetch_race.py`)
**Compressed:** no
**Investigation depth:** deep — used in production

The first event (at ~12 ms into the session) delivers all 22 driver objects in a single top-level dict keyed by racing-number string. Subsequent events (153 total over ~149 minutes) are sparse patches that update only the `Line` field as live positions change during the session.

**Example event (first, abbreviated):**

```json
{
  "12": {
    "RacingNumber": "12", "BroadcastName": "K ANTONELLI", "FullName": "Kimi ANTONELLI",
    "Tla": "ANT", "Line": 1, "TeamName": "Mercedes", "TeamColour": "00D7B6",
    "FirstName": "Kimi", "LastName": "Antonelli", "Reference": "ANDANT01",
    "HeadshotUrl": "https://media.formula1.com/.../andant01.png.transform/1col/image.png"
  }
}
```

**Known quirks:** `TeamColour` is a six-digit hex string **without** the leading `#` (e.g. `"00D7B6"`). `driver_meta.py::_normalize_color` prepends `#` before the value reaches the site. `Line` in this feed is the entry-list/grid line number, not a live race position — live positions come from `TimingData`. No `_deleted` operations were observed; drivers do not disappear even if they retire.

**Feeds these features** (current): driver identity (TLA, name, team, team colour, headshot) consumed by `precompute/src/f1/driver_meta.py::build_driver_meta` and rendered throughout the site — driver cards, race strategy chart, tyre inventory.

**Could power** (speculative): driver nationality displays (via `CountryCode`), retro driver-number visualizations, team-lineup timeline across the season.

## Environment

Feeds in this group describe conditions around the session. One of them — `Heartbeat` — is a connection keep-alive grouped here by elimination rather than topical fit.

### `WeatherData.jsonStream`

**Fetched by CI:** ❌ no
**Compressed:** no
**Investigation depth:** medium

Delivers one snapshot per minute of ambient track conditions. The Japanese GP Race session produced exactly 156 events over ~155 minutes — one event every ~60 seconds throughout. Each event carries a complete snapshot (no sparse patching): all seven fields are always present.

All field values are **strings**, even numeric ones — consumers must parse to float.

**Example event (ts ≈ 47 s into session):**

```json
{
  "AirTemp": "19.4",
  "TrackTemp": "37.0",
  "Humidity": "46.1",
  "Pressure": "1012.1",
  "WindSpeed": "3.1",
  "WindDirection": "115",
  "Rainfall": "0"
}
```

**Field inventory and observed ranges (Japanese GP Race 2026):**

| Field | Type (wire) | Range observed | Notes |
|---|---|---|---|
| `AirTemp` | string (°C) | 17.3 – 19.5 | One decimal place |
| `TrackTemp` | string (°C) | 29.2 – 38.3 | One decimal place |
| `Humidity` | string (%) | 44.7 – 62.8 | One decimal place |
| `Pressure` | string (hPa) | 1011.5 – 1012.1 | One decimal place |
| `WindSpeed` | string (m/s) | 0.0 – 3.7 | One decimal place |
| `WindDirection` | string (°) | 0 – 344 | Integer degrees; 0 observed when wind speed = 0 |
| `Rainfall` | string | `"0"` only | Not a bool; appears to be a count or flag; no rain during this session |

**Known quirks:** `Rainfall` is always `"0"` in a dry race; its semantics when nonzero (boolean flag vs. mm count vs. mm/hr) cannot be confirmed from this session alone.

**Feeds these features** (current): none — not consumed by the precompute pipeline.

**Could power** (speculative): weather overlay on race strategy timeline, session summary badge (dry/wet), track temperature trend chart.

### `Heartbeat.jsonStream`

**Fetched by CI:** ❌ no
**Compressed:** no
**Investigation depth:** medium

A connection keep-alive. The Japanese GP Race produced 704 events over ~176 minutes at a perfectly uniform cadence of **one event every 15 seconds**. Each event carries a single field:

```json
{ "Utc": "2026-03-29T04:10:34.413835Z" }
```

The `timestamp_ms` values parsed by `f1.parse` do not advance uniformly (407 distinct values for 704 events), suggesting the stream offset is snapped to coarser boundaries than the UTC payload. The UTC timestamp in the payload is the accurate wall-clock time.

**Feeds these features** (current): none.

**Could power** (speculative): detecting whether a live session is still broadcasting (presence heartbeat), or computing exact session wall-clock start/end from the UTC payload.

## Audio / video

Feeds in this group describe media streams and team-radio captures. None is currently fetched in CI. These are the least investigated in this reference — they're unlikely to power features in this static-site project (no backend to proxy URLs), but documented for completeness.

### `TeamRadio.jsonStream`

**Fetched by CI:** ❌ no
**Compressed:** no
**Investigation depth:** medium

**Note:** this file is **absent from the Japan 2026 Race** session (26 of 27 expected files present). The example below comes from the **Mexico City 2025 Race** session (`seasons/2025/2025-10-26_Mexico_City_Grand_Prix/2025-10-26_Race/`), which contains a complete copy.

The stream carries per-clip metadata for team radio recordings. The **first event** uses a JSON array for `Captures` (batch upload of multiple clips); **all subsequent events** use a dict keyed by a monotonically-increasing integer index (one new clip per event). Each capture has three fields:

```json
{
  "Captures": {
    "3": {
      "Utc": "2025-10-26T19:23:36.176Z",
      "RacingNumber": "1",
      "Path": "TeamRadio/MAXVER01_1_20251026_132318.mp3"
    }
  }
}
```

`Path` is a relative path under the session's base URL on `livetiming.formula1.com/static/`. The full audio file URL would be constructed as `<session-base>/<Path>`. No `Duration` field is present. The Mexico 2025 Race produced 27 events covering 27 distinct clips across many drivers.

**Feeds these features** (current): none.

---

### `AudioStreams.jsonStream`

**Fetched by CI:** ❌ no
**Compressed:** no
**Investigation depth:** medium

A single-event manifest listing the live audio commentary streams available for the session. The Japan 2026 Race produced exactly **1 event** at session-relative timestamp 55:07, carrying a `Streams` array:

```json
{
  "Streams": [
    {
      "Name": "Live coverage (EN)",
      "Language": "en",
      "Uri": "https://rdio.formula1.com/rdio-prod/livetimingts/hls.m3u8",
      "Path": "Live_coverage_(EN)-en/stream.m3u8",
      "Utc": "2026-03-29T05:05:24.688Z"
    }
  ]
}
```

`Uri` is the live HLS stream URL served from `rdio.formula1.com` (or CloudFront for older sessions). `Path` is a session-relative mirror path. Only English commentary appeared in both 2025 and 2026 sessions inspected — the feed likely lists one entry per available language. The stream URL is authenticated/ephemeral; it does not persist post-race.

**Feeds these features** (current): none.

---

### `ContentStreams.jsonStream`

**Fetched by CI:** ❌ no
**Compressed:** no
**Investigation depth:** medium

A two-event manifest listing video and audio content streams. The Japan 2026 Race produced **2 events** at the same timestamp (55:07), one per stream type. The first event uses an array for `Streams`; the second uses a dict keyed by integer index — the same dual-format pattern seen in `TeamRadio`.

```json
{ "Streams": [{ "Type": "Commentary", "Name": "monterosa", "Language": "en",
    "Uri": "https://interactioncloud.formula1.com/?h=cdn.monterosa.cloud&...",
    "Utc": "0001-01-01T00:00:00" }] }

{ "Streams": { "1": { "Type": "Audio", "Name": "Live coverage (EN)", "Language": "en",
    "Uri": "https://rdio.formula1.com/rdio-prod/livetimingts/hls.m3u8",
    "Path": "Live_coverage_(EN)-en/stream.m3u8",
    "Utc": "2026-03-29T05:05:24.688Z" }}}
```

Two stream types appear: `"Commentary"` (a Monterosa interactive cloud widget URL, `Utc` is the .NET default `0001-01-01` indicating no live timestamp) and `"Audio"` (the same HLS URL as in `AudioStreams`). The `Uri` values are ephemeral authenticated URLs; no onboard-camera or video-highlight entries were observed in the sessions inspected.

**Feeds these features** (current): none.

## Predictions

### `ChampionshipPrediction.jsonStream`

**Fetched by CI:** ❌ no
**Compressed:** no
**Investigation depth:** medium

Emits live driver and constructor championship projections throughout the race. Japan 2026 Race produced **85 events** over ~94 minutes (avg ~67 s apart, irregular cadence). The first two events arrive at the same timestamp: one initialises all entries to empty dicts, the second seeds the full baseline. Subsequent events are **partial diffs** — only entries whose predicted values changed are included.

Reduced state has two top-level keys, `Drivers` and `Teams`. Each entry carries `CurrentPosition`, `CurrentPoints` (season standings at session start), `PredictedPosition`, and `PredictedPoints` (projected post-race standings given the current race order). `Teams` uses the full technical team name as key (e.g. `"McLaren Mercedes"`), with a shorter `TeamName` display field.

```json
// Driver #12 — Antonelli, final reduced state
"12": {
  "RacingNumber": "12",
  "CurrentPosition": 2, "CurrentPoints": 47.0,
  "PredictedPosition": 1, "PredictedPoints": 72.0
}
// Driver #63 — Russell, final reduced state
"63": {
  "RacingNumber": "63",
  "CurrentPosition": 1, "CurrentPoints": 51.0,
  "PredictedPosition": 2, "PredictedPoints": 63.0
}
```

**Known quirks:** The dual-event initialisation (empty dict followed immediately by full baseline) must be handled before merging diffs, or the baseline is silently dropped. Sprint-weekend carry-over was not tested; `CurrentPoints` is assumed to reflect any sprint points already awarded before the main race.

**Feeds these features** (current): none.

**Could power:** post-race championship standings table; race-impact visualisation showing who gained or lost positions in the championship; win-probability or title-contention charts updated lap by lap.

## Cross-feed opportunities

Feature ideas that need two or more feeds. Each entry: a one-line pitch, the feeds required (with ✅ for CI-fetched and ❌ for full-archive-only), and one "verify first" note that flags an alignment question or data-shape caveat.

**None of these is committed work.** This is a menu the user scans when deciding what to build next. Every entry has a caveat that must be answered before implementation starts.

---

### Sector-colour timing tower

Display a live timing tower where each driver's sector splits are coloured purple (session best), green (personal best), or yellow (slower) — the classic broadcast look.

**Feeds required.** `TimingData.jsonStream` ✅ + `TimingStats.jsonStream` ❌

**Verify first.** `TimingStats.BestSectors.Position` is session rank (1 = fastest in session); the purple/green/yellow logic can key off that value directly, but `TimingStats` is not fetched in CI so this feature requires the full archive.

---

### Weather overlay on the race strategy chart

Render a secondary axis below the race strategy chart showing track temperature and rainfall status across the race laps, letting viewers correlate tyre behaviour with ambient conditions.

**Feeds required.** `WeatherData.jsonStream` ❌ + `TimingData.jsonStream` ✅

**Verify first.** `WeatherData` emits one full snapshot per minute (wall-clock), while `TimingData` is event-driven per lap completion. Alignment is coarse (~1 min resolution); lap-to-timestamp mapping requires either `SessionData.Series` lap-boundary UTCs (also ❌) or approximation from session start time plus elapsed laps.

---

### Flag / SC / VSC / red-flag overlay on the race strategy chart

Shade the strategy chart background in yellow/red and annotate Safety Car and VSC windows so viewers can immediately see how incidents shaped the race.

**Status:** Built — `site/src/components/StrategyChart.tsx` renders this overlay from `manifest.race.race_status_bands` / `sprint_status_bands`. The SessionData/RaceControlMessages enrichments remain unimplemented (still ❌).

**Feeds required.** `TrackStatus.jsonStream` ✅ + `SessionData.jsonStream` ❌ + `RaceControlMessages.jsonStream` ❌

**Verify first.** `TrackStatus` gives machine-readable state transitions with session-relative timestamps; `SessionData.StatusSeries` gives the same transitions with UTC timestamps; `RaceControlMessages` provides the human-readable label (e.g. "SAFETY CAR DEPLOYED"). All three are ❌, so none is available in CI. Use `TrackStatus` as the authoritative state source and `RaceControlMessages` for the annotation text — they may arrive out of order by a few seconds.

---

### Per-lap position trace chart

Show every driver's on-track position (1–22) lap by lap, the classic "racing lines" visualization that reveals overtakes, Safety Car bunching, and strategy divergence.

**Feeds required.** `LapSeries.jsonStream` ❌ + `TimingData.jsonStream` ✅ + `LapCount.jsonStream` ❌

**Verify first.** `LapSeries.LapPosition` values are strings, not integers. The bootstrap event emits a JSON array (lap 1 maps to index `"0"` after list→dict promotion), creating an off-by-one that callers must handle. The lap-1 figure reflects on-track order after race start, not grid order — driver 12 (race winner, pole) appears at position `"6"` on lap 1.

---

### Pit-stop timeline annotations on the race strategy chart

Enrich the existing strategy chart with explicit pit-stop duration labels: show each stop's lap number and how many seconds it took.

**Feeds required.** `PitLaneTimeCollection.jsonStream` ❌ + `TyreStintSeries.jsonStream` ✅ + `TimingData.jsonStream` ✅

**Verify first.** `PitLaneTimeCollection` reduced state is always `{}` — the raw event stream must be walked to harvest insert events before they are `_deleted` on pit exit. Join the collected events to `TyreStintSeries` stints on `(driver_number, lap)` using the `Lap` field from `PitLaneTimeCollection` vs. `TotalLaps` at stint boundary in `TyreStintSeries`.

---

### Pit-stop duration histogram and undercut/overcut analysis

Compare each driver's pit-stop durations across the field; pair with lap times before and after the stop to identify successful undercuts and failed overcuts.

**Feeds required.** `PitLaneTimeCollection.jsonStream` ❌ + `TimingData.jsonStream` ✅

**Verify first.** Same `_deleted` caveat as above — `PitLaneTimeCollection` final state is `{}`; the event stream must be consumed live, collecting each insert before deletion. `Duration` and `Lap` are strings; parse before arithmetic. Driver 23 in Japan 2026 logged 5 stops on laps 45–49 (penalty visits with `TyresNotChanged: "1"`) — penalty stops should be filtered or flagged separately.

---

### Championship-impact visualization

Show, for each race finisher, how many championship points and positions they gained or lost relative to pre-race standings — making it immediately clear who the race mattered most to.

**Feeds required.** `ChampionshipPrediction.jsonStream` ❌ + `DriverList.jsonStream` ✅

**Verify first.** `ChampionshipPrediction` emits partial diffs after the first full-baseline event; the dual-event initialization (empty dict immediately followed by full baseline) must be handled before merging diffs, or the baseline is silently dropped. The feed updates irregularly (~67 s apart on average) so mid-race snapshots are coarse.

---

### Penalty audit page

List every investigation, penalty, and lap deletion in chronological order, annotated with the affected driver's name and the lap time that was (or was not) deleted.

**Feeds required.** `RaceControlMessages.jsonStream` ❌ + `TimingData.jsonStream` ✅ + `DriverList.jsonStream` ✅

**Verify first.** Penalties and investigations appear as free-text in `Category: "Other"` — there is no structured penalty field or dedicated penalty category. Extracting the racing number and penalty type requires text parsing (regex on strings like `"TURN 13 INCIDENT INVOLVING CARS 43 (COL) AND 87 (BEA) NOTED"`). False-positive rate from text parsing is unknown across multiple sessions.

---

### Throttle and brake trace per driver per lap

Render a corner-by-corner throttle/brake trace for a selected driver on a selected lap, overlaid against their lap time — the kind of telemetry analysis previously available only in professional tools.

**Feeds required.** `CarData.z.jsonStream` ❌ + `TimingData.jsonStream` ✅

**Verify first.** `parse_stream` does NOT work on `.z.` files — the outer line format is `HH:MM:SS.mmm"<base64>"` (a JSON string), not a JSON object; `parse_stream` silently returns 0 events. A custom outer-loop decoder is required before decompression. Lap boundary alignment requires joining `CarData` UTC timestamps with lap-boundary UTCs derivable from `SessionData.Series` (also ❌). Sentinel value 104 on both throttle and brake channels simultaneously indicates stale/frozen telemetry — filter before rendering.

---

### Animated track map with all 22 cars

Play back the full race as an animated top-down track map, with each car dot coloured by team, pausing on Safety Car periods and showing overtakes live.

**Feeds required.** `Position.z.jsonStream` ❌ + `DriverList.jsonStream` ✅ + `TrackStatus.jsonStream` ❌

**Verify first.** `Position` coordinates are in a proprietary track-map unit system (not meters or lat/lon); per-circuit normalization is required before rendering. `parse_stream` does not work on this file (same compressed outer format as `CarData.z`). `OffTrack` entries carry `X=Y=Z=0` and must be filtered to avoid spurious origin spikes. The coordinate-space bounding box implies ~0.1–0.15 m/unit for XY but a different ratio for Z (elevation), so Z cannot be used for elevation rendering without independent calibration.
