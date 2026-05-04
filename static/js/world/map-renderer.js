// ── Rendering constants ────────────────────────────────────────────────
const BASE_CELL  = 52;
const CHUNK_SIZE = 16;
const ZOOM_MIN   = 0.15;
const ZOOM_MAX   = 3.0;
const ZOOM_STEP  = 0.1;
const FOG_FADE   = 4;

// ── Entity colours ([r, g, b, a]) ──────────────────────────────────────
const EC = {
  castle_own:   [37,  99, 235, 0.82],
  castle_other: [30,  58, 138, 0.82],  // covers both NPC and player enemy castles
  fort_own:     [22,  163, 74, 0.82],
  fort_npc:     [180, 83,   9, 0.82],
  fort_enemy:   [220, 38,  38, 0.82],
  fort_monster: [234, 88,  12, 0.82],
  camp:         [147, 51, 234, 0.82],
};
function ecRgba(c, a) { return `rgba(${c[0]},${c[1]},${c[2]},${a ?? c[3]})`; }

// Terrain palette — subtle per-tile variation via seeded hash
const GRASS = ['#4a9640', '#4e9844', '#529648', '#489040', '#50974a'];

// ── Sprite registry — loaded once at startup, never inside render ───────
const SPR = {};
(function preload() {
  const pairs = [
    ['castle',       `${THEME_PATH}/locations/castle.${SPRITE_EXT}`],
    ['fort',         `${THEME_PATH}/locations/fort.${SPRITE_EXT}`],
    ['monster_camp', `${THEME_PATH}/locations/monster-camp.${SPRITE_EXT}`],
    ['trees',        `${THEME_PATH}/terrain/trees.${SPRITE_EXT}`],
    ['bushes',       `${THEME_PATH}/terrain/bushes.${SPRITE_EXT}`],
    ['grass',        `${THEME_PATH}/terrain/grass.${SPRITE_EXT}`],
    ['pond',         `${THEME_PATH}/terrain/pond.${SPRITE_EXT}`],
  ];
  for (const [k, u] of pairs) {
    const img = new Image();
    img.onload = () => draw();   // redraw once each sprite is ready
    img.src = u;
    SPR[k] = img;
  }
})();

// ── Camera ─────────────────────────────────────────────────────────────
const cam = { x: 0.0, y: 0.0, zoom: 1.0 };

function worldToScreen(wx, wy) {
  return { x: (wx - cam.x) * cam.zoom, y: (wy - cam.y) * cam.zoom };
}
function screenToWorld(sx, sy) {
  return { x: sx / cam.zoom + cam.x, y: sy / cam.zoom + cam.y };
}
function clampCamera() {
  const W = WORLD_W * BASE_CELL, H = WORLD_H * BASE_CELL;
  const margin = 4 * BASE_CELL;
  cam.x = Math.max(-margin, Math.min(W - canvas.width  / cam.zoom + margin, cam.x));
  cam.y = Math.max(-margin, Math.min(H - canvas.height / cam.zoom + margin, cam.y));
}

// ── Deterministic 2-D hash (no allocations, pure function) ─────────────
function hash2(x, y) {
  let h = ((WORLD_SEED * 1000003 + x * 65537 + y * 31337) ^ 0x9e3779b9) >>> 0;
  h = (Math.imul(h ^ (h >>> 16), 0x45d9f3b)) >>> 0;
  h = (Math.imul(h ^ (h >>> 16), 0x45d9f3b)) >>> 0;
  return (h ^ (h >>> 16)) / 4294967296;
}

// ── Chunk cache — procedural props computed once, reused every frame ────
const _chunkCache = {};
function getChunk(cx, cy) {
  const key = `${cx},${cy}`;
  if (_chunkCache[key]) return _chunkCache[key];
  const props = [];
  const ox = cx * CHUNK_SIZE, oy = cy * CHUNK_SIZE;
  for (let ly = 0; ly < CHUNK_SIZE; ly++) {
    for (let lx = 0; lx < CHUNK_SIZE; lx++) {
      const gx = ox + lx, gy = oy + ly;
      if (gx >= WORLD_W || gy >= WORLD_H) continue;
      const r  = hash2(gx, gy);
      const r2 = hash2(gx + 7777, gy + 3333);
      if      (r < 0.07)              props.push({ gx, gy, spr: 'trees',  scale: 0.60 + r2 * 0.60 });
      else if (r < 0.12)              props.push({ gx, gy, spr: 'bushes', scale: 0.40 + r2 * 0.40 });
      else if (r < 0.13 && r2 < 0.3) props.push({ gx, gy, spr: 'pond',   scale: 0.80 + r2 * 0.30 });
    }
  }
  _chunkCache[key] = { props };
  return _chunkCache[key];
}

// ── Shared mutable state ───────────────────────────────────────────────
let entityMap    = {};        // "gx,gy" → API item
let _dbDecoSet   = new Set(); // "gx,gy" of DB-decoration cells
let _viewFilter  = null;      // null | 'own' | { type:'friend', id:NUMBER }
let _zoomAllMode = false;
let showLabels   = false;
let legendOpen   = true;
let _friends     = [];

// ── Canvas setup ───────────────────────────────────────────────────────
const canvas = document.getElementById('world-canvas');
const ctx    = canvas.getContext('2d');

function resizeCanvas() {
  const shell   = document.getElementById('world-map-shell');
  canvas.width  = shell.clientWidth  || window.innerWidth;
  canvas.height = shell.clientHeight || window.innerHeight;
  clampCamera();
  draw();
}
new ResizeObserver(resizeCanvas).observe(document.getElementById('world-map-shell'));

// ── Rounded-rect path (no object allocations) ──────────────────────────
function roundRect(c, x, y, w, h, r) {
  c.beginPath();
  c.moveTo(x + r, y);
  c.lineTo(x + w - r, y);     c.quadraticCurveTo(x + w, y,     x + w, y + r);
  c.lineTo(x + w, y + h - r); c.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  c.lineTo(x + r, y + h);     c.quadraticCurveTo(x,     y + h, x,     y + h - r);
  c.lineTo(x, y + r);         c.quadraticCurveTo(x,     y,     x + r, y);
  c.closePath();
}

// ── Main draw ──────────────────────────────────────────────────────────
function draw() {
  const cw = canvas.width, ch = canvas.height;
  ctx.clearRect(0, 0, cw, ch);

  // Compute visible tile range
  const { x: vx0, y: vy0 } = screenToWorld(0,  0);
  const { x: vx1, y: vy1 } = screenToWorld(cw, ch);
  const tx0 = Math.max(0,           Math.floor(vx0 / BASE_CELL));
  const ty0 = Math.max(0,           Math.floor(vy0 / BASE_CELL));
  const tx1 = Math.min(WORLD_W - 1, Math.ceil(vx1  / BASE_CELL));
  const ty1 = Math.min(WORLD_H - 1, Math.ceil(vy1  / BASE_CELL));
  const cs  = BASE_CELL * cam.zoom;

  // 1. Terrain
  for (let ty = ty0; ty <= ty1; ty++) {
    for (let tx = tx0; tx <= tx1; tx++) {
      const { x: sx, y: sy } = worldToScreen(tx * BASE_CELL, ty * BASE_CELL);
      ctx.fillStyle = GRASS[Math.floor(hash2(tx, ty) * GRASS.length)];
      ctx.fillRect(Math.floor(sx), Math.floor(sy), Math.ceil(cs) + 1, Math.ceil(cs) + 1);
    }
  }

  // 2. Procedural props (chunk cache)
  const cx0 = Math.floor(tx0 / CHUNK_SIZE), cy0 = Math.floor(ty0 / CHUNK_SIZE);
  const cx1 = Math.floor(tx1 / CHUNK_SIZE), cy1 = Math.floor(ty1 / CHUNK_SIZE);
  for (let cy = cy0; cy <= cy1; cy++) {
    for (let cx = cx0; cx <= cx1; cx++) {
      for (const p of getChunk(cx, cy).props) {
        if (p.gx < tx0 || p.gx > tx1 || p.gy < ty0 || p.gy > ty1) continue;
        const key = `${p.gx},${p.gy}`;
        const existing = entityMap[key];
        if (existing && existing.type !== 'decoration') continue;
        if (_dbDecoSet.has(key)) continue;
        const spr = SPR[p.spr];
        if (!spr || !spr.complete || !spr.naturalWidth) continue;
        const { x: sx, y: sy } = worldToScreen(p.gx * BASE_CELL, p.gy * BASE_CELL);
        const drawSz = cs * p.scale, off = (cs - drawSz) * 0.5;
        ctx.drawImage(spr, sx + off, sy + off, drawSz, drawSz);
      }
    }
  }

  // 3. DB decorations
  for (const item of Object.values(entityMap)) {
    if (item.type !== 'decoration') continue;
    if (item.grid_x < tx0 || item.grid_x > tx1 || item.grid_y < ty0 || item.grid_y > ty1) continue;
    const spr = SPR[item.decoration_type] || SPR['trees'];
    if (!spr || !spr.complete || !spr.naturalWidth) continue;
    const { x: sx, y: sy } = worldToScreen(item.grid_x * BASE_CELL, item.grid_y * BASE_CELL);
    const drawSz = cs * (item.display_scale ?? 1.0), off = (cs - drawSz) * 0.5;
    ctx.drawImage(spr, sx + off, sy + off, drawSz, drawSz);
  }

  // 4. Interactive entities (castles, forts, camps)
  const fontSize = Math.max(8, Math.min(13, cs * 0.18));
  ctx.font = `bold ${fontSize}px sans-serif`;
  ctx.textAlign    = 'center';
  ctx.textBaseline = 'bottom';

  for (const item of Object.values(entityMap)) {
    if (item.type === 'decoration') continue;
    if (item.grid_x < tx0 || item.grid_x > tx1 || item.grid_y < ty0 || item.grid_y > ty1) continue;

    const { x: sx, y: sy } = worldToScreen(item.grid_x * BASE_CELL, item.grid_y * BASE_CELL);
    let col = null, label = '', starStr = '';

    if (item.type === 'castle') {
      col   = item.owner_id === PLAYER_ID ? EC.castle_own : EC.castle_other;
      label = item.owner_id === PLAYER_ID ? 'Your Castle' : (item.owner_name || '?');
    } else if (item.type === 'fort') {
      if      (item.owner_id === PLAYER_ID) { col = EC.fort_own;     label = 'Your Fort'; }
      else if (item.is_npc)                 { col = EC.fort_npc;     label = item.owner_name || 'NPC Fort';   starStr = '\u2605'.repeat(Math.min(item.star_level || 0, 4)); }
      else if (item.owner_id)               { col = EC.fort_enemy;   label = item.owner_name || 'Enemy Fort'; }
      else                                  { col = EC.fort_monster; label = 'Abandoned Fort'; starStr = '\u2605'.repeat(Math.min(item.star_level || 0, 4)); }
    } else if (item.type === 'monster_camp') {
      col = EC.camp; label = 'Monster Camp'; starStr = '\u2605'.repeat(Math.min(item.star_level || 0, 4));
    }
    if (!col) continue;

    const r = Math.max(2, cs * 0.06);
    ctx.fillStyle = ecRgba(col);
    roundRect(ctx, sx, sy, cs, cs, r);
    ctx.fill();

    let ringColor = null;
    if      (_viewFilter === 'own' && item.owner_id === PLAYER_ID)                              ringColor = '#22d3ee';
    else if (_viewFilter && _viewFilter.type === 'friend' && item.owner_id === _viewFilter.id) ringColor = '#f59e0b';
    if (ringColor) {
      ctx.strokeStyle = ringColor;
      ctx.lineWidth   = Math.max(2, cs * 0.05);
      roundRect(ctx, sx + 1, sy + 1, cs - 2, cs - 2, r);
      ctx.stroke();
    }

    const spr = SPR[item.type];
    if (spr && spr.complete && spr.naturalWidth) {
      const pad = cs * 0.08;
      ctx.drawImage(spr, sx + pad, sy + pad, cs - pad * 2, cs - pad * 2);
    }

    if (showLabels || cs >= 38) {
      const txt = label + (starStr ? ' ' + starStr : '');
      const tw  = ctx.measureText(txt).width + 6;
      ctx.fillStyle = 'rgba(0,0,0,0.78)';
      ctx.fillRect(sx + cs / 2 - tw / 2, sy - fontSize - 4, tw, fontSize + 4);
      ctx.fillStyle = '#e5e7eb';
      ctx.fillText(txt, sx + cs / 2, sy - 2);
    }
  }

  // 5. Edge fog
  drawFog();
}

// ── Edge fog ───────────────────────────────────────────────────────────
function drawFog() {
  const W = WORLD_W * BASE_CELL, H = WORLD_H * BASE_CELL;
  const cw = canvas.width, ch = canvas.height;
  const { x: x0, y: y0 } = worldToScreen(0, 0);
  const { x: x1, y: y1 } = worldToScreen(W, H);
  const bg = '#111827';

  ctx.fillStyle = bg;
  if (x0 > 0)  ctx.fillRect(0,  0,  x0,      ch);
  if (x1 < cw) ctx.fillRect(x1, 0,  cw - x1, ch);
  if (y0 > 0)  ctx.fillRect(x0, 0,  x1 - x0, y0);
  if (y1 < ch) ctx.fillRect(x0, y1, x1 - x0, ch - y1);

  const fogPx = Math.min(
    FOG_FADE * BASE_CELL * cam.zoom,
    Math.max(0, (x1 - x0) * 0.15),
    Math.max(0, (y1 - y0) * 0.15),
  );
  if (fogPx <= 1) return;

  function fogGrad(x1g, y1g, x2g, y2g) {
    const g = ctx.createLinearGradient(x1g, y1g, x2g, y2g);
    g.addColorStop(0, 'rgba(17,24,39,0.88)');
    g.addColorStop(1, 'rgba(17,24,39,0)');
    return g;
  }
  ctx.fillStyle = fogGrad(0, y0, 0, y0 + fogPx);  ctx.fillRect(x0,          y0,          x1 - x0, fogPx);
  ctx.fillStyle = fogGrad(0, y1, 0, y1 - fogPx);  ctx.fillRect(x0,          y1 - fogPx, x1 - x0, fogPx);
  ctx.fillStyle = fogGrad(x0, 0, x0 + fogPx, 0); ctx.fillRect(x0,          y0,          fogPx,   y1 - y0);
  ctx.fillStyle = fogGrad(x1, 0, x1 - fogPx, 0); ctx.fillRect(x1 - fogPx, y0,          fogPx,   y1 - y0);
}
