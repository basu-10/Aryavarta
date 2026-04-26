"""
run_admin_test_harness.py - CLI wrapper for admin battle test harness.

This intentionally allows local scripted test runs without web login/password.
All results are written as normal mission/battle records for the selected admin.
"""

from __future__ import annotations

import argparse
import sys

from app import create_app
from db import models as m
from utils.admin_test_harness import list_available_presets, run_admin_formation_tests


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run admin-only formation test harness.")
    parser.add_argument("--admin", default="admin", help="Admin username (default: admin)")
    parser.add_argument(
        "--preset",
        action="append",
        default=[],
        help="Preset name to include; repeat flag for multiple presets. Defaults to all presets.",
    )
    parser.add_argument("--star-level", type=int, default=1, help="Target star level filter (1-6)")
    parser.add_argument(
        "--target-type",
        action="append",
        default=[],
        choices=["monster_camp", "monster_fort", "npc_fort"],
        help=(
            "Target categories to include; repeat flag for multiple types. "
            "Defaults to all types."
        ),
    )
    parser.add_argument(
        "--max-targets",
        type=int,
        default=1,
        help="Optional cap on targets per run (default: 1 for quick smoke tests).",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    app = create_app()
    with app.app_context():
        player = m.get_player_by_username(args.admin)
        if not player:
            print(f"ERROR: admin user '{args.admin}' not found.")
            sys.exit(1)
        if player.get("role") != "admin":
            print(f"ERROR: user '{args.admin}' is not an admin.")
            sys.exit(1)

        presets = args.preset or list_available_presets()
        target_types = set(args.target_type or ["monster_camp", "monster_fort", "npc_fort"])

        summary = run_admin_formation_tests(
            admin_player_id=player["id"],
            preset_names=presets,
            star_level=args.star_level,
            target_types=target_types,
            max_targets=args.max_targets,
        )

        print("Admin test harness run complete")
        print(f"- admin: {player['username']} (id={player['id']})")
        print(f"- star_level: {summary['star_level']}")
        print(f"- target_types: {', '.join(summary['selected_target_types'])}")
        print(f"- resolved_battles: {summary['resolved_battles']}")
        if summary.get("runs"):
            print("- sample results:")
            for run in summary["runs"][:5]:
                print(
                    f"  * {run['preset_name']} vs {run['target_label']} -> "
                    f"{run['winner']} (battle_id={run['battle_id']})"
                )

        failures = summary.get("failures", [])
        if failures:
            print("- failures:")
            for msg in failures[:10]:
                print(f"  * {msg}")

        # Non-zero exit when nothing resolved helps automation detect no-op/failure runs.
        if summary["resolved_battles"] <= 0:
            sys.exit(2)


if __name__ == "__main__":
    main()
