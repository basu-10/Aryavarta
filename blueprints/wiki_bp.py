"""
blueprints/wiki_bp.py — Troopedia: game wiki pages for every troop type.
"""

from __future__ import annotations

from flask import Blueprint, render_template, abort
from db import get_db

wiki_bp = Blueprint("wiki", __name__, url_prefix="/troopedia")


def _slug(name: str) -> str:
    return name.lower().replace(" ", "-")


def _troop_image_path(name: str) -> str | None:
    """Return the URL path for a troop's full-art SVG, or None."""
    _IMAGE_MAP: dict[str, str] = {
        "Archer":      "/assets/theme1/troops/human/full/archer.svg",
        "Hussar":      "/assets/theme1/troops/human/full/hussar.svg",
        "Longbowman":  "/assets/theme1/troops/human/full/longbowman.svg",
        "Troll":       "/assets/theme1/troops/monster/full/troll.svg",
        "Wraith":      "/assets/theme1/troops/monster/full/wraith.svg",
    }
    return _IMAGE_MAP.get(name)


def _category_label(category: str) -> str:
    return {
        "infantry":     "Infantry",
        "ranged":       "Ranged",
        "cavalry":      "Cavalry",
        "monster":      "Monster",
        "siege_defence": "Siege / Defence",
    }.get(category, category.title())


def _category_color(category: str) -> str:
    return {
        "infantry":     "text-orange-400",
        "ranged":       "text-sky-400",
        "cavalry":      "text-yellow-400",
        "monster":      "text-red-400",
        "siege_defence": "text-purple-400",
    }.get(category, "text-gray-400")


@wiki_bp.route("/")
def troopedia_index():
    db = get_db()
    # One row per troop — level-1 stats only
    rows = db.execute(
        "SELECT * FROM ref_troop_level WHERE level = 1 ORDER BY category, troop_type"
    ).fetchall()

    troops = []
    for r in rows:
        r = dict(r)
        r["slug"] = _slug(r["troop_type"])
        r["image"] = _troop_image_path(r["troop_type"])
        r["category_label"] = _category_label(r["category"])
        r["category_color"] = _category_color(r["category"])
        troops.append(r)

    # Group by category for display
    categories: dict[str, list] = {}
    for t in troops:
        categories.setdefault(t["category_label"], []).append(t)

    return render_template("wiki/troopedia.html", troops=troops, categories=categories)


@wiki_bp.route("/<slug>")
def troop_detail(slug: str):
    db = get_db()
    # Resolve slug back to troop_type
    all_types = db.execute(
        "SELECT DISTINCT troop_type FROM ref_troop_level"
    ).fetchall()

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
    )
