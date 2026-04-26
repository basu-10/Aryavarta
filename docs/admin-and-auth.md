# Authentication and Admin

## Session-based auth

Flask's built-in signed cookie session is used. On login/register, two values are stored:

```text
session["player_id"]  — integer PK
session["username"]   — display name
```

The `login_required` decorator in `auth_bp.py` checks for `session["player_id"]`. The `admin_required` decorator additionally checks the logged-in player's role from the database.

Admin role checks are sourced from the database on each request (`player.role == 'admin'`), so role changes are effective immediately.

The navbar receives a `nav_is_admin` flag from an app-level context processor and only shows `Admin Dashboard` + `Test Run` links for logged-in admins.

### Secret key

`app.secret_key` is read from the `SECRET_KEY` environment variable. If not set, `secrets.token_hex(32)` generates a random key at startup. In development this is fine; in production, set `SECRET_KEY` as a persistent environment variable so sessions survive server restarts.

---

## Player roles

| Role | Access |
|---|---|
| `player` | All normal game routes |
| `admin` | All normal routes + `/admin/*` (dashboard + test harness) |
| `banned` | Login rejected at the `login_required` check |

---

## Admin bootstrap

There is no built-in first-admin registration flow. To create the first admin after `flask init-db`:

```bash
# Promote an existing registered player by username
flask --app app shell
>>> from db import models as m
>>> from app import create_app; app = create_app()
>>> with app.app_context():
...     p = m.get_player_by_username("yourusername")
...     m.set_player_role(p["id"], "admin")
```

Alternatively, the admin dashboard's `/admin/promote/<id>` route can be used by any existing admin.

---

## Admin dashboard capabilities

- View player count, fort count, active mission count, clan count.
- Ban a player (sets role to `"banned"`).
- Promote a player to admin.
- Spawn additional forts or monster camps onto the world map.
- Deactivate a monster camp manually.
- Disband a clan (clears all member clan_ids then deletes the clan row).

---

## Admin test harness

Admin-only bulk testing is available in two ways:

- Web page: `GET /admin/test-run`
- Form submit: `POST /admin/test-run`
- Script: `python run_admin_test_harness.py`

Both paths call the shared module `utils/admin_test_harness.py`.

Capabilities:

- Select multiple formation presets in one run.
- Filter targets by one star level (`1..6`).
- Filter target categories: `monster_camp`, `monster_fort`, `npc_fort`.
- Resolve each attack through the normal mission flow and append results to the admin account's regular battle history (`/battles`).

Safety notes (development only):

- Harness runs can auto-fill missing troops and even auto-grant an origin fort to the admin so runs do not block on setup.
- Script mode does not require web login/password; it directly resolves against the specified admin username.
