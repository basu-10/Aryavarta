"""
unit.py — Unit dataclass representing a single combatant on the battlefield.

Design notes:
- Immutable core stats set at construction time.
- Mutable runtime state: hp, row, col, alive, _intent.
- _intent is ephemeral (set each tick by the intent phase, never persisted).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Unit:
    unit_id: str          # e.g. "A_B1", "B_AR2"
    team: str             # 'A' or 'B'
    unit_type: str        # 'Barbarian', 'Archer', 'Troll', 'Wraith', etc.
    row: int
    col: int
    hp: int
    max_hp: int
    damage: int
    defense: int
    range: int            # Chebyshev range
    speed: float          # movement credit per tick: 1.0 = 1x, 0.5 = 0.5x
    ammo: Optional[int] = None  # Used by defence units; None means unlimited/not applicable
    quantity: int = 1           # Number of stacked troops this unit represents
    alive: bool = True
    # Ephemeral per-tick fields (not serialised to CSV/JSON directly)
    _intent: str = field(default="hold", repr=False, compare=False)
    _target_id: Optional[str] = field(default=None, repr=False, compare=False)
    _damage_dealt: int = field(default=0, repr=False, compare=False)
    _action: str = field(default="", repr=False, compare=False)
    # Persists across ticks — movement credit accumulator for fractional speed
    _move_acc: float = field(default=0.0, repr=False, compare=False)

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    @property
    def pos(self) -> tuple[int, int]:
        return (self.row, self.col)

    @property
    def forward_dir(self) -> int:
        """Column delta for 'advancing': +1 for Team A (→), -1 for Team B (←)."""
        return 1 if self.team == "A" else -1

    def is_alive(self) -> bool:
        return self.alive and self.hp > 0

    def take_damage(self, attacker_damage: int) -> int:
        """Apply damage, return effective damage dealt."""
        effective = max(0, attacker_damage - self.defense)
        self.hp -= effective
        return effective

    def reset_tick_state(self) -> None:
        """Clear per-tick ephemeral fields before each new tick."""
        self._intent = "hold"
        self._target_id = None
        self._damage_dealt = 0
        self._action = ""

    def to_dict(self) -> dict:
        """Serialise to a plain dict (used by csv_writer and serializer)."""
        d = {
            "unit_id": self.unit_id,
            "team": self.team,
            "type": self.unit_type,
            "row": self.row,
            "col": self.col,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "alive": self.alive,
        }
        if self.ammo is not None:
            d["ammo"] = self.ammo
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Unit":
        """Reconstruct a Unit from a plain dict (e.g. JSON army config)."""
        from utils.troops_store import get_all_unit_stats  # local import avoids circular

        all_stats = get_all_unit_stats()
        utype = data["type"]
        if utype not in all_stats:
            raise KeyError(f"Unknown unit type: '{utype}'")
        stats = all_stats[utype]
        hp = data.get("hp", stats["hp"])
        return cls(
            unit_id=data["unit_id"],
            team=data["team"],
            unit_type=data["type"],
            row=data["row"],
            col=data["col"],
            hp=hp,
            max_hp=stats["hp"],
            damage=stats["damage"],
            defense=stats["defense"],
            range=stats["range"],
            speed=stats["speed"],
            ammo=data.get("ammo"),
        )
