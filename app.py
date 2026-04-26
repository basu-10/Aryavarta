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

from flask import Flask

from blueprints.battle_bp import battle_bp
from blueprints.auth_bp import auth_bp
from blueprints.world_bp import world_bp
from blueprints.fort_bp import fort_bp
from blueprints.clan_bp import clan_bp
from blueprints.admin_bp import admin_bp
import db as database


def create_app(output_dir: str | None = None) -> Flask:
    """Application factory — testable and config-injectable."""
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # Secret key (use env var in production)
    app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

    # Resolve output directory
    base = Path(__file__).parent
    app.config["OUTPUT_DIR"] = output_dir or str(base / "output")
    Path(app.config["OUTPUT_DIR"]).mkdir(exist_ok=True)

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

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
