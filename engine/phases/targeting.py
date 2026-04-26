"""
targeting.py — Phase 3: Target Selection

Each attacker picks the closest living enemy within its attack range.
Tie-break: smallest Chebyshev distance first, then alphabetically by unit_id.

Sets unit._target_id for use by the damage phase.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from engine.phases.intent import chebyshev, enemies_in_range

if TYPE_CHECKING:
    from engine.unit import Unit


def select_target(attacker: "Unit", candidates: list["Unit"]) -> "Unit | None":
    """Pick the closest enemy from *candidates*. None if list is empty."""
    if not candidates:
        return None
    return min(candidates, key=lambda e: (chebyshev(attacker, e), e.unit_id))


def resolve_targeting(units: list["Unit"]) -> None:
    """
    For every attacker, find the closest in-range enemy and store its id.
    Mutates unit._target_id in-place.
    """
    living = [u for u in units if u.is_alive()]
    attackers = [u for u in living if u._intent == "attack"]

    for attacker in attackers:
        candidates = enemies_in_range(attacker, living)
        target = select_target(attacker, candidates)
        attacker._target_id = target.unit_id if target else None
