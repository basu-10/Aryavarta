"""tests/test_grid.py — Unit tests for engine.grid.Grid"""

import pytest
from engine.grid import Grid


def test_place_and_query():
    g = Grid(4, 5)
    assert g.place("A_B1", 0, 0) is True
    assert g.is_occupied(0, 0) is True
    assert g.get_unit_id(0, 0) == "A_B1"


def test_place_out_of_bounds():
    g = Grid(4, 5)
    assert g.place("X", 5, 0) is False
    assert g.place("X", 0, 5) is False


def test_place_occupied():
    g = Grid(4, 5)
    g.place("A", 1, 1)
    assert g.place("B", 1, 1) is False


def test_remove():
    g = Grid(4, 5)
    g.place("A_B1", 2, 2)
    uid = g.remove(2, 2)
    assert uid == "A_B1"
    assert not g.is_occupied(2, 2)


def test_remove_empty_returns_none():
    g = Grid(4, 5)
    assert g.remove(0, 0) is None


def test_move_unit_success():
    g = Grid(4, 5)
    g.place("A_B1", 0, 0)
    assert g.move_unit(0, 0, 0, 1) is True
    assert not g.is_occupied(0, 0)
    assert g.get_unit_id(0, 1) == "A_B1"


def test_move_unit_blocked_by_occupant():
    g = Grid(4, 5)
    g.place("A_B1", 0, 0)
    g.place("B_B1", 0, 1)
    assert g.move_unit(0, 0, 0, 1) is False
    # Original position unchanged
    assert g.get_unit_id(0, 0) == "A_B1"


def test_move_unit_out_of_bounds():
    g = Grid(4, 5)
    g.place("A_B1", 0, 4)
    assert g.move_unit(0, 4, 0, 5) is False


def test_snapshot_is_copy():
    g = Grid(4, 5)
    g.place("A_B1", 0, 0)
    snap = g.snapshot()
    g.place("B_B1", 1, 1)
    # Snapshot should NOT reflect the new placement
    assert (1, 1) not in snap


def test_in_bounds():
    g = Grid(4, 5)
    assert g.in_bounds(0, 0) is True
    assert g.in_bounds(3, 4) is True
    assert g.in_bounds(-1, 0) is False
    assert g.in_bounds(4, 0) is False
