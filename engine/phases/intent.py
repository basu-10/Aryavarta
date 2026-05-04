"""
intent.py — Phase 1: Intent Evaluation

Each living unit inspects the current battlefield and records
what it intends to do this tick: 'attack', 'move', 'retreat', 'attack_pool', or 'hold'.

Rules (in priority order):
1. No living enemies anywhere → if unit is at/past the enemy defense column, attack pool;
   otherwise hold.
2. Ranged unit (range > 1) has an enemy directly ahead in the same row
   AND that enemy is closer than the unit's range (distance < range)
   → retreat (move backward to re-establish optimal range).
3. Any enemy is within the unit's attack range → attack.
4. Unit is at the enemy's defense column (dead-end) with no enemies in range
   → attack_pool (hit the opposing HP pool directly).
5. Otherwise → move (advance toward enemy territory).

No positions change here — pure read-only resolution.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.unit import Unit

import config


def chebyshev(u1: "Unit", u2: "Unit") -> int:
    """Chebyshev (chessboard) distance between two units."""
    return max(abs(u1.row - u2.row), abs(u1.col - u2.col))


def enemies_in_range(unit: "Unit", all_units: list["Unit"]) -> list["Unit"]:
    """
    Return living enemies within attack range that are directly in front
    or diagonally in front of this unit.

    "In front" means the enemy column is strictly ahead in the unit's
    forward direction (forward_dir > 0 means higher col; < 0 means lower).
    Purely sideways (same col, different row) and backward targets are
    excluded — troops can never attack backwards.
    """
    return [
        u
        for u in all_units
        if u.team != unit.team
        and u.is_alive()
        and chebyshev(unit, u) <= unit.range
        # Must be strictly ahead — col delta in forward direction >= 1
        and (u.col - unit.col) * unit.forward_dir >= 1
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


def _unit_can_reach_pool(unit: "Unit") -> bool:
    """
    Return True if this unit is positioned to attack the opposing HP pool.
    Team A attacks Team B's pool (TEAM_B_DEF_COL); their range must bridge the gap.
    Team B attacks Team A's pool (TEAM_A_DEF_COL); their range must bridge the gap.
    """
    if unit.team == "A":
        # Distance from unit's column to Team B defense column
        dist = config.TEAM_B_DEF_COL - unit.col
    else:
        # Distance from unit's column to Team A defense column
        dist = unit.col - config.TEAM_A_DEF_COL
    return dist >= 0 and dist <= unit.range


def evaluate_intents(units: list["Unit"], pool_a_hp: int = 0, pool_b_hp: int = 0) -> None:
    """
    Mutate each unit's _intent field in-place.
    Called at the start of every tick before any other phase.

    pool_a_hp / pool_b_hp — current HP pool values passed in from Battle so
    intent can fall back to attack_pool when all enemies are dead but the
    opposing pool is still standing.  Defaults to 0 (no pool / pool dead) so
    existing tests that don't pass pool values still work correctly.
    """
    living = [u for u in units if u.is_alive()]

    for unit in living:
        unit.reset_tick_state()

        enemies = [u for u in living if u.team != unit.team]
        if not enemies:
            # No living enemies — attack pool if in range, advance toward it if not,
            # or hold if no HP pool system is active (pool_hp == 0).
            opposing_pool_hp = pool_b_hp if unit.team == "A" else pool_a_hp
            if opposing_pool_hp > 0:
                if _unit_can_reach_pool(unit):
                    unit._intent = "attack_pool"
                else:
                    unit._intent = "move"  # keep advancing toward enemy pool
            else:
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

        # Priority 3: attack HP pool if at enemy's defense column end and can reach it
        opposing_pool_hp = pool_b_hp if unit.team == "A" else pool_a_hp
        if opposing_pool_hp > 0 and _unit_can_reach_pool(unit):
            unit._intent = "attack_pool"
            continue

        # Priority 4: advance toward the enemy
        unit._intent = "move"
