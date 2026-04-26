"""
utils/battle_store.py — Shared in-memory store for battle result data.

Both battle_bp (manual simulator) and world_bp (world attacks) write here.
The results page reads from here by battle_id.

In production this would be replaced with a database-backed store;
the interface (store_battle / get_battle) would not change.
"""

from __future__ import annotations

_battles: dict[str, dict] = {}


def store_battle(battle_id: str, data: dict) -> None:
    """Store a battle result dict keyed by UUID."""
    _battles[battle_id] = data


def get_battle(battle_id: str) -> dict | None:
    """Retrieve a stored battle result, or None if not found / server restarted."""
    return _battles.get(battle_id)


def all_battle_ids() -> list[str]:
    return list(_battles.keys())
