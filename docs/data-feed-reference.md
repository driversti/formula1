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
