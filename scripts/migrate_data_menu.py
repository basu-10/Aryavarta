"""
Menu-driven SQLite data export/import helper for BattleCells.

Primary use case:
- Export only player login data before a destructive migration.
- Re-import that data into a refreshed database after git pull / init-db.

Usage:
    python migrate_data_menu.py
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_DB_PATH = PROJECT_ROOT / "battlecells.db"
DEFAULT_EXPORT_DIR = PROJECT_ROOT / "output"

FILE_SCHEMA_VERSION = 1

TABLE_GROUPS: dict[str, list[str]] = {
    "1": ["player"],
    "2": ["player", "auth_remember_token"],
    "3": ["player", "castle", "building", "troop", "training_queue", "building_ammo"],
    "4": [
        "player",
        "clan",
        "clan_application",
        "clan_message",
        "world_message",
        "dm_message",
        "friendship",
    ],
    "5": [
        "player",
        "auth_remember_token",
        "castle",
        "building",
        "troop",
        "training_queue",
        "building_ammo",
        "clan",
        "clan_application",
        "clan_message",
        "world_message",
        "dm_message",
        "friendship",
        "battle_mission",
    ],
}

GROUP_LABELS: dict[str, str] = {
    "1": "Players only (recommended for login continuity)",
    "2": "Players + remember-me tokens",
    "3": "Players + castle/buildings/troops/training",
    "4": "Players + social/clan/messages/friends",
    "5": "Broad player-linked snapshot (advanced)",
}


@dataclass
class TablePayload:
    columns: list[str]
    rows: list[dict[str, Any]]


class MigrationError(Exception):
    pass


def prompt(msg: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default is not None else ""
    value = input(f"{msg}{suffix}: ").strip()
    if not value and default is not None:
        return default
    return value


def choose_db_path() -> Path:
    value = prompt("SQLite DB path", str(DEFAULT_DB_PATH))
    return Path(value).expanduser().resolve()


def connect_db(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise MigrationError(f"Database not found: {db_path}")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_existing_tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {row["name"] for row in rows}


def pick_tables(existing_tables: set[str]) -> list[str]:
    print("\nTable selection:")
    for key in sorted(TABLE_GROUPS):
        print(f"  {key}) {GROUP_LABELS[key]}")
    print("  6) Custom table list")

    while True:
        choice = prompt("Choose a table group", "1")
        if choice in TABLE_GROUPS:
            tables = [t for t in TABLE_GROUPS[choice] if t in existing_tables]
            missing = [t for t in TABLE_GROUPS[choice] if t not in existing_tables]
            if missing:
                print(f"Warning: missing tables in this DB (will skip): {', '.join(missing)}")
            if not tables:
                print("Selected group contains no existing tables. Choose another option.")
                continue
            return tables

        if choice == "6":
            print("Enter comma-separated table names, e.g. player,castle,troop")
            raw = prompt("Tables")
            requested = [t.strip() for t in raw.split(",") if t.strip()]
            valid = [t for t in requested if t in existing_tables]
            missing = [t for t in requested if t not in existing_tables]
            if missing:
                print(f"Warning: unknown tables skipped: {', '.join(missing)}")
            if not valid:
                print("No valid tables selected.")
                continue
            return valid

        print("Invalid choice. Try again.")


def fetch_table_payload(conn: sqlite3.Connection, table: str) -> TablePayload:
    columns = [row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    rows = [dict(row) for row in conn.execute(f"SELECT * FROM {table}").fetchall()]
    return TablePayload(columns=columns, rows=rows)


def export_tables(db_path: Path) -> None:
    conn = connect_db(db_path)
    try:
        existing = get_existing_tables(conn)
        tables = pick_tables(existing)

        payload = {
            "schema_version": FILE_SCHEMA_VERSION,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_db": str(db_path),
            "tables": {},
        }

        for table in tables:
            tp = fetch_table_payload(conn, table)
            payload["tables"][table] = {
                "columns": tp.columns,
                "rows": tp.rows,
            }
            print(f"Exported {table}: {len(tp.rows)} rows")

        DEFAULT_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        default_file = DEFAULT_EXPORT_DIR / f"migration_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        out_path = Path(prompt("Output JSON file", str(default_file))).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
        print(f"\nExport complete: {out_path}")
    finally:
        conn.close()


def _table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def _single_pk(conn: sqlite3.Connection, table: str) -> str | None:
    pk_cols = [row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall() if row["pk"]]
    return pk_cols[0] if len(pk_cols) == 1 else None


def _conflict_target_for_table(conn: sqlite3.Connection, table: str, file_columns: list[str]) -> str | None:
    pk = _single_pk(conn, table)
    if pk and pk in file_columns:
        return pk

    return None


def _upsert_row(
    conn: sqlite3.Connection,
    table: str,
    row: dict[str, Any],
    allowed_cols: list[str],
    conflict_target: str | None,
    overwrite: bool,
) -> None:
    insert_cols = [c for c in row.keys() if c in allowed_cols]
    if not insert_cols:
        return

    placeholders = ", ".join("?" for _ in insert_cols)
    col_sql = ", ".join(insert_cols)
    values = [row[c] for c in insert_cols]

    if overwrite:
        if conflict_target is None:
            sql = f"INSERT OR REPLACE INTO {table} ({col_sql}) VALUES ({placeholders})"
            conn.execute(sql, values)
            return

        update_cols = [c for c in insert_cols if c != conflict_target]
        if update_cols:
            update_sql = ", ".join(f"{c}=excluded.{c}" for c in update_cols)
            sql = (
                f"INSERT INTO {table} ({col_sql}) VALUES ({placeholders}) "
                f"ON CONFLICT({conflict_target}) DO UPDATE SET {update_sql}"
            )
        else:
            sql = (
                f"INSERT INTO {table} ({col_sql}) VALUES ({placeholders}) "
                f"ON CONFLICT({conflict_target}) DO NOTHING"
            )
        conn.execute(sql, values)
        return

    if conflict_target is None:
        sql = f"INSERT OR IGNORE INTO {table} ({col_sql}) VALUES ({placeholders})"
    else:
        sql = (
            f"INSERT INTO {table} ({col_sql}) VALUES ({placeholders}) "
            f"ON CONFLICT({conflict_target}) DO NOTHING"
        )
    conn.execute(sql, values)


def _sync_autoincrement(conn: sqlite3.Connection, table: str) -> None:
    cols = _table_columns(conn, table)
    if "id" not in cols:
        return

    row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'").fetchone()
    if not row:
        return

    max_id = conn.execute(f"SELECT COALESCE(MAX(id), 0) AS max_id FROM {table}").fetchone()["max_id"]
    seq_exists = conn.execute("SELECT 1 FROM sqlite_sequence WHERE name=?", (table,)).fetchone()
    if seq_exists:
        conn.execute("UPDATE sqlite_sequence SET seq=? WHERE name=?", (max_id, table))
    else:
        conn.execute("INSERT INTO sqlite_sequence(name, seq) VALUES (?, ?)", (table, max_id))


def _load_export_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise MigrationError(f"Export file not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != FILE_SCHEMA_VERSION:
        raise MigrationError(
            f"Unsupported schema_version={data.get('schema_version')}; expected {FILE_SCHEMA_VERSION}"
        )
    if not isinstance(data.get("tables"), dict):
        raise MigrationError("Invalid export file: missing tables object")

    return data


def _choose_overwrite_mode() -> bool:
    print("\nConflict behavior:")
    print("  1) Keep existing rows (insert only new rows)")
    print("  2) Overwrite existing rows from file")
    while True:
        choice = prompt("Choose conflict mode", "1")
        if choice == "1":
            return False
        if choice == "2":
            return True
        print("Invalid choice. Try again.")


def _import_in_order(table_payload: dict[str, dict[str, Any]]) -> list[str]:
    preferred = [
        "world",
        "clan",
        "player",
        "castle",
        "fort",
        "building",
        "building_ammo",
        "troop",
        "training_queue",
        "monster_camp",
        "battle_mission",
        "clan_application",
        "friendship",
        "clan_message",
        "world_message",
        "dm_message",
        "auth_remember_token",
        "ref_building_level",
        "ref_troop_level",
        "map_decoration",
    ]
    available = set(table_payload.keys())
    ordered = [t for t in preferred if t in available]
    ordered.extend(sorted(available - set(ordered)))
    return ordered


def import_tables(db_path: Path) -> None:
    file_path = Path(prompt("Path to export JSON file")).expanduser().resolve()
    data = _load_export_file(file_path)
    overwrite = _choose_overwrite_mode()

    conn = connect_db(db_path)
    try:
        existing_tables = get_existing_tables(conn)
        file_tables: dict[str, dict[str, Any]] = data["tables"]
        ordered_tables = _import_in_order(file_tables)

        print("\nImport summary:")
        for table in ordered_tables:
            row_count = len(file_tables[table].get("rows", []))
            status = "ready" if table in existing_tables else "missing in target DB"
            print(f"  - {table}: {row_count} rows ({status})")

        proceed = prompt("Proceed with import? (y/n)", "n").lower()
        if proceed != "y":
            print("Import cancelled.")
            return

        conn.execute("PRAGMA foreign_keys = OFF")
        imported = 0
        skipped_missing = 0

        for table in ordered_tables:
            if table not in existing_tables:
                skipped_missing += 1
                continue

            payload = file_tables[table]
            rows = payload.get("rows", [])
            if not isinstance(rows, list):
                raise MigrationError(f"Invalid rows payload for table '{table}'")

            table_cols = _table_columns(conn, table)
            conflict_target = _conflict_target_for_table(conn, table, payload.get("columns", []))

            before_changes = conn.total_changes
            for row in rows:
                if not isinstance(row, dict):
                    raise MigrationError(f"Invalid row payload in table '{table}'")
                _upsert_row(conn, table, row, table_cols, conflict_target, overwrite)
            table_changes = conn.total_changes - before_changes

            _sync_autoincrement(conn, table)
            imported += 1
            print(f"Imported {table}: attempted {len(rows)} rows, changed {table_changes} rows")

        conn.commit()

        conn.execute("PRAGMA foreign_keys = ON")
        fk_issues = conn.execute("PRAGMA foreign_key_check").fetchall()
        if fk_issues:
            print("\nWarning: foreign key integrity issues detected after import:")
            for issue in fk_issues[:20]:
                print(f"  {tuple(issue)}")
            if len(fk_issues) > 20:
                print(f"  ... plus {len(fk_issues) - 20} more")
        else:
            print("\nForeign key check passed.")

        print(
            f"\nImport complete. Processed {imported} tables. "
            f"Skipped {skipped_missing} tables missing in target DB."
        )
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def print_logic_notes() -> None:
    print("\nMigration logic notes:")
    print("- Exporting only 'player' is safe for preserving username/password login.")
    print("- If table schemas diverge (columns renamed/removed), import may partially skip data.")
    print("- Existing signed Flask sessions are not preserved across secret key changes/restarts.")
    print("- For strict parity of remember-me cookies, include 'auth_remember_token'.")


def main() -> None:
    print("BattleCells Menu Migration Helper")
    print("=" * 32)
    print_logic_notes()

    db_path = choose_db_path()

    while True:
        print("\nMain menu:")
        print("  1) Export tables to JSON")
        print("  2) Import tables from JSON")
        print("  3) Exit")

        choice = prompt("Choose an option", "1")
        try:
            if choice == "1":
                export_tables(db_path)
            elif choice == "2":
                import_tables(db_path)
            elif choice == "3":
                print("Done.")
                return
            else:
                print("Invalid choice. Try again.")
        except MigrationError as e:
            print(f"Error: {e}")
        except sqlite3.DatabaseError as e:
            print(f"SQLite error: {e}")


if __name__ == "__main__":
    main()
