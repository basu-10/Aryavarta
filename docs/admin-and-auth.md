# Authentication and Admin

## Session-based auth

Flask's built-in signed cookie session is used. On login/register, two values are stored:

```text
session["player_id"]  — integer PK
session["username"]   — display name
```

In addition to the Flask session cookie, login/register now issues a `bc_remember` cookie.
The raw token is never stored in plaintext: its SHA-256 hash is persisted in `auth_remember_token`.

If a request arrives without `session["player_id"]` but with a valid non-revoked remember token,
the app restores the session automatically before route handlers run. This allows a user to log in once
and then refresh other open tabs to continue without re-entering credentials in each tab.

Logout revokes the remember token in the database and clears the cookie.

The `login_required` decorator in `auth_bp.py` checks for `session["player_id"]`. The `admin_required` decorator additionally checks the logged-in player's role from the database.

Admin role checks are sourced from the database on each request (`player.role == 'admin'`), so role changes are effective immediately.

The navbar receives a `nav_is_admin` flag from an app-level context processor and only shows `Admin Dashboard` + `Test Run` links for logged-in admins.

### Secret key

`app.secret_key` is read from the `SECRET_KEY` environment variable. If not set, `secrets.token_hex(32)` generates a random key at startup. In development this is fine; in production, set `SECRET_KEY` as a persistent environment variable so sessions survive server restarts.

With remember tokens enabled, a random key rotation no longer forces manual re-entry of credentials on every open tab. A simple refresh can restore the session from the remember token.

---

## Default entry route

The root route `/` now serves a public landing page for guests.
If the user is already authenticated, opening `/` redirects to `/world`.

---

## Player roles

There are two independent role fields on the `player` table:

### System role (`player.role`)
Controls access to game routes and the admin area.

| Role | Access |
|---|---|
| `player` | All normal game routes |
| `admin` | All normal routes + `/admin/*` (dashboard + test harness) |
| `banned` | Login rejected at the `login_required` check |

### Clan role (`player.clan_role`)
Controls permissions within the player's clan. `NULL` when the player is not in any clan.

| Clan role | Permissions |
|---|---|
| `leader` | Full control — promote/demote anyone, set description, kick, disband |
| `co-leader` | Promote/demote Elders and Members; accept/reject applications |
| `elder` | Accept/reject applications; send recruitment DMs |
| `member` | Chat only |

The two roles are completely independent. An `admin` player has no special powers inside a clan unless they also hold a leader/elder role there.

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
