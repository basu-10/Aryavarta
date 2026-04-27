"""
utils/admin_test_harness.py - Admin-only bulk battle test harness.

This module runs scripted formation-vs-world attacks and persists outcomes
through the same mission/battle flow used by normal world attacks.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from blueprints.world_bp import _resolve_one_mission
from db import get_db
from db import models as m


PRESETS_DIR = Path(__file__).resolve().parent.parent / "presets"
ALLOWED_TARGET_TYPES = {"monster_camp", "monster_fort", "npc_fort"}


def list_available_presets() -> list[str]:
    PRESETS_DIR.mkdir(exist_ok=True)
    names: list[str] = []
    for f in sorted(PRESETS_DIR.glob("*.json")):
        names.append(f.stem)
    return names


def _safe_preset_name(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name).strip()


def load_preset_formation(preset_name: str) -> list[dict]:
    """Load preset Team A units as explicit placement formation."""
    safe = _safe_preset_name(preset_name)
    if not safe:
        return []

    path = PRESETS_DIR / f"{safe}.json"
    if not path.exists():
        return []

    try:
        preset = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    formation: list[dict] = []
    for unit in preset.get("army_a", []):
        if not isinstance(unit, dict):
            continue
        utype = (unit.get("type") or unit.get("unit_type") or "").strip()
        row = unit.get("row")
        col = unit.get("col")
        if not utype or not isinstance(row, int) or not isinstance(col, int):
            continue
        try:
            qty = max(1, int(unit.get("quantity", 1)))
        except (TypeError, ValueError):
            qty = 1
        formation.append({"unit_type": utype, "quantity": qty, "row": row, "col": col})

    return formation


def _target_pool(star_level: int, target_types: set[str], attacker_id: int) -> list[dict]:
    """Build attack target list from selected categories and star level."""
    targets: list[dict] = []

    if "monster_camp" in target_types:
        for camp in m.get_all_active_monster_camps():
            if int(camp.get("star_level", 0)) != star_level:
                continue
            targets.append(
                {
                    "kind": "monster_camp",
                    "target_type": "monster_camp",
                    "target_id": camp["id"],
                    "label": f"Monster Camp #{camp['id']}",
                }
            )

    if "monster_fort" in target_types:
        for fort in m.get_all_forts():
            if fort.get("owner_id") is not None:
                continue
            if int(fort.get("star_level", 0)) != star_level:
                continue
            targets.append(
                {
                    "kind": "monster_fort",
                    "target_type": "fort",
                    "target_id": fort["id"],
                    "label": f"Monster Fort #{fort['id']}",
                }
            )

    if "npc_fort" in target_types:
        db = get_db()
        rows = db.execute(
            """SELECT f.id, f.star_level, p.username AS owner_name
               FROM fort f
               JOIN player p ON p.id=f.owner_id
               WHERE p.role='npc' AND f.owner_id != ?
               ORDER BY f.id""",
            (attacker_id,),
        ).fetchall()
        for row in rows:
            if int(row["star_level"]) != star_level:
                continue
            targets.append(
                {
                    "kind": "npc_fort",
                    "target_type": "fort",
                    "target_id": row["id"],
                    "label": f"NPC Fort #{row['id']} ({row['owner_name']})",
                }
            )

    targets.sort(key=lambda x: (x["kind"], x["target_id"]))
    return targets


def _ensure_origin_for_admin(admin_player_id: int) -> tuple[str, int]:
    castle = m.get_castle_by_player(admin_player_id)
    if castle:
        return "castle", castle["id"]

    owned_forts = m.get_forts_by_owner(admin_player_id)
    if owned_forts:
        return "fort", owned_forts[0]["id"]

    # Unsafe-by-design testing helper: auto-grant one fort for origin.
    fort_id = m.admin_grant_fort(admin_player_id, slot_count=8, fully_built=True)
    return "fort", fort_id


def _formation_requirements(formation: list[dict]) -> dict[str, int]:
    needed: dict[str, int] = {}
    for e in formation:
        utype = (e.get("unit_type") or e.get("type") or "").strip()
        if not utype:
            continue
        try:
            qty = int(e.get("quantity", 1))
        except (TypeError, ValueError):
            qty = 1
        if qty <= 0:
            continue
        needed[utype] = needed.get(utype, 0) + qty
    return needed


def _ensure_admin_troops(
    admin_player_id: int,
    origin_type: str,
    origin_id: int,
    required: dict[str, int],
) -> None:
    troops = m.get_troops_at(origin_type, origin_id)
    have: dict[str, int] = {}
    for t in troops:
        if t.get("owner_id") != admin_player_id:
            continue
        utype = t.get("unit_type")
        have[utype] = have.get(utype, 0) + int(t.get("quantity", 0))

    for utype, qty in required.items():
        deficit = qty - have.get(utype, 0)
        if deficit > 0:
            m.add_troop(admin_player_id, utype, deficit, origin_type, origin_id)


def run_admin_formation_tests(
    admin_player_id: int,
    preset_names: list[str],
    star_level: int,
    target_types: set[str],
    max_targets: int | None = None,
) -> dict:
    """
    Run all selected presets against all selected targets at one star level.

    Returns a summary dict with resolved battle ids and failures.
    """
    player = m.get_player_by_id(admin_player_id)
    if not player or player.get("role") != "admin":
        raise ValueError("Only admin accounts can run test harness battles.")

    star_level = max(1, min(10, int(star_level)))
    clean_types = {t for t in target_types if t in ALLOWED_TARGET_TYPES}
    if not clean_types:
        raise ValueError("At least one target type must be selected.")

    unique_presets: list[str] = []
    seen: set[str] = set()
    for name in preset_names:
        if not isinstance(name, str):
            continue
        n = name.strip()
        if n and n not in seen:
            seen.add(n)
            unique_presets.append(n)

    if not unique_presets:
        raise ValueError("At least one preset must be selected.")

    loaded_presets: list[tuple[str, list[dict]]] = []
    failures: list[str] = []
    for name in unique_presets:
        formation = load_preset_formation(name)
        if not formation:
            failures.append(f"Preset '{name}' is empty, invalid, or missing.")
            continue
        loaded_presets.append((name, formation))

    if not loaded_presets:
        return {
            "resolved_battles": 0,
            "selected_presets": unique_presets,
            "selected_target_types": sorted(clean_types),
            "star_level": star_level,
            "runs": [],
            "failures": failures,
        }

    targets = _target_pool(star_level, clean_types, admin_player_id)
    if max_targets is not None and max_targets > 0:
        targets = targets[:max_targets]

    if not targets:
        failures.append("No matching targets found for selected filters.")
        return {
            "resolved_battles": 0,
            "selected_presets": unique_presets,
            "selected_target_types": sorted(clean_types),
            "star_level": star_level,
            "runs": [],
            "failures": failures,
        }

    origin_type, origin_id = _ensure_origin_for_admin(admin_player_id)
    runs: list[dict] = []

    for target in targets:
        for preset_name, formation in loaded_presets:
            try:
                required = _formation_requirements(formation)
                _ensure_admin_troops(admin_player_id, origin_type, origin_id, required)

                # Deduct troops exactly like standard attacks, then resolve mission.
                for entry in formation:
                    utype = (entry.get("unit_type") or entry.get("type") or "").strip()
                    qty = int(entry.get("quantity", 1))
                    if qty <= 0:
                        continue
                    ok = m.deduct_troop(admin_player_id, utype, qty, origin_type, origin_id)
                    if not ok:
                        raise RuntimeError(
                            f"Not enough troops for preset '{preset_name}': {utype} x{qty}"
                        )

                arrive_now = datetime.now(timezone.utc).isoformat(timespec="seconds")
                mission_id = m.create_mission(
                    admin_player_id,
                    target["target_type"],
                    target["target_id"],
                    formation,
                    origin_type,
                    origin_id,
                    arrive_now,
                )

                due = m.get_pending_missions_for_player(admin_player_id)
                mission = next((mis for mis in due if mis["id"] == mission_id), None)
                if not mission:
                    raise RuntimeError(f"Mission #{mission_id} was not due for resolution.")

                result = _resolve_one_mission(mission)
                runs.append(
                    {
                        "preset_name": preset_name,
                        "target_kind": target["kind"],
                        "target_id": target["target_id"],
                        "target_label": target["label"],
                        "battle_id": result["battle_id"],
                        "winner": result["winner"],
                        "mission_id": result["mission_id"],
                    }
                )
            except Exception as exc:  # noqa: BLE001 - capture per-run failure, continue batch
                failures.append(
                    f"{preset_name} vs {target['label']}: {type(exc).__name__}: {exc}"
                )

    return {
        "resolved_battles": len(runs),
        "selected_presets": unique_presets,
        "selected_target_types": sorted(clean_types),
        "star_level": star_level,
        "origin_type": origin_type,
        "origin_id": origin_id,
        "runs": runs,
        "failures": failures,
    }
