"""
movement.py — Phase 2: Movement Resolution

Units with intent='move' advance toward the enemy; units with intent='retreat'
back away to re-establish optimal attack range. Movement is limited to the
column axis — row never changes.

Speed model (fractional):
  Each tick a moving/retreating unit gains `unit.speed` movement credit
  (_move_acc).  When credit reaches >= 1.0 the unit attempts to move 1 cell;
  the credit is then reduced by 1.0.  Credit is capped at 1.0 to prevent
  banked-up burst movement when a unit is repeatedly blocked.

  Examples:
    speed=1.0 → moves every tick (1x)
    speed=0.5 → accumulates 0.5/tick, moves on every 2nd tick (0.5x)

Conflict tie-break:
  When two units desire the same cell the alphabetically-earliest unit_id wins
  (deterministic, prevents deadlocks).

Blocked retreat → fall back to attack:
  If a ranged unit wants to retreat but is blocked (edge of grid or occupied
  cell behind), its intent is switched to 'attack' so the targeting phase can
  still fire.
"""

from __future__ import annotations
from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.unit import Unit
    from engine.grid import Grid

from engine.phases.intent import enemies_in_range


def _desired_step(unit: "Unit", snapshot: dict, grid: "Grid") -> tuple[int, int] | None:
    """
    Return the next cell for this unit based on its intent:
      'move'    → one step in forward_dir  (+col for A, -col for B)
      'retreat' → one step in -forward_dir (opposite direction)
    Returns None if the target cell is out-of-bounds or occupied.
    """
    r, c = unit.row, unit.col
    dc = unit.forward_dir if unit._intent == "move" else -unit.forward_dir
    target = (r, c + dc)
    if grid.in_bounds(*target) and target not in snapshot:
        return target
    return None


def resolve_movement(units: list["Unit"], grid: "Grid") -> list[dict]:
    """
    Resolve movement for all 'move' and 'retreat' intent units.
    Returns a list of event dicts (currently empty; battle.py handles logging).
    """
    movers = [u for u in units if u.is_alive() and u._intent in ("move", "retreat")]

    # Accumulate movement credit for this tick (capped at 1.0)
    for unit in movers:
        unit._move_acc = min(unit._move_acc + unit.speed, 1.0)

    # Only units with enough credit attempt to move
    ready = [u for u in movers if unit._move_acc >= 1.0  # intentional shadow avoided below
             ] if False else [u for u in movers if u._move_acc >= 1.0]

    if not ready:
        return []

    snapshot = grid.snapshot()

    # Compute each unit's desired next cell
    desired: dict[str, tuple[int, int]] = {}
    for unit in ready:
        target = _desired_step(unit, snapshot, grid)
        if target is not None:
            desired[unit.unit_id] = target

    # Conflict resolution: give contested cells to alphabetically-first unit_id
    dest_map: dict[tuple, list[str]] = defaultdict(list)
    for uid, target in desired.items():
        dest_map[target].append(uid)

    allowed_uids: set[str] = set()
    for dest, uid_list in dest_map.items():
        allowed_uids.add(sorted(uid_list)[0])

    # Apply valid moves
    retreated_ids: set[str] = set()
    for unit in ready:
        if unit.unit_id not in allowed_uids:
            continue
        target = desired.get(unit.unit_id)
        if target and grid.move_unit(unit.row, unit.col, *target):
            unit.row, unit.col = target
            unit._move_acc -= 1.0
            if unit._intent == "retreat":
                retreated_ids.add(unit.unit_id)

    # Blocked retreaters: switch intent to 'attack' so targeting can fire
    living = [u for u in units if u.is_alive()]
    for unit in ready:
        if unit._intent == "retreat" and unit.unit_id not in retreated_ids:
            # Couldn't retreat — attack if anything is still in range
            unit._intent = "attack"

    return []
