"""
app.py — BattleCells Flask entry point.

Run with:
    flask --app app run --debug
or:
    python app.py
"""

import os
import secrets
from pathlib import Path

from flask import Flask, send_from_directory, session

from blueprints.battle_bp import battle_bp
from blueprints.auth_bp import auth_bp
from blueprints.world_bp import world_bp
from blueprints.fort_bp import fort_bp
from blueprints.clan_bp import clan_bp
from blueprints.admin_bp import admin_bp
from blueprints.wiki_bp import wiki_bp
import db as database
from utils.battle_store import init_store


def _format_qty(n) -> str:
    """Jinja2 filter: format large numbers as 1k / 1M / 1B."""
    try:
        n = int(n)
    except (TypeError, ValueError):
        return str(n)
    if n < 1:
        return "0"
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}".rstrip("0").rstrip(".") + "B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}".rstrip("0").rstrip(".") + "M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}".rstrip("0").rstrip(".") + "k"
    return str(n)


def create_app(output_dir: str | None = None) -> Flask:
    """Application factory — testable and config-injectable."""
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.jinja_env.filters["format_qty"] = _format_qty

    # Secret key (use env var in production)
    app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

    # Resolve output directory
    base = Path(__file__).parent
    app.config["OUTPUT_DIR"] = output_dir or str(base / "output")
    Path(app.config["OUTPUT_DIR"]).mkdir(exist_ok=True)
    init_store(app.config["OUTPUT_DIR"])

    # Database
    app.config["DATABASE"] = str(base / "battlecells.db")
    database.init_app(app)

    # Register blueprints
    app.register_blueprint(battle_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(world_bp)
    app.register_blueprint(fort_bp)
    app.register_blueprint(clan_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(wiki_bp)

    # Serve the assets folder at /assets/<path>
    assets_dir = str(base / "assets")

    @app.route("/assets/<path:filename>")
    def serve_asset(filename: str):
        return send_from_directory(assets_dir, filename)

    @app.context_processor
    def inject_nav_flags():
        player_id = session.get("player_id")
        if not player_id:
            return {"nav_is_admin": False, "nav_clan_id": None, "show_tutorial": False}
        from db import models as m
        player = m.get_player_by_id(player_id)
        return {
            "nav_is_admin": bool(player and player.get("role") == "admin"),
            "nav_clan_id": player.get("clan_id") if player else None,
            "show_tutorial": bool(player and not player.get("tutorial_seen", 1)),
        }

    # Seed monster forts and camps on startup (tops up to configured maximums)
    with app.app_context():
        from db import init_db
        init_db()
        from db.world_seeder import ensure_world_entities
        ensure_world_entities()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
