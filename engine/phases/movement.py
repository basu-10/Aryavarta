"""
movement.py — Phase 2: Movement Resolution

Units with intent='move' advance toward the enemy; units with intent='retreat'
back away to re-establish optimal attack range. Movement is limited to the
column axis — row never changes.

Speed model (multi-cell support):
  Each tick a moving/retreating unit gains `unit.speed` movement credit
  (_move_acc), capped at max(unit.speed, 1.0) to prevent burst movement
  after blocking while still allowing speed > 1.0 units to move multiple
  cells per tick (e.g. Hussar speed=2.0 moves 2 cells/tick).

  Examples:
    speed=1.0 → moves 1 cell/tick
    speed=2.0 → moves 2 cells/tick (cavalry charge)
    speed=0.5 → accumulates 0.5/tick, moves 1 cell every 2 ticks

Conflict resolution:
  Movers are processed in alphabetical unit_id order — earliest alphabetical
  unit wins any contested cell (deterministic, prevents deadlocks).

Blocked retreat → fall back to attack:
  If a ranged unit wants to retreat but is blocked (edge of grid or occupied
  cell behind), its intent is switched to 'attack' so the targeting phase can
  still fire.
"""

from __future__ import annotations
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

    Speed model (multi-cell support):
      Accumulate `unit.speed` credit per tick, capped at `max(unit.speed, 1.0)` to
      prevent burst movement after blocked ticks while still allowing speed > 1.0
      units (e.g. Hussar speed=2.0) to move multiple cells per tick.
      Units move repeatedly until credit < 1.0 or blocked.

    Conflict resolution: movers are processed in alphabetical unit_id order so
    the result is fully deterministic — the earlier-alphabetical unit wins any
    contested cell.
    """
    movers = [u for u in units if u.is_alive() and u._intent in ("move", "retreat")]

    # Accumulate movement credit — cap at speed (not 1.0) to allow multi-cell moves
    # while still preventing unlimited burst after prolonged blocking.
    for unit in movers:
        cap = max(unit.speed, 1.0)
        unit._move_acc = min(unit._move_acc + unit.speed, cap)

    # Process movers alphabetically for deterministic conflict resolution.
    # Each unit consumes as many 1.0 credits as it can (supports speed > 1.0).
    retreated_ids: set[str] = set()
    for unit in sorted(movers, key=lambda u: u.unit_id):
        if unit._move_acc < 1.0:
            continue
        while unit._move_acc >= 1.0:
            target = _desired_step(unit, grid.snapshot(), grid)
            if target and grid.move_unit(unit.row, unit.col, *target):
                unit.row, unit.col = target
                unit._move_acc -= 1.0
                if unit._intent == "retreat":
                    retreated_ids.add(unit.unit_id)
            else:
                # Blocked — stop trying this tick; keep remaining credit
                # but cap to just below 1.0 so it doesn't trigger again
                unit._move_acc = min(unit._move_acc, 0.999)
                break

    # Blocked retreaters: switch intent to 'attack' so targeting can fire
    for unit in movers:
        if unit._intent == "retreat" and unit.unit_id not in retreated_ids:
            unit._intent = "attack"

    return []
