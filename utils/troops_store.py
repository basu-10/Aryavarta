"""
troops_store.py — Persist and retrieve custom troop type definitions.

Custom troops are saved to troops/custom_troops.json as a JSON array:
  [
    { "name": "Knight", "hp": 15, "damage": 2, "defense": 2,
      "range": 1, "speed": 1, "default_move": "Advance",
      "default_attack": "Closest" },
    ...
  ]

Call get_all_unit_stats() anywhere you need the full merged dict of
built-in + custom types.
"""

from __future__ import annotations

import json
from pathlib import Path

import config

TROOPS_FILE = Path(__file__).parent.parent / "troops" / "custom_troops.json"


def load_custom_troops() -> list[dict]:
    """Return list of custom troop dicts, or [] if none exist."""
    if not TROOPS_FILE.exists():
        return []
    try:
        data = json.loads(TROOPS_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def save_custom_troops(troops: list[dict]) -> None:
    """Overwrite the custom troops file with the given list."""
    TROOPS_FILE.parent.mkdir(exist_ok=True)
    TROOPS_FILE.write_text(json.dumps(troops, indent=2), encoding="utf-8")


def get_all_unit_stats() -> dict[str, dict]:
    """Return a merged dict of built-in and custom unit stats."""
    merged: dict[str, dict] = {}
    for name, stats in config.UNIT_STATS.items():
        merged[name] = dict(stats)
    for troop in load_custom_troops():
        name = troop.get("name", "")
        if not name:
            continue
        merged[name] = {
            "hp": troop.get("hp", 10),
            "damage": troop.get("damage", 1),
            "defense": troop.get("defense", 0),
            "range": troop.get("range", 1),
            "speed": float(troop.get("speed", 1.0)),
        }
    return merged


def get_all_unit_types() -> list[str]:
    """Return all unit type names (built-in first, then custom)."""
    return list(get_all_unit_stats().keys())
