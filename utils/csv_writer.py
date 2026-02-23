"""
csv_writer.py — Write per-tick unit snapshots to a CSV file.

Schema (one row per unit per tick):
  tick, unit_id, team, type, row, col, hp, status, action, target_id, damage_dealt
"""

from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.battle import BattleResult

CSV_FIELDS = [
    "tick",
    "unit_id",
    "team",
    "type",
    "row",
    "col",
    "hp",
    "status",
    "action",
    "target_id",
    "damage_dealt",
]


def write_battle_csv(result: "BattleResult", filepath: str | Path) -> Path:
    """
    Write all tick snapshots from a BattleResult to a CSV file.

    Parameters
    ----------
    result   : BattleResult returned by Battle.run()
    filepath : Destination path (created/overwritten)

    Returns the resolved Path.
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()

        for tick_snap in result.ticks:
            tick_num = tick_snap["tick"]
            for unit_state in tick_snap["units"]:
                writer.writerow(
                    {
                        "tick": tick_num,
                        "unit_id": unit_state["unit_id"],
                        "team": unit_state["team"],
                        "type": unit_state["type"],
                        "row": unit_state["row"],
                        "col": unit_state["col"],
                        "hp": unit_state["hp"],
                        "status": unit_state["status"],
                        "action": unit_state["action"],
                        "target_id": unit_state.get("target_id", ""),
                        "damage_dealt": unit_state.get("damage_dealt", 0),
                    }
                )

    return filepath
