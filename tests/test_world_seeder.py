"""tests/test_world_seeder.py — Focused tests for world monster spawn rules."""

import pytest

import config
from db.models import compute_star_level
from db.world_seeder import _random_monster_spec


@pytest.mark.parametrize(
    "star_level,expected_range",
    [
        (1, (2, 3)),
        (2, (4, 5)),
        (3, (6, 8)),
        (4, (9, 11)),
        (5, (12, 14)),
        (6, (15, 16)),
    ],
)
def test_random_monster_spec_stays_within_star_band(star_level, expected_range):
    expected_min, expected_max = expected_range

    for _ in range(20):
        spec = _random_monster_spec(star_level)
        total_units = sum(entry["count"] for entry in spec)

        assert expected_min <= total_units <= expected_max
        assert compute_star_level(total_units) == star_level
        assert {entry["type"] for entry in spec} <= {"Troll", "Wraith"}


def test_star_thresholds_match_spawn_ranges():
    expected_thresholds = [
        config.MONSTER_STAR_UNIT_RANGES[star_level][1]
        for star_level in range(1, max(config.MONSTER_STAR_UNIT_RANGES))
    ]

    assert config.STAR_THRESHOLDS == expected_thresholds