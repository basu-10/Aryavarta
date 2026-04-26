"""
utils/battle_store.py — Shared store for battle result data.

Both battle_bp (manual simulator) and world_bp (world attacks) write here.
The results page reads from here by battle_id.

Records are persisted to <output_dir>/<battle_id>.json so they survive
server restarts.  The in-memory dict acts as a fast cache.
"""

from __future__ import annotations

import json
from pathlib import Path

_battles: dict[str, dict] = {}
_output_dir: Path | None = None


def init_store(output_dir: str) -> None:
    """Called once at app startup to set the persistence directory."""
    global _output_dir
    _output_dir = Path(output_dir)
    _output_dir.mkdir(exist_ok=True)


def _json_path(battle_id: str) -> Path | None:
    if _output_dir is None:
        return None
    return _output_dir / f"{battle_id}.json"


def store_battle(battle_id: str, data: dict) -> None:
    """Store a battle result dict keyed by UUID, also persisting to disk."""
    _battles[battle_id] = data
    path = _json_path(battle_id)
    if path is not None:
        try:
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass


def get_battle(battle_id: str) -> dict | None:
    """Retrieve a stored battle result; loads from disk on cache miss."""
    if battle_id in _battles:
        return _battles[battle_id]
    path = _json_path(battle_id)
    if path is not None and path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            _battles[battle_id] = data  # warm the cache
            return data
        except Exception:
            return None
    return None


def all_battle_ids() -> list[str]:
    return list(_battles.keys())
