# Data Model

## Schema overview

Twelve tables in `db/schema.sql`:

```
clan ──< player >──── castle
  │         │
  │         ├──── fort >──── building
  │         │               (also castle → building)
  │         ├──── troop
  │         ├──── battle_mission
  │         └──── clan_message
  │
  └──< clan_application >── player
monster_camp (standalone)
dm_message (sender ↔ recipient, optional recruit_clan_id)
training_queue ──< building
building_ammo  ──< building
```

---

## Key design decisions

### Circular FK between `player` and `clan`
`clan.leader_id` references `player.id`, and `player.clan_id` references `clan.id`. SQLite cannot enforce both directions without deferrable constraints (which it doesn't support). The FK from `player.clan_id` to `clan` is declared; the reverse is enforced at the application layer (`disband_clan` clears all member `clan_id`s before deleting the clan row).

### Clan roles stored on `player`
`player.clan_role` holds `'leader' | 'co-leader' | 'elder' | 'member'` (or `NULL` when not in a clan). Storing the role on the player row avoids a separate join table for the common case of "what is this player's clan rank?". Because there is exactly one active role per player at a time, the denormalisation is safe.

### `clan_joined_at` as chat cutoff
`player.clan_joined_at` records the UTC timestamp at which the player joined their current clan. The clan chat query filters by `sent_at >= clan_joined_at`, so players only see messages from after they joined — no pre-join history is exposed. This is reset to `NULL` when they leave.

### `clan_application` table
Pending join requests live in a separate table (`status = 'pending' | 'accepted' | 'rejected'`) rather than a boolean flag on the player. This allows:
- A player to re-apply after rejection (row is updated back to `pending`).
- The application history to be auditable (`resolved_by`, `resolved_at`).
- Multiple clans to have independent pending applications from the same player (enforced by the `UNIQUE(clan_id, player_id)` constraint).

### Recruitment DMs reuse `dm_message`
Instead of a separate `clan_invite` table, recruitment messages set `is_recruit = 1` and store the inviting clan's ID in `recruit_clan_id`. This keeps DM rendering uniform (same inbox) while allowing the recipient to accept/decline inline without a separate page.

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
