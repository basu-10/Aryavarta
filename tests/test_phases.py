"""tests/test_phases.py — Tests for each battle phase module."""

import pytest
from engine.grid import Grid
from engine.phases.intent import evaluate_intents, chebyshev, enemies_in_range
from engine.phases.movement import resolve_movement
from engine.phases.targeting import resolve_targeting, select_target
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
        archer = make_unit("B_AR1", "B", "Archer", 0, 8)
        barb = make_unit("A_B1", "A", "Barbarian", 0, 6)
        result = enemies_in_range(archer, [archer, barb])
        assert barb in result  # distance 2, archer range 2

    def test_enemy_out_of_range_archer(self):
        archer = make_unit("B_AR1", "B", "Archer", 0, 8)
        barb = make_unit("A_B1", "A", "Barbarian", 0, 5)  # dist=3, range=2
        result = enemies_in_range(archer, [archer, barb])
        assert barb not in result

    def test_intent_attack_when_in_range(self):
        barb = make_unit("A_B1", "A", "Barbarian", 0, 1)
        enemy = make_unit("B_B1", "B", "Barbarian", 0, 2)  # dist=1, in range
        evaluate_intents([barb, enemy])
        assert barb._intent == "attack"

    def test_intent_move_when_out_of_range(self):
        barb = make_unit("A_B1", "A", "Barbarian", 0, 0)
        enemy = make_unit("B_B1", "B", "Barbarian", 0, 8)  # dist=8, out of range
        evaluate_intents([barb, enemy])
        assert barb._intent == "move"

    def test_intent_hold_when_no_enemies(self):
        barb = make_unit("A_B1", "A", "Barbarian", 0, 0)
        evaluate_intents([barb])
        assert barb._intent == "hold"

    def test_intent_retreat_ranged_too_close(self):
        """Ranged unit retreats when front enemy is closer than its range."""
        archer = make_unit("B_AR1", "B", "Archer", 0, 6)  # range=2
        barb = make_unit("A_B1", "A", "Barbarian", 0, 5)  # distance=1 < range=2
        evaluate_intents([archer, barb])
        assert archer._intent == "retreat"

    def test_intent_attack_ranged_at_optimal_range(self):
        """Ranged unit attacks when front enemy is exactly at range."""
        archer = make_unit("B_AR1", "B", "Archer", 0, 7)  # range=2
        barb = make_unit("A_B1", "A", "Barbarian", 0, 5)  # distance=2 == range=2
        evaluate_intents([archer, barb])
        assert archer._intent == "attack"

    def test_dead_units_are_ignored(self):
        barb = make_unit("A_B1", "A", "Barbarian", 0, 0)
        dead_enemy = make_unit("B_B1", "B", "Barbarian", 0, 1)
        dead_enemy.alive = False
        dead_enemy.hp = 0
        evaluate_intents([barb, dead_enemy])
        # No living enemies — should hold
        assert barb._intent == "hold"


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Movement
# ─────────────────────────────────────────────────────────────────────────────

class TestMovementPhase:

    def _placed_grid(self, *units):
        g = Grid(4, 9)
        for u in units:
            g.place(u.unit_id, u.row, u.col)
        return g

    def test_barbarian_advances_one_cell(self):
        """Barbarian speed=1.0: moves 1 cell in the first tick."""
        barb = make_unit("A_B1", "A", "Barbarian", 0, 0)  # speed=1.0
        barb._intent = "move"
        g = self._placed_grid(barb)
        resolve_movement([barb], g)
        assert barb.col == 1  # moved 1 step right
        assert barb.row == 0  # row unchanged

    def test_archer_moves_every_two_ticks(self):
        """Archer speed=0.5: accumulates credit, moves on 2nd resolve call."""
        archer = make_unit("B_AR1", "B", "Archer", 0, 8)  # speed=0.5
        archer._intent = "move"
        g = self._placed_grid(archer)
        resolve_movement([archer], g)  # tick 1: acc=0.5, no move
        assert archer.col == 8
        archer._intent = "move"        # set intent again for tick 2
        resolve_movement([archer], g)  # tick 2: acc=1.0, moves
        assert archer.col == 7  # moved 1 step left (toward Team A)
        assert archer.row == 0

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

    def test_conflict_both_advance(self):
        """
        Two opposing-team units advancing toward each other on the same row.
        They stop when they would collide in the same cell.
        """
        a = make_unit("A_B1", "A", "Barbarian", 0, 0)
        b = make_unit("B_B1", "B", "Barbarian", 0, 2)
        a._intent = "move"
        b._intent = "move"
        g = Grid(4, 9)
        g.place(a.unit_id, a.row, a.col)
        g.place(b.unit_id, b.row, b.col)
        resolve_movement([a, b], g)
        # A wants col 1, B wants col 1 — conflict: alphabetical "A_B1" wins
        assert a.col == 1
        assert b.col == 2  # B blocked

    def test_grid_updated_after_move(self):
        barb = make_unit("A_B1", "A", "Barbarian", 1, 1)
        barb._intent = "move"
        g = Grid(4, 9)
        g.place(barb.unit_id, barb.row, barb.col)
        resolve_movement([barb], g)
        if barb.col != 1:  # if actually moved
            assert not g.is_occupied(1, 1)

    def test_forward_stop_at_edge(self):
        """Unit at the last column cannot move further — stops cleanly."""
        barb = make_unit("A_B1", "A", "Barbarian", 0, 8)  # right edge of 9-col grid
        barb._intent = "move"
        g = self._placed_grid(barb)
        resolve_movement([barb], g)
        assert barb.col == 8  # can't go beyond col 8

    def test_retreat_moves_backward(self):
        """Ranged unit with retreat intent moves backward (away from enemy)."""
        archer = make_unit("B_AR1", "B", "Archer", 0, 6)  # Team B forward=-1, retreat=+1
        archer._intent = "retreat"
        g = self._placed_grid(archer)
        resolve_movement([archer], g)  # tick 1: acc=0.5, no move
        archer._intent = "retreat"
        resolve_movement([archer], g)  # tick 2: acc=1.0, retreats
        assert archer.col == 7  # moved right (away from Team A enemies)

    def test_blocked_retreat_switches_to_attack(self):
        """Archer at the back wall can't retreat — intent switches to attack."""
        archer = make_unit("B_AR1", "B", "Archer", 0, 8)  # at right edge
        archer._intent = "retreat"
        # Give enough credit to attempt movement
        archer._move_acc = 1.0
        g = self._placed_grid(archer)
        resolve_movement([archer], g)
        assert archer._intent == "attack"  # switched because retreat was blocked


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — Targeting
# ─────────────────────────────────────────────────────────────────────────────

class TestTargetingPhase:

    def test_picks_closest_enemy(self):
        """Targeting always picks the closest in-range enemy."""
        attacker = make_unit("A_B1", "A", "Barbarian", 0, 3)
        near = make_unit("B_B1", "B", "Barbarian", 0, 4)  # dist=1
        far  = make_unit("B_B2", "B", "Barbarian", 0, 5)  # dist=2, out of barb range
        attacker._intent = "attack"
        resolve_targeting([attacker, near, far])
        assert attacker._target_id == "B_B1"

    def test_tie_break_by_unit_id(self):
        """Two equidistant off-row enemies — alphabetically-first unit_id wins."""
        # Attacker in middle row so both targets are diagonal (neither direct-front)
        attacker = make_unit("A_B1", "A", "Barbarian", 1, 3)
        e1 = make_unit("B_B2", "B", "Barbarian", 0, 4)  # Chebyshev=1, row 0
        e2 = make_unit("B_B1", "B", "Barbarian", 2, 4)  # Chebyshev=1, row 2
        attacker._intent = "attack"
        resolve_targeting([attacker, e1, e2])
        assert attacker._target_id == "B_B1"  # alphabetically first

    def test_no_target_if_out_of_range(self):
        attacker = make_unit("A_B1", "A", "Barbarian", 0, 0)
        enemy = make_unit("B_B1", "B", "Barbarian", 0, 3)  # dist=3, barb range=1
        attacker._intent = "attack"
        resolve_targeting([attacker, enemy])
        assert attacker._target_id is None

    def test_archer_picks_closest_in_range(self):
        """Archer range=2 — picks closest within 2 cells."""
        archer = make_unit("B_AR1", "B", "Archer", 0, 7)  # range=2
        e1 = make_unit("A_B1", "A", "Barbarian", 0, 5)  # dist=2, in range
        e2 = make_unit("A_B2", "A", "Barbarian", 0, 4)  # dist=3, out of range
        archer._intent = "attack"
        resolve_targeting([archer, e1, e2])
        assert archer._target_id == "A_B1"


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
        assert target.hp == 90  # 100 - 10

    def test_simultaneous_damage(self):
        """Both units attack each other — neither dies mid-phase."""
        a = make_unit("A_B1", "A", "Barbarian", 0, 1)
        b = make_unit("B_B1", "B", "Barbarian", 0, 0)
        a._intent = "attack"; a._target_id = "B_B1"
        b._intent = "attack"; b._target_id = "A_B1"
        apply_damage([a, b])
        # Both should have taken 10 HP of damage
        assert a.hp == 90
        assert b.hp == 90

    def test_multiple_attackers_on_one_target(self):
        """Two units attacking same target — damage accumulates."""
        a1 = make_unit("A_B1", "A", "Barbarian", 0, 1)
        a2 = make_unit("A_B2", "A", "Barbarian", 1, 1)
        t  = make_unit("B_B1", "B", "Barbarian", 0, 2)
        a1._intent = "attack"; a1._target_id = "B_B1"
        a2._intent = "attack"; a2._target_id = "B_B1"
        apply_damage([a1, a2, t])
        assert t.hp == 80  # 100 - 10 - 10

    def test_returns_events(self):
        a = make_unit("A_B1", "A", "Barbarian", 0, 1)
        t = make_unit("B_B1", "B", "Barbarian", 0, 2)
        a._intent = "attack"; a._target_id = "B_B1"
        events, pool_damage = apply_damage([a, t])
        assert len(events) == 1
        assert events[0]["attacker_id"] == "A_B1"
        assert events[0]["target_id"] == "B_B1"
        assert events[0]["damage"] == 10  # Barbarian damage=10, target defense=0


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
