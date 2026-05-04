# Player and Auth Rules

## Registration

- Username must be unique. No email required.
- On registration, the player receives:
  - A castle at an unoccupied cell (assigned by the server)
  - Starting resources: 200 food, 200 timber, 100 gold, 100 metal
- The player has no fort yet — they must capture one.

---

## Session

- Login uses Flask's signed cookie session storing `player_id` and `username`.
- A `bc_remember` cookie is issued at login for persistent sessions. Its hash is stored in the database, not the raw token.
- If a request arrives without a valid session cookie but with a valid remember token, the session is restored automatically.
- Logout revokes the remember token and clears the cookie. All tabs become unauthenticated after revocation.

---

## Player roles (system)

Two independent role systems exist: system role and clan role.

### System role

| Role | Access |
|---|---|
| `player` | All normal game routes |
| `admin` | All normal routes + admin dashboard |
| `banned` | Login rejected — cannot access anything |

- Role changes take effect **immediately** on the next request (checked from the database, not the session).
- There is no self-registration for admin. An existing admin must promote another player via the shell or admin dashboard.

### Clan role

Stored on the player row as `clan_role`. See [clan-rules.md](clan-rules.md) for details.

- `NULL` when the player is not in a clan.
- The system role and clan role are completely independent — being an admin gives no special powers inside a clan.

---

## Admin capabilities

Admins access the `/admin` dashboard, which allows:

- Banning or unbanning players
- Promoting players to admin
- Spawning world entities (forts, monster camps) manually
- Disbanding clans
- Running test harnesses

---

## Direct messages (DMs)

- Any player can send a DM to any other player.
- Clan recruitment DMs are a special subtype with Accept/Decline buttons. Accepting one joins the clan as a Member.
- DMs are stored in `dm_message`. There is no read receipts or typing indicators.
- Players see only their own inbox — DMs to others are not visible.

---

## What new players should do first

1. Check starting resources.
2. Build a Farm, Lumber Mill, or other resource building at the castle.
3. Build a Garrison or Stable to start training troops.
4. Once enough troops are trained, attack a ★ (1-star) fort on the world map.
5. After capturing a fort, repair the Command Centre before using it to dispatch troops.
