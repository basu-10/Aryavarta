"""One-time migration: add clan_role, clan_joined_at, description, clan_application, dm recruit fields."""
import sqlite3

db = sqlite3.connect("battlecells.db")

alters = [
    "ALTER TABLE clan ADD COLUMN description TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE player ADD COLUMN clan_role TEXT",
    "ALTER TABLE player ADD COLUMN clan_joined_at TEXT",
    "ALTER TABLE dm_message ADD COLUMN is_recruit INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE dm_message ADD COLUMN recruit_clan_id INTEGER",
]
for sql in alters:
    try:
        db.execute(sql)
        print("OK:", sql[:70])
    except Exception as e:
        print("SKIP:", e)

db.execute(
    """CREATE TABLE IF NOT EXISTS clan_application (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        clan_id INTEGER NOT NULL REFERENCES clan(id) ON DELETE CASCADE,
        player_id INTEGER NOT NULL REFERENCES player(id) ON DELETE CASCADE,
        status TEXT NOT NULL DEFAULT 'pending',
        applied_at TEXT NOT NULL DEFAULT (datetime('now')),
        resolved_at TEXT,
        resolved_by INTEGER REFERENCES player(id),
        UNIQUE(clan_id, player_id)
    )"""
)
print("clan_application table ready")

db.execute(
    """UPDATE player SET clan_role='leader'
       WHERE clan_id IS NOT NULL
         AND id IN (SELECT leader_id FROM clan)
         AND clan_role IS NULL"""
)
db.execute(
    """UPDATE player SET clan_role='member'
       WHERE clan_id IS NOT NULL
         AND clan_role IS NULL"""
)
db.commit()
print("migrated existing clan members")
db.close()
print("Done.")
