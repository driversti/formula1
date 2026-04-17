"""Per-file verification pass over the mirror.

For every session directory that already exists on disk, this walks the
SESSION_FILES list and:
  - leaves files that are present on disk alone,
  - probes files that are missing, downloading 200s and recording 404/403
    as permanently unavailable,
  - retries transient failures a few times before giving up.

Writes `coverage.json` with a per-session {file: status} matrix where each
status is one of: "ok" (on disk), "fetched" (just downloaded),
"absent" (404/403 from server), "error" (all retries failed).
"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from download_f1 import SESSION_FILES, ROOT, BASE_URL, fetch, save  # noqa: E402

OUTPUT = ROOT / "coverage.json"
MAX_WORKERS = 10


def iter_sessions() -> list[Path]:
    """Yield every session directory (seasons root/<year>/<meeting>/<session>/)."""
    out: list[Path] = []
    for year_dir in sorted(ROOT.glob("20??")):
        if not year_dir.is_dir():
            continue
        for meeting_dir in sorted(year_dir.iterdir()):
            if not meeting_dir.is_dir():
                continue
            for session_dir in sorted(meeting_dir.iterdir()):
                if session_dir.is_dir():
                    out.append(session_dir)
    return out


def check_file(session_dir: Path, fname: str) -> tuple[str, str]:
    """Ensure fname exists locally; fetch once if missing. Returns (fname, status)."""
    dest = session_dir / fname
    if dest.exists() and dest.stat().st_size > 0:
        return (fname, "ok")
    rel = dest.relative_to(ROOT).as_posix()
    url = f"{BASE_URL}/{rel}"
    try:
        data = fetch(url)
    except Exception:
        return (fname, "error")
    if data is None:
        return (fname, "absent")
    save(dest, data)
    return (fname, "fetched")


def verify_session(session_dir: Path) -> dict[str, str]:
    """Return {file: status} for one session."""
    result: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = [pool.submit(check_file, session_dir, f) for f in SESSION_FILES]
        for fut in as_completed(futures):
            fname, status = fut.result()
            result[fname] = status
    return result


def main() -> None:
    sessions = iter_sessions()
    print(f"Verifying {len(sessions)} sessions against {len(SESSION_FILES)} files each "
          f"({len(sessions) * len(SESSION_FILES)} checks)...")
    coverage: dict[str, dict[str, str]] = {}
    totals = {"ok": 0, "fetched": 0, "absent": 0, "error": 0}
    for i, session_dir in enumerate(sessions, 1):
        rel = session_dir.relative_to(ROOT).as_posix()
        statuses = verify_session(session_dir)
        coverage[rel] = statuses
        counts = {k: 0 for k in totals}
        for s in statuses.values():
            counts[s] += 1
            totals[s] += 1
        tag = []
        if counts["fetched"]:
            tag.append(f"{counts['fetched']} fetched")
        if counts["error"]:
            tag.append(f"{counts['error']} error")
        suffix = f" [{', '.join(tag)}]" if tag else ""
        print(f"[{i:>3}/{len(sessions)}] {rel}: "
              f"{counts['ok']}/{len(SESSION_FILES)} ok, "
              f"{counts['absent']} absent{suffix}")

    OUTPUT.write_text(json.dumps(coverage, indent=2, ensure_ascii=False))
    print(f"\nWrote coverage report to {OUTPUT}")
    print(f"Totals: {totals}")


if __name__ == "__main__":
    main()
