# BattleCells — Development Plan

## Stack

| Layer | Technology |
|---|---|
| Backend / Simulation | Python 3.x |
| Web Framework | Flask |
| Frontend | HTML + CSS + Vanilla JS |
| Data Output | CSV (per-tick snapshots) |

---

## V1 — MVP Goals

Test and validate core battle mechanics:
- Grid placement and unit occupancy
- Deterministic movement (Advance / Hold)
- Turning behavior (costs 1 tick)
- Range detection and attack phase sequencing
- All 6 battle phases in strict order
- Simultaneous damage application and death resolution
- Barbarian and Archer unit types only (no special behaviors)

No real-time interaction. No video. No randomness.

---

## V1 — Visualization Recommendation

Displaying every tick as a stacked 5×4 table means potentially 30+ tables on one page — hard to read.

**Recommended approach: Tick Stepper (single grid + nav buttons)**

- One 5×4 grid is shown at a time
- Prev / Next buttons step through ticks
- A tick counter displays current position (e.g., `Tick 3 / 17`)
- Grid cells are color-coded: blue = Team A, red = Team B, gray = empty
- Each occupied cell shows: unit type initial + current HP (e.g., `B 8` for Barbarian with 8 HP)
- Below the grid: a short event log for that tick (attacks, deaths, moves)

This is pure HTML + CSS + a small JS snippet — no canvas, no video, no libraries required.
The CSV is still generated for full data export. If you prefer the all-ticks-at-once table view, it can be an optional second tab on the same page.

---

## File Structure

```
app.py                        # Flask entry point, registers blueprints
config.py                     # Grid dimensions, unit base stats, phase order

engine/
  __init__.py
  unit.py                     # Unit dataclass (id, team, type, pos, hp, dmg, def, range, speed, behaviors)
  grid.py                     # Grid state: cell occupancy, bounds checking
  phases/
    __init__.py
    intent.py                 # Phase 1 — evaluate move vs attack intent for each unit
    movement.py               # Phase 2 — resolve simultaneous movement
    targeting.py              # Phase 3 — target selection with tie-break rules
    damage.py                 # Phase 4 — simultaneous damage application
    death.py                  # Phase 5 — remove dead units, free cells
  battle.py                   # Orchestrates all phases per tick, win check (Phase 6)

blueprints/
  __init__.py
  battle_bp.py                # Routes: /setup, /run, /results/<battle_id>

presets/
  default_army.json           # Example pre-configured army for quick testing

utils/
  csv_writer.py               # Writes per-tick unit snapshots to output/battle_log.csv
  serializer.py               # Converts engine state to JSON for Flask → template

templates/
  base.html                   # Shared layout, nav
  setup.html                  # Army placement form (unit type, position, behaviors)
  results.html                # Tick stepper page

static/
  css/
    style.css                 # Grid cell colors, layout, stepper UI
  js/
    tick_viewer.js            # Stores tick snapshots as JSON array, handles prev/next logic

output/
  battle_log.csv              # Generated after each run
```

---

## CSV Schema

One row per unit per tick. Written after each full tick resolves.

| Column | Description |
|---|---|
| `tick` | Tick number (0 = initial state) |
| `unit_id` | Unique unit identifier (e.g., `A_B1`, `B_AR2`) |
| `team` | `A` or `B` |
| `type` | `Barbarian` or `Archer` |
| `row` | Grid row (0–3) |
| `col` | Grid column (0–4) |
| `hp` | Current HP at end of tick |
| `status` | `alive` or `dead` |
| `action` | What the unit did this tick: `move`, `attack`, `blocked`, `dead`, `turn` |
| `target_id` | ID of unit attacked (empty if no attack) |
| `damage_dealt` | Effective damage dealt this tick (0 if no attack) |

---

## API / Route Design

| Route | Method | Description |
|---|---|---|
| `/` | GET | Redirect to `/setup` |
| `/setup` | GET | Army configuration form |
| `/run` | POST | Accepts army JSON, runs full simulation, returns battle ID |
| `/results/<battle_id>` | GET | Renders tick stepper page with all tick data embedded |
| `/download/<battle_id>` | GET | Download the battle CSV |

The simulation runs synchronously on `/run` (V1). The full tick-by-tick state is serialized to JSON and embedded in the results page so the JS stepper needs no further API calls.

---

## Data Flow

```
Setup Form (HTML)
  → POST /run (army JSON)
    → battle.py: runs all ticks
      → csv_writer.py: writes output/battle_log.csv
      → serializer.py: builds tick_data[] JSON array
    → results.html rendered with tick_data embedded
      → tick_viewer.js: stepper reads tick_data[], updates grid + log
```

---

## Unit Base Stats (V1)

| Attribute | Barbarian | Archer |
|---|---|---|
| Cell Occupancy | 1 | 1 |
| HP | 10 | 6 |
| Damage | 1 | 2 |
| Defense | 0 | 0 |
| Range | 1 cell | 3 cells |
| Move Speed | 2 cells/tick | 1 cell/tick |
| Turn Cost | 1 tick | 1 tick |
| Movement Behavior | Advance / Hold | Advance / Hold |
| Attack Behavior | Closest / Lowest HP / Highest HP | Closest / Lowest HP / Highest HP |
| Special Behavior | None (V1) | None (V1) |

**Damage formula:** `Effective Damage = max(0, attacker.damage − target.defense)`

---

## Battle Phase Order (per tick)

1. **Intent Evaluation** — each unit decides: attack if enemy in range, else move (or turn)
2. **Movement Resolution** — simultaneous; blocked if cell occupied or out of bounds
3. **Target Selection** — apply attack behavior rule + deterministic tie-break (distance → fixed ID order)
4. **Damage Application** — all attacks fire simultaneously; HP reduced
5. **Death Resolution** — units with HP ≤ 0 removed; cells freed; deaths logged
6. **Win Check** — if a team has no living units, battle ends; else increment tick and repeat

---

## Build Order

### Phase 0 — Foundation
- [ ] `config.py`: grid size constants, unit stat dictionaries
- [ ] `engine/unit.py`: Unit dataclass
- [ ] `engine/grid.py`: Grid class with occupancy tracking

### Phase 1 — Simulation Engine
- [ ] `engine/phases/intent.py`
- [ ] `engine/phases/movement.py`
- [ ] `engine/phases/targeting.py`
- [ ] `engine/phases/damage.py`
- [ ] `engine/phases/death.py`
- [ ] `engine/battle.py`: tick loop + win check

### Phase 2 — Output
- [ ] `utils/csv_writer.py`
- [ ] `utils/serializer.py`: state → JSON

### Phase 3 — Flask Web Layer
- [ ] `app.py` + `blueprints/battle_bp.py`
- [ ] `templates/setup.html`: army builder form
- [ ] `templates/results.html`: tick stepper shell

### Phase 4 — Frontend Stepper
- [ ] `static/css/style.css`: grid, colors, layout
- [ ] `static/js/tick_viewer.js`: stepper logic, grid render, event log

### Phase 5 — Testing
- [ ] Unit tests for each phase (edge cases: blocked movement, simultaneous kills, tie-breaks)
- [ ] End-to-end test: Barbarians vs Archers preset, verify CSV output

---

## V2 — Upgrade Path (Post-MVP)

- Replace tick stepper with animated auto-battle playback (canvas or CSS transitions)
- Smooth unit movement animation between grid positions
- Speed control (0.5×, 1×, 2×)
- Replay scrubber (seek to any tick)
- Sound effects (optional)
- Special unit behaviors unlocked
- Multiplayer army submission
