# Authentication and Admin

## Session-based auth

Flask's built-in signed cookie session is used. On login/register, three values are stored:

```
session["player_id"]  — integer PK
session["username"]   — display name
session["role"]       — "player" | "admin" | "banned"
```

The `login_required` decorator in `auth_bp.py` checks for `session["player_id"]`. The `admin_required` decorator additionally checks `session["role"] == "admin"`.

### Secret key

`app.secret_key` is read from the `SECRET_KEY` environment variable. If not set, `secrets.token_hex(32)` generates a random key at startup. In development this is fine; in production, set `SECRET_KEY` as a persistent environment variable so sessions survive server restarts.

---

## Player roles

| Role | Access |
|---|---|
| `player` | All normal game routes |
| `admin` | All normal routes + `/admin/*` |
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
