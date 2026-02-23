"""
targeting.py — Phase 3: Target Selection

Directional priority (applied before attack_behavior):

  FRONT   — same row as attacker, enemy is *ahead* (in forward column direction)
  BACK    — same row as attacker, enemy is *behind* (opposite column direction)
  SIDE    — different row (left / right lanes), any column

Selection logic:
  1. Collect all in-range enemies by direction zone.
  2. If any FRONT enemies exist → apply attack_behavior among them
     (Closest / LowestHP / HighestHP), deterministic tie-break.
  3. Else if BACK or SIDE enemies exist → pick ONE at random from
     the combined BACK + SIDE pool (randomness matches the flanking
     uncertainty of peripheral threats).
  4. No candidates → no attack this tick.

Sets unit._target_id for use by the damage phase.
"""

from __future__ import annotations
import random
from typing import TYPE_CHECKING

from engine.phases.intent import chebyshev, enemies_in_range

if TYPE_CHECKING:
    from engine.unit import Unit


# ------------------------------------------------------------------ #
# Direction helpers                                                    #
# ------------------------------------------------------------------ #

def direction_of(attacker: "Unit", enemy: "Unit") -> str:
    """
    Classify the enemy relative to the attacker:
      'front' — same row, enemy is in the forward column direction
      'back'  — same row, enemy is in the backward column direction
      'side'  — different row (left / right)
    """
    dr = enemy.row - attacker.row
    dc = enemy.col - attacker.col

    if dr == 0:
        # Same row — front or back
        if dc * attacker.forward_dir > 0:
            return "front"
        return "back"
    # Different row — side (left or right)
    return "side"


def _apply_behavior(attacker: "Unit", candidates: list["Unit"]) -> "Unit":
    """
    Pick the best target from *candidates* using attacker.attack_behavior.
    Deterministic tie-break: distance then unit_id.
    Caller guarantees candidates is non-empty.
    """
    behavior = attacker.attack_behavior
    if behavior == "LowestHP":
        return min(candidates, key=lambda e: (e.hp, chebyshev(attacker, e), e.unit_id))
    elif behavior == "HighestHP":
        return min(candidates, key=lambda e: (-e.hp, chebyshev(attacker, e), e.unit_id))
    else:  # "Closest" or unknown
        return min(candidates, key=lambda e: (chebyshev(attacker, e), e.unit_id))


def select_target(attacker: "Unit", candidates: list["Unit"]) -> "Unit | None":
    """
    Directional priority selection:
      1. Front enemies  → deterministic (attack_behavior)
      2. Back + Side    → random pick from the combined pool
    """
    if not candidates:
        return None

    front = [e for e in candidates if direction_of(attacker, e) == "front"]
    flanks = [e for e in candidates if direction_of(attacker, e) != "front"]

    if front:
        return _apply_behavior(attacker, front)

    if flanks:
        return random.choice(flanks)

    return None


def resolve_targeting(units: list["Unit"]) -> None:
    """
    For every attacker, find its target and store the target's unit_id.
    Mutates unit._target_id in-place.
    """
    living = [u for u in units if u.is_alive()]
    attackers = [u for u in living if u._intent == "attack"]

    for attacker in attackers:
        candidates = enemies_in_range(attacker, living)
        target = select_target(attacker, candidates)
        attacker._target_id = target.unit_id if target else None
