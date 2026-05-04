# World Map Rules

## The Grid

- 50×50 cell map. Each cell holds at most **one** entity: a player castle, a player fort, or a monster camp.
- Empty cells have no database row — occupancy is determined by querying the relevant tables, not a separate "cell" table.

---

## Entity types on the map

| Entity | Owned by | Attackable? | Permanent? |
|---|---|---|---|
| Castle | Player | No | Yes |
| Fort | Player or monster | Yes | Yes (never moves) |
| Monster camp | Monster | Yes | No (respawns elsewhere after defeat) |

---

## Monster fort caps

- The map maintains at most **15 unowned monster forts** and **10 active monster camps** at any time.
- Caps are enforced on app startup and every time the world map is requested (GET `/api/world/map`).
- Spawn is a **top-up**, not a periodic wave — only enough entities are created to reach the cap.
- When a player captures a monster fort, that cell stays player-owned; a new monster fort can spawn elsewhere to restore the cap.

---

## Star levels (difficulty)

Rolled once at spawn for both forts and monster camps. Never changes after that.

| Stars | Spawn chance | Garrison size |
|---|---|---|
| ★ | 20% | 2–3 units |
| ★★ | 18% | 4–5 units |
| ★★★ | 15% | 6–8 units |
| ★★★★ | 12% | 9–11 units |
| ★★★★★ | 10% | 12–14 units |
| ★★★★★★ | 8% | 15–16 units |
| ★★★★★★★ | 7% | 17–19 units |
| ★★★★★★★★ | 5% | 20–22 units |
| ★★★★★★★★★ | 3% | 23–25 units |
| ★★★★★★★★★★ | 2% | 26–30 units |

The unit mix is random from the monster roster, but total unit count always stays inside the band.

---

## Respawn behaviour

- A defeated monster camp is deactivated. The next top-up spawns a replacement in a different empty cell.
- Monster forts do not relocate — the same cell stays a fort, ownership just changes.
- If the attacker loses, nothing respawns or changes; the fort/camp is still alive.

---

## Travel time

Travel time from origin to target is:

```
travel_seconds = chebyshev_distance(origin, target) × WORLD_TRAVEL_SECONDS_PER_CELL / slowest_unit_speed
```

- Chebyshev distance means diagonal moves cost the same as cardinal moves.
- Speed is determined by the slowest unit in the attacking party.
- The browser countdown uses the returned `travel_seconds`. Resolution is **client-triggered** — the browser calls resolve when the timer hits zero.
- The server re-validates `arrive_time ≤ now` before running the battle, so early resolution is rejected.
