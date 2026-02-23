"""
battle.py — Battle Orchestrator

Drives the full simulation loop, executing all 6 phases per tick in strict order:

  1. Intent Evaluation  (intent.py)
  2. Movement Resolution (movement.py)
  3. Target Selection   (targeting.py)
  4. Damage Application (damage.py)
  5. Death Resolution   (death.py)
  6. Win Check          (this module)

Usage:
    from engine.battle import Battle
    b = Battle(army_a, army_b)
    result = b.run()

`result` is a BattleResult with:
  - winner     : 'A' | 'B' | 'Draw'
  - ticks      : list of TickSnapshot dicts
  - all_units  : final unit states
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Optional

import config
from engine.grid import Grid
from engine.unit import Unit
from engine.phases.intent import evaluate_intents
from engine.phases.movement import resolve_movement
from engine.phases.targeting import resolve_targeting
from engine.phases.damage import apply_damage
from engine.phases.death import resolve_deaths


@dataclass
class BattleResult:
    winner: str                          # 'A', 'B', or 'Draw'
    total_ticks: int
    ticks: list[dict] = field(default_factory=list)   # list of TickSnapshot dicts
    all_units: list[Unit] = field(default_factory=list)


class Battle:
    """
    Encapsulates one complete battle simulation.

    Parameters
    ----------
    army_a, army_b : lists of Unit objects (already configured)
    grid           : optional pre-built Grid; constructed from config if omitted
    """

    def __init__(
        self,
        army_a: list[Unit],
        army_b: list[Unit],
        grid: Optional[Grid] = None,
    ) -> None:
        self.grid = grid or Grid(config.GRID_ROWS, config.GRID_COLS)
        self.units: list[Unit] = army_a + army_b
        self._place_units()

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def run(self) -> BattleResult:
        """Execute the full battle and return a BattleResult."""
        ticks: list[dict] = []

        # Tick 0 — initial state snapshot (before anything happens)
        ticks.append(self._snapshot(tick=0, events=[]))

        for tick_num in range(1, config.MAX_TICKS + 1):
            events = self._run_tick(tick_num)
            ticks.append(self._snapshot(tick=tick_num, events=events))

            winner = self._check_winner()
            if winner is not None:
                return BattleResult(
                    winner=winner,
                    total_ticks=tick_num,
                    ticks=ticks,
                    all_units=self.units,
                )

        # Reached MAX_TICKS — declare draw
        return BattleResult(
            winner="Draw",
            total_ticks=config.MAX_TICKS,
            ticks=ticks,
            all_units=self.units,
        )

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _place_units(self) -> None:
        """Register all units on the grid. Raises ValueError if a cell is blocked."""
        for unit in self.units:
            if not self.grid.place(unit.unit_id, unit.row, unit.col):
                raise ValueError(
                    f"Cannot place {unit.unit_id} at ({unit.row},{unit.col}): "
                    "cell is occupied or out of bounds."
                )

    def _run_tick(self, tick_num: int) -> list[dict]:
        """Execute phases 1-5 for one tick. Returns event list."""
        events: list[dict] = []

        # --- Phase 1: Intent Evaluation ---
        evaluate_intents(self.units)

        # Record pre-movement positions for action logging
        pre_move_pos: dict[str, tuple[int, int]] = {
            u.unit_id: u.pos for u in self.units if u.is_alive()
        }

        # --- Phase 2: Movement Resolution ---
        resolve_movement(self.units, self.grid)

        # Log movement events
        for unit in self.units:
            if unit.is_alive() and unit._intent == "move":
                if unit.pos != pre_move_pos.get(unit.unit_id):
                    unit._action = "move"
                    events.append(
                        {
                            "type": "move",
                            "unit_id": unit.unit_id,
                            "from": list(pre_move_pos[unit.unit_id]),
                            "to": list(unit.pos),
                        }
                    )
                else:
                    unit._action = "blocked"
                    events.append(
                        {
                            "type": "blocked",
                            "unit_id": unit.unit_id,
                            "pos": list(unit.pos),
                        }
                    )

        # --- Phase 3: Target Selection ---
        resolve_targeting(self.units)

        # --- Phase 4: Damage Application ---
        dmg_events = apply_damage(self.units)
        for ev in dmg_events:
            events.append({"type": "attack", **ev})

        # --- Phase 5: Death Resolution ---
        dead_ids = resolve_deaths(self.units, self.grid)
        for uid in dead_ids:
            events.append({"type": "death", "unit_id": uid})

        return events

    def _check_winner(self) -> Optional[str]:
        """Return winner team ('A'/'B'), 'Draw', or None if battle continues."""
        living_a = any(u.team == "A" and u.is_alive() for u in self.units)
        living_b = any(u.team == "B" and u.is_alive() for u in self.units)

        if living_a and living_b:
            return None   # battle continues
        if living_a:
            return "A"
        if living_b:
            return "B"
        return "Draw"

    def _snapshot(self, tick: int, events: list[dict]) -> dict:
        """Build a tick snapshot dict for the frontend stepper and CSV writer."""
        units_state = []
        for u in self.units:
            state = u.to_dict()
            state["status"] = "alive" if u.alive else "dead"
            state["action"] = u._action if u._action else ("dead" if not u.alive else "hold")
            state["target_id"] = u._target_id or ""
            state["damage_dealt"] = u._damage_dealt
            units_state.append(state)

        return {
            "tick": tick,
            "units": units_state,
            "events": events,
        }
