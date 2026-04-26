# Frontend

## Library choices

### HTMX 1.9.12 (CDN)
Used for all server-driven partial updates. No custom JS fetch calls are needed for standard CRUD interactions. This keeps the JS footprint near zero and all rendering server-side.

Loaded from CDN in `base.html`; no local build step.

### Alpine.js 3.x (CDN)
Used for:
- The attack panel on the world map (formation builder).
- The battle simulator troop selection modal (setup page).
- Local toggle/show/hide interactions.

Chosen over Vue/React because:
- No build step or bundler needed.
- Fits naturally alongside HTMX (Alpine handles local UI state; HTMX handles server communication).
- Entire library loads in ~15 KB.

### Tailwind CSS (CDN)
Utility-first CSS loaded from CDN. No PostCSS/PurgeCSS step needed for a project at this scale.

---

## World map

The world map is rendered as a CSS grid (`#world-grid`) of clickable cells. The browser fetches a JSON snapshot from `GET /api/world/map`, then rebuilds the grid DOM with per-cell colours and SVG location markers.

### Asset organization reference

UI and map visuals are stored in `assets/theme1` using an entity-first structure:
- `troops/<faction>/<variant>/...` for unit visuals (for example `full` and `map-icons`).
- `buildings/<category>/...` for structure visuals.
- `map/locations/...` and `map/terrain/...` for world-map visuals.
- `ui/command-centre/...` for non-entity fort/castle UI visuals.

See `assets/assets_readme.md` for exact folder rules.

### Colour coding

| Entity | Colour |
|---|---|
| Player's own castle | Blue |
| Player's own fort | Green |
| Enemy fort (other player) | Red |
| Monster fort (unowned) | Orange |
| Monster camp | Purple |
| Empty | Light grey |

### World map asset wiring

- Base terrain tile per world cell: `/assets/theme1/map/terrain/grass.svg`.
- Entity markers: `/assets/theme1/map/locations/castle.svg`, `/assets/theme1/map/locations/fort.svg`, `/assets/theme1/map/locations/monster-camp.svg`.

### Interaction
Clicking a cell fires an HTMX request to `GET /world/item/<type>/<id>`, which returns an HTML partial injected into the popup panel. The popup contains an attack button that mounts the Alpine `attackPanel()` component.

When attacking from the popup, the selected preset name is sent to `POST /api/attack` as `preset_name`. The server loads that preset file and derives Team A formation from `army_a`, so the selected preset is the authoritative source for units sent.

The map JSON is refreshed every 10 seconds via a `setInterval` in `templates/world/map.html`.

### Map zoom

The world map now supports client-side zoom controls in the map header:
- `+` and `-` buttons,
- a range slider,
- a reset button that returns to `100%`,
- optional `Ctrl + mouse wheel` zoom while hovering the map.

Zoom updates world-cell size and marker size without changing server APIs.

---

## HTMX polling intervals

| Feature | Endpoint | Interval | Trigger |
|---|---|---|---|
| Clan chat | `/api/clan/<id>/chat` | 3 s | `hx-trigger="every 3s"` |
| Resource bars | `/api/fort/<id>/resources`, `/api/castle/resources` | 5 s | `hx-trigger="every 5s"` |
| Active missions countdown | `/api/battles/active` | 5 s | `hx-trigger="every 5s"` |
| World map | `/api/world/map` (JS fetch) | 10 s | `setInterval` |

---

## Castle and fort management UI

The location page (`/castle` and `/fort/<id>`) uses a click-to-manage building panel.

- Castle view renders building slots as a fixed 3x3 grass grid.
- Buildings are overlaid on top of each grass tile and remain click-to-manage.
- Empty unlocked tiles expose the Build action; locked tiles are shown as locked when slot count is below 9.
- Fort view keeps the existing slot card layout.

- Clicking `Command Centre` opens a troop details table (unit count + core stats).
- Clicking `Garrison (Barracks)` or `Stable` opens troop management:
	- queue troop training,
	- view active queue length and current countdown,
	- dismiss troops with immediate partial refund,
	- upgrade building.
- Clicking `Cannon` or `Archer Tower` opens defense management:
	- upgrade building,
	- load ammo in bulk,
	- view loaded ammo count and per-ammo resource cost.

### Why the castle page previously appeared frozen

The page could appear unusable because a completed building timer could still be present in `build_complete_at`, causing repeated auto-reloads on every second tick. The current behavior clears expired `build_complete_at` values server-side before rendering, so the page only reloads once when needed.

### Resource bar polling detail

The location header HTMX targets now return rendered HTML partials (`fort/_header_cards.html`) rather than JSON, matching `hx-swap="innerHTML"` expectations.

The header shows two adjacent cards:
- Uncollected resource totals (food/timber/gold/metal) for the current location.
- Troop totals currently stationed at the current location.

### Owned forts on castle page

The castle page includes an `Owned Forts` card grid with per-fort summary details:
- garrisoned troop count,
- world-map position,
- distance from castle,
- uncollected resource total (red/green highlight),
- training queue count (red/green highlight).

### Fort/castle asset wiring

- Building overlays use SVGs from `/assets/theme1/buildings/...`.
- Castle slot backgrounds use `/assets/theme1/map/terrain/grass.svg`.
- Troop rows use map icons from `/assets/theme1/troops/<faction>/map-icons/...`.
- The Command Centre troop table overlays `/assets/theme1/ui/command-centre/grid.svg`.

---

## Battle simulation and replay asset wiring

- Setup page (`/setup`):
   - Unit cells and Add Troop modal use troop map-icons for both human and monster factions.
   - Grid area overlays `/assets/theme1/ui/battlefield/grid.svg`.
- Replay page (`/results/<id>`):
   - Battlefield cells render troop map-icons instead of initials when icon mapping exists.
   - Replay grid overlays `/assets/theme1/ui/battlefield/grid.svg`.

### Troop GIF animations

- Animated action GIFs are stored under `assets/theme1/troops/human/animations/<troop>/`.
- Current animated troops: `archer`, `barbarian`.
- Action files used: `idle.gif`, `walk.gif`, `attack.gif`, `hurt.gif`, `death.gif`.
- Setup page (`/setup`) uses `idle` animations for in-cell previews and troop-picker cards.
- Replay page (`/results/<id>`) switches animation per unit state:
   - `attack` when unit action is attack,
   - `walk` when unit action is move,
   - `hurt` when HP decreases between ticks,
   - `death` when unit status is dead,
   - `idle` otherwise.
- Troopedia (`/troopedia`) card grid and troop detail hero cycle all five actions in sequence for animated troops.

---

## Client-side mission resolution

The browser is responsible for triggering battle resolution when a mission's travel timer expires. The flow:

1. `/api/battles/active` returns JSON with `mission_id` and `seconds_remaining`.
2. The partial template renders a countdown using the value from the server.
3. When `seconds_remaining ≤ 0`, the browser calls `POST /api/missions/resolve?mission_id=<id>`.
4. The server re-checks `arrive_time ≤ now` before processing; it rejects early calls.

This eliminates the need for background workers. The server is always the authority; the client merely knows when to ask.

---

## Battles history page (`/battles`)

- The profile page has been removed and replaced by a dedicated battles history page.
- `/battles` shows recent resolved missions for the logged-in player in a table (arrival time, target, outcome, replay link).
- Replay links continue to open the existing per-battle viewer at `/results/<battle_id>`.
- Navbar `Battles` now points directly to `/battles`.

---

## Battle simulator (`/setup`)

The battle simulator page allows players to build custom armies by placing units on a grid, then running simulations to test formations.

### Troop selection modal

When a player clicks any grid cell (Team A or Team B zone), a modal opens for troop selection:

**Modal structure:**
- **Header**: Shows the cell position (row, col).
- **Current troop display** (if cell is occupied):
  - Shows the troop type with all stats (HP, DMG, DEF, RNG, SPD).
  - Includes a "Delete" button to remove the unit.
  - Only shown when editing an existing unit.
- **Troop categories**: Troops are grouped by:
  - **Faction**: Human vs Monster (defined in `config.UNIT_CLASSIFICATION`).
  - **Type**: Melee (range ≤ 1) vs Ranged (range > 1).
- **Troop cards**: Each card shows the troop name and stat summary in a grid format.
- **Cancel button**: Always present to close the modal without changes.

### Multi-troop placement

Cells can now contain **multiple troops** of the same team. The UI adapts based on cell occupancy:

- **Single unit**: Grid shows troop visual directly on the battlefield image.
- **Multiple units**: Grid shows a **yellow badge** with the count (e.g., "3 units").
- **Current Troops section**: Displays all troops in the cell with individual "Remove" buttons for each.
- **Add Troop to Cell section**: Always available to stack more troops onto the same cell.

The battlefield grid is now rendered as a transparent click-overlay on top of the battlefield image:
- placement cells use no colored borders,
- empty deployable cells show a `+` marker,
- controls (load preset, preset name, save preset, run battle) are placed directly below the battlefield.

### Data flow

1. Frontend passes `UNIT_CLASSIFICATION` dict to the modal from the setup route (`battle_bp.py`).
2. `unitMap` now stores arrays: `unitMap["r,c"] = [unit1, unit2, ...]` instead of a single unit.
3. Helper methods:
   - `getUnitCount(r, c)`: Returns count of units in a cell.
   - `getUnits(r, c)`: Returns array of all units in a cell.
   - `getUnit(r, c)`: Returns first unit (for backward compatibility).
4. Selecting a troop calls `selectTroop(troopName)`, which:
   - **Adds** a new unit to the cell array (does not replace).
   - Updates modal display with the new unit.
   - Rebuilds the army summaries.
5. Deleting a specific troop via `deleteSpecificTroop(unit_id)`:
   - Removes only that unit from the array.
   - Cleans up empty arrays when a cell becomes vacant.
   - Rebuilds armies.
6. On load/preset load, the array structure is initialized: `unitMap[key] = [unit1, unit2, ...]`.

### Army totals panel

The dual per-unit list has been replaced with total counters only:
- Team A total units,
- Team B total units.

### Custom troops

If custom troops are saved via the troops page (`/troops`), they are:
1. Loaded from `troops/custom_troops.json`.
2. Merged with built-in units by `get_all_unit_stats()`.
3. Auto-classified as **human** faction with type inferred from **range** (if not in `UNIT_CLASSIFICATION`).
4. Available in the modal alongside built-in troops.

