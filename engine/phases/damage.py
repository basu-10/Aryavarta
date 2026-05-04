"""
damage.py — Phase 4: Damage Application

All attacks fire simultaneously:
  - Effective Damage = max(0, attacker.damage − target.defense)
  - HP reductions are collected first, then applied all at once.
  - Units do NOT die during this phase (see death.py).
  - Units with intent 'attack_pool' deal full damage directly to the opposing HP pool
    (no defense reduction — the pool is a structural target, not an armoured unit).

Mutates unit.hp and sets unit._damage_dealt / unit._action.
"""

from __future__ import annotations
from typing import TYPE_CHECKING
from collections import defaultdict

if TYPE_CHECKING:
    from engine.unit import Unit


def apply_damage(units: list["Unit"]) -> tuple[list[dict], dict[str, int]]:
    """
    Apply simultaneous damage for all attackers that have a valid target.

    Returns:
      - list of event dicts (attacker_id, target_id, damage) for unit attacks
      - dict {"A": <int>, "B": <int>} with total pool damage dealt this tick
        (key = which pool was attacked)
    """
    # Build a lookup map: unit_id -> Unit
    unit_map: dict[str, "Unit"] = {u.unit_id: u for u in units}

    # Accumulate damage per target (simultaneous)
    pending: dict[str, int] = defaultdict(int)  # target_id -> total incoming damage
    attacker_events: list[dict] = []
    pool_damage: dict[str, int] = {"A": 0, "B": 0}

    for attacker in units:
        if not attacker.is_alive():
            continue

        # --- Pool attack ---
        if attacker._intent == "attack_pool":
            # Team A units attack Team B pool, Team B units attack Team A pool
            target_pool = "B" if attacker.team == "A" else "A"
            pool_damage[target_pool] += attacker.damage
            attacker._damage_dealt = attacker.damage
            attacker._action = "attack_pool"
            continue

        # --- Normal unit attack ---
        if attacker._intent != "attack" or attacker._target_id is None:
            continue

        # Defence buildings with finite ammo cannot fire when empty.
        if attacker.unit_type in ("Cannon", "Archer Tower") and attacker.ammo is not None and attacker.ammo <= 0:
            attacker._action = "out_of_ammo"
            continue

        target = unit_map.get(attacker._target_id)
        if target is None or not target.is_alive():
            attacker._target_id = None
            continue

        effective = max(0, attacker.damage - target.defense)
        if attacker.unit_type in ("Cannon", "Archer Tower") and attacker.ammo is not None:
            attacker.ammo = max(0, attacker.ammo - 1)
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

    return attacker_events, pool_damage
