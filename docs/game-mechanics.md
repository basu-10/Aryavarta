# Game Mechanics

## World map

- 50 × 50 grid of cells.
- Each cell holds at most one entity: a player's castle, a fort, or a monster camp.
- Empty cells have no row in the database; occupancy is determined by querying `castle`, `fort`, and `monster_camp` for matching `(grid_x, grid_y)`.

---

## Castles

- One castle per player, assigned at registration.
- Indestructible and unattackable. Players can never lose their castle.
- Castle slot count is fixed at creation; Command Centre occupies slot 0 automatically.

---

## Forts

- Pre-seeded with monster garrisons and random slot counts (4–10).
- `owner_id = NULL` while monster-occupied; becomes the player's ID after capture.
- Capturing destroys all buildings at the fort (all `is_destroyed = 1`). The attacker starts from scratch except for the Command Centre that a new `create_fort` inserts.
- Losing a fort resets it the same way; the old owner loses all buildings there.

### Star levels (fort and monster camp difficulty)

Star level is determined by total defender unit count at seed time:

| Defenders | Stars |
|---|---|
| 1 – 4 | ★ |
| 5 – 8 | ★★ |
| 9 – 12 | ★★★ |
| 13+ | ★★★★ |

Thresholds live in `config.STAR_THRESHOLDS = [4, 8, 12]`.

---

## Attack & travel

1. Player selects troops and a target from the world map.
2. Server validates origin ownership and deducts troops immediately at dispatch (total wipeout on loss — there is no "return on failure").
3. Travel time is calculated as:
   ```
   travel_seconds = chebyshev_distance(origin, target) × WORLD_TRAVEL_SECONDS_PER_CELL / slowest_unit_speed
   ```
4. A `battle_mission` row is created with `depart_time` and `arrive_time`.
5. The browser counts down the travel time using the returned `travel_seconds`.
6. When the timer hits zero, the browser calls `POST /api/missions/resolve`.
7. The server re-validates `arrive_time ≤ now` before running the battle (prevents early resolution).

---

## Battle resolution

The existing deterministic 6-phase battle engine (`engine/`) is used unchanged.

- Attacker units are placed at random positions in Team A columns (0–3).
- Defender units are placed at random positions in Team B columns (5–8).
- Column 4 is no-man's-land.
- The battle runs up to `MAX_TICKS = 200` ticks.
- The result is stored via `utils/battle_store.py` (in-memory keyed by UUID).

### Outcomes

| Result | What happens |
|---|---|
| Attacker wins vs monster fort | `claim_fort` or `capture_fort`; loot resources added to attacker |
| Attacker wins vs player fort | `capture_fort`; all buildings destroyed; ownership transferred |
| Attacker wins vs monster camp | `deactivate_monster_camp`; gold + metal loot added to attacker |
| Defender wins | Nothing changes; attacker troops already gone (deducted at dispatch) |

---

## Resource system

Four resources: **food**, **timber**, **gold**, **metal**.

- Starting amounts: food 200, timber 200, gold 100, metal 100.
- Production buildings accumulate resources continuously using lazy evaluation (see [data-model.md](data-model.md)).
- Production rate doubles per building level: `rate × 2^(level-1)`.
- Players collect manually; collection resets `last_collected_at`.

### Building production rates (per second, level 1)

| Building | Resource | Rate/s |
|---|---|---|
| Farm | food | 0.05 |
| Lumber Mill | timber | 0.05 |
| Merchant | gold | 0.05 |
| Mine | metal | 0.05 |

---

## Troop production

Army buildings produce troops over time (same lazy eval as resources):

| Building | Produces | Interval |
|---|---|---|
| Garrison | Longbowman | 60 s / unit |
| Stable | Hussar | 90 s / unit |

Troops are added to the troop table as an idle stack at the building's location when collected.

---

## Monster camp loot

Defeating a monster camp awards: **50 gold + 30 metal**.
