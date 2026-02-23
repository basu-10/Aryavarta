"""
intent.py — Phase 1: Intent Evaluation

Each living unit inspects the current battlefield and records
what it intends to do this tick: 'attack', 'move', or 'hold'.

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


def evaluate_intents(units: list["Unit"]) -> None:
    """
    Mutate each unit's _intent field in-place.
    Called at the start of every tick before any other phase.
    """
    living = [u for u in units if u.is_alive()]

    for unit in living:
        unit.reset_tick_state()

        if enemies_in_range(unit, living):
            unit._intent = "attack"
        elif unit.move_behavior == "Advance":
            unit._intent = "move"
        else:
            unit._intent = "hold"
            unit._action = "hold"
