"""
create_admin.py — One-time script to create or reset an admin account.

Usage:
    python create_admin.py
    python create_admin.py --username myadmin --password mysecretpass

The script must be run from the project root so Flask can locate the database.
It never touches any existing game data.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# ── Bootstrap Flask app context so db helpers work ──────────────────────
sys.path.insert(0, str(Path(__file__).parent))

from app import create_app
from werkzeug.security import generate_password_hash
from db import models as m, get_db


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or reset a BattleCells admin account.")
    parser.add_argument("--username", default="admin",  help="Admin username (default: admin)")
    parser.add_argument("--password", default="admin123", help="Admin password (default: admin123)")
    args = parser.parse_args()

    username = args.username.strip()
    password = args.password.strip()

    if not username or not password:
        print("ERROR: username and password cannot be empty.")
        sys.exit(1)

    app = create_app()
    with app.app_context():
        existing = m.get_player_by_username(username)

        if existing:
            # Update password hash and force role to admin
            db = get_db()
            db.execute(
                "UPDATE player SET password_hash=?, role='admin' WHERE id=?",
                (generate_password_hash(password), existing["id"]),
            )
            db.commit()
            print(f"[✓] Admin account updated — username: '{username}'  (id {existing['id']})")
        else:
            pw_hash   = generate_password_hash(password)
            player_id = m.create_player(username, pw_hash)
            m.set_player_role(player_id, "admin")
            print(f"[✓] Admin account created — username: '{username}'  password: '{password}'  (id {player_id})")
            print("    NOTE: Admin accounts do not need a castle. They can still be granted one")
            print("    via the admin dashboard if desired.")

        print()
        print(f"    Login at:  http://127.0.0.1:5000/login")
        print(f"    Dashboard: http://127.0.0.1:5000/admin/")


if __name__ == "__main__":
    main()
