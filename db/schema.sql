-- BattleCells World — SQLite Schema
-- Circular FK (player.clan_id ↔ clan.leader_id) is handled at app layer.
-- PRAGMA foreign_keys = ON is set per connection in db/__init__.py.
CREATE TABLE IF NOT EXISTS clan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    leader_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS player (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'player',
    food REAL NOT NULL DEFAULT 200.0,
    timber REAL NOT NULL DEFAULT 200.0,
    gold REAL NOT NULL DEFAULT 100.0,
    metal REAL NOT NULL DEFAULT 100.0,
    clan_id INTEGER REFERENCES clan(id) ON DELETE
    SET NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS castle (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL UNIQUE REFERENCES player(id),
    slot_count INTEGER NOT NULL,
    grid_x INTEGER NOT NULL,
    grid_y INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS fort (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER REFERENCES player(id) ON DELETE
    SET NULL,
        slot_count INTEGER NOT NULL,
        grid_x INTEGER NOT NULL,
        grid_y INTEGER NOT NULL,
        monster_data TEXT,
        -- JSON unit spec when unowned
        star_level INTEGER NOT NULL DEFAULT 1,
        last_defeated_at TEXT
);
CREATE TABLE IF NOT EXISTS building (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    location_type TEXT NOT NULL,
    -- 'castle' or 'fort'
    location_id INTEGER NOT NULL,
    slot_index INTEGER NOT NULL,
    type TEXT NOT NULL,
    level INTEGER NOT NULL DEFAULT 1,
    placed_at TEXT NOT NULL DEFAULT (datetime('now')),
    build_complete_at TEXT,
    -- NULL = already built
    is_destroyed INTEGER NOT NULL DEFAULT 0,
    last_collected_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(location_type, location_id, slot_index)
);
CREATE TABLE IF NOT EXISTS monster_camp (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    grid_x INTEGER NOT NULL,
    grid_y INTEGER NOT NULL,
    unit_data TEXT NOT NULL,
    -- JSON unit spec
    star_level INTEGER NOT NULL DEFAULT 1,
    is_active INTEGER NOT NULL DEFAULT 1,
    spawned_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS troop (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER NOT NULL REFERENCES player(id),
    unit_type TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    location_type TEXT NOT NULL,
    -- 'castle' or 'fort'
    location_id INTEGER NOT NULL,
    state TEXT NOT NULL DEFAULT 'idle' -- 'idle' | 'traveling' | 'in_battle'
);
CREATE TABLE IF NOT EXISTS battle_mission (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attacker_id INTEGER NOT NULL REFERENCES player(id),
    target_type TEXT NOT NULL,
    -- 'fort' | 'monster_camp'
    target_id INTEGER NOT NULL,
    formation TEXT NOT NULL,
    -- JSON [{unit_type, quantity}]
    origin_type TEXT NOT NULL,
    -- 'castle' | 'fort'
    origin_id INTEGER NOT NULL,
    depart_time TEXT NOT NULL,
    arrive_time TEXT NOT NULL,
    resolved INTEGER NOT NULL DEFAULT 0,
    result_battle_id TEXT,
    winner TEXT -- 'attacker' | 'defender' | NULL
);
CREATE TABLE IF NOT EXISTS clan_message (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clan_id INTEGER NOT NULL REFERENCES clan(id),
    sender_id INTEGER NOT NULL REFERENCES player(id),
    message TEXT NOT NULL,
    sent_at TEXT NOT NULL DEFAULT (datetime('now'))
);