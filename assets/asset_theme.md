# Theme Switching System

## Overview

The world map uses a **theme-switching system** that allows instant visual customization without restarting the server. Currently, two themes are available:

- **theme1**: Green grass (original)
- **theme2**: Brown grass (desert/autumn variant)

---

## How It Works

### 1. **Configuration** (`config.py`)

```python
ACTIVE_THEME = "theme1"  # The currently active theme
AVAILABLE_THEMES = ["theme1", "theme2"]  # All available themes
```

- Admin can switch themes from the admin panel
- The setting is **in-memory** (persists until server restart) — perfect for dev

### 2. **Backend Render** (`blueprints/world_bp.py`)

When loading the world map, the Flask view passes the active theme to the template:

```python
@world_bp.route("/world")
def world_map():
    return render_template("world/map.html",
                           world_w=config.WORLD_GRID_W,
                           world_h=config.WORLD_GRID_H,
                           active_theme=config.ACTIVE_THEME)  # ← Pass current theme
```

### 3. **Frontend Rendering** (`templates/world/map.html`)

The JavaScript receives the theme name and maps it to SVG asset URLs:

```javascript
const TILESETS = {
  theme1: { grass: "/assets/theme1/map/terrain/grass.svg" },
  theme2: { grass: "/assets/theme2/map/terrain/grass.svg" }
};

const ACTIVE_TILESET_KEY = '{{ active_theme }}';  // ← Jinja2 template variable

function tileUrl(tileId) {
  const set = TILESETS[ACTIVE_TILESET_KEY] || TILESETS.theme1;
  return set[tileId] || set[BASE_TILE_ID];
}

function cellStyle(overlayColor) {
  const tile = tileUrl(BASE_TILE_ID);
  // Each cell uses the background-image pointing to the current theme's grass SVG
  return `width:26px;height:26px;background-image:url(${tile});...`;
}
```

Each map cell's background is set dynamically using `cellStyle()`, which looks up the URL via `tileUrl()`.

### 4. **Admin Control** (`blueprints/admin_bp.py`)

A POST endpoint changes the active theme:

```python
@admin_bp.route("/set-theme/<theme_name>", methods=["POST"])
@admin_required
def set_theme(theme_name: str):
    if theme_name not in config.AVAILABLE_THEMES:
        return jsonify({"ok": False, "error": f"Theme '{theme_name}' not found."}), 400
    config.ACTIVE_THEME = theme_name  # ← Update global config
    return jsonify({"ok": True, "active_theme": config.ACTIVE_THEME})
```

### 5. **Admin Dashboard** (`templates/admin/dashboard.html`)

The admin panel displays a theme selector with buttons. Clicking a button:

1. Calls `switchTheme(themeName)` JavaScript function
2. POSTs to `/admin/set-theme/{themeName}`
3. Reloads the page to fetch the new theme

```javascript
async function switchTheme(themeName) {
  const r = await fetch(`/admin/set-theme/${themeName}`, { method: 'POST' });
  const j = await r.json();
  if (j.ok) {
    location.reload();  // Reload to apply theme instantly
  } else {
    alert(`Failed to switch theme: ${j.error}`);
  }
}
```

---

## File Structure

```
assets/
├── theme1/
│   └── map/terrain/
│       └── grass.svg          ← Green gradient + highlights
├── theme2/
│   └── map/terrain/
│       └── grass.svg          ← Brown gradient + highlights
```

### Grass Color Palettes

**theme1 (Green):**
- Gradient: `#63b152` → `#4e9844`
- Highlights: `#73c363`
- Strokes: `#89d676`

**theme2 (Brown):**
- Gradient: `#8b6f47` → `#6d5a3f`
- Highlights: `#a0845a`
- Strokes: `#9d7a54`

---

## Customization Guide

### Adding a New Theme

1. **Create folder:**
   ```
   assets/theme3/
   └── map/terrain/
       └── grass.svg
   ```

2. **Add to config:**
   ```python
   AVAILABLE_THEMES = ["theme1", "theme2", "theme3"]
   ```

3. **Register in world/map.html TILESETS:**
   ```javascript
   const TILESETS = {
     theme1: { grass: "/assets/theme1/map/terrain/grass.svg" },
     theme2: { grass: "/assets/theme2/map/terrain/grass.svg" },
     theme3: { grass: "/assets/theme3/map/terrain/grass.svg" }  // ← New
   };
   ```

4. **Create SVG** with custom colors for `grass.svg`

### Modifying Grass Colors

Edit the SVG file (e.g., `assets/theme2/map/terrain/grass.svg`):

```xml
<defs>
  <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#YOUR_COLOR_1" />
    <stop offset="100%" stop-color="#YOUR_COLOR_2" />
  </linearGradient>
</defs>
```

Update color hex codes to your palette. The theme will apply instantly when users reload the map.

---

## Instant vs. Persisted

- **Current behavior**: Theme change is instant in-memory (`config.ACTIVE_THEME`)
- **Production approach** (if needed):
  - Store in database table `settings` (key='active_theme', value='theme1')
  - Load at app startup: `config.ACTIVE_THEME = db.get_setting('active_theme')`
  - Update endpoint writes to DB as well as config

---

## Testing

1. **Admin panel:** Go to `/admin/` → Click theme button
2. **World map:** Navigate to `/world` → Should show the new grass tile
3. **Multiple browsers:** Theme change affects all connected users (after reload)

---

## Notes

- Assets are served from `/assets/` (Flask static folder)
- Each 26×26 grass tile is repeated across the 50×50 grid via CSS background-repeat
- Theme switching is instant; users see the new tileset on page reload
- For production, consider persisting theme choice to a database or config file
