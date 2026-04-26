# Units and Buildings

## Unit stats

All units share the same stat schema: `hp`, `damage`, `defense`, `range`, `speed`.

- **speed**: cells per tick. `0.0` = stationary (defence buildings).
- **range**: attack range in cells. Melee = 1.
- **defense**: damage reduction per hit.

| Unit | HP | Damage | Defense | Range | Speed | Notes |
|---|---|---|---|---|---|---|
| Barbarian | 10 | 1 | 0 | 1 | 1.0 | Basic melee; advances every tick |
| Archer | 6 | 2 | 0 | 2 | 0.5 | Ranged; advances every 2 ticks |
| Troll | 20 | 3 | 2 | 1 | 1.0 | Melee brute; high HP and defence |
| Wraith | 8 | 3 | 0 | 3 | 1.0 | Fast glass cannon; long range |
| Longbowman | 6 | 2 | 0 | 3 | 0.5 | Slow long-range infantry; produced by Garrison |
| Hussar | 8 | 3 | 1 | 1 | 2.0 | Fast cavalry; 2 cells per tick; produced by Stable |
| Cannon | 30 | 5 | 3 | 4 | 0.0 | Stationary defence; placed via Cannon building |
| Archer Tower | 20 | 3 | 2 | 3 | 0.0 | Stationary defence; placed via Archer Tower building |

Troll and Wraith are monster-only units that appear in fort and camp garrisons.
Cannon and Archer Tower are stationary and placed as defence buildings; their unit row is spawned from the building during battle setup.

---

## Building types

### Resource buildings
Produce resources lazily (no background timer). All base rate = 0.05/s at level 1.

| Building | Produces | Build time | Build cost |
|---|---|---|---|
| Farm | food | 45 s | 50 food + 30 timber |
| Lumber Mill | timber | 60 s | 50 timber + 30 gold |
| Merchant | gold | 50 s | 80 gold + 20 metal |
| Mine | metal | 55 s | 50 metal + 40 gold |

### Army buildings
Produce troops lazily.

| Building | Produces | Rate | Build time | Build cost |
|---|---|---|---|---|
| Garrison | Longbowman | 1 / 60 s | 60 s | 100 gold + 50 metal |
| Stable | Hussar | 1 / 90 s | 60 s | 120 gold + 60 metal + 20 timber |

### Defence buildings
Spawn a stationary unit into the grid when the location is attacked.

| Building | Unit spawned | Build time | Build cost |
|---|---|---|---|
| Cannon | Cannon | 45 s | 100 metal + 50 gold |
| Archer Tower | Archer Tower | 45 s | 60 metal + 60 timber |

### Special
| Building | Notes |
|---|---|
| Command Centre | Auto-placed in slot 0 of every castle and fort. Build time = 0 (instant). No cost. Cannot be removed. Marks the location as "established". |

---

## Repair cost

Repair cost is half the build cost (rounded down per resource). This applies when a building is destroyed following a fort capture.

---

## Building level multiplier

Production rate doubles per level: `rate × 2^(level-1)`.

| Level | Multiplier |
|---|---|
| 1 | ×1 |
| 2 | ×2 |
| 3 | ×4 |
| 4 | ×8 |
