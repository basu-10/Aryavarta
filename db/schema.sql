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
-- ── Training Queue ───────────────────────────────────────────────────── --
-- One row per troop queued for training.  Ordered by complete_at; the entry
-- with the earliest complete_at is the one currently being trained.
-- Resources are deducted immediately on queuing.
CREATE TABLE IF NOT EXISTS training_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    building_id INTEGER NOT NULL REFERENCES building(id) ON DELETE CASCADE,
    owner_id INTEGER NOT NULL REFERENCES player(id),
    unit_type TEXT NOT NULL,
    queued_at TEXT NOT NULL DEFAULT (datetime('now')),
    complete_at TEXT NOT NULL -- absolute UTC time when training finishes
);
-- ── Building Ammo ────────────────────────────────────────────────────── --
-- Tracks loaded ammo in defence buildings (Cannon / Archer Tower).
-- Ammo is consumed one per tick during battle.
CREATE TABLE IF NOT EXISTS building_ammo (
    building_id INTEGER NOT NULL REFERENCES building(id) ON DELETE CASCADE,
    ammo_type TEXT NOT NULL,
    -- 'cannon_ball' | 'arrow'
    count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (building_id, ammo_type)
);
-- ── Developer Reference Tables ──────────────────────────────────────── --
-- Read-only lookup tables that document every level's costs and stats.
-- Populated by `flask seed-ref`. Not used by live game logic.
CREATE TABLE IF NOT EXISTS ref_building_level (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    building_type TEXT NOT NULL,
    -- 'resource' | 'army' | 'defence' | 'special'
    category TEXT NOT NULL,
    level INTEGER NOT NULL,
    -- Upgrade / build costs at this level
    gold_cost REAL NOT NULL DEFAULT 0,
    food_cost REAL NOT NULL DEFAULT 0,
    timber_cost REAL NOT NULL DEFAULT 0,
    metal_cost REAL NOT NULL DEFAULT 0,
    build_time_seconds INTEGER NOT NULL DEFAULT 0,
    -- Resource buildings only
    production_resource TEXT,
    -- 'food' | 'timber' | 'gold' | 'metal'
    production_rate_per_second REAL,
    -- effective output at this level
    -- Army buildings only
    unit_produced TEXT,
    -- troop type name
    training_interval_seconds INTEGER,
    -- seconds between each produced unit
    training_multiplier REAL,
    -- throughput relative to level 1 (1.0 = base)
    -- Defence buildings only (stats of the unit spawned in battle)
    spawned_unit_hp INTEGER,
    spawned_unit_damage INTEGER,
    spawned_unit_defense INTEGER,
    spawned_unit_range INTEGER,
    notes TEXT,
    UNIQUE(building_type, level)
);
CREATE TABLE IF NOT EXISTS ref_troop_level (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    troop_type TEXT NOT NULL,
    -- 'infantry' | 'ranged' | 'cavalry' | 'monster' | 'siege_defence'
    category TEXT NOT NULL,
    level INTEGER NOT NULL,
    -- Combat stats at this level
    hp INTEGER NOT NULL,
    damage INTEGER NOT NULL,
    defense INTEGER NOT NULL DEFAULT 0,
    range INTEGER NOT NULL,
    speed REAL NOT NULL,
    attack_speed REAL NOT NULL DEFAULT 1.0,
    -- Cost to train one unit at this level
    gold_cost REAL NOT NULL DEFAULT 0,
    food_cost REAL NOT NULL DEFAULT 0,
    timber_cost REAL NOT NULL DEFAULT 0,
    metal_cost REAL NOT NULL DEFAULT 0,
    training_time_seconds INTEGER NOT NULL DEFAULT 0,
    lore TEXT,
    -- flavour text (stored at level 1 only)
    notes TEXT,
    UNIQUE(troop_type, level)
);