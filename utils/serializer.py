"""
serializer.py — Convert BattleResult / engine state to JSON-safe structures.

The primary output is `build_tick_data()`, which produces a list of tick
snapshot dicts that the frontend tick_viewer.js can consume directly.

Each snapshot has:
  {
    "tick": <int>,
    "events": [ ... ],          # raw event list (attack, move, death…)
    "log": [ "<str>", ... ],    # human-readable event lines for the UI
    "cells": {                  # (row, col) -> cell info, only occupied cells
      "<r>,<c>": {
        "unit_id": "A_B1",
        "team": "A",
        "type": "Barbarian",
        "hp": 8,
        "max_hp": 10,
        "status": "alive"
      }, ...
    }
  }
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.battle import BattleResult


def _event_to_log_line(ev: dict) -> str:
    """Convert an event dict to a human-readable string."""
    t = ev.get("type", "")
    if t == "move":
        fr = ev["from"]
        to = ev["to"]
        return f"{ev['unit_id']} moved ({fr[0]},{fr[1]}) → ({to[0]},{to[1]})"
    elif t == "blocked":
        p = ev["pos"]
        return f"{ev['unit_id']} blocked at ({p[0]},{p[1]})"
    elif t == "attack":
        return (
            f"{ev['attacker_id']} attacked {ev['target_id']} "
            f"for {ev['damage']} damage"
        )
    elif t == "death":
        return f"{ev['unit_id']} was eliminated"
    return str(ev)


def build_tick_data(result: "BattleResult") -> list[dict]:
    """
    Build the tick_data JSON array for the frontend stepper.

    Each element corresponds to one tick snapshot.
    """
    tick_data = []

    for snap in result.ticks:
        cells: dict[str, dict] = {}
        for u in snap["units"]:
            if u["status"] == "alive":
                key = f"{u['row']},{u['col']}"
                cells[key] = {
                    "unit_id": u["unit_id"],
                    "team": u["team"],
                    "type": u["type"],
                    "hp": u["hp"],
                    "max_hp": u["max_hp"],
                    "status": u["status"],
                    "action": u["action"],
                }

        log_lines = [_event_to_log_line(ev) for ev in snap.get("events", [])]
        if not log_lines:
            log_lines = ["— No events this tick —"]

        tick_data.append(
            {
                "tick": snap["tick"],
                "events": snap.get("events", []),
                "log": log_lines,
                "cells": cells,
                "units": snap["units"],   # full unit list for summary panel
            }
        )

    return tick_data


def army_from_json(army_json: list[dict]) -> list:
    """
    Parse a JSON army definition (list of unit dicts) into Unit objects.
    Delegates to Unit.from_dict().
    """
    from engine.unit import Unit
    return [Unit.from_dict(d) for d in army_json]
