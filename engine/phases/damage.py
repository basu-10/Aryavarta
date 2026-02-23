"""
damage.py — Phase 4: Damage Application

All attacks fire simultaneously:
  - Effective Damage = max(0, attacker.damage − target.defense)
  - HP reductions are collected first, then applied all at once.
  - Units do NOT die during this phase (see death.py).

Mutates unit.hp and sets unit._damage_dealt / unit._action.
"""

from __future__ import annotations
from typing import TYPE_CHECKING
from collections import defaultdict

if TYPE_CHECKING:
    from engine.unit import Unit


def apply_damage(units: list["Unit"]) -> list[dict]:
    """
    Apply simultaneous damage for all attackers that have a valid target.
    Returns a list of event dicts (attacker_id, target_id, damage).
    """
    # Build a lookup map: unit_id -> Unit
    unit_map: dict[str, "Unit"] = {u.unit_id: u for u in units}

    # Accumulate damage per target (simultaneous)
    pending: dict[str, int] = defaultdict(int)  # target_id -> total incoming damage
    attacker_events: list[dict] = []

    for attacker in units:
        if not attacker.is_alive():
            continue
        if attacker._intent != "attack" or attacker._target_id is None:
            continue
        target = unit_map.get(attacker._target_id)
        if target is None or not target.is_alive():
            attacker._target_id = None
            continue

        effective = max(0, attacker.damage - target.defense)
        pending[target.unit_id] += effective
        attacker._damage_dealt = effective
        attacker._action = "attack"
        attacker_events.append(
            {
                "attacker_id": attacker.unit_id,
                "target_id": target.unit_id,
                "damage": effective,
            }
        )

    # Apply accumulated damage simultaneously
    for target_id, total_dmg in pending.items():
        target = unit_map.get(target_id)
        if target:
            target.hp -= total_dmg

    return attacker_events
