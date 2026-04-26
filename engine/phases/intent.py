"""
intent.py — Phase 1: Intent Evaluation

Each living unit inspects the current battlefield and records
what it intends to do this tick: 'attack', 'move', 'retreat', or 'hold'.

Rules (in priority order):
1. No living enemies anywhere → hold.
2. Ranged unit (range > 1) has an enemy directly ahead in the same row
   AND that enemy is closer than the unit's range (distance < range)
   → retreat (move backward to re-establish optimal range).
3. Any enemy is within the unit's attack range → attack.
4. Otherwise → move (advance toward enemy territory).

No positions change here — pure read-only resolution.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.unit import Unit


def chebyshev(u1: "Unit", u2: "Unit") -> int:
    """Chebyshev (chessboard) distance between two units."""
    return max(abs(u1.row - u2.row), abs(u1.col - u2.col))


def enemies_in_range(unit: "Unit", all_units: list["Unit"]) -> list["Unit"]:
    """Return living enemies within unit's attack range."""
    return [
        u
        for u in all_units
        if u.team != unit.team and u.is_alive() and chebyshev(unit, u) <= unit.range
    ]


def _front_enemies_too_close(unit: "Unit", all_units: list["Unit"]) -> list["Unit"]:
    """
    Return enemies that are in the same row, directly ahead, and closer than
    the unit's range. Only relevant for ranged units (range > 1).
    """
    return [
        e for e in all_units
        if e.team != unit.team
        and e.is_alive()
        and e.row == unit.row
        and (e.col - unit.col) * unit.forward_dir > 0   # enemy is ahead
        and chebyshev(unit, e) < unit.range              # closer than optimal range
    ]


def evaluate_intents(units: list["Unit"]) -> None:
    """
    Mutate each unit's _intent field in-place.
    Called at the start of every tick before any other phase.
    """
    living = [u for u in units if u.is_alive()]

    for unit in living:
        unit.reset_tick_state()

        enemies = [u for u in living if u.team != unit.team]
        if not enemies:
            unit._intent = "hold"
            unit._action = "hold"
            continue

        # Priority 1: ranged kiting — back up if a front enemy is too close
        if unit.range > 1 and _front_enemies_too_close(unit, living):
            unit._intent = "retreat"
            continue

        # Priority 2: attack if any enemy is in range
        if enemies_in_range(unit, living):
            unit._intent = "attack"
            continue

        # Priority 3: advance toward the enemy
        unit._intent = "move"
