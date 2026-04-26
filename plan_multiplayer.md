# BattleCells — Multiplayer World Game Plan

---

## 1. Project Overview

A browser-based multiplayer strategy game hosted on a public server. Players register, build a castle, claim forts across a shared world map, produce resources, train troops, and wage war against monster camps and other players. Combat uses the existing deterministic grid-based battle engine. No WebSockets — all dynamic updates delivered via HTMX polling.

---

## 2. Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python / Flask |
| Frontend | HTML + CSS + HTMX (polling) |
| Auth | Flask session-based login |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Battle Engine | Existing `engine/` (unchanged) |
| Dynamic Updates | HTMX `hx-trigger="every Ns"` polling |

---

## 3. Core Concepts

### 3.1 Castle (Player Home Base)
- Every player owns exactly **one castle**, auto-assigned on registration.
- Castles are **permanently indestructible and uncapturable**.
- Castles **cannot be attacked** — no attack option appears in the world map popup.
- Follows the same building slot rules as forts.
- Slot count: same range as forts (4–10 slots), assigned on account creation.

### 3.2 Fort
- Structures scattered across the world map grid.
- Spawned randomly with a **random slot count** (4–10; 4–5 common, 10 rare).
- **Freshly spawned forts** contain only a **Command Centre** (default fixed building) and monster defenders. All other slots are empty.
- Players claim a fort by attacking and defeating its monster defenders.
- Once owned, the player can construct buildings in empty slots.
- Forts **can be captured** by other players — all buildings are destroyed on defeat; ownership transfers to the attacker. Previous owner must find and claim a new unclaimed fort.
- A player can own **any number of forts** simultaneously (no cap).

### 3.3 Monster Camp
- Non-player enemy entities placed randomly across the world grid.
- Attacking a monster camp yields **Gold and Metal only** (no Food or Timber).
- Defeating a monster camp **captures** the monsters — they become troops under the player's command and appear at the attacking fort's Command Centre.
- New monster camps spawn randomly across the world over time (server-side scheduled task).

### 3.4 Troop
- Two sources of troops:
  1. **Trained** — produced by Garrison (Longbowmen) or Stable (Hussars) buildings.
  2. **Captured** — monster units obtained by defeating monster camps; appear at the nearest Command Centre.
- Troops have no global cap; limited only by production rate.
- While troops are **traveling to a battle**, they are locked and unavailable.
- After a battle resolves, **surviving troops remain at the target location**. If the fort was captured, they garrison there automatically.

---

## 4. Resources

### 4.1 Resource Types
| Resource | Produced By |
|---|---|
| Food | Farm |
| Timber | Lumber Mill |
| Gold | Merchant |
| Metal | Mine |

### 4.2 Storage & Collection
- Resources produced by a building are stored **in the fort/castle where that building is located**, not in the player's account.
- Players must **manually collect** resources to transfer them to their account balance.
- If a fort is defeated while holding uncollected resources, **all uncollected resources in that fort are lost** and awarded to the attacker.
- The castle's uncollected resources are safe (castle cannot be captured or attacked).

### 4.3 Production Model
- Buildings accumulate resources based on elapsed time since last collection (lazy calculation — computed on demand when the player visits or polls).
- The HTMX-polled resource display fetches the server-calculated current value each interval.

---

## 5. Building System

### 5.1 Building Types
| Category | Building | Output / Function |
|---|---|---|
| Resource | Farm | Produces Food |
| Resource | Lumber Mill | Produces Timber |
| Resource | Merchant | Produces Gold |
| Resource | Mine | Produces Metal |
| Army | Garrison | Trains Longbowmen (slow, long-range) |
| Army | Stable | Trains Hussars (light, fast cavalry) |
| Defence | Cannon | Splash damage, slow rate of fire |
| Defence | Archer Tower | Single-target, fast rate of fire |
| Default (fixed) | Command Centre | Troop management; captured troops appear here |

### 5.2 Slot Rules
- Each building occupies 1 slot.
- Command Centre is the default fixed building — always present; does not occupy a numbered slot.
- All other building types are placed by the player into available slots.

### 5.3 Build, Repair, Upgrade
| Action | Time | Cost |
|---|---|---|
| Place a new building in an empty slot | 30 seconds – 1 minute | Varies by building type |
| Repair a destroyed building | Instant | Resource cost (varies) |
| Upgrade a building | TBD | TBD (increases output rate or troop production speed) |

- Repair restores a previously destroyed building to full function immediately on payment.
- Placing a new building in a blank slot triggers a build timer visible to the player.

---

## 6. World Map

### 6.1 Structure
- A **large 2D grid** shared by all players.
- Each cell may be occupied by: a player castle, a player-owned fort, a monster camp, or an unclaimed fort (containing monsters).
- Items are represented as clickable icons on the map.

### 6.2 World Map Item Popup
When a player clicks an icon, a popup appears with relevant options:

| Target Type | Available Actions |
|---|---|
| Own castle | Manage (buildings, troops, resources) |
| Own fort | Manage (buildings, troops, resources) |
| Another player's castle | Scout only |
| Another player's fort | Scout, Attack |
| Unclaimed fort (monsters inside) | Scout, Attack |
| Monster camp | Scout, Attack |

No Attack option is shown for another player's castle.

### 6.3 Distance & Travel Time
- Distance between two grid cells is calculated as grid units (e.g., Chebyshev or Manhattan distance — TBD).
- Travel time = distance × 1 second per tick (using the movement speed of the **slowest troop** in the formation).
- Players can send troops from **multiple forts simultaneously** toward a single target (each group travels independently; travel time differs per origin fort).

---

## 7. Combat System

### 7.1 Initiating an Attack
1. Player clicks target icon on world map → popup appears.
2. Player selects **Attack**.
3. Player selects a troop formation — choose from saved presets or build a custom one using available troops across their castle and forts.
4. Troops are locked (unavailable for other deployments) immediately on dispatch.
5. A **countdown timer** is displayed until the battle resolves.

### 7.2 Defender Placement (Random)
When a battle is triggered against a fort or monster camp, all defending units are placed at **random positions** within Team B's half of the battle grid (columns 5–8). This applies to garrisoned troops, defence building units (Cannon, Archer Tower), and monster units alike. Attacker units are placed randomly in Team A's half (columns 0–3).

### 7.2a Star Level
Forts occupied by monsters and standalone monster camps display a **star level (1–4)** indicating how densely their battle grid half is filled with defenders:

| Stars | Defender Count |
|---|---|
| ★ | 1–4 units |
| ★★ | 5–8 units |
| ★★★ | 9–12 units |
| ★★★★ | 13–16 units |

### 7.3 Battle Resolution
- After the travel time elapses, the existing battle engine (`engine/`) runs the simulation deterministically.
- The attacker receives a **battle report** (same as the existing `/results/` page).
- **If attacker wins (fort/monster camp):**
  - Ownership of the fort transfers to the attacker.
  - All uncollected resources in the fort are awarded to the attacker.
  - All buildings in the fort are destroyed (require instant-repair before functioning).
  - Surviving attacker troops remain and garrison the captured fort.
- **If attacker loses:**
  - Defending fort/camp remains unchanged.
  - Attacker troops are lost.

### 7.3 Scout Action
- Player selects **Scout** from the popup instead of Attack.
- A scout unit is dispatched; travel time follows the same distance formula.
- On arrival, a **scout report** is returned showing the target's troop composition and building layout.
- Scout report is visible only to the dispatching player.

---

## 8. Troop Production

### 8.1 Training (Human Troops)
- Garrison produces **Longbowmen** — slow, long-range attackers.
- Stable produces **Hussars** — light, fast cavalry.
- Production cost and time: TBD.
- Produced troops appear at the building's fort Command Centre when ready.

### 8.2 Captured Troops (Monsters)
- Defeating a monster camp captures the monster units.
- They travel back with surviving troops and appear at the **attacking fort's Command Centre** after the elapsed travel time.
- Captured monsters are treated as standard troops once in the Command Centre.

---

## 9. Player Account & Authentication

### 9.1 Flows
- Register (username, password)
- Login / Logout
- Profile page (account balance of all 4 resources, owned forts overview, troop summary)

### 9.2 Account Resource Balance
- Separate from fort-stored resources.
- Increased when player manually collects from a fort/castle.
- Used to pay for building construction, repair, upgrades, and troop training.

---

## 10. Clan / Alliance System

- Players can create or join a **clan** (guild/alliance).
- Each clan has its own **clan chat** (isolated from other clans).
- Clan chat uses HTMX polling for near-real-time messages.
- Attacks are always **individual** — clans are social only; no joint attacks.
- Admin can manage clans from the dashboard.

---

## 11. Admin Dashboard

Accessible only to admin-role accounts. Covers:

| Area | Functions |
|---|---|
| User Management | View accounts, ban users, delete accounts |
| World State | View live world map, manually spawn/remove monsters and forts |
| Clan Management | View, edit, or disband clans |
| Server Stats | Active sessions, recent battle logs, error logs |
| Preset / Unit Config | Edit unit base stats (damage, speed, range, etc.) without touching code |

---

## 12. HTMX Polling Architecture

| What is polled | Endpoint | Interval |
|---|---|---|
| Fort resource display | `GET /api/fort/<id>/resources` | ~5 seconds |
| Castle resource display | `GET /api/castle/resources` | ~5 seconds |
| Clan chat messages | `GET /api/clan/<id>/chat` | ~3 seconds |
| Active battle countdowns | `GET /api/battles/active` | ~2 seconds |
| World map updates | `GET /api/world/map` | ~10 seconds |

- All resource values are computed server-side using elapsed time since last collection.
- Polling stops or pauses when the relevant page/element is not visible.

---

## 13. Pages & Routes

| Page | Route | Description |
|---|---|---|
| Landing / Login | `/` | Login form or redirect to world if logged in |
| Register | `/register` | Create account |
| World Map | `/world` | Main game view — the shared grid map |
| Castle | `/castle` | Manage own castle (buildings, troops, resources) |
| Fort | `/fort/<id>` | Manage a specific owned fort |
| Battle Report | `/results/<battle_id>` | Post-battle result viewer (existing page) |
| Clan | `/clan` | Clan overview + chat |
| Profile | `/profile` | Account stats, fort list, troop summary |
| Admin | `/admin` | Admin dashboard (role-gated) |

---

## 14. High-Level Data Model

| Entity | Key Fields |
|---|---|
| Player | id, username, password_hash, role, food, timber, gold, metal, clan_id |
| Castle | id, player_id, slot_count, grid_x, grid_y |
| Fort | id, owner_id (nullable), slot_count, grid_x, grid_y, last_defeated_at |
| Building | id, location_type (castle/fort), location_id, slot_index, type, level, placed_at, last_collected_at |
| WorldItem | id, type (monster_camp / unclaimed_fort), grid_x, grid_y, unit_data (JSON), is_active |
| Troop | id, owner_id, type, count, garrison_location_type, garrison_location_id, state (idle / traveling / in_battle) |
| BattleMission | id, attacker_id, target_type, target_id, formation (JSON), depart_time, arrive_time, resolved, result_id |
| BattleResult | id, mission_id, winner, report_csv_path |
| Clan | id, name, leader_id, created_at |
| ClanMessage | id, clan_id, sender_id, message, sent_at |

---

## 15. Open Questions (TBD)

| # | Question |
|---|---|
| 1 | Scout unit type — does the player spend a specific troop unit to scout, or is it a free action with travel time? |
| 2 | Building upgrade — is upgrading instant or timed? What are the resource costs per level? |
| 3 | Troop training — what are the resource costs and training times for Longbowmen and Hussars? |
| 4 | Distance formula — Manhattan or Chebyshev distance on the world grid? |
| 5 | World map size — what are the grid dimensions? |
| 6 | Fort spawn rate — how frequently do new forts and monster camps appear? |
| 7 | Resource production rates per building type and per level |
| 8 | Building repair costs per building type |
| 9 | Multi-fort troop dispatch — if troops from multiple forts arrive at different times, does each group fight separately or wait to combine? | **Resolved:** each group travels and fights independently. |
| 10 | Troop death on loss — do all attacking troops die on a loss, or do some survive and return? | **Resolved: Total wipeout** — all attacking troops are lost on a defeat. |
