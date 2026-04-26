"""tests/test_unit.py — Unit tests for engine.unit.Unit"""

import pytest
from tests.conftest import make_unit


def test_forward_dir_team_a():
    u = make_unit("A_B1", "A", "Barbarian", 0, 0)
    assert u.forward_dir == 1


def test_forward_dir_team_b():
    u = make_unit("B_B1", "B", "Barbarian", 0, 4)
    assert u.forward_dir == -1


def test_take_damage_no_defense():
    u = make_unit("A_B1", "A", "Barbarian", 0, 0)
    effective = u.take_damage(3)
    assert effective == 3
    assert u.hp == 7


def test_take_damage_with_defense():
    u = make_unit("A_B1", "A", "Barbarian", 0, 0)
    u.defense = 2
    effective = u.take_damage(3)
    assert effective == 1
    assert u.hp == 9


def test_take_damage_cannot_go_negative():
    u = make_unit("A_B1", "A", "Barbarian", 0, 0)
    u.defense = 10
    effective = u.take_damage(3)
    assert effective == 0
    assert u.hp == 10  # unchanged


def test_is_alive():
    u = make_unit("A_B1", "A", "Barbarian", 0, 0)
    assert u.is_alive() is True
    u.hp = 0
    assert u.is_alive() is False


def test_reset_tick_state():
    u = make_unit("A_B1", "A", "Barbarian", 0, 0)
    u._intent = "attack"
    u._target_id = "B_B1"
    u._damage_dealt = 5
    u._action = "attack"
    u.reset_tick_state()
    assert u._intent == "hold"
    assert u._target_id is None
    assert u._damage_dealt == 0
    assert u._action == ""


def test_to_dict_keys():
    u = make_unit("A_B1", "A", "Barbarian", 1, 2)
    d = u.to_dict()
    assert d["unit_id"] == "A_B1"
    assert d["team"] == "A"
    assert d["row"] == 1
    assert d["col"] == 2


def test_from_dict_round_trip():
    from engine.unit import Unit
    data = {
        "unit_id": "B_AR1",
        "team": "B",
        "type": "Archer",
        "row": 3,
        "col": 8,
    }
    u = Unit.from_dict(data)
    assert u.unit_id == "B_AR1"
    assert u.team == "B"
    assert u.hp == 6          # Archer base HP
    assert u.damage == 2
    assert u.range == 2       # updated Archer range
    assert u.speed == 0.5     # updated Archer speed
