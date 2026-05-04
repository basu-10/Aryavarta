# Resource Rules

## Four resources

food, timber, gold, metal.

Every player starts with: food 200, timber 200, gold 100, metal 100.

---

## Production

Resources are produced by buildings and accumulate passively. There is no background job or timer — the server computes what has accumulated on demand using:

```
accumulated = base_rate × 2^(level-1) × seconds_since_last_collection
```

Base production rates at level 1:

| Building | Resource | Rate (per second) |
|---|---|---|
| Farm | food | 0.05 |
| Lumber Mill | timber | 0.05 |
| Merchant | gold | 0.05 |
| Mine | metal | 0.05 |

Production only accrues from fully built, non-destroyed buildings.

---

## Collecting resources

- Players must manually collect resources by visiting a fort or castle.
- Collection resets `last_collected_at` on the building.
- Uncollected resources keep accumulating indefinitely — there is no cap or overflow.

---

## Spending resources

Resources are spent on:

| Action | Cost |
|---|---|
| Building construction | Varies per building (see buildings-rules.md) |
| Troop training | Deducted immediately when unit is queued |
| Building repair | 50% of original build cost |
| Clan creation | 1000 food + 1000 timber + 1000 gold + 1000 metal |
| Ammo purchase | Varies per ammo type |

Resources are **deducted immediately** on any purchase. There is no "reserving" resources for queued actions — each queue item takes its cost at the moment it is added.

---

## Loot from battles

Winning an attack against a monster fort or camp awards gold + metal to the attacker. Loot is added directly to the attacker's resource balance.

---

## No resource sharing

Resources belong to the player, not the clan. There is no clan bank or resource transfer between players.
