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
- The map keeps at most **15 unowned monster forts** and **10 active monster camps** at a time.

### Star levels (fort and monster camp difficulty)

Wild fort and camp star level is rolled at spawn time using the same table for both entity types:

| Stars | Spawn chance | Defender total |
|---|---|
| ★ | 25% | 2–3 monsters |
| ★★ | 25% | 4–5 monsters |
| ★★★ | 20% | 6–8 monsters |
| ★★★★ | 15% | 9–11 monsters |
| ★★★★★ | 10% | 12–14 monsters |
| ★★★★★★ | 5% | 15–16 monsters |

The rolled star level is stored on the fort/camp row in `star_level`. The spawned unit mix is random across the monster roster, but the total unit count always stays inside that star band's range.

### Spawn and respawn rules

- Spawn occurs in two places: once on app startup, and again every time the world map API (`GET /api/world/map`) is requested.
- Spawn is a top-up, not a periodic wave timer. The server only creates enough wild entities to reach the configured caps.
- A defeated monster camp is deactivated. When the next top-up runs, a replacement camp appears in a new empty cell.
- A monster fort does not relocate when a player wins it. The same fort stays on the same cell and becomes player-owned.
- If a monster fort is claimed by a player, the next top-up can spawn a different monster fort somewhere else so the map returns to the unowned-fort cap.
- If the attacker loses, nothing respawns or moves because the original fort/camp is still there.

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

## Troop training

Army buildings train only human troops and use a real queue (not passive lazy production):

| Building | Produces | Base training time |
|---|---|---|
| Garrison (Barracks) | Longbowman | 60 s / unit |
| Stable | Hussar | 90 s / unit |

- Training is one-at-a-time per building, but multiple troops can be queued.
- Resources are deducted immediately when a unit is queued.
- Completed units are deployed instantly to the same location (`castle` or `fort`) as idle troops.
- UI shows both queue length and available troop count for the trained type.

### Dismissal and refund

- Dismissing troops is instant.
- Refund is immediate and currently set to 50% of that troop's training cost (`config.TROOP_REFUND_RATE`).

### Training queue storage

- Queue rows are stored in `training_queue` with absolute `complete_at` timestamps.
- Queue completion is processed when location/building data is fetched.

### Defense ammo system

- `Cannon` consumes `cannon_ball` ammo; `Archer Tower` consumes `arrow` ammo.
- Ammo is purchased with resources and loaded in bulk per building.
- Defense buildings are expected to hold multiple ammo units.
- During battle simulation, 1 ammo is consumed for each attack tick fired by a defense building unit.

---

## Clans

### Creation

Any player can found a clan by spending **1000 Food, 1000 Timber, 1000 Gold, and 1000 Metal**. The founding player becomes the clan's **Leader** automatically.

### Role hierarchy

```
Leader  >  Co-leader  >  Elder  >  Member
```

All new joiners are assigned the **Member** role.

### Promotion and demotion rules

| Actor role | Can promote/demote |
|---|---|
| Leader | Anyone below Leader (co-leader, elder, member) |
| Co-leader | Elders and Members only |
| Elder | Nobody |
| Member | Nobody |

A Leader can transfer leadership to any member. The old Leader is automatically demoted to Co-leader when this happens.

### Join flow (application)

1. A player without a clan visits any public clan page (`/clan/<id>`) or the clan list (`/clan`) and clicks **Apply**.
2. An `clan_application` row is created with `status = 'pending'`.
3. The pending application appears in the **Applications** tab of the clan's member UI, visible to Elders and above.
4. An Elder, Co-leader, or Leader accepts or rejects the application.
5. On acceptance the player is added to the clan with the Member role and `clan_joined_at` is set.
6. A rejected player may re-apply.

### Recruitment DMs

Elders, Co-leaders, and Leaders can send a **recruitment DM** directly to any player from the world map. The DM appears in the recipient's inbox with **Accept / Decline** buttons. Accepting the invite automatically adds the player to the clan as a Member (instant join — no application approval needed).

### Chat

Clan chat is polled every 3 seconds. A player only sees messages sent **after** the timestamp they joined the clan (`clan_joined_at`), so no pre-join history is visible. Old history is not shown regardless of how much history exists.

### Leaving and disbanding

- Any non-Leader member can leave at any time.
- A Leader must transfer leadership before leaving if other members remain.
- If the Leader is the only member, leaving automatically **disbands** the clan (all data, messages, and applications are deleted).

### Clan description

The clan description (up to 500 characters) can be set and edited by the Leader or Co-leader only. It is shown on the public clan page and in the Info tab.

### Public clan page

`/clan/<id>` is visible to any logged-in player. Non-members see the Apply button (or a "pending" indicator if they have already applied). Members see a "View My Clan" link instead.

---

## Monster camp loot

Defeating a monster camp awards: **50 gold + 30 metal**.
