# Buildings Rules

## Slot limits

- Every fort and castle has a fixed number of building slots (4–10 for forts; fixed count for castles).
- Slot 0 is always occupied by the Command Centre. Players fill the remaining slots.
- You cannot build more buildings than available slots.

---

## Command Centre

- Auto-placed in slot 0 of every fort and castle. Cannot be removed.
- If the Command Centre is **broken**, the owner cannot send troops from that location. It must be repaired first.
- Build time is instant; no cost.

---

## Resource buildings

Produce one resource passively. No background timer — resources accumulate lazily (see resources-rules.md).

| Building | Produces | Build time | Build cost |
|---|---|---|---|
| Farm | food | 45 s | 50 food + 30 timber |
| Lumber Mill | timber | 60 s | 50 timber + 30 gold |
| Merchant | gold | 50 s | 80 gold + 20 metal |
| Mine | metal | 55 s | 50 metal + 40 gold |

---

## Army buildings

Train human troops in a queue.

| Building | Produces | Build time | Build cost |
|---|---|---|---|
| Garrison | Longbowman | 60 s | 100 gold + 50 metal |
| Stable | Hussar | 60 s | 120 gold + 60 metal + 20 timber |

---

## Defence buildings

Spawn a stationary unit into the battle grid when the location is attacked.

| Building | Unit spawned | Build time | Build cost |
|---|---|---|---|
| Cannon | Cannon unit | 45 s | 100 metal + 50 gold |
| Archer Tower | Archer Tower unit | 45 s | 60 metal + 60 timber |

- Defence buildings must be loaded with ammo to fire. Ammo is purchased separately.
- Cannon uses cannon balls; Archer Tower uses arrows.
- 1 ammo consumed per attack tick. No ammo = no contribution in battle.

---

## Building levels

All buildings (except Command Centre) can be levelled up. Production rate doubles per level.

| Level | Rate multiplier |
|---|---|
| 1 | ×1 |
| 2 | ×2 |
| 3 | ×4 |
| 4 | ×8 |

---

## Building states

- **Under construction:** building is placed but `build_complete_at` hasn't passed yet. Not functional.
- **Active:** fully built and working.
- **Destroyed (`is_destroyed = 1`):** non-functional until repaired. Happens when a fort is captured.

---

## Repair cost

Repair cost = **50% of the original build cost** (rounded down per resource). Applies to all destroyed buildings including the Command Centre.

---

## What happens to buildings on fort capture

- When a player captures a fort, **all buildings are destroyed** (`is_destroyed = 1`).
- The new owner starts from scratch — they must rebuild or repair.
- The Command Centre in the captured fort is also destroyed; the new owner must repair it before sending troops.
