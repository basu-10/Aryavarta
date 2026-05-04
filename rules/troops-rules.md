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

- Troll, Wraith, Demon, and Pegasus cannot be trained. They are captured from monster camps and forts.
- Captured monsters join the player's army at the origin fort/castle after a battle win.
- Monster troops appear in all wild garrison defences (mixed randomly within the star-level unit count band).

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
