"""
blueprints/wiki_bp.py — Game Wiki: landing page, troops compendium, and buildings reference.
"""

from __future__ import annotations

import math

from flask import Blueprint, render_template, abort, url_for
from db import get_db
import config

wiki_bp = Blueprint("wiki", __name__, url_prefix="/wiki")


def _slug(name: str) -> str:
    return name.lower().replace(" ", "-")


def _troop_image_path(name: str) -> str | None:
    """Return the URL path for a troop art asset, or None."""
    _IMAGE_MAP: dict[str, str] = {
        "Barbarian":   "/assets/theme1/troops/human/animations/barbarian/idle.gif",
        "Archer":      "/assets/theme1/troops/human/full/archer.svg",
        "Hussar":      "/assets/theme1/troops/human/full/hussar.svg",
        "Longbowman":  "/assets/theme1/troops/human/full/longbowman.svg",
        "Troll":       "/assets/theme1/troops/monster/full/troll.svg",
        "Wraith":      "/assets/theme1/troops/monster/full/wraith.svg",
    }
    return _IMAGE_MAP.get(name)


def _category_label(category: str) -> str:
    return {
        "infantry":     "Melee",
        "ranged":       "Ranged",
        "cavalry":      "Melee",
        "monster":      "Monster",
        "siege_defence": "Siege / Defence",
    }.get(category, category.title())


def _category_color(category: str) -> str:
    return {
        "infantry":     "text-orange-400",
        "ranged":       "text-sky-400",
        "cavalry":      "text-orange-400",
        "monster":      "text-red-400",
        "siege_defence": "text-purple-400",
    }.get(category, "text-gray-400")


def _fallback_category(troop_name: str) -> str:
    if troop_name in {"Cannon", "Archer Tower"}:
        return "siege_defence"

    cls = config.UNIT_CLASSIFICATION.get(troop_name, {})
    faction = cls.get("faction")
    role = cls.get("type")

    if faction == "monster":
        return "monster"
    if troop_name == "Hussar":
        return "cavalry"
    if role == "ranged":
        return "ranged"
    return "infantry"


def _fallback_lore_notes(troop_name: str) -> tuple[str | None, str | None]:
    lore_map: dict[str, str] = {
        "Barbarian": "Fierce melee warrior. Advances every tick and overwhelms defences with sheer numbers.",
        "Archer": "Disciplined ranged unit. Hangs back to rain arrows while others advance.",
        "Troll": "Massive brute found guarding monster camps. High HP and natural armour.",
        "Wraith": "Spectral assassin. Blurs across the battlefield to deliver devastating ranged strikes.",
        "Goblin Brute": "Savage vanguard that swarms intruders with cleaver strikes.",
        "Harpy": "Winged raider that dives repeatedly from mid-range.",
        "Minotaur": "Labyrinth warlord that crushes frontlines with horned charges.",
        "Basilisk": "Petrifying serpent that punishes overextended lines from afar.",
        "Gargoyle": "Living obsidian sentinel that shrugs off ordinary weapons.",
        "Manticore": "Barbed apex hunter whose tail volleys shred dense formations.",
        "Hydra": "Regenerative behemoth that grinds armies down in prolonged clashes.",
        "Siren": "Sea witch whose resonance blasts break disciplined ranks.",
        "Behemoth": "Mountain-sized juggernaut that anchors heavy garrisons.",
        "Chimera": "Tri-headed abomination that projects lethal fire at long range.",
        "Leviathan": "Abyss-born titan whose mass alone can halt a siege.",
        "Phoenix": "Solar predator that scorches lanes with reborn fury.",
        "Colossus": "Runic giant forged for annihilation at fortress gates.",
        "Thunderbird": "Tempest avatar that chains lightning through exposed wings.",
        "Abyssal Titan": "Void-forged executioner that erases frontlines with singular blows.",
        "Void Drake": "Rift-breath dragon that bombards defenders from extreme range.",
        "Longbowman": "Trained bowman from the Garrison. Steady, long-range support for assault waves.",
        "Hussar": "Fast cavalry from the Stable. Charges at twice normal speed, punching through lines.",
        "Cannon": "Heavy defensive emplacement. Stationary but deals massive damage at great range.",
        "Archer Tower": "Fortified arrow platform. Defends locations with sustained ranged fire.",
        "Demon": "Ancient terror of the abyss. Nigh-impenetrable hide turns aside all but the most overwhelming numbers.",
        "Pegasus": "Winged glass-cannon from the outer realms. No armour — pure devastation delivered from range.",
    }
    notes_map: dict[str, str | None] = {
        "Troll": "Star-1 monster melee unit. Spawns in star-1 forts and camps.",
        "Wraith": "Star-1 monster ranged unit. Spawns in star-1 forts and camps.",
        "Goblin Brute": "Star-2 monster melee unit. Spawns in star-2 forts and camps.",
        "Harpy": "Star-2 monster ranged unit. Spawns in star-2 forts and camps.",
        "Minotaur": "Star-3 monster melee unit. Spawns in star-3 forts and camps.",
        "Basilisk": "Star-3 monster ranged unit. Spawns in star-3 forts and camps.",
        "Gargoyle": "Star-4 monster melee unit. Spawns in star-4 forts and camps.",
        "Manticore": "Star-4 monster ranged unit. Spawns in star-4 forts and camps.",
        "Hydra": "Star-5 monster melee unit. Spawns in star-5 forts and camps.",
        "Siren": "Star-5 monster ranged unit. Spawns in star-5 forts and camps.",
        "Behemoth": "Star-6 monster melee unit. Spawns in star-6 forts and camps.",
        "Chimera": "Star-6 monster ranged unit. Spawns in star-6 forts and camps.",
        "Leviathan": "Star-7 monster melee unit. Spawns in star-7 forts and camps.",
        "Phoenix": "Star-7 monster ranged unit. Spawns in star-7 forts and camps.",
        "Colossus": "Star-8 monster melee unit. Spawns in star-8 forts and camps.",
        "Thunderbird": "Star-8 monster ranged unit. Spawns in star-8 forts and camps.",
        "Abyssal Titan": "Star-9 monster melee unit. Spawns in star-9 forts and camps.",
        "Void Drake": "Star-9 monster ranged unit. Spawns in star-9 forts and camps.",
        "Longbowman": "Produced by the Garrison building.",
        "Hussar": "Produced by the Stable building.",
        "Cannon": "Spawned into battle from the Cannon building. Stationary (speed 0).",
        "Archer Tower": "Spawned into battle from the Archer Tower building. Stationary (speed 0).",
        "Demon": "Star-10 apex monster. Def=1 billion blocks all damage until very high stacked counts are fielded.",
        "Pegasus": "Star-10 apex monster. Zero defence but 2 billion damage — kills unarmoured attackers in seconds.",
    }
    return lore_map.get(troop_name), notes_map.get(troop_name)


def _training_time_base_seconds(troop_name: str) -> int:
    for _, v in config.ARMY_BUILDINGS.items():
        if v.get("unit_type") == troop_name:
            return int(v.get("training_seconds", 60))
    return 60


def _fallback_levels(troop_name: str, max_levels: int = 10) -> list[dict]:
    base = config.UNIT_STATS.get(troop_name)
    if not base:
        return []

    base_cost = config.TROOP_TRAIN_COST.get(troop_name, {})
    gold = float(base_cost.get("gold", 0))
    food = float(base_cost.get("food", 0))
    timber = float(base_cost.get("timber", 0))
    metal = float(base_cost.get("metal", 0))
    base_time = _training_time_base_seconds(troop_name)
    lore, notes = _fallback_lore_notes(troop_name)

    levels: list[dict] = []
    for lvl in range(1, max_levels + 1):
        levels.append({
            "troop_type": troop_name,
            "category": _fallback_category(troop_name),
            "level": lvl,
            "hp": round(float(base["hp"]) * (1.15 ** (lvl - 1))),
            "damage": round(float(base["damage"]) * (1.10 ** (lvl - 1))),
            "defense": int(base["defense"]) + math.floor((lvl - 1) * 0.5),
            "range": int(base["range"]),
            "speed": float(base["speed"]),
            "attack_speed": float(base.get("attack_speed", 1.0)),
            "gold_cost": round(gold * (1.50 ** (lvl - 1))),
            "food_cost": round(food * (1.50 ** (lvl - 1))),
            "timber_cost": round(timber * (1.50 ** (lvl - 1))),
            "metal_cost": round(metal * (1.50 ** (lvl - 1))),
            "training_time_seconds": round(base_time * (1.25 ** (lvl - 1))),
            "lore": lore if lvl == 1 else None,
            "notes": notes if lvl == 1 else None,
        })

    return levels


def _fallback_level_one_rows() -> list[dict]:
    rows: list[dict] = []
    for troop_name in config.UNIT_TYPES:
        levels = _fallback_levels(troop_name, max_levels=1)
        if levels:
            rows.append(levels[0])
    return rows


@wiki_bp.route("/")
def wiki_index():
    return render_template("wiki/index.html")


@wiki_bp.route("/troops")
def troops_index():
    db = get_db()
    # One row per troop — level-1 stats only
    rows = [dict(r) for r in db.execute(
        "SELECT * FROM ref_troop_level WHERE level = 1 ORDER BY category, troop_type"
    ).fetchall()]

    if not rows:
        rows = _fallback_level_one_rows()

    troops = []
    for r in rows:
        r["slug"] = _slug(r["troop_type"])
        r["image"] = _troop_image_path(r["troop_type"])
        r["category_label"] = _category_label(r["category"])
        r["category_color"] = _category_color(r["category"])
        troops.append(r)

    # Group by category for display
    categories: dict[str, list] = {}
    for t in troops:
        categories.setdefault(t["category_label"], []).append(t)

    # Build monster rows: each entry pairs melee + ranged by star level
    _MONSTER_STAR_PAIRS = [
        (1,  "Troll",        "Wraith"),
        (2,  "Goblin Brute", "Harpy"),
        (3,  "Minotaur",     "Basilisk"),
        (4,  "Gargoyle",     "Manticore"),
        (5,  "Hydra",        "Siren"),
        (6,  "Behemoth",     "Chimera"),
        (7,  "Leviathan",    "Phoenix"),
        (8,  "Colossus",     "Thunderbird"),
        (9,  "Abyssal Titan", "Void Drake"),
        (10, "Demon",        "Pegasus"),
    ]
    troop_by_name = {t["troop_type"]: t for t in troops}
    monster_rows = []
    for star, melee_name, ranged_name in _MONSTER_STAR_PAIRS:
        melee_t  = troop_by_name.get(melee_name)
        ranged_t = troop_by_name.get(ranged_name)
        if melee_t or ranged_t:
            monster_rows.append({"star": star, "melee": melee_t, "ranged": ranged_t})

    return render_template("wiki/troops.html", troops=troops, categories=categories,
                           monster_rows=monster_rows)


@wiki_bp.route("/buildings")
def buildings_index():
    from config import (
        BUILDING_BUILD_COST, BUILDING_BUILD_TIME,
        ARMY_BUILDINGS, BUILDING_UPGRADE_COST, DEFENCE_BUILDING_AMMO,
    )
    _BUILDING_ICONS: dict[str, str] = {
        "Farm":           "/assets/theme1/buildings/resource/farm.svg",
        "Lumber Mill":    "/assets/theme1/buildings/resource/lumber-mill.svg",
        "Merchant":       "/assets/theme1/buildings/resource/merchant.svg",
        "Mine":           "/assets/theme1/buildings/resource/mine.svg",
        "Garrison":       "/assets/theme1/buildings/military/garrison.svg",
        "Stable":         "/assets/theme1/buildings/military/stable.svg",
        "Cannon":         "/assets/theme1/buildings/defense/cannon.svg",
        "Archer Tower":   "/assets/theme1/buildings/defense/archer-tower.svg",
        "Command Centre": "/assets/theme1/buildings/default/command-centre.svg",
    }
    _BUILDING_TIPS: dict[str, str] = {
        "Farm":           "Produces food passively. All troop training consumes food, so this keeps queues running.",
        "Lumber Mill":    "Generates timber. Most fort construction and upgrades depend on it.",
        "Merchant":       "Earns gold over time. Gold pays for troop training and many higher-tier upgrades.",
        "Mine":           "Extracts metal. Needed for cavalry, defenses, and late-game upgrades.",
        "Garrison":       "Trains Longbowmen. Core ranged production for early and mid-game attacks.",
        "Stable":         "Trains Hussars. Fast cavalry that reach targets quickly and punch through lines.",
        "Cannon":         "Adds heavy defensive firepower. Best when you need high damage from a fixed position.",
        "Archer Tower":   "Adds steady ranged defense. Helps forts survive repeated attacks.",
        "Command Centre": "Permanent fort core. Upgrading it improves the fort and unlocks stronger progression.",
    }
    buildings = []
    for name in BUILDING_BUILD_TIME.keys():
        buildings.append({
            "name":             name,
            "build_cost":       BUILDING_BUILD_COST.get(name, {}),
            "build_time":       BUILDING_BUILD_TIME.get(name, 0),
            "upgrade_cost":     BUILDING_UPGRADE_COST.get(name, {}),
            "trains":           ARMY_BUILDINGS.get(name, {}).get("unit_type"),
            "training_seconds": ARMY_BUILDINGS.get(name, {}).get("training_seconds"),
            "ammo":             DEFENCE_BUILDING_AMMO.get(name),
            "icon":             _BUILDING_ICONS.get(name),
            "tip":              _BUILDING_TIPS.get(name),
            "fort_buildable":   name != "Command Centre",
        })
    return render_template("wiki/buildings.html", buildings=buildings)


@wiki_bp.route("/troops/<slug>")
def troop_detail(slug: str):
    db = get_db()
    # Resolve slug back to troop_type
    all_types = [dict(r) for r in db.execute(
        "SELECT DISTINCT troop_type FROM ref_troop_level"
    ).fetchall()]
    if not all_types:
        all_types = [{"troop_type": name} for name in config.UNIT_TYPES]

    troop_name = None
    for row in all_types:
        if _slug(row["troop_type"]) == slug:
            troop_name = row["troop_type"]
            break

    if troop_name is None:
        abort(404)

    levels = [dict(r) for r in db.execute(
        "SELECT * FROM ref_troop_level WHERE troop_type = ? ORDER BY level",
        (troop_name,)
    ).fetchall()]
    if not levels:
        levels = _fallback_levels(troop_name)

    if not levels:
        abort(404)

    base = levels[0]  # level-1 row carries lore + notes

    return render_template(
        "wiki/troop_detail.html",
        troop_name=troop_name,
        slug=slug,
        base=base,
        levels=levels,
        image=_troop_image_path(troop_name),
        category_label=_category_label(base["category"]),
        category_color=_category_color(base["category"]),
        back_url=url_for("wiki.troops_index"),
    )


# Game guides
@wiki_bp.route("/guides")
def guides_index():
    return render_template("wiki/guide_index.html")


@wiki_bp.route("/guides/<guide>")
def guide(guide: str):
    """Serve individual guide pages."""
    valid_guides = {
        "welcome":          "wiki/guide_welcome.html",
        "getting-started":  "wiki/guide_getting_started.html",
        "resources":        "wiki/guide_resources.html",
        "buildings":        "wiki/guide_buildings.html",
        "armies":           "wiki/guide_armies.html",
        "world-map":        "wiki/guide_world_map.html",
        "combat-basics":    "wiki/guide_combat_basics.html",
        "monster-camps":    "wiki/guide_monster_camps.html",
        "forts":            "wiki/guide_forts.html",
        "advanced-combat":  "wiki/guide_advanced_combat.html",
        "clans":            "wiki/guide_clans.html",
        "tips":             "wiki/guide_tips.html",
    }

    if guide not in valid_guides:
        abort(404)

    return render_template(valid_guides[guide])
