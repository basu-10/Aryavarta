# Frontend

## Library choices

### HTMX 1.9.12 (CDN)
Used for all server-driven partial updates. No custom JS fetch calls are needed for standard CRUD interactions. This keeps the JS footprint near zero and all rendering server-side.

Loaded from CDN in `base.html`; no local build step.

### Alpine.js 3.x (CDN)
Used for the attack panel on the world map (formation builder) and any local toggle/show/hide interactions. Chosen over Vue/React because:
- No build step or bundler needed.
- Fits naturally alongside HTMX (Alpine handles local UI state; HTMX handles server communication).
- Entire library loads in ~15 KB.

### Tailwind CSS (CDN)
Utility-first CSS loaded from CDN. No PostCSS/PurgeCSS step needed for a project at this scale.

---

## World map

The world map is rendered on an HTML `<canvas>` element. The browser fetches a JSON snapshot from `GET /api/world/map`, then draws each cell as a coloured square.

### Colour coding

| Entity | Colour |
|---|---|
| Player's own castle | Blue |
| Player's own fort | Green |
| Enemy fort (other player) | Red |
| Monster fort (unowned) | Orange |
| Monster camp | Purple |
| Empty | Light grey |

### Interaction
Clicking a cell fires an HTMX request to `GET /world/item/<type>/<id>`, which returns an HTML partial injected into the popup panel. The popup contains an attack button that mounts the Alpine `attackPanel()` component.

The map JSON is refreshed every 10 seconds via a `setInterval` in `tick_viewer.js`.

---

## HTMX polling intervals

| Feature | Endpoint | Interval | Trigger |
|---|---|---|---|
| Clan chat | `/api/clan/<id>/chat` | 3 s | `hx-trigger="every 3s"` |
| Resource bars | `/api/fort/<id>/resources`, `/api/castle/resources` | 5 s | `hx-trigger="every 5s"` |
| Active missions countdown | `/api/battles/active` | 5 s | `hx-trigger="every 5s"` |
| World map | `/api/world/map` (JS fetch) | 10 s | `setInterval` |

---

## Client-side mission resolution

The browser is responsible for triggering battle resolution when a mission's travel timer expires. The flow:

1. `/api/battles/active` returns JSON with `mission_id` and `seconds_remaining`.
2. The partial template renders a countdown using the value from the server.
3. When `seconds_remaining ≤ 0`, the browser calls `POST /api/missions/resolve?mission_id=<id>`.
4. The server re-checks `arrive_time ≤ now` before processing; it rejects early calls.

This eliminates the need for background workers. The server is always the authority; the client merely knows when to ask.
