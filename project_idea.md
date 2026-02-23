# Project Name: BattleCells

## Description

Grid Tactics Engine is a deterministic, grid-based auto-battler where two teams deploy units on a 5x4 battlefield and watch the outcome unfold without further input. Players configure unit placement and behaviors before battle; the simulation then resolves automatically in discrete ticks, following strict, transparent rules for movement, targeting, and combat. The system supports full battle replays, enabling step-by-step review of every action and outcome. Designed for clarity, fairness, and replayability, Grid Tactics Engine is ideal for strategy enthusiasts and AI competition platforms.

## CORE GAME STRUCTURE
Grid-based battlefield (5*4).
Each team controls one half(5*2).
Units are placed before battle.
No control after submission.
Battle resolves automatically in discrete ticks.
Replay shows precomputed results.
No real-time interaction. No physics. No randomness (for V1).

## UNIT MODEL

Each unit has:
Team
Unique ID
Cell Occupancy (1–3 cells)
Position (grid cells)
Health
Damage
Defense
Range
Movement Speed (cells per tick)
Movement Behavior (Advance / hold)
Attack Behavior (Closest / Lowest HP / Highest HP)
Optional Special Behavior (overrides lower rules)
All stats are deterministic.

## DAMAGE MODEL

Effective Damage = max(0, Attacker Damage − Target Defense)
Damage from both teams is applied simultaneously.
Units die only after the full damage phase of a tick completes.
BATTLE FLOW (PER TICK)
Each tick executes in strict phases.
Order never changes.

### Phase 1 — Intent Evaluation

For every living unit:
Check if enemy in range.
If yes → prepare attack.
If no → prepare movement (based on movement behavior).
Special behaviors override default logic.
Turning (if required to face enemy column) consumes the tick.
No actions are executed yet. Only intentions are recorded.

### Phase 2 — Movement Resolution

Units that intend to move attempt forward movement.
Movement respects:
Grid bounds
Occupied cells
Unit size
If blocked → movement fails.
All valid movements resolve simultaneously.

### Phase 3 — Target Selection
For units attacking:
Identify enemies within range.
Apply attack selection rule:
Closest
Lowest HP
Highest HP
If tie → deterministic tie-break (distance → fixed ID).
Special behaviors may override targeting.

### Phase 4 — Damage Application
All attacks resolve simultaneously.
For each attack:
Compute effective damage.
Subtract from target HP.
No mid-phase removal.

## Phase 5 — Death Resolution

After all damage is applied:
Units with HP ≤ 0 are removed.
Their grid cells are freed.
Deaths logged.

### Phase 6 — Win Check

If one team has no living units:
Battle ends.
Winner declared.
Otherwise:
Increment tick.
Repeat.

## IMPLICIT DEFAULT RULES

Units advance forward by default.
Units may turn left/right if enemy is in adjacent column.
Diagonal attack allowed (if within range).
No retreat unless defined later.
No randomness.
No terrain effects.

## PLAYER FLOW

### Pre-Battle

Place units on grid.
Configure movement + attack behavior.
Submit army.

### Post-Submission

No interaction.
Server simulates full battle.
Replay available.

## REPLAY SYSTEM

Backend produces:
Initial state snapshot.
Full state snapshot per tick (recommended for V1).
Frontend:
Play (auto-advance ticks).
Step forward.
Step backward.
Jump to start/end.
Rendering is playback only. No simulation in frontend.

## Base Troop Specifications (V1)

Attribute	Barbarian (Melee Skirmisher)	Archer (Ranged DPS)

Role	Fast melee pressure	Slow ranged damage
Cell Occupancy	1	1
Health	10	6
Damage	1	2
Defense	0	0
Range (cells)	1	3
Movement Speed	2 cells per tick	1 cell per tick
Can Turn	Yes (costs 1 tick)	Yes (costs 1 tick)
Movement Config	Advance / hold	Advance / hold
Attack Config	Closest / Lowest HP / Highest HP	Closest / Lowest HP / Highest HP
Special Behavior	No(for v1)	No(for v1)


