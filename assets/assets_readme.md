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
```

## Placement rules

1. Troop art always goes in `troops/...`, never in `buildings/...`.
2. Building art always goes in `buildings/...`.
3. World map location markers/icons (fort, camp, castle) go in `map/locations/...`.
4. Terrain visuals (grass, bushes, trees, pond) go in `map/terrain/...`.
5. Non-entity UI visuals (grid, decoration, frames) go in `ui/...`.

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