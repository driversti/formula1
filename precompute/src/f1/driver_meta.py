"""Extract driver metadata (name, team, color) and grid positions."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DriverMeta:
    racing_number: str
    tla: str
    full_name: str
    team_name: str
    team_color: str  # canonical form "#RRGGBB"


_REQUIRED_FIELDS = ("Tla", "FullName", "TeamName", "TeamColour")


def _normalize_color(raw: object) -> str | None:
    if not isinstance(raw, str) or not raw:
        return None
    return raw if raw.startswith("#") else f"#{raw}"


def build_driver_meta(driver_list_state: dict[str, object]) -> dict[str, DriverMeta]:
    """Turn reduced DriverList state into a racing_number -> DriverMeta map.

    Entries missing any required field are dropped.
    """
    result: dict[str, DriverMeta] = {}
    for racing_number, raw in driver_list_state.items():
        if not isinstance(raw, dict):
            continue
        if any(field not in raw or not raw[field] for field in _REQUIRED_FIELDS):
            continue
        color = _normalize_color(raw.get("TeamColour"))
        if color is None:
            continue
        result[str(racing_number)] = DriverMeta(
            racing_number=str(racing_number),
            tla=str(raw["Tla"]),
            full_name=str(raw["FullName"]),
            team_name=str(raw["TeamName"]),
            team_color=color,
        )
    return result


def extract_grid_positions(timing_app_state: dict[str, object]) -> dict[str, int]:
    """Read GridPos from the reduced TimingAppData state (Qualifying session)."""
    lines = timing_app_state.get("Lines")
    if not isinstance(lines, dict):
        return {}
    grid: dict[str, int] = {}
    for racing_number, raw in lines.items():
        if not isinstance(raw, dict):
            continue
        pos = raw.get("GridPos")
        if pos is None or pos == "":
            continue
        try:
            grid[str(racing_number)] = int(pos)
        except (TypeError, ValueError):
            continue
    return grid


def _to_bool_loose(value: object) -> bool:
    """The feed encodes booleans as either Python bool or the strings 'true'/'false'."""
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


def _to_int_optional(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def extract_final_positions_and_retirements(
    timing_data_state: dict[str, object],
) -> dict[str, tuple[int | None, bool]]:
    """Read final ``Line`` position and ``Retired`` flag per driver.

    ``Line`` is the driver's last observed position; ``Retired`` is True
    iff their last observed ``Retired`` value was truthy. Both fields
    may be absent from the feed for a given driver; the tuple slot stays
    ``None``/``False`` in that case.
    """
    lines = timing_data_state.get("Lines")
    if not isinstance(lines, dict):
        return {}
    result: dict[str, tuple[int | None, bool]] = {}
    for racing_number, raw in lines.items():
        if not isinstance(raw, dict):
            continue
        final_line = _to_int_optional(raw.get("Line"))
        retired = _to_bool_loose(raw.get("Retired", False))
        result[str(racing_number)] = (final_line, retired)
    return result
