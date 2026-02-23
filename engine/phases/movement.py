"""
movement.py — Phase 2: Movement Resolution

Units with intent='move' attempt to advance toward the enemy.
Movement is resolved simultaneously using a pre-tick position snapshot.

Rules:
- Units move ONLY forward (column direction). Row NEVER changes.
- Team A forward = +col; Team B forward = −col.
- If the cell directly ahead is occupied or out-of-bounds the unit stops
  (no diagonal fallback, no sideways drift).
- Each speed step is resolved simultaneously for all movers.
- Conflict tie-break: alphabetically earliest unit_id wins the contested cell.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.unit import Unit
    from engine.grid import Grid


def _desired_step(unit: "Unit", snapshot: dict, grid: "Grid") -> tuple[int, int] | None:
    """
    Return the cell directly ahead (same row, one column forward) if free.
    Returns None if blocked or out-of-bounds — no diagonal/sideways fallback.
    """
    r, c = unit.row, unit.col
    dc = unit.forward_dir  # +1 for A, -1 for B

    ahead = (r, c + dc)
    if grid.in_bounds(*ahead) and ahead not in snapshot:
        return ahead

    return None  # blocked — unit stops, no alternate path


def resolve_movement(units: list["Unit"], grid: "Grid") -> list[dict]:
    """
    Advance all 'move'-intent units up to their speed, simultaneously.
    Returns a list of event dicts for the battle log.
    """
    events: list[dict] = []
    movers = [u for u in units if u.is_alive() and u._intent == "move"]

    for _step in range(_max_speed(movers)):
        snapshot = grid.snapshot()

        # Compute desired moves for units that still have steps left
        desired: dict[str, tuple[int, int]] = {}  # unit_id -> target cell
        for unit in movers:
            if _steps_remaining(unit, _step):
                target = _desired_step(unit, snapshot, grid)
                if target is not None:
                    desired[unit.unit_id] = target

        # Resolve conflicts: when multiple units want the same cell,
        # give it to the unit_id that sorts first (deterministic tie-break).
        # This prevents symmetrical deadlocks (e.g., two enemies closing
        # distance on the same column).
        from collections import defaultdict
        dest_map: dict[tuple, list] = defaultdict(list)
        for uid, target in desired.items():
            dest_map[target].append(uid)

        allowed_uids: set[str] = set()
        for dest, uid_list in dest_map.items():
            winner = sorted(uid_list)[0]  # alphabetical first wins
            allowed_uids.add(winner)

        # Apply valid moves
        moved_ids: set[str] = set()
        for unit in movers:
            if unit.unit_id not in allowed_uids:
                continue
            target = desired[unit.unit_id]
            if grid.move_unit(unit.row, unit.col, *target):
                unit.row, unit.col = target
                moved_ids.add(unit.unit_id)

        # Units that didn't move this step → stop trying further steps
        movers = [u for u in movers if u.unit_id in moved_ids]

    # Build events for units that moved at all
    for unit in [u for u in units if u.is_alive() and u._intent == "move"]:
        if unit._action == "":
            # Will be set after we know final position vs initial
            pass

    # Record final actions (compare against pre-phase positions captured by caller)
    # The battle.py caller records start positions and uses this list:
    return events


def _max_speed(movers: list) -> int:
    if not movers:
        return 0
    return max((u.speed for u in movers), default=0)


def _steps_remaining(unit: "Unit", step_index: int) -> bool:
    return step_index < unit.speed
