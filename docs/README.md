# BattleCells World — Design Documentation

This folder records the key design decisions made during the game's construction.
Each file covers one concern area and explains *why* choices were made, not just *what* was built.

| File | Topic |
|---|---|
| [architecture.md](architecture.md) | Tech stack, request lifecycle, blueprint layout |
| [data-model.md](data-model.md) | Database schema choices and trade-offs |
| [game-mechanics.md](game-mechanics.md) | Combat, travel, capture, resources, clan system |
| [units-and-buildings.md](units-and-buildings.md) | All unit types, building types, production rates |
| [frontend.md](frontend.md) | HTMX polling strategy, Alpine.js, world map, battle results, wiki |
| [admin-and-auth.md](admin-and-auth.md) | Session auth, roles, admin bootstrap, and admin test harness |

---

## Recent changes (April 2026)

### Floating global chat panel
A persistent 💬 floating button (bottom-right) is available on all pages for logged-in players. Clicking it opens a tabbed chat panel with:
- **🌍 World Chat** — global chat (moved from the world map page)
- **✉ DM** — direct messages inbox + conversation view (consolidated from the old fixed bottom panel on the map)
- **⚔ Clan Chat** — clan channel (tab only shown when the player is in a clan; removed from the clan page tabs)

The player context menu (visit castle, see on map, send DM, recruit) is now globally available from world chat name clicks.

### World map improvements
- **Responsive full-height layout**: the map now fills the entire viewport height below the navbar (`calc(100dvh - 52px)`). The `main` container has no padding on the map page.
- **Zoom controls moved inside the map**: the −/100%/+ buttons and range slider are overlaid at the top-left of the map shell.
- **Mobile-aware default zoom**: starts at 60% zoom on small screens (< 640 px wide) so more of the map is visible.
- **Thick scrollbars**: `#world-map-scroll` uses 8 px scrollbars (2× the previous 4 px).
- **Scroll helper buttons**: four directional overlay buttons (▲▼◀▶) are placed at the map edges; holding them continuously scrolls the map at 130 px / 40 ms.

### Clan page — chat tab removed
The 💬 Chat tab has been removed from the clan page. Clan chat is now accessed via the global floating chat panel.

### Landing page is now the default `/`
The root route now opens a dedicated landing page for guests, while authenticated users opening `/` are redirected to `/world`.

### Cross-tab re-authentication after session loss
Auth now uses a server-side remember token (`bc_remember` cookie + `auth_remember_token` table). If Flask session data is lost (for example after a server restart), logging in once restores access across other tabs on refresh without re-entering credentials in each tab.

### Full clan system
Clans are now fully implemented with role hierarchy, join applications, recruitment DMs, a tabbed member UI, and description management. See [game-mechanics.md](game-mechanics.md#clans).

### Wiki (replaces Troopedia)
The `/troopedia` route has been replaced by a full wiki at `/wiki/`. The landing page links to sub-pages for Troops (`/wiki/troops`) and Buildings (`/wiki/buildings`). Individual troop detail pages remain at `/wiki/troops/<slug>`.

### Battle history navigation
The battle results page (`/results/<id>`) now has ◀ / ▶ navigation buttons to cycle through all saved battles, with a `N/total` position counter.

### Battle results battlefield
The replay battlefield on the results page now uses the same visual style as the battle setup page — coloured team columns (`bc-cell-a`, `bc-cell-b`, `bc-cell-neutral`), 80 × 80 px cells, troop sprites, and a legend.
