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
