# Fort and Castle Ownership Rules

## Castle vs Fort

| | Castle | Fort |
|---|---|---|
| One per player | Yes | No limit |
| Can be attacked | No | Yes |
| Can be lost | No | Yes |
| Gained by | Registration | Capturing |
| Buildings | Up to slot count (fixed) | Up to slot count (4–10) |
| Command Centre | Always in slot 0 | Always in slot 0 |

---

## Capturing a fort

- To capture a fort, attack it and win the battle.
- On capture, **all buildings are destroyed** — both the old defender's buildings and any monster garrison data are wiped.
- The Command Centre is also set to destroyed state. The new owner must repair it before sending troops from that fort.
- Ownership is transferred immediately after the battle resolves.

---

## Losing a fort

- If another player wins a battle against your fort, you lose it instantly. No warning or delay.
- You lose all buildings in that fort — they are destroyed and belong to the new owner to rebuild.
- Troops stationed at the lost fort are **not** moved back to you; they are gone.

---

## Command Centre state

- A **broken Command Centre** blocks troop dispatch from that location. Nothing else is blocked (building, collecting resources, etc.).
- The Command Centre can be repaired at 50% of its original build cost. Since its build cost is 0, repair is free.
- A player can still be attacked at a fort with a broken Command Centre.

---

## Monster-owned forts

- Monster forts have `owner_id = NULL` and a JSON garrison instead of built buildings.
- Capturing one clears the garrison and transfers ownership. The new owner gets a fresh Command Centre in slot 0; all other slots are empty.
- Monster garrisons don't produce resources and don't have an ammo system.

---

## Fort attack restrictions

- You cannot attack a fort you already own.
- You cannot attack your own castle.
- The Command Centre at the **origin** must not be broken to dispatch troops (you need a working command centre to send troops, not to receive an attack).
- There is no "cooldown" between attacks on the same fort. A fort can be attacked again immediately after a failed attack.

---

## Buildings after capture

The new owner starts with only the Command Centre (destroyed, needs repair). Everything else must be built from scratch. Repair cost for Command Centre = free. Build costs for everything else are standard.
