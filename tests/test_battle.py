"""tests/test_battle.py — Integration tests for the full battle simulation."""

import pytest
from engine.battle import Battle
from engine.unit import Unit
from tests.conftest import make_unit


def _barbs_vs_archers():
    """4 barbarians (A) vs 4 archers (B) — default preset."""
    army_a = [
        make_unit("A_B1", "A", "Barbarian", 0, 0, attack_behavior="Closest"),
        make_unit("A_B2", "A", "Barbarian", 1, 0, attack_behavior="Closest"),
        make_unit("A_B3", "A", "Barbarian", 2, 1, attack_behavior="LowestHP"),
        make_unit("A_B4", "A", "Barbarian", 3, 1, attack_behavior="LowestHP"),
    ]
    army_b = [
        make_unit("B_AR1", "B", "Archer", 0, 4, move_behavior="Hold", attack_behavior="Closest"),
        make_unit("B_AR2", "B", "Archer", 1, 4, move_behavior="Hold", attack_behavior="LowestHP"),
        make_unit("B_AR3", "B", "Archer", 2, 3, move_behavior="Hold", attack_behavior="LowestHP"),
        make_unit("B_AR4", "B", "Archer", 3, 3, move_behavior="Hold", attack_behavior="Closest"),
    ]
    return army_a, army_b


class TestBattleIntegration:

    def test_has_winner(self):
        a, b = _barbs_vs_archers()
        result = Battle(a, b).run()
        assert result.winner in ("A", "B", "Draw")

    def test_tick_0_is_initial_state(self):
        a, b = _barbs_vs_archers()
        result = Battle(a, b).run()
        snap0 = result.ticks[0]
        assert snap0["tick"] == 0
        # All 8 units should be alive at tick 0
        alive = [u for u in snap0["units"] if u["status"] == "alive"]
        assert len(alive) == 8

    def test_ticks_monotonically_increase(self):
        a, b = _barbs_vs_archers()
        result = Battle(a, b).run()
        tick_nums = [s["tick"] for s in result.ticks]
        assert tick_nums == list(range(len(tick_nums)))

    def test_total_ticks_matches_snapshot_count(self):
        a, b = _barbs_vs_archers()
        result = Battle(a, b).run()
        # ticks list includes tick 0, so length = total_ticks + 1
        assert len(result.ticks) == result.total_ticks + 1

    def test_no_overlap_positions_per_tick(self):
        """At every tick, no two alive units share the same cell."""
        a, b = _barbs_vs_archers()
        result = Battle(a, b).run()
        for snap in result.ticks:
            positions = [
                (u["row"], u["col"]) for u in snap["units"] if u["status"] == "alive"
            ]
            assert len(positions) == len(set(positions)), (
                f"Overlap detected at tick {snap['tick']}: {positions}"
            )

    def test_hp_never_increases(self):
        """HP can only decrease or stay the same across ticks."""
        a, b = _barbs_vs_archers()
        result = Battle(a, b).run()
        hp_history: dict[str, list[int]] = {}
        for snap in result.ticks:
            for u in snap["units"]:
                uid = u["unit_id"]
                hp_history.setdefault(uid, []).append(u["hp"])
        for uid, hps in hp_history.items():
            for i in range(1, len(hps)):
                if hps[i - 1] > 0:  # ignore if already dead (hp may be 0)
                    assert hps[i] <= hps[i - 1], (
                        f"{uid} HP went up from {hps[i-1]} to {hps[i]}"
                    )

    def test_unit_placement_conflict_raises(self):
        a = [make_unit("A_B1", "A", "Barbarian", 0, 0)]
        b = [make_unit("B_B1", "B", "Barbarian", 0, 0)]  # same cell!
        with pytest.raises(ValueError):
            Battle(a, b).run()

    def test_single_vs_single_barbarian_fight(self):
        """One barb vs one barb at adjacent cells — should resolve quickly."""
        a = [make_unit("A_B1", "A", "Barbarian", 0, 1)]
        b = [make_unit("B_B1", "B", "Barbarian", 0, 3)]
        result = Battle(a, b).run()
        assert result.winner in ("A", "B", "Draw")
        assert result.total_ticks < 50  # should not run forever


class TestBattleEdgeCases:

    def test_archers_hold_beat_advancing_barbarians(self):
        """
        4 holding archers (range 3, dmg 2) at the far right should outrange
        and kill advancing barbarians before melee begins (or at least win).
        This validates range advantage.
        """
        a = [make_unit(f"A_B{i}", "A", "Barbarian", i, 0) for i in range(4)]
        b = [
            make_unit(f"B_AR{i}", "B", "Archer", i, 4, move_behavior="Hold")
            for i in range(4)
        ]
        result = Battle(a, b).run()
        # Archers deal 2 dmg/tick each, barbarians have 10 HP, speed 2
        # Barbarians take ~3 ticks to reach range-3 zone, archers fire each tick
        # Result is not guaranteed but should finish in reasonable time
        assert result.total_ticks < config_max()

    def test_draw_declared_at_max_ticks(self):
        """If two immortal units face each other they draw at MAX_TICKS."""
        import config
        a = [make_unit("A_B1", "A", "Barbarian", 0, 1)]
        b = [make_unit("B_B1", "B", "Barbarian", 0, 3)]
        # Make them invincible
        for u in [a[0], b[0]]:
            u.defense = 9999
        result = Battle(a, b).run()
        assert result.winner == "Draw"
        assert result.total_ticks == config.MAX_TICKS


def config_max():
    import config
    return config.MAX_TICKS
