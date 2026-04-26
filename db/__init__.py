"""
db/__init__.py — Database connection factory for BattleCells World.

Provides:
    get_db()   — returns the SQLite connection for the current Flask app context
    init_db()  — creates all tables from schema.sql
    init_app() — registers teardown and CLI commands with a Flask app

To swap to a different database backend later, update only this module
and db/models.py (the query layer). All callers use get_db().
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from flask import Flask, g

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"
_DB_KEY = "_battlecells_db"


def get_db() -> sqlite3.Connection:
    """Return the SQLite connection bound to the current Flask app context."""
    if not hasattr(g, _DB_KEY):
        from flask import current_app
        conn = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        setattr(g, _DB_KEY, conn)
    return getattr(g, _DB_KEY)


def close_db(exc=None) -> None:
    conn = getattr(g, _DB_KEY, None)
    if conn is not None:
        delattr(g, _DB_KEY)
        conn.close()


def init_db() -> None:
    """Run schema.sql against the configured database."""
    db = get_db()
    db.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))
    db.commit()


def init_app(app: Flask) -> None:
    """Register DB lifecycle hooks and CLI commands with the Flask app."""
    app.teardown_appcontext(close_db)

    @app.cli.command("init-db")
    def _cli_init_db():
        """Create database tables from schema.sql."""
        from flask import current_app
        init_db()
        print(f"Database initialised at {current_app.config['DATABASE']}")

    @app.cli.command("seed-world")
    def _cli_seed_world():
        """Seed initial forts and monster camps onto the world map (idempotent)."""
        from db.world_seeder import seed_world
        count = seed_world()
        if count.get("skipped"):
            print("World already seeded — skipped (database already contains forts/camps).")
        else:
            print(f"World seeded: {count['forts']} forts, {count['camps']} monster camps.")
