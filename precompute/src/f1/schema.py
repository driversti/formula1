"""Emit JSON Schema for the TypeScript side to consume."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from f1.models import Manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export Manifest JSON Schema")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "out" / "schema.json",
    )
    args = parser.parse_args(argv)

    schema = Manifest.model_json_schema()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
