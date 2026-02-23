"""
death.py — Phase 5: Death Resolution

After all damage is applied, remove any unit whose HP has dropped to 0 or below:
  - Mark unit.alive = False
  - Free the unit's grid cell

Returns a list of unit_ids that died this tick.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.unit import Unit
    from engine.grid import Grid


def resolve_deaths(units: list["Unit"], grid: "Grid") -> list[str]:
    """
    Mark dead units and free their cells.
    Returns the list of unit_ids that died this tick.
    """
    dead_ids: list[str] = []

    for unit in units:
        if unit.is_alive():
            continue  # still alive
        if unit.alive:
            # First time we're marking this unit dead
            unit.alive = False
            unit._action = "dead"
            grid.remove(unit.row, unit.col)
            dead_ids.append(unit.unit_id)

    return dead_ids
