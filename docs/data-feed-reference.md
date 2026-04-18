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

_TBD placeholders in this table are intentional: they get filled in by the Phase 2 task that investigates each group, which keeps each commit self-contained.

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
- **Championship predictions?** → `ChampionshipPrediction.jsonStream` ❌_
