# Data Model

## Schema overview

Nine tables in `db/schema.sql`:

```
clan ──< player >──── castle
                │
                ├──── fort >──── building
                │               (also castle → building)
                ├──── troop
                ├──── battle_mission
                └──── clan_message
monster_camp (standalone)
```

---

## Key design decisions

### Circular FK between `player` and `clan`
`clan.leader_id` references `player.id`, and `player.clan_id` references `clan.id`. SQLite cannot enforce both directions without deferrable constraints (which it doesn't support). The FK from `player.clan_id` to `clan` is declared; the reverse is enforced at the application layer (disband_clan clears all member clan_ids before deleting the clan row).

### `fort.owner_id` is nullable
`NULL` means the fort is unowned / occupied by monsters. No separate "unowned fort" concept is needed; the same row represents both states. When a player captures the fort, `owner_id` is set and `monster_data` is cleared.

### `fort.monster_data` is JSON
Monster garrison specs are variable-length lists of `{type, count}` pairs. Normalising them into a separate table would add joins with no benefit; JSON in a TEXT column is simpler and easily readable.

### `building.build_complete_at` is NULL when built instantly
`Command Centre` has a build time of 0 seconds, so its `build_complete_at` is stored as `NULL` rather than a past timestamp. The accumulation logic treats `NULL` as "already complete". This avoids timezone arithmetic edge cases.

### Lazy resource accumulation
Resources are **not** ticked on a timer. Instead, every building records `last_collected_at`. When the player collects (or when the server needs a balance), `_calc_accumulated()` computes:

```
amount = base_rate × 2^(level-1) × elapsed_seconds
```

This means resource totals are always up to date with no background job. The trade-off is that a collect call is O(buildings_at_location), which is acceptable (max ~10 buildings per fort).

### `troop` rows are merged stacks, not individual units
One row per `(owner_id, unit_type, location_type, location_id, state)` combination. Quantities are summed into that stack. This keeps the troop table small regardless of army size.

### `battle_mission` stores formation as JSON
The dispatched formation (`[{unit_type, quantity}]`) is serialised into the mission row at dispatch time. This makes the row self-contained: the battle can be re-run from the row alone, and the original troop records don't need to be kept alive during travel.

### Timestamps are ISO 8601 UTC strings
SQLite has no native timestamp type. Using `TEXT` in ISO 8601 format (`datetime('now')` or Python's `datetime.isoformat`) keeps values human-readable and sortable, and avoids driver-specific type mapping.

---

## Idempotency

| Command | Safe to re-run? | How |
|---|---|---|
| `flask init-db` | Yes | All `CREATE TABLE IF NOT EXISTS` |
| `flask seed-world` | Yes | Checks `COUNT(*)` from `fort` and `monster_camp`; skips if either > 0 |
