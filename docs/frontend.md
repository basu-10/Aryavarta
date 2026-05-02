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

### Layout

The map page overrides the default body and `main` container so the document is a fixed-height viewport (`h-screen` on `body`, `min-h-0 flex flex-col` on `main`). The map shell (`#world-map-shell`) and inner scroll surface (`#world-map-scroll`) then take the remaining height as flex items, which keeps document scrolling disabled and confines overflow to the map itself on both desktop and mobile.

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
Clicking a cell fires an HTMX request to `GET /world/item/<type>/<id>`, which returns an HTML partial injected into the popup panel. For forts and monster camps the popup shows an **Attack** link that navigates to the dedicated attack preparation page (`GET /attack/<target_type>/<target_id>`).

### Attack Preparation Page (`/attack/<target_type>/<target_id>`)

A full-page pre-attack UI that replaces the old inline modal. It has three main sections:

1. **Available Troops panel** — lists idle troops stationed at the player's castle and each owned fort. Includes an "Attack From" origin selector.
2. **Saved Formations grid** — all presets are rendered as clickable cards. Each card shows a mini 4×4 battlefield (Team A side only). Clicking a card selects it. Presets created on `/setup` (both teams) and presets created on this page (Team A only) are both listed.
3. **Build a New Formation** — an inline 4-row × 4-col Team A grid. Click any cell to open the troop-picker modal. The built formation can be used directly for the attack, or saved as a named preset (stored in `presets/<name>.json` with `army_b: []`).

After selecting a formation (either a saved preset or a freshly built one) the player clicks **Launch Attack!** which calls `POST /api/attack` and immediately redirects to `/results/<battle_id>`.

Alpine.js `attackPrep()` component manages all selection, builder, and attack dispatch logic client-side.

The map JSON is refreshed every 10 seconds via a `setInterval` in `templates/world/map.html`.

### Map zoom (inside the map)

Zoom controls are overlaid at the top-left corner of the map shell:
- `−` and `+` buttons,
- a reset button that displays the current level and resets to `100%`,
- a range slider (hidden on narrow screens),
- optional `Ctrl + mouse wheel` zoom while hovering the map.

Default zoom is **60 %** on mobile (< 640 px wide) and **100 %** on desktop.

### Scroll helpers

Four directional buttons (▲▼◀▶) are positioned at the edges of the map shell. Holding one triggers a `setInterval` that calls `scrollBy` at 130 px per 40 ms tick, allowing fast navigation. Releasing the pointer (or the button leaving the element) stops the interval.

Scrollbars are 8 px wide/tall (2× the default) and styled to match the dark theme.

---

## Global floating chat panel

A 💬 FAB (floating action button) fixed at `bottom-6 right-6` is rendered in `base.html` for every logged-in page. Clicking it toggles a `360 × 480 px` panel with three tabs:

| Tab | Endpoint polled | Interval |
|---|---|---|
| 🌍 World | `/api/world/chat` | 5 s |
| ✉ DM | `/api/dm/inbox` | 8 s |
| ⚔ Clan | `/api/clan/<id>/chat` | 5 s (only shown when player has a clan) |

The DM tab has two sub-views: the inbox list and a conversation view (with a ← Back button). Opening a conversation from any context (world chat name click, recruitment action, etc.) calls `openDmPanel()`, which is global.

An unread-DM badge is polled every 10 s and appears on both the FAB and the DM tab label.

The player context menu (🏰 Visit Castle, 📍 See on Map, ✉ Send Message, 📣 Send Recruitment) is also rendered globally in `base.html` and triggered by clicking a username in the World Chat pane. "See on Map" calls `scrollGridToCell()` if it is defined (map page only), otherwise navigates to `/world`.

---

## HTMX polling intervals

| Feature | Endpoint | Interval | Trigger |
|---|---|---|---|
| Clan applications | `/api/clan/<id>/applications` | 5 s | `hx-trigger="every 5s"` |
| Resource bars | `/api/fort/<id>/resources`, `/api/castle/resources` | 5 s | `hx-trigger="every 5s"` |
| Active missions countdown | `/api/battles/active` | 5 s | `hx-trigger="every 5s"` |
| World map | `/api/world/map` (JS fetch) | 10 s | `setInterval` |

---

## Clan tabbed interface

The clan hub (`/clan`) renders one of two views depending on whether the player is currently in a clan.

### Non-member view
- **Create** form: shows the resource cost (1000 ×4) and submits to `POST /api/clan/create` via Alpine `createClan()`.
- **All clans** list: each clan card shows member count and a per-card **Apply** button (calls `applyClan(id)`).
- **Search box**: client-side filter on clan name.

### Member view
The member view wraps five tabs managed by an Alpine `clanHub()` component:

| Tab | Contents | HTMX polling |
|---|---|---|
| Chat | Message list + send box | `every 3s` → `/api/clan/<id>/chat?since=<clan_joined_at>` |
| Members | Role-badged list; promote/demote/kick for eligible actors | — |
| Info | Description (editable by Leader/Co-leader), founded date, member count | — |
| Applications | Pending applicant list with Accept / Reject; only shown for Elder+ | `every 5s` → `/api/clan/<id>/applications` |
| Attacks | Placeholder for future clan war feature | — |

The header bar shows: clan name, the player's own role badge, member count, **Leave** button, and a notification bell.

---

## Battle history navigation

The results page (`/results/<battle_id>`) now includes ◀ (previous) and ▶ (next) navigation controls.

- `GET /results/<id>?prev=1` and `GET /results/<id>?next=1` resolve the adjacent battle in the list sorted by file modification time.
- Navigation wraps around (last battle → first; first battle → last).
- A counter (`N / total`) shows the current position in the full history.
- `list_battles_sorted()` in `utils/battle_store.py` returns all battle IDs ordered by file mtime.

---

## Battle results battlefield

The tick-by-tick replay viewer on the results page uses the same visual style as the battle setup page:

- **Cell classes**: `bc-cell-a` (Team A columns 0–3), `bc-cell-neutral` (column 4), `bc-cell-b` (Team B columns 5–8).
- **Cell size**: fluid — cells use `flex: 1` and `aspect-ratio: 1/1` so the grid stretches to full page width with 20 px padding on each side.
- **Neutral detection**: `isNeutral(col)` in `static/js/tick_viewer.js` checks `col === 4`.
- Troop sprites and a legend are shown the same way as on the setup page.
- **Troop Actions log**: Replaces the old "Unit Status" table and "Tick Log". Shows one line per event (attack, move, blocked, death) for the current tick with attacker type, position, target type, position, damage dealt, and HP change.

---

## Wiki

The wiki replaces the former Troopedia at a new URL hierarchy under `/wiki/`.

| Page | URL | Description |
|---|---|---|
| Landing | `/wiki/` | Two entry cards: Troops and Buildings |
| Troops | `/wiki/troops` | Filterable list of all troop types with stats |
| Buildings | `/wiki/buildings` | Four category sections: Resource, Military, Defence, Special |
| Troop detail | `/wiki/troops/<slug>` | Full stat card for a single troop type |

- Data is sourced from the reference tables seeded by `db/ref_seeder.py` (no extra files).
- Nav link in `base.html` reads "Wiki" (was "Troopedia").

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

