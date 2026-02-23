"""
app.py — BattleCells Flask entry point.

Run with:
    flask --app app run --debug
or:
    python app.py
"""

import os
from pathlib import Path

from flask import Flask

from blueprints.battle_bp import battle_bp


def create_app(output_dir: str | None = None) -> Flask:
    """Application factory — testable and config-injectable."""
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # Resolve output directory
    base = Path(__file__).parent
    app.config["OUTPUT_DIR"] = output_dir or str(base / "output")
    Path(app.config["OUTPUT_DIR"]).mkdir(exist_ok=True)

    # Register blueprints
    app.register_blueprint(battle_bp)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
