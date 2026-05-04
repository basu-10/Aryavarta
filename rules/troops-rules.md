# Troop Rules

## Unit types overview

| Unit | Type | Origin |
|---|---|---|
| Barbarian | Human melee | Captured from monster camps |
| Archer | Human ranged | Captured from monster camps |
| Longbowman | Human ranged | Trained in Garrison |
| Hussar | Human melee | Trained in Stable |
| Troll | Monster melee | Monster forts and camps only |
| Wraith | Monster ranged | Monster forts and camps only |
| Goblin Brute | Monster melee | Monster forts and camps only |
| Harpy | Monster ranged | Monster forts and camps only |
| Minotaur | Monster melee | Monster forts and camps only |
| Basilisk | Monster ranged | Monster forts and camps only |
| Gargoyle | Monster melee | Monster forts and camps only |
| Manticore | Monster ranged | Monster forts and camps only |
| Hydra | Monster melee | Monster forts and camps only |
| Siren | Monster ranged | Monster forts and camps only |
| Behemoth | Monster melee | Monster forts and camps only |
| Chimera | Monster ranged | Monster forts and camps only |
| Leviathan | Monster melee | Monster forts and camps only |
| Phoenix | Monster ranged | Monster forts and camps only |
| Colossus | Monster melee | Monster forts and camps only |
| Thunderbird | Monster ranged | Monster forts and camps only |
| Abyssal Titan | Monster melee | Monster forts and camps only |
| Void Drake | Monster ranged | Monster forts and camps only |
| Demon | Monster melee | Monster forts and camps only |
| Pegasus | Monster ranged | Monster forts and camps only |

---

## Unit stats

| Unit | HP | Damage | Defense | Range | Speed |
|---|---|---|---|---|---|
| Barbarian | 10 | 1 | 0 | 1 | 1.0 |
| Archer | 6 | 2 | 0 | 2 | 0.5 |
| Longbowman | 6 | 2 | 0 | 3 | 0.5 |
| Hussar | 8 | 3 | 1 | 1 | 2.0 |
| Troll | 20 | 3 | 2 | 1 | 1.0 |
| Wraith | 8 | 3 | 0 | 3 | 1.0 |
| Goblin Brute | 45 | 5.5 | 3.5 | 1 | 1.0 |
| Harpy | 22 | 7 | 1 | 3 | 1.0 |
| Minotaur | 90 | 9.5 | 7 | 1 | 1.0 |
| Basilisk | 45 | 12 | 3 | 3 | 0.9 |
| Gargoyle | 180 | 17 | 13 | 1 | 0.9 |
| Manticore | 90 | 21 | 5.5 | 3 | 0.9 |
| Hydra | 360 | 30 | 24 | 1 | 0.9 |
| Siren | 170 | 36 | 10 | 3 | 0.8 |
| Behemoth | 800 | 52 | 42 | 1 | 0.8 |
| Chimera | 360 | 65 | 18 | 4 | 0.8 |
| Leviathan | 2000 | 120 | 90 | 1 | 0.8 |
| Phoenix | 1000 | 170 | 32 | 4 | 0.7 |
| Colossus | 12000 | 800 | 600 | 1 | 0.7 |
| Thunderbird | 7000 | 1100 | 220 | 4 | 0.7 |
| Abyssal Titan | 800000 | 30000 | 18000 | 1 | 0.7 |
| Void Drake | 500000 | 42000 | 9000 | 4 | 0.6 |
| Demon | 40000000000 | 120000000 | 100000000 | 1 | 1.0 |
| Pegasus | 25000000000 | 200000000 | 0 | 3 | 0.5 |
| Cannon | 30 | 5 | 3 | 4 | 0.0 |
| Archer Tower | 20 | 3 | 2 | 3 | 0.0 |

- **Speed** is cells per tick. `0.0` = stationary (defence buildings only).
- **Range** is in cells. Range 1 = melee.
- **Defense** reduces incoming damage per hit.

---

## Human troops (trainable)

- Longbowman and Hussar are the only troops players can actively train.
- Barbarian and Archer are obtainable only by winning battles against monster camps or forts.
- Human troops can be trained at castles and at any player-owned fort with the appropriate building.

### Training rules

- One unit trains at a time per building. Multiple units can be queued.
- Resources are deducted **immediately** when a unit is added to the queue.
- Completed units deploy instantly to the same location as idle troops.
- Training times: Longbowman = 60 s/unit, Hussar = 90 s/unit.

### Dismissal

- Any troops can be dismissed at any time. This is instant.
- Refund on dismissal is **50%** of the troop's training cost (no refund for captured monster troops).

---

## Monster troops (captured)

- Monster units cannot be trained. They are captured from monster camps and monster forts.
- Captured monsters join the player's army at the origin fort/castle after a battle win.
- Monster troops appear in all wild garrison defences (mixed randomly within the star-level unit count band).

### Monster pair per star level

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

### Monster attack-speed scaling (level 1)

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

---

## Troop storage

- Troops are stored as stacks, not individual units. One row per `(owner, unit_type, location, state)`.
- There is no per-unit identity — a stack of 50 Hussars is one database row.
- Troops can be stationed at a castle or at any player-owned fort.

---

## Defence buildings (stationary units)

- Cannon and Archer Tower are not troops — they are buildings that spawn a stationary unit into the battle grid.
- They do not move. They can only fire if loaded with ammo.
- Ammo (cannon balls / arrows) must be purchased separately and loaded onto the building before battle.
- 1 ammo is consumed per attack tick. A building with 0 ammo does not fire.
