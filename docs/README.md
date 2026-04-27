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

### Full clan system
Clans are now fully implemented with role hierarchy, join applications, recruitment DMs, a tabbed member UI, and description management. See [game-mechanics.md](game-mechanics.md#clans).

### Wiki (replaces Troopedia)
The `/troopedia` route has been replaced by a full wiki at `/wiki/`. The landing page links to sub-pages for Troops (`/wiki/troops`) and Buildings (`/wiki/buildings`). Individual troop detail pages remain at `/wiki/troops/<slug>`.

### Battle history navigation
The battle results page (`/results/<id>`) now has ◀ / ▶ navigation buttons to cycle through all saved battles, with a `N/total` position counter.

### Battle results battlefield
The replay battlefield on the results page now uses the same visual style as the battle setup page — coloured team columns (`bc-cell-a`, `bc-cell-b`, `bc-cell-neutral`), 80 × 80 px cells, troop sprites, and a legend.
