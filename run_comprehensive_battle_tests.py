"""
run_comprehensive_battle_tests.py
===================================
Finds the minimum number of stacked Barbarians and Archers needed to beat
every star level (1-6) in monster_camp and monster_fort categories.

How it works
------------
* Three formation types are tested:
    - barb_only  : 16 cells (4 rows × 4 cols) of Barbarians, qty N each
    - archer_only: 16 cells of Archers, qty N each
    - mixed      : rows 0-1 (8 cells) Barbarians + rows 2-3 (8 cells) Archers, qty N each

* A geometric quantity ladder is used:
    1, 3, 5, 10, 25, 50, 100, 250, 500, 1 000, 5 000, 10 000,
    50 000, 100 000, 1 000 000, 10 000 000
  For each step, BATTLES_PER_QTY battles are run against targets at that star
  level.  The search stops at the first quantity where
  WIN_THRESHOLD_FRACTION of the battles are won.

* Results are printed as an ASCII table so they can be read in the terminal or
  piped to a file.

Usage
-----
    python run_comprehensive_battle_tests.py
    python run_comprehensive_battle_tests.py --admin admin --battles-per-qty 3 --target-type monster_camp

Flags
-----
--admin             Admin username (default: admin)
--target-type       monster_camp | monster_fort | both  (default: both)
--battles-per-qty   Battles run per (formation, quantity, star-level) triple (default: 3)
--win-threshold     Fraction of battles that must be won to declare the qty "sufficient" (default: 0.67)
--no-cleanup        Keep generated preset JSON files after the run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))

from app import create_app  # noqa: E402
from db import models as m  # noqa: E402
from utils.admin_test_harness import run_admin_formation_tests  # noqa: E402

PRESETS_DIR = _ROOT / "presets"

# Grid constants (mirror config values to avoid importing config at module level)
_GRID_ROWS   = 4
_TEAM_A_COLS = [0, 1, 2, 3]

# All 16 attacker positions
_ALL_POSITIONS = [(r, c) for r in range(_GRID_ROWS) for c in _TEAM_A_COLS]
_BARB_CELLS   = [(r, c) for r in range(_GRID_ROWS) for c in _TEAM_A_COLS]          # all 16
_ARCHER_CELLS = [(r, c) for r in range(_GRID_ROWS) for c in _TEAM_A_COLS]          # all 16
_MIXED_BARB   = [(r, c) for r in [0, 1] for c in _TEAM_A_COLS]                     # 8 cells
_MIXED_ARCH   = [(r, c) for r in [2, 3] for c in _TEAM_A_COLS]                     # 8 cells

# Quantity search ladder (geometric, roughly ×3 each step)
# Extended into the billions range for Tier-10 Demon/Pegasus encounters
_QTY_LADDER = [
    1, 3, 5, 10, 25, 50, 100, 250, 500,
    1_000, 5_000, 10_000, 50_000, 100_000,
    1_000_000, 10_000_000, 50_000_000, 100_000_000,
    500_000_000, 1_000_000_000, 2_000_000_000,
]

STAR_RANGE = range(1, 11)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FormationSpec(NamedTuple):
    key: str          # short identifier used in preset name and table headers
    label: str        # human-readable label
    cells: list[tuple[str, int, int]]  # [(unit_type, row, col), ...]


_FORMATIONS = [
    FormationSpec(
        key="barb",
        label="Barb-only (16 cells)",
        cells=[("Barbarian", r, c) for r, c in _BARB_CELLS],
    ),
    FormationSpec(
        key="arch",
        label="Archer-only (16 cells)",
        cells=[("Archer", r, c) for r, c in _ARCHER_CELLS],
    ),
    FormationSpec(
        key="mixed",
        label="Mixed 8B+8A",
        cells=(
            [("Barbarian", r, c) for r, c in _MIXED_BARB]
            + [("Archer", r, c) for r, c in _MIXED_ARCH]
        ),
    ),
]


def _preset_name(form_key: str, qty: int) -> str:
    return f"comp_{form_key}_q{qty}"


def _create_preset(form: FormationSpec, qty: int) -> str:
    """Write a preset JSON file and return its stem name."""
    army_a = [
        {"type": utype, "row": row, "col": col, "quantity": qty}
        for utype, row, col in form.cells
    ]
    data = {"name": _preset_name(form.key, qty), "army_a": army_a}
    PRESETS_DIR.mkdir(exist_ok=True)
    path = PRESETS_DIR / f"{_preset_name(form.key, qty)}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path.stem


def _delete_preset(form_key: str, qty: int) -> None:
    path = PRESETS_DIR / f"{_preset_name(form_key, qty)}.json"
    path.unlink(missing_ok=True)


def _fmt_qty(n: int | None) -> str:
    if n is None:
        return "NEVER"
    if n >= 1_000_000:
        return f"{n // 1_000_000}M"
    if n >= 1_000:
        return f"{n // 1_000}k"
    return str(n)


def _ensure_seeded_all_stars(targets_per_star: int = 2, verbose: bool = False) -> None:
    """
    Guarantee at least `targets_per_star` monster camps at every star level 1-6.
    Creates camps directly when the random seeder hasn't populated a level.
    """
    from db import models as m2
    from db.world_seeder import _random_monster_spec  # type: ignore[attr-defined]

    for star in range(1, 11):
        # Count how many active camps exist at this star level
        from db import get_db
        existing = get_db().execute(
            "SELECT COUNT(*) FROM monster_camp WHERE is_active=1 AND star_level=?",
            (star,),
        ).fetchone()[0]
        needed = max(0, targets_per_star - existing)
        for _ in range(needed):
            unit_data = _random_monster_spec(star)
            x, y = m2.find_empty_cell()
            m2.create_monster_camp(x, y, unit_data, star)
        if needed:
            if verbose:
                print(f"  [seed] Created {needed} monster_camp(s) at star {star}")

    # Also ensure monster forts exist for each star level
    for star in range(1, 11):
        from db import get_db
        import config
        existing = get_db().execute(
            "SELECT COUNT(*) FROM fort WHERE owner_id IS NULL AND star_level=?",
            (star,),
        ).fetchone()[0]
        needed = max(0, targets_per_star - existing)
        for _ in range(needed):
            from db.world_seeder import _random_monster_spec  # noqa: F811
            import random
            monster_data = _random_monster_spec(star)
            slot_count = random.choices(
                [4, 5, 6, 7, 8, 9, 10],
                weights=config.FORT_SLOT_WEIGHTS,
            )[0]
            x, y = m2.find_empty_cell()
            m2.create_fort(slot_count, x, y, monster_data, star)
        if needed:
            if verbose:
                print(f"  [seed] Created {needed} monster_fort(s) at star {star}")


# ---------------------------------------------------------------------------
# Core search
# ---------------------------------------------------------------------------

def _search_min_qty(
    admin_id: int,
    form: FormationSpec,
    star: int,
    target_types: set[str],
    battles_per_qty: int,
    win_threshold: float,
    cleanup: bool,
) -> tuple[int | None, dict]:
    """
    Walk the quantity ladder and return the first qty where win rate >=
    win_threshold.  Returns (qty_or_None, detail_dict).
    """
    detail: dict[int, dict] = {}

    for qty in _QTY_LADDER:
        # Re-seed targets before each quantity attempt so won/deactivated
        # camps from a previous run don't starve this test.
        _ensure_seeded_all_stars(targets_per_star=battles_per_qty + 1, verbose=False)

        preset_name = _create_preset(form, qty)

        summary = run_admin_formation_tests(
            admin_player_id=admin_id,
            preset_names=[preset_name],
            star_level=star,
            target_types=target_types,
            max_targets=battles_per_qty,
        )

        wins   = sum(1 for r in summary["runs"] if r["winner"] == "attacker")
        total  = summary["resolved_battles"]
        losses = total - wins
        no_target = total == 0

        detail[qty] = {
            "wins": wins,
            "total": total,
            "rate": wins / total if total > 0 else 0.0,
            "no_target": no_target,
        }

        if cleanup:
            _delete_preset(form.key, qty)

        if no_target:
            # No targets available for this star level; skip entire star
            return None, detail

        win_rate = wins / total if total > 0 else 0.0
        if win_rate >= win_threshold:
            return qty, detail

    return None, detail   # never reached win threshold within ladder


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

def _render_table(
    results: dict,   # {star: {form_key: (min_qty, detail)}}
    form_labels: list[tuple[str, str]],   # [(key, label), ...]
    target_types: set[str],
) -> None:
    col_w = 22
    header_parts = [f"{'Star':^5}", f"{'# Monsters':^12}"]
    for _, label in form_labels:
        header_parts.append(f"{label:^{col_w}}")
    header = " | ".join(header_parts)
    sep = "-" * len(header)

    monster_range = {
        1: "2-3",  2: "4-5",  3: "6-8",  4: "9-11",  5: "12-14",
        6: "15-16", 7: "2-3",  8: "4-5",  9: "6-8",   10: "9-11",
    }

    print()
    print("=" * len(header))
    print(f"  Minimum troops per cell to achieve ≥67% win rate")
    print(f"  Target types: {', '.join(sorted(target_types))}")
    print("=" * len(header))
    print(header)
    print(sep)

    for star in STAR_RANGE:
        row_parts = [f"{star:^5}", f"{monster_range.get(star, '?'):^12}"]
        for fkey, _ in form_labels:
            min_qty, detail = results.get(star, {}).get(fkey, (None, {}))
            if min_qty is None:
                # Check if no target existed or just never won
                has_no_target = any(v.get("no_target") for v in detail.values())
                cell = "no targets" if has_no_target else f">{_fmt_qty(_QTY_LADDER[-1])}"
            else:
                wins = detail[min_qty]["wins"]
                total = detail[min_qty]["total"]
                cell = f"{_fmt_qty(min_qty)} ({wins}/{total} wins)"
            row_parts.append(f"{cell:^{col_w}}")
        print(" | ".join(row_parts))

    print(sep)
    print()
    print("Notes:")
    print("  • qty = troops stacked per cell (hp and dmg both scale linearly)")
    print("  • Barbarian: hp=100, dmg=10, def=0, range=1 | Archer: hp=60, dmg=20, def=0, range=2")
    print("  • Troll: hp=200, dmg=30, def=20 (stars 1-6) | Wraith: hp=80, dmg=30, def=0, range=3")
    print("  • Demon: hp=400B, dmg=1.2B, def=1B (stars 7-10) | Pegasus: hp=250B, dmg=2B, range=3")
    print("  • Barb-only: 16 Barbarian cells  |  Archer-only: 16 Archer cells")
    print("  • Mixed: 8 Barbarian cells (rows 0-1) + 8 Archer cells (rows 2-3)")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Comprehensive min-troops finder")
    p.add_argument("--admin", default="admin")
    p.add_argument(
        "--target-type",
        choices=["monster_camp", "monster_fort", "both"],
        default="both",
    )
    p.add_argument("--battles-per-qty", type=int, default=3,
                   help="Number of battles per (formation, qty, star) combo (default: 3)")
    p.add_argument("--win-threshold", type=float, default=0.67,
                   help="Fraction of battles that must be won to declare a qty sufficient")
    p.add_argument("--no-cleanup", action="store_true",
                   help="Keep generated preset files after the run")
    return p.parse_args()


def main() -> None:
    args = _parse_args()

    if args.target_type == "both":
        target_types = {"monster_camp", "monster_fort"}
    else:
        target_types = {args.target_type}

    cleanup = not args.no_cleanup

    app = create_app()
    with app.app_context():
        # Ensure there is a player to run as
        player = m.get_player_by_username(args.admin)
        if not player:
            print(f"ERROR: admin user '{args.admin}' not found.")
            sys.exit(1)
        if player.get("role") != "admin":
            print(f"ERROR: user '{args.admin}' is not an admin.")
            sys.exit(1)
        admin_id = player["id"]

        # Seed world entities so every star level has at least some targets
        print("Ensuring all star levels are seeded...")
        _ensure_seeded_all_stars(targets_per_star=3, verbose=True)
        print()

        print(f"\nRunning comprehensive battle tests as '{args.admin}' (id={admin_id})")
        print(f"Target types  : {', '.join(sorted(target_types))}")
        print(f"Battles/qty   : {args.battles_per_qty}")
        print(f"Win threshold : {args.win_threshold:.0%}")
        print(f"Formations    : {', '.join(f.key for f in _FORMATIONS)}")
        print(f"Qty ladder    : {_QTY_LADDER}")
        print()

        results: dict[int, dict[str, tuple]] = {}

        for star in STAR_RANGE:
            results[star] = {}
            print(f"── Star {star} {'─'*50}")
            for form in _FORMATIONS:
                min_qty, detail = _search_min_qty(
                    admin_id=admin_id,
                    form=form,
                    star=star,
                    target_types=target_types,
                    battles_per_qty=args.battles_per_qty,
                    win_threshold=args.win_threshold,
                    cleanup=cleanup,
                )
                results[star][form.key] = (min_qty, detail)

                # Live progress
                found = _fmt_qty(min_qty) if min_qty is not None else "NOT FOUND"
                # Show last tested qty and its result if min_qty not found yet
                tested_qtys = sorted(detail.keys())
                last_qty = tested_qtys[-1] if tested_qtys else 0
                last_info = detail.get(last_qty, {})
                if last_info.get("no_target"):
                    status = "(no targets at this star level)"
                elif min_qty is not None:
                    w = detail[min_qty]["wins"]
                    t = detail[min_qty]["total"]
                    status = f"{w}/{t} wins at qty={_fmt_qty(min_qty)}"
                else:
                    w = last_info.get("wins", 0)
                    t = last_info.get("total", 0)
                    status = f"last tested qty={_fmt_qty(last_qty)}: {w}/{t} wins — NOT FOUND"
                print(f"   {form.key:8s}: min_qty={found:>10s}  [{status}]")

        _render_table(
            results,
            [(f.key, f.label) for f in _FORMATIONS],
            target_types,
        )

        if not cleanup:
            preset_names = [
                _preset_name(f.key, q)
                for f in _FORMATIONS
                for q in _QTY_LADDER
            ]
            print(f"Generated preset files kept in {PRESETS_DIR}/")
            print(f"  e.g. {preset_names[0]}.json  ...  {preset_names[-1]}.json")


if __name__ == "__main__":
    main()
