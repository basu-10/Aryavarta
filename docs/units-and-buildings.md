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
| Goblin Brute | 45 | 5.5 | 3.5 | 1 | 1.0 | Star-2 melee bruiser |
| Harpy | 22 | 7 | 1 | 3 | 1.0 | Star-2 ranged diver |
| Minotaur | 90 | 9.5 | 7 | 1 | 1.0 | Star-3 frontline charger |
| Basilisk | 45 | 12 | 3 | 3 | 0.9 | Star-3 ranged petrifier |
| Gargoyle | 180 | 17 | 13 | 1 | 0.9 | Star-4 armoured melee sentinel |
| Manticore | 90 | 21 | 5.5 | 3 | 0.9 | Star-4 barbed ranged hunter |
| Hydra | 360 | 30 | 24 | 1 | 0.9 | Star-5 high-endurance melee |
| Siren | 170 | 36 | 10 | 3 | 0.8 | Star-5 resonance caster |
| Behemoth | 800 | 52 | 42 | 1 | 0.8 | Star-6 fortress breaker |
| Chimera | 360 | 65 | 18 | 4 | 0.8 | Star-6 long-range hybrid beast |
| Leviathan | 2000 | 120 | 90 | 1 | 0.8 | Star-7 abyssal melee titan |
| Phoenix | 1000 | 170 | 32 | 4 | 0.7 | Star-7 blazing ranged predator |
| Colossus | 12000 | 800 | 600 | 1 | 0.7 | Star-8 runic juggernaut |
| Thunderbird | 7000 | 1100 | 220 | 4 | 0.7 | Star-8 storm artillery flyer |
| Abyssal Titan | 800000 | 30000 | 18000 | 1 | 0.7 | Star-9 void melee executioner |
| Void Drake | 500000 | 42000 | 9000 | 4 | 0.6 | Star-9 rift-breath artillery |
| Demon | 40000000000 | 120000000 | 100000000 | 1 | 1.0 | Star-10 apex melee wall |
| Pegasus | 25000000000 | 200000000 | 0 | 3 | 0.5 | Star-10 apex ranged glass-cannon |
| Longbowman | 6 | 2 | 0 | 3 | 0.5 | Slow long-range infantry; produced by Garrison |
| Hussar | 8 | 3 | 1 | 1 | 2.0 | Fast cavalry; 2 cells per tick; produced by Stable |
| Cannon | 30 | 5 | 3 | 4 | 0.0 | Stationary defence; placed via Cannon building |
| Archer Tower | 20 | 3 | 2 | 3 | 0.0 | Stationary defence; placed via Archer Tower building |

Monster-only units appear in fort and camp garrisons using a star-pair table:

| Star | Monster pair |
|---|---|
| 1 | Troll, Wraith |
| 2 | Goblin Brute, Harpy |
| 3 | Minotaur, Basilisk |
| 4 | Gargoyle, Manticore |
| 5 | Hydra, Siren |
| 6 | Behemoth, Chimera |
| 7 | Leviathan, Phoenix |
| 8 | Colossus, Thunderbird |
| 9 | Abyssal Titan, Void Drake |
| 10 | Demon, Pegasus |

Monster attack-speed progression (level 1):

| Star | Melee attack speed | Ranged attack speed |
|---|---|---|
| 1 | Troll 1.00 | Wraith 1.10 |
| 2 | Goblin Brute 0.95 | Harpy 1.05 |
| 3 | Minotaur 0.90 | Basilisk 1.00 |
| 4 | Gargoyle 0.85 | Manticore 0.95 |
| 5 | Hydra 0.80 | Siren 0.90 |
| 6 | Behemoth 0.78 | Chimera 0.88 |
| 7 | Leviathan 0.75 | Phoenix 0.85 |
| 8 | Colossus 0.72 | Thunderbird 0.82 |
| 9 | Abyssal Titan 0.70 | Void Drake 0.80 |
| 10 | Demon 0.68 | Pegasus 0.78 |

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
