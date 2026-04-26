"""
tests/conftest.py — Shared pytest fixtures for BattleCells tests.
"""

import sys
from pathlib import Path

# Ensure the project root is on sys.path so `import config`, `import engine.*` work.
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from engine.unit import Unit
from engine.grid import Grid
from config import UNIT_STATS


def make_unit(
    unit_id: str,
    team: str,
    unit_type: str,
    row: int,
    col: int,
) -> Unit:
    """Factory helper — creates a Unit from stats table."""
    stats = UNIT_STATS[unit_type]
    return Unit(
        unit_id=unit_id,
        team=team,
        unit_type=unit_type,
        row=row,
        col=col,
        hp=stats["hp"],
        max_hp=stats["hp"],
        damage=stats["damage"],
        defense=stats["defense"],
        range=stats["range"],
        speed=stats["speed"],
    )


@pytest.fixture
def barb_a():
    return make_unit("A_B1", "A", "Barbarian", row=0, col=0)


@pytest.fixture
def barb_b():
    return make_unit("B_B1", "B", "Barbarian", row=0, col=8)


@pytest.fixture
def archer_b():
    return make_unit("B_AR1", "B", "Archer", row=0, col=8)


@pytest.fixture
def small_grid():
    return Grid(rows=4, cols=5)
