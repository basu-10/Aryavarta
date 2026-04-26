# Assets Guide

This folder uses an entity-first structure. Keep art with the game object it represents, then split by usage variant (`full`, `map-icons`, etc.).

## Current structure

```text
assets/
	assets_readme.md
	theme1/
		troops/
			human/
				full/
				map-icons/
					animations/
						archer/
						barbarian/
			monster/
				full/
				map-icons/
		buildings/
			resource/
			military/
			defense/
			default/
		map/
			locations/
			terrain/
		ui/
			command-centre/
			battlefield/
```

## Placement rules

1. Troop art always goes in `troops/...`, never in `buildings/...`.
2. Building art always goes in `buildings/...`.
3. World map location markers/icons (fort, camp, castle) go in `map/locations/...`.
4. Terrain visuals (grass, bushes, trees, pond) go in `map/terrain/...`.
5. Non-entity UI visuals (grid, decoration, frames) go in `ui/...`.
6. Animated troop actions go in `troops/<faction>/animations/<troop>/<action>.gif`.

### Grid assets

- Building placement grid: `assets/theme1/ui/command-centre/grid.svg` (3x3)
- Battlefield combat grid: `assets/theme1/ui/battlefield/grid.svg` (4x9 with center no-man's-land column)
- World map terrain base tile: `assets/theme1/map/terrain/grass.svg` (single-cell tile mapped to each map cell)

### Tile-map design notes

- World cells are tile-first: each cell gets a base terrain tile (grass) before entity overlays.
- Entity visuals (fort/camp/castle/terrain props) are layered on top of the base tile.
- This supports future theme switching by swapping tile-set mappings rather than rewriting map logic.

## Your Troll/Wraith question

`Troll` and `Wraith` are monster troops, so their source files belong in:

- `assets/theme1/troops/monster/full/`

If they are also shown as mini icons on the world map, keep map-sized versions in:

- `assets/theme1/troops/monster/map-icons/`

If dedicated icon art does not exist yet, reuse/copy the `full` version temporarily.

## Naming convention

- Use lowercase kebab-case filenames: `archer-tower.svg`, `monster-camp.svg`.
- Keep one file per visual variant per entity.
- Do not encode game logic in filenames; only visual identity and variant.

## Content reference

Troop/unit IDs come from `config.py` (`UNIT_STATS`) and world seeding.
Building IDs come from `config.py` (`BUILDING_*` dictionaries).