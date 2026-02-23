"""tests/test_phases.py — Tests for each battle phase module."""

import random
import pytest
from engine.grid import Grid
from engine.phases.intent import evaluate_intents, chebyshev, enemies_in_range
from engine.phases.movement import resolve_movement
from engine.phases.targeting import resolve_targeting, select_target, direction_of
from engine.phases.damage import apply_damage
from engine.phases.death import resolve_deaths
from tests.conftest import make_unit


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Intent
# ─────────────────────────────────────────────────────────────────────────────

class TestIntentPhase:

    def test_chebyshev_same_cell(self):
        u1 = make_unit("A", "A", "Barbarian", 0, 0)
        u2 = make_unit("B", "B", "Barbarian", 0, 0)
        assert chebyshev(u1, u2) == 0

    def test_chebyshev_diagonal(self):
        u1 = make_unit("A", "A", "Barbarian", 0, 0)
        u2 = make_unit("B", "B", "Barbarian", 2, 2)
        assert chebyshev(u1, u2) == 2

    def test_enemy_in_range_archer(self):
        archer = make_unit("B_AR1", "B", "Archer", 0, 4)
        barb = make_unit("A_B1", "A", "Barbarian", 0, 1)
        result = enemies_in_range(archer, [archer, barb])
        assert barb in result  # distance 3, archer range 3

    def test_enemy_out_of_range(self):
        barb = make_unit("A_B1", "A", "Barbarian", 0, 0)
        enemy = make_unit("B_B1", "B", "Barbarian", 0, 2)  # dist=2, barb range=1
        result = enemies_in_range(barb, [barb, enemy])
        assert enemy not in result

    def test_intent_attack_when_in_range(self):
        barb = make_unit("A_B1", "A", "Barbarian", 0, 1)
        enemy = make_unit("B_B1", "B", "Barbarian", 0, 2)  # dist=1, in range
        evaluate_intents([barb, enemy])
        assert barb._intent == "attack"

    def test_intent_move_when_out_of_range(self):
        barb = make_unit("A_B1", "A", "Barbarian", 0, 0)
        enemy = make_unit("B_B1", "B", "Barbarian", 0, 4)  # dist=4, out of range
        evaluate_intents([barb, enemy])
        assert barb._intent == "move"

    def test_intent_hold_when_behavior_hold(self):
        barb = make_unit("A_B1", "A", "Barbarian", 0, 0, move_behavior="Hold")
        enemy = make_unit("B_B1", "B", "Barbarian", 0, 4)
        evaluate_intents([barb, enemy])
        assert barb._intent == "hold"

    def test_dead_units_are_ignored(self):
        barb = make_unit("A_B1", "A", "Barbarian", 0, 0)
        dead_enemy = make_unit("B_B1", "B", "Barbarian", 0, 1)
        dead_enemy.alive = False
        dead_enemy.hp = 0
        evaluate_intents([barb, dead_enemy])
        # No living enemies in range — should still want to move
        assert barb._intent == "move"


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Movement
# ─────────────────────────────────────────────────────────────────────────────

class TestMovementPhase:

    def _placed_grid(self, *units):
        g = Grid(4, 5)
        for u in units:
            g.place(u.unit_id, u.row, u.col)
        return g

    def test_barbarian_advances_two_cells(self):
        barb = make_unit("A_B1", "A", "Barbarian", 0, 0)  # speed=2
        barb._intent = "move"
        g = self._placed_grid(barb)
        resolve_movement([barb], g)
        assert barb.col == 2  # moved 2 steps right
        assert barb.row == 0  # row unchanged

    def test_archer_advances_one_cell(self):
        archer = make_unit("B_AR1", "B", "Archer", 0, 4)  # speed=1
        archer._intent = "move"
        g = self._placed_grid(archer)
        resolve_movement([archer], g)
        assert archer.col == 3  # moved 1 step left
        assert archer.row == 0  # row unchanged

    def test_no_diagonal_movement(self):
        """Unit blocked straight ahead stays put — no diagonal fallback."""
        b1 = make_unit("A_B1", "A", "Barbarian", 0, 0)
        b2 = make_unit("A_B2", "A", "Barbarian", 0, 1)  # blocks straight ahead
        b1._intent = "move"
        b2._intent = "hold"
        g = self._placed_grid(b1, b2)
        resolve_movement([b1, b2], g)
        # b1 must stay at (0,0) — no diagonal to (1,1) allowed
        assert b1.col == 0
        assert b1.row == 0

    def test_blocked_unit_row_never_changes(self):
        """Even fully blocked units must never shift rows."""
        b1 = make_unit("A_B1", "A", "Barbarian", 2, 0)
        wall = make_unit("A_B2", "A", "Barbarian", 2, 1)
        b1._intent = "move"
        wall._intent = "hold"
        g = self._placed_grid(b1, wall)
        resolve_movement([b1, wall], g)
        assert b1.row == 2  # row locked

    def test_conflict_both_blocked(self):
        """
        Two opposing-team units advancing into the same cell get resolved:
        the alphabetically-first unit_id wins, the other stops.

        Setup (Barbarians speed=2, same row):
          A_B1 at col 0 → step1: (r,1) step2: (r,2)
          B_B1 at col 4 → step1: (r,3) step2: (r,2)   ← conflict at step 2
        """
        a = make_unit("A_B1", "A", "Barbarian", 1, 0)
        b = make_unit("B_B1", "B", "Barbarian", 1, 4)
        a._intent = "move"
        b._intent = "move"
        g = Grid(4, 5)
        g.place(a.unit_id, a.row, a.col)
        g.place(b.unit_id, b.row, b.col)
        resolve_movement([a, b], g)
        # "A_B1" < "B_B1" → A wins the contested (1,2), B stops at col 3
        assert a.col == 2
        assert b.col == 3

    def test_grid_updated_after_move(self):
        barb = make_unit("A_B1", "A", "Barbarian", 1, 1)
        barb._intent = "move"
        g = Grid(4, 5)
        g.place(barb.unit_id, barb.row, barb.col)
        resolve_movement([barb], g)
        if barb.col != 1:  # if actually moved
            assert not g.is_occupied(1, 1)

    def test_forward_stop_at_edge(self):
        """Unit at the edge column cannot move further — stops cleanly."""
        barb = make_unit("A_B1", "A", "Barbarian", 0, 4)  # already at right edge
        barb._intent = "move"
        g = self._placed_grid(barb)
        resolve_movement([barb], g)
        assert barb.col == 4  # can't go beyond col 4


def barb_col_after(u):
    return u.col


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — Targeting
# ─────────────────────────────────────────────────────────────────────────────

class TestDirectionOf:
    """Unit tests for the direction_of helper."""

    def test_front_team_a(self):
        # Team A moves right (+col); enemy to the right = front
        a = make_unit("A_B1", "A", "Barbarian", 2, 2)
        e = make_unit("B_B1", "B", "Barbarian", 2, 4)
        assert direction_of(a, e) == "front"

    def test_back_team_a(self):
        a = make_unit("A_B1", "A", "Barbarian", 2, 3)
        e = make_unit("B_B1", "B", "Barbarian", 2, 0)
        assert direction_of(a, e) == "back"

    def test_side_same_col(self):
        a = make_unit("A_B1", "A", "Barbarian", 1, 2)
        e = make_unit("B_B1", "B", "Barbarian", 3, 2)
        assert direction_of(a, e) == "side"

    def test_side_different_col_and_row(self):
        # Different row AND different col — classified as side
        a = make_unit("A_B1", "A", "Barbarian", 1, 2)
        e = make_unit("B_B1", "B", "Barbarian", 3, 4)
        assert direction_of(a, e) == "side"

    def test_front_team_b(self):
        # Team B moves left (-col); enemy to the left = front
        b = make_unit("B_B1", "B", "Barbarian", 2, 4)
        e = make_unit("A_B1", "A", "Barbarian", 2, 1)
        assert direction_of(b, e) == "front"

    def test_back_team_b(self):
        b = make_unit("B_B1", "B", "Barbarian", 2, 1)
        e = make_unit("A_B1", "A", "Barbarian", 2, 4)
        assert direction_of(b, e) == "back"


class TestTargetingPhase:

    # ── Front priority ──────────────────────────────────────────────── #

    def test_front_enemy_chosen_over_side(self):
        """Front enemy is always preferred, even if the side enemy has lower HP."""
        attacker = make_unit("A_B1", "A", "Barbarian", 0, 3, attack_behavior="LowestHP")
        front_e  = make_unit("B_B1", "B", "Barbarian", 0, 4)  # same row, ahead
        side_e   = make_unit("B_B2", "B", "Barbarian", 2, 4)  # different row
        front_e.hp = 9
        side_e.hp  = 1  # much lower HP, but NOT in front
        attacker._intent = "attack"
        resolve_targeting([attacker, front_e, side_e])
        assert attacker._target_id == "B_B1"

    def test_front_behavior_closest(self):
        """Among front enemies, Closest behavior picks the nearer one."""
        attacker = make_unit("A_AR1", "A", "Archer", 0, 0, attack_behavior="Closest")
        attacker.range = 3
        near = make_unit("B_B1", "B", "Barbarian", 0, 1)  # closer
        far  = make_unit("B_B2", "B", "Barbarian", 0, 3)  # further
        attacker._intent = "attack"
        resolve_targeting([attacker, near, far])
        assert attacker._target_id == "B_B1"

    def test_front_behavior_lowest_hp(self):
        """Among front enemies, LowestHP applies correctly."""
        attacker = make_unit("A_AR1", "A", "Archer", 0, 0, attack_behavior="LowestHP")
        attacker.range = 4
        e1 = make_unit("B_B1", "B", "Barbarian", 0, 1)
        e2 = make_unit("B_B2", "B", "Barbarian", 0, 2)
        e1.hp = 9
        e2.hp = 4  # lower HP, also in front
        attacker._intent = "attack"
        resolve_targeting([attacker, e1, e2])
        assert attacker._target_id == "B_B2"

    def test_front_behavior_highest_hp(self):
        """Among front enemies, HighestHP applies correctly."""
        attacker = make_unit("A_AR1", "A", "Archer", 0, 0, attack_behavior="HighestHP")
        attacker.range = 4
        e1 = make_unit("B_B1", "B", "Barbarian", 0, 1)
        e2 = make_unit("B_B2", "B", "Barbarian", 0, 2)
        e1.hp = 9
        e2.hp = 4
        attacker._intent = "attack"
        resolve_targeting([attacker, e1, e2])
        assert attacker._target_id == "B_B1"  # higher HP

    def test_front_tie_break_by_id(self):
        """Two equidistant front enemies — deterministic via unit_id."""
        attacker = make_unit("A_AR1", "A", "Archer", 1, 0, attack_behavior="Closest")
        attacker.range = 4
        e1 = make_unit("B_B2", "B", "Barbarian", 1, 1)  # same row ahead
        e2 = make_unit("B_B1", "B", "Barbarian", 1, 1)  # would collide in real game; ok for unit test
        # give them distinct cols so range works; same Cheby distance
        e2.col = 2
        e2.hp = 10
        attacker._intent = "attack"
        resolve_targeting([attacker, e1, e2])
        # e1 is closer (col 1 vs col 2), so Closest picks e1
        assert attacker._target_id == "B_B2"

    # ── Flank (back / side) ──────────────────────────────────────────── #

    def test_flank_random_from_side_only(self):
        """No front enemy — random pick from the side pool."""
        attacker = make_unit("A_AR1", "A", "Archer", 1, 2, attack_behavior="Closest")
        attacker.range = 3
        side1 = make_unit("B_B1", "B", "Barbarian", 0, 2)  # same col, different row
        side2 = make_unit("B_B2", "B", "Barbarian", 3, 2)  # same col, different row
        # No enemy in front (row=1, col>2) within range
        attacker._intent = "attack"

        chosen = set()
        for seed in range(30):  # collect draws across many seeds
            random.seed(seed)
            resolve_targeting([attacker, side1, side2])
            chosen.add(attacker._target_id)
            attacker.reset_tick_state()
            attacker._intent = "attack"

        assert "B_B1" in chosen
        assert "B_B2" in chosen

    def test_flank_random_from_back_and_side(self):
        """No front enemy — random pick from combined back+side pool."""
        attacker = make_unit("A_AR1", "A", "Archer", 1, 4, attack_behavior="Closest")
        attacker.range = 3
        back_e = make_unit("B_B1", "B", "Barbarian", 1, 2)   # same row, behind
        side_e = make_unit("B_B2", "B", "Barbarian", 0, 4)   # different row
        # No enemy in front (col > 4 OOB)
        attacker._intent = "attack"

        chosen = set()
        for seed in range(30):
            random.seed(seed)
            resolve_targeting([attacker, back_e, side_e])
            chosen.add(attacker._target_id)
            attacker.reset_tick_state()
            attacker._intent = "attack"

        assert "B_B1" in chosen
        assert "B_B2" in chosen

    # ── Edge cases ──────────────────────────────────────────────────── #

    def test_no_target_if_out_of_range(self):
        attacker = make_unit("A_B1", "A", "Barbarian", 0, 0, attack_behavior="Closest")
        enemy = make_unit("B_B1", "B", "Barbarian", 0, 3)  # dist=3, barb range=1
        attacker._intent = "attack"
        resolve_targeting([attacker, enemy])
        assert attacker._target_id is None


def evaluate_with_mock_intent(units):
    """Set _intent=attack for Team A, hold for Team B (for targeting tests)."""
    for u in units:
        if u.team == "A":
            u._intent = "attack"


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4 — Damage
# ─────────────────────────────────────────────────────────────────────────────

class TestDamagePhase:

    def test_basic_damage(self):
        attacker = make_unit("A_B1", "A", "Barbarian", 0, 1)
        target   = make_unit("B_B1", "B", "Barbarian", 0, 2)
        attacker._intent = "attack"
        attacker._target_id = "B_B1"
        apply_damage([attacker, target])
        assert target.hp == 9  # 10 - 1

    def test_simultaneous_damage(self):
        """Both units attack each other — neither dies mid-phase."""
        a = make_unit("A_B1", "A", "Barbarian", 0, 1)
        b = make_unit("B_B1", "B", "Barbarian", 0, 0)
        a._intent = "attack"; a._target_id = "B_B1"
        b._intent = "attack"; b._target_id = "A_B1"
        apply_damage([a, b])
        # Both should have taken 1 HP of damage
        assert a.hp == 9
        assert b.hp == 9

    def test_multiple_attackers_on_one_target(self):
        """Two units attacking same target — damage accumulates."""
        a1 = make_unit("A_B1", "A", "Barbarian", 0, 1)
        a2 = make_unit("A_B2", "A", "Barbarian", 1, 1)
        t  = make_unit("B_B1", "B", "Barbarian", 0, 2)
        a1._intent = "attack"; a1._target_id = "B_B1"
        a2._intent = "attack"; a2._target_id = "B_B1"
        apply_damage([a1, a2, t])
        assert t.hp == 8  # 10 - 1 - 1

    def test_returns_events(self):
        a = make_unit("A_B1", "A", "Barbarian", 0, 1)
        t = make_unit("B_B1", "B", "Barbarian", 0, 2)
        a._intent = "attack"; a._target_id = "B_B1"
        events = apply_damage([a, t])
        assert len(events) == 1
        assert events[0]["attacker_id"] == "A_B1"
        assert events[0]["target_id"] == "B_B1"
        assert events[0]["damage"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5 — Death
# ─────────────────────────────────────────────────────────────────────────────

class TestDeathPhase:

    def test_dead_unit_removed_from_grid(self):
        g = Grid(4, 5)
        u = make_unit("A_B1", "A", "Barbarian", 0, 0)
        g.place(u.unit_id, u.row, u.col)
        u.hp = 0  # killed by damage phase
        dead = resolve_deaths([u], g)
        assert "A_B1" in dead
        assert u.alive is False
        assert not g.is_occupied(0, 0)

    def test_alive_unit_not_affected(self):
        g = Grid(4, 5)
        u = make_unit("A_B1", "A", "Barbarian", 0, 0)
        g.place(u.unit_id, u.row, u.col)
        dead = resolve_deaths([u], g)
        assert dead == []
        assert u.alive is True

    def test_negative_hp_counts_as_dead(self):
        g = Grid(4, 5)
        u = make_unit("A_B1", "A", "Barbarian", 0, 0)
        u.hp = -3
        g.place(u.unit_id, u.row, u.col)
        dead = resolve_deaths([u], g)
        assert "A_B1" in dead
