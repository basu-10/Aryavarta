# Battle Rules

## Grid setup

- The battle grid is **4 rows × 9 columns** (rows 0–3, columns 0–8).
- Team A (attacker) starts in columns 0–3. Team B (defender) starts in columns 5–8. Column 4 is no-man's-land.
- When a preset/explicit formation is used, unit positions are taken directly from the preset.
- When no preset is used (world-map random dispatch), one unit stack is placed per troop type at a random Team A cell.
- The battle runs up to **500 ticks** (`MAX_TICKS`). If no winner by tick 500, a draw is declared (defender holds).

---

## Troop stacking

Troops are represented as **stacked units** on the grid — one Unit object per formation entry, not one sprite per soldier.

- `hp` and `damage` scale linearly with the stack's `quantity`: a stack of 500 Hussars has `hp = 80 × 500 = 40 000` and `damage = 30 × 500 = 15 000`.
- `defense` does **not** scale with quantity (it is a per-unit stat).
- A stack that survives battle returns to its origin **at its full quantity** (no HP-to-troop conversion).

---

## Dispatch and troop deduction

- Troops are deducted from the origin **immediately at dispatch**, before travel begins.
- There is no "return on failure" — if the attacker loses, those troops are gone.
- Surviving attacker stacks return their full `quantity` to the origin location after a win.

---

## Movement

Movement uses a **fractional accumulator** model:

- Each tick, a moving unit gains `speed` movement credit (capped at 1.0 per tick).
- When credit ≥ 1.0 the unit moves 1 cell forward and the credit is reduced by 1.0.
- Effectively: `speed 1.0` → moves every tick; `speed 0.5` → moves every 2 ticks.
- The accumulator is capped at 1.0 to prevent burst movement after blocked ticks. Units with `speed > 1.0` still move once per tick (not multiple cells).
- Melee units (range 1) advance until adjacent to an enemy. Ranged units (range > 1) stop when a target is within attack range.
- **Ranged kiting:** if an enemy is in the same row, directly ahead, and closer than the unit's range, the ranged unit retreats one cell instead of attacking. If blocked from retreating, it attacks instead.
- Stationary units (Cannon, Archer Tower, `speed = 0`) never move.

---

## Targeting rules

Troops may only attack enemies **ahead of them** — columns to the right for Team A, columns to the left for Team B. Sideways (same column) and backward targets are never valid.

An enemy is in range if:
1. Its **Chebyshev distance** (max of column-diff and row-diff) ≤ the unit's `range`.
2. Its column is **strictly ahead** in the unit's forward direction.

| Priority | Target selection within range |
|---|---|
| 1 | Same row as attacker (direct front) — closest first |
| 2 | Any other in-range enemy — closest first |

Ties at equal distance are broken alphabetically by unit ID.

---

## Damage formula

All attacks in a tick fire **simultaneously**; damage is accumulated and applied all at once.

```
effective_damage = max(0, attacker.damage − target.defense)
```

- Minimum effective damage is **0** (a high-defense unit can negate a hit entirely).
- A stack's `damage` already incorporates its `quantity`, so a 500-Hussar stack deals `30 × 500 − target.defense` per tick.

---

## Death

A unit (stack) dies when its HP reaches 0 or below. It is removed from the grid immediately at the end of the tick. No revival mechanic exists.

---

## Battle outcomes

| Result | What happens |
|---|---|
| Attacker wins vs monster fort | Fort ownership transferred to attacker; loot added |
| Attacker wins vs player fort | Fort ownership transferred; all defender buildings destroyed |
| Attacker wins vs monster camp | Camp deactivated; gold + metal loot added to attacker; monsters added to attacker's Command Centre |
| Defender wins | Nothing changes; attacker troops already gone |

---

## Garrison updates after defence

If a player-owned fort successfully defends, dead defending stacks are removed from the garrison so the recorded count matches actual survivors.

---

## Defense buildings in battle

- Cannon and Archer Tower buildings each spawn one stationary Unit into the battle grid when their fort is attacked.
- Each fires once per tick if a valid target is in range.
- Each attack tick consumes 1 ammo unit. No ammo = no fire.
- Remaining ammo is persisted back to the building after the battle resolves.

---

## Monster fort garrison (star levels)

Monster-occupied forts are seeded with Troll/Wraith units (stars 1–6) or Demon/Pegasus units (stars 7–10).

| Star | Unit count | Types |
|---|---|---|
| 1 | 2–3 | Troll, Wraith |
| 2 | 4–5 | Troll, Wraith |
| 3 | 6–8 | Troll, Wraith |
| 4 | 9–11 | Troll, Wraith |
| 5 | 12–14 | Troll, Wraith |
| 6 | 15–16 | Troll, Wraith |
| 7 | 2–3 | Demon, Pegasus |
| 8 | 4–5 | Demon, Pegasus |
| 9 | 6–8 | Demon, Pegasus |
| 10 | 9–11 | Demon, Pegasus |

Monster defenders are placed as individual unstacked units (one per grid cell, `quantity = 1`).

---

## Unit base stats (level 1)

| Unit | HP | Damage | Defense | Range | Speed |
|---|---|---|---|---|---|
| Barbarian | 100 | 10 | 0 | 1 | 1.0 |
| Archer | 60 | 20 | 0 | 2 | 0.5 |
| Longbowman | 60 | 20 | 0 | 3 | 0.5 |
| Hussar | 80 | 30 | 10 | 1 | 1.0* |
| Troll | 200 | 30 | 20 | 1 | 1.0 |
| Wraith | 80 | 30 | 0 | 3 | 1.0 |
| Cannon | 300 | 50 | 30 | 4 | 0 (stationary) |
| Archer Tower | 200 | 30 | 20 | 3 | 0 (stationary) |

\* Hussar `speed` is defined as 2.0 in config but due to the movement accumulator cap at 1.0, the effective movement rate is 1 cell/tick — same as `speed 1.0`.
