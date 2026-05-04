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
    pool_a_initial: int = 0              # Team A HP pool at battle start
    pool_b_initial: int = 0              # Team B HP pool at battle start
    pool_a_hp: int = 0                   # Team A HP pool at battle end
    pool_b_hp: int = 0                   # Team B HP pool at battle end
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

        # HP Pools — each side's base is defended.  Computed as the average of
        # both teams' total HP (gives a balanced, scaling target for all army sizes).
        total_hp_a = sum(u.hp for u in army_a)
        total_hp_b = sum(u.hp for u in army_b)
        pool_init = max(1, (total_hp_a + total_hp_b) // 2)
        self.pool_a_hp: int = pool_init   # Team B must reduce this to win via pool
        self.pool_b_hp: int = pool_init   # Team A must reduce this to win via pool
        self._pool_a_initial: int = pool_init
        self._pool_b_initial: int = pool_init

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
                    pool_a_initial=self._pool_a_initial,
                    pool_b_initial=self._pool_b_initial,
                    pool_a_hp=self.pool_a_hp,
                    pool_b_hp=self.pool_b_hp,
                    ticks=ticks,
                    all_units=self.units,
                )

        # Reached MAX_TICKS — declare draw
        return BattleResult(
            winner="Draw",
            total_ticks=config.MAX_TICKS,
            pool_a_initial=self._pool_a_initial,
            pool_b_initial=self._pool_b_initial,
            pool_a_hp=self.pool_a_hp,
            pool_b_hp=self.pool_b_hp,
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
        evaluate_intents(self.units, self.pool_a_hp, self.pool_b_hp)

        # Record pre-movement positions for action logging
        pre_move_pos: dict[str, tuple[int, int]] = {
            u.unit_id: u.pos for u in self.units if u.is_alive()
        }

        # --- Phase 2: Movement Resolution ---
        resolve_movement(self.units, self.grid)

        # Log movement events (covers both 'move' and 'retreat' intents)
        for unit in self.units:
            if unit.is_alive() and unit._intent in ("move", "retreat"):
                if unit.pos != pre_move_pos.get(unit.unit_id):
                    unit._action = unit._intent  # 'move' or 'retreat'
                    events.append(
                        {
                            "type": unit._intent,
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

        # --- Phase 4: Damage Application (units + HP pools) ---
        dmg_events, pool_dmg = apply_damage(self.units)
        for ev in dmg_events:
            events.append({"type": "attack", **ev})

        # Apply pool damage (units with attack_pool intent hit the opposing pool)
        if pool_dmg["A"] > 0:
            self.pool_a_hp = max(0, self.pool_a_hp - pool_dmg["A"])
            events.append({"type": "pool_attack", "target_pool": "A", "damage": pool_dmg["A"],
                           "pool_hp": self.pool_a_hp})
        if pool_dmg["B"] > 0:
            self.pool_b_hp = max(0, self.pool_b_hp - pool_dmg["B"])
            events.append({"type": "pool_attack", "target_pool": "B", "damage": pool_dmg["B"],
                           "pool_hp": self.pool_b_hp})

        # --- Phase 5: Death Resolution ---
        dead_ids = resolve_deaths(self.units, self.grid)
        for uid in dead_ids:
            events.append({"type": "death", "unit_id": uid})

        return events

    def _check_winner(self) -> Optional[str]:
        """Return winner team ('A'/'B'), 'Draw', or None if battle continues."""
        # HP pool win condition — whoever's pool hits 0 loses
        if self.pool_a_hp <= 0 and self.pool_b_hp <= 0:
            return "Draw"
        if self.pool_a_hp <= 0:
            return "B"
        if self.pool_b_hp <= 0:
            return "A"

        # Unit-elimination win condition
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
            "pool_a_hp": self.pool_a_hp,
            "pool_b_hp": self.pool_b_hp,
            "pool_a_initial": self._pool_a_initial,
            "pool_b_initial": self._pool_b_initial,
        }
