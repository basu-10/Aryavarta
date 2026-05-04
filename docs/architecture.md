# Architecture

## Tech stack choices

### Flask 3.x + Python
The existing battle simulator already ran on Flask. Extending it with blueprints kept the project unified and avoided introducing a second web framework.

### SQLite via `sqlite3` (stdlib)
No ORM was introduced deliberately. The game is a small single-server application; raw SQL keeps the query layer explicit and easy to inspect. Swapping to PostgreSQL later requires changing only `db/__init__.py` (the connection factory).

`PRAGMA foreign_keys = ON` is set on every connection. SQLite disables FK enforcement by default; the pragma ensures referential integrity is actually checked.

### No WebSockets — HTMX polling
All dynamic updates (resource bars, chat, mission countdowns, world map) use HTMX `hx-trigger="every Ns"` polling against plain HTML partial endpoints or JSON endpoints. This eliminates the need for an async server layer (Channels, Socket.IO, etc.) and lets Flask run as a standard WSGI app. Polling intervals are tuned per concern: chat at 3 s, resources at 5 s, map at 10 s.

### No message queue / background workers
There is no Celery, Redis, or cron. Battle resolution is **client-triggered**: the browser polls `/api/battles/active`, counts down the travel timer client-side, then calls `POST /api/missions/resolve` when the timer expires. The server re-validates the arrive_time before processing. This avoids any out-of-process infrastructure while remaining correct (the server is the authority on timing).

---

## Application factory pattern

`create_app()` in `app.py` is the entry point. Benefits:
- The test suite can call `create_app()` with a different `OUTPUT_DIR` without side effects.
- Database path is injected via `app.config["DATABASE"]`, not a global.

---

## Blueprint layout

| Blueprint | URL prefix | Responsibility |
|---|---|---|
| `battle_bp` | `/` | Battle simulator (setup, run, results, download, history navigation) |
| `auth_bp` | `/` | Register, login, logout, battle history (`/battles`) |
| `world_bp` | `/world` | World map, attack dispatch, mission resolution |
| `fort_bp` | `/` | Castle and fort management (buildings, troops, collect) |
| `clan_bp` | `/clan` | Full clan system — creation, roles, applications, chat, recruitment DMs |
| `wiki_bp` | `/wiki` | Game wiki — landing page, troops compendium, buildings reference, troop detail |
| `admin_bp` | `/admin` | Admin dashboard (ban, promote, spawn, disband) |

All world-game routes are gated behind the `login_required` decorator defined in `auth_bp`.

---

## Database lifecycle

`db/__init__.py` manages one SQLite connection per Flask app context via `flask.g`.
- `get_db()` opens a connection on first call within a request and caches it on `g` using `setattr`/`getattr` (Flask 3.x requires attribute access on `g`, not item assignment).
- `get_db()` enables `PRAGMA journal_mode = WAL` so map polling reads can proceed with less lock contention while writes are happening.
- `close_db()` is registered as a teardown callback; it closes the connection at the end of every request.
- `flask init-db` runs `db/schema.sql` (all `CREATE TABLE IF NOT EXISTS` — safe to re-run).
- `flask seed-world` is idempotent: it checks for existing forts/camps before inserting anything.

World-map entity tables (`castle`, `fort`, `monster_camp`, `map_decoration`) include composite `(world_id, grid_x, grid_y)` indexes (and `monster_camp` also includes `is_active`) to reduce scan cost for snapshot/occupancy queries.
