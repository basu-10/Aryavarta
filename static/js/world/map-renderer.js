// ── Rendering constants ────────────────────────────────────────────────
const BASE_CELL  = 52;          // pixels per world unit at zoom=1
const CHUNK_SIZE = 16;          // world units per chunk side
const ZOOM_MIN   = 0.15;
const ZOOM_MAX   = 3.0;
const ZOOM_STEP  = 0.1;
const FOG_FADE   = 4;
const PROP_CELL  = 0.85;        // sub-cell size used for prop scatter (world units)

// ── Biome terrain palettes — subtle per-tile variation via hash ─────────
const BIOME_PAL = {
  forest:    ['#3d8a32','#418e36','#459240','#3f8c3a','#3a863e'],
  shrubland: ['#50803e','#548444','#4e8840','#568040','#52843c'],
  rocky:     ['#6e6450','#726854','#6a6248','#74664c','#706256'],
  open:      ['#52963e','#569a42','#509840','#5a9c44','#4e943c'],
};

// ── Asset intrinsic sizes [width, height] in world units ───────────────
// Sprites are rendered at these sizes (× scale factor from biome def).
// Bottom-center anchor is used so taller trees stand up naturally.
const ASSET_SIZE = {
  trees:           [1.20, 1.40],
  mixed_trees:     [1.30, 1.50],
  conifers:        [1.00, 1.60],
  dense_forest:    [1.80, 2.00],
  single_tree:     [0.70, 1.00],
  mini_tree_row:   [1.40, 0.85],
  bushes:          [0.60, 0.42],
  bushes_alt:      [0.60, 0.42],
  dense_shrubbery: [0.78, 0.52],
  loose_shrubbery: [0.68, 0.46],
  golden_shrub:    [0.50, 0.36],
  shrubbery_rock:  [0.68, 0.50],
  pond:            [1.25, 0.92],
  rock_large:      [0.88, 0.68],
  graveyard:       [1.12, 0.92],
  magma_rocks:     [0.98, 0.78],
  grass:           [0.50, 0.30],
};

const SPRITE_PATHS = ACTIVE_THEME === 'theme2'
  ? {
      castle: `${THEME_PATH}/locations/castle.png`,
      fort: `${THEME_PATH}/locations/fort.png`,
  monster_camp: `${THEME_PATH}/locations/monster-camp.png`,
  own_fort_banner: `${THEME_PATH}/locations/banners/own-fort.png`,
  friend_banner: `${THEME_PATH}/locations/banners/friend-banner.png`,
  clan_banner: `${THEME_PATH}/locations/banners/clan-banner.png`,
  enemy_banner: `${THEME_PATH}/locations/banners/enemy-banner.png`,
  abandoned_banner: `${THEME_PATH}/locations/banners/abandoned-banner.png`,
      trees: `${THEME_PATH}/terrain/trees.png`,
      mixed_trees: `${THEME_PATH}/terrain/mixed-trees.png`,
      conifers: `${THEME_PATH}/terrain/conifers.png`,
      dense_forest: `${THEME_PATH}/terrain/dense-forest.png`,
      single_tree: `${THEME_PATH}/terrain/single-tree.png`,
      mini_tree_row: `${THEME_PATH}/terrain/mini-tree-row.png`,
      bushes: `${THEME_PATH}/terrain/bushes.png`,
      bushes_alt: `${THEME_PATH}/terrain/bushes-alt.png`,
      dense_shrubbery: `${THEME_PATH}/terrain/dense-shrubbery.png`,
      loose_shrubbery: `${THEME_PATH}/terrain/loose-shrubbery.png`,
      golden_shrub: `${THEME_PATH}/terrain/golden-shrub.png`,
      shrubbery_rock: `${THEME_PATH}/terrain/shrubbery-rock.png`,
      grass: `${THEME_PATH}/terrain/grass.svg`,
      pond: `${THEME_PATH}/terrain/pond.png`,
      rock_large: `${THEME_PATH}/terrain/rock-large.png`,
      graveyard: `${THEME_PATH}/terrain/graveyard.png`,
      magma_rocks: `${THEME_PATH}/terrain/magma-rocks.png`,
    }
  : {
      castle: `${THEME_PATH}/locations/castle.svg`,
      fort: `${THEME_PATH}/locations/fort.svg`,
      monster_camp: `${THEME_PATH}/locations/monster-camp.svg`,
      trees: `${THEME_PATH}/terrain/trees.svg`,
      bushes: `${THEME_PATH}/terrain/bushes.svg`,
      grass: `${THEME_PATH}/terrain/grass.svg`,
      pond: `${THEME_PATH}/terrain/pond.svg`,
    };

// Entity sprite scale multipliers (relative to cell size cs).
// > 1.0 = sprite overflows its tile for visual presence.
const ENTITY_SPR_MULT = { castle: 1.45, fort: 1.28, monster_camp: 1.18 };

// ── Biome prop definitions ─────────────────────────────────────────────
// density  : probability [0,1] that a sub-cell spawns a prop
// props    : weighted list; sMin/sMax are scale multipliers on ASSET_SIZE
const BIOME_PROPS = ACTIVE_THEME === 'theme2'
  ? {
      forest: {
        density: 0.72,
        props: [
          { spr: 'dense_forest',  wt: 3, sMin: 0.88, sMax: 1.12 },
          { spr: 'trees',         wt: 5, sMin: 0.90, sMax: 1.18 },
          { spr: 'mixed_trees',   wt: 3, sMin: 0.88, sMax: 1.16 },
          { spr: 'conifers',      wt: 2, sMin: 0.80, sMax: 1.05 },
          { spr: 'single_tree',   wt: 2, sMin: 0.72, sMax: 0.98 },
          { spr: 'mini_tree_row', wt: 1, sMin: 0.75, sMax: 0.95 },
        ],
      },
      shrubland: {
        density: 0.48,
        props: [
          { spr: 'bushes',          wt: 4, sMin: 0.88, sMax: 1.12 },
          { spr: 'bushes_alt',      wt: 3, sMin: 0.88, sMax: 1.10 },
          { spr: 'dense_shrubbery', wt: 2, sMin: 0.90, sMax: 1.14 },
          { spr: 'loose_shrubbery', wt: 3, sMin: 0.88, sMax: 1.08 },
          { spr: 'golden_shrub',    wt: 2, sMin: 0.85, sMax: 1.05 },
          { spr: 'shrubbery_rock',  wt: 2, sMin: 0.88, sMax: 1.10 },
          { spr: 'single_tree',     wt: 1, sMin: 0.65, sMax: 0.88 },
        ],
      },
      rocky: {
        density: 0.32,
        props: [
          { spr: 'rock_large',  wt: 5, sMin: 0.90, sMax: 1.20 },
          { spr: 'magma_rocks', wt: 2, sMin: 0.88, sMax: 1.15 },
          { spr: 'graveyard',   wt: 1, sMin: 0.82, sMax: 1.02 },
        ],
      },
      open: {
        density: 0.08,
        props: [
          { spr: 'bushes',       wt: 2, sMin: 0.78, sMax: 1.02 },
          { spr: 'golden_shrub', wt: 1, sMin: 0.72, sMax: 0.92 },
          { spr: 'single_tree',  wt: 1, sMin: 0.72, sMax: 0.98 },
        ],
      },
    }
  : {
      forest: {
        density: 0.68,
        props: [
          { spr: 'trees',  wt: 4, sMin: 0.82, sMax: 1.20 },
          { spr: 'bushes', wt: 2, sMin: 0.72, sMax: 0.98 },
        ],
      },
      shrubland: {
        density: 0.40,
        props: [
          { spr: 'bushes', wt: 4, sMin: 0.82, sMax: 1.10 },
          { spr: 'trees',  wt: 1, sMin: 0.62, sMax: 0.88 },
        ],
      },
      rocky: {
        density: 0.18,
        props: [
          { spr: 'bushes', wt: 2, sMin: 0.62, sMax: 0.88 },
        ],
      },
      open: {
        density: 0.05,
        props: [
          { spr: 'bushes', wt: 1, sMin: 0.62, sMax: 0.80 },
        ],
      },
    };

// Precompute cumulative weights once
for (const biome of Object.values(BIOME_PROPS)) {
  let t = 0;
  biome._cumWt   = biome.props.map(p => { t += p.wt; return t; });
  biome._totalWt = t;
}

const PROP_VARIANTS = ACTIVE_THEME === 'theme2'
  ? {
      // legacy – kept so external code referencing it doesn't break
      trees: [], bushes: [], pond: [], feature: [],
    }
  : {
      // legacy alias stubs — kept for backward compat only
      trees: [], bushes: [], pond: [], feature: [],
    };

// ── Deterministic 2-D hash (no allocations, pure function) ─────────────
function hash2(x, y) {
  let h = ((WORLD_SEED * 1000003 + x * 65537 + y * 31337) ^ 0x9e3779b9) >>> 0;
  h = (Math.imul(h ^ (h >>> 16), 0x45d9f3b)) >>> 0;
  h = (Math.imul(h ^ (h >>> 16), 0x45d9f3b)) >>> 0;
  return (h ^ (h >>> 16)) / 4294967296;
}

// Integer hash for a specific sub-cell + salt so each property is independent
function cellHash(ix, iy, salt) {
  return hash2(ix * 7 + salt * 13, iy * 11 + salt * 17);
}

// ── Smooth biome noise — bilinear interpolation over a coarse grid ──────
const BIOME_SCALE = 12; // world units between biome anchor points
function biomeVal(wx, wy) {
  const bx = wx / BIOME_SCALE, by = wy / BIOME_SCALE;
  const ix = Math.floor(bx), iy = Math.floor(by);
  const fx = bx - ix, fy = by - iy;
  // smoothstep
  const ux = fx * fx * (3 - 2 * fx), uy = fy * fy * (3 - 2 * fy);
  const h00 = hash2(ix,     iy);
  const h10 = hash2(ix + 1, iy);
  const h01 = hash2(ix,     iy + 1);
  const h11 = hash2(ix + 1, iy + 1);
  return h00 * (1 - ux) * (1 - uy) + h10 * ux * (1 - uy)
       + h01 * (1 - ux) * uy       + h11 * ux * uy;
}

function getBiome(wx, wy) {
  const v = biomeVal(wx, wy);
  if (v < 0.30) return 'forest';
  if (v < 0.55) return 'shrubland';
  if (v < 0.72) return 'rocky';
  return 'open';
}

// Weighted prop picker — O(n) linear scan on short lists
function pickBiomeProp(biome, seed) {
  const b = BIOME_PROPS[biome];
  if (!b || !b.props.length) return null;
  const t = seed * b._totalWt;
  let idx = 0;
  while (idx < b._cumWt.length - 1 && b._cumWt[idx] <= t) idx++;
  return b.props[idx];
}

// ── Sprite registry — loaded once at startup ────────────────────────────
const SPR = {};
(function preload() {
  for (const [k, u] of Object.entries(SPRITE_PATHS)) {
    const img = new Image();
    img.onload = () => draw();
    img.src = u;
    SPR[k] = img;
  }
})();

// ── Camera (pixel-world-space) ──────────────────────────────────────────
const cam = { x: 0.0, y: 0.0, zoom: 1.0 };

// wx, wy are in pixel-world-space (grid_cell × BASE_CELL)
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

// ── Chunk cache — free-placement props, computed once per chunk ─────────
// Each prop: { px, py } float world-unit coords; { w, h } world-unit size;
// { spr } sprite key.  Anchor: bottom-center at (px, py).
const _chunkCache = {};
function getChunk(cx, cy) {
  const key = `${cx},${cy}`;
  if (_chunkCache[key]) return _chunkCache[key];

  const props = [];
  const ox = cx * CHUNK_SIZE, oy = cy * CHUNK_SIZE;
  const nCells = Math.ceil(CHUNK_SIZE / PROP_CELL);

  for (let lcy = 0; lcy < nCells; lcy++) {
    for (let lcx = 0; lcx < nCells; lcx++) {
      const cellX = ox + lcx * PROP_CELL;
      const cellY = oy + lcy * PROP_CELL;
      if (cellX >= WORLD_W || cellY >= WORLD_H) continue;

      // Use integer sub-cell coords as hash keys (×100 to preserve 2 decimals)
      const icx = Math.round(cellX * 100);
      const icy = Math.round(cellY * 100);

      const biome  = getBiome(cellX + PROP_CELL * 0.5, cellY + PROP_CELL * 0.5);
      const bd     = BIOME_PROPS[biome];
      if (!bd) continue;

      const rSpawn = cellHash(icx, icy, 1);
      if (rSpawn >= bd.density) continue;

      // Random offset within sub-cell for natural scatter
      const rOx    = cellHash(icx, icy, 2);
      const rOy    = cellHash(icx, icy, 3);
      const rPick  = cellHash(icx, icy, 4);
      const rScale = cellHash(icx, icy, 5);

      const px = Math.min(WORLD_W - 0.01, cellX + rOx * PROP_CELL);
      const py = Math.min(WORLD_H - 0.01, cellY + rOy * PROP_CELL);

      const prop = pickBiomeProp(biome, rPick);
      if (!prop) continue;

      const scale      = prop.sMin + rScale * (prop.sMax - prop.sMin);
      const [aw, ah]   = ASSET_SIZE[prop.spr] || [1.0, 1.0];
      props.push({ px, py, spr: prop.spr, w: aw * scale, h: ah * scale });
    }
  }

  // Painter's algorithm: draw lower-Y props first so taller ones overlap
  props.sort((a, b) => a.py - b.py);

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

function getFortBannerKeys(item) {
  if (item.owner_id === PLAYER_ID) return ['own_fort_banner'];
  if (!item.owner_id) return ['abandoned_banner'];

  const banners = [];
  if (item.is_friend) banners.push('friend_banner');
  if (item.is_same_clan) banners.push('clan_banner');
  if (!banners.length) banners.push('enemy_banner');
  return banners;
}

function drawFortBanners(item, sx, sy, cs) {
  const bannerKeys = getFortBannerKeys(item);
  if (!bannerKeys.length) return;

  const anchorXs = bannerKeys.length === 1
    ? [sx + cs * 0.06]
    : [sx - cs * 0.08, sx + cs * 0.68];
  const bannerY = sy + cs * 0.20;

  bannerKeys.forEach((bannerKey, index) => {
    const spr = SPR[bannerKey];
    if (!spr || !spr.complete || !spr.naturalWidth || !spr.naturalHeight) return;

    const bannerH = cs * 0.92;
    const ratio = spr.naturalWidth / spr.naturalHeight;
    const bannerW = bannerH * ratio;
    ctx.drawImage(spr, anchorXs[index], bannerY, bannerW, bannerH);
  });
}

// ── Main draw ──────────────────────────────────────────────────────────
function draw() {
  const cw = canvas.width, ch = canvas.height;
  ctx.clearRect(0, 0, cw, ch);

  // Viewport in pixel-world-space → convert to grid-cell space
  const { x: vpx0, y: vpy0 } = screenToWorld(0,  0);
  const { x: vpx1, y: vpy1 } = screenToWorld(cw, ch);
  const vx0 = vpx0 / BASE_CELL, vy0 = vpy0 / BASE_CELL;
  const vx1 = vpx1 / BASE_CELL, vy1 = vpy1 / BASE_CELL;

  // Integer tile range
  const tx0 = Math.max(0,           Math.floor(vx0));
  const ty0 = Math.max(0,           Math.floor(vy0));
  const tx1 = Math.min(WORLD_W - 1, Math.ceil(vx1));
  const ty1 = Math.min(WORLD_H - 1, Math.ceil(vy1));
  const cs  = BASE_CELL * cam.zoom;   // screen pixels per world unit

  // 1. Biome terrain background — per-tile, biome colour + subtle hash variation
  for (let ty = ty0; ty <= ty1; ty++) {
    for (let tx = tx0; tx <= tx1; tx++) {
      const biome  = getBiome(tx + 0.5, ty + 0.5);
      const pal    = BIOME_PAL[biome] || BIOME_PAL.open;
      const { x: sx, y: sy } = worldToScreen(tx * BASE_CELL, ty * BASE_CELL);
      ctx.fillStyle = pal[Math.floor(hash2(tx, ty) * pal.length)];
      ctx.fillRect(Math.floor(sx), Math.floor(sy), Math.ceil(cs) + 1, Math.ceil(cs) + 1);
    }
  }

  // 2. Procedural props — free-placement, biome-clustered, Y-sorted per chunk
  // Expand chunk range by ±1 so large sprites near chunk edges stay visible
  const cx0 = Math.floor(tx0 / CHUNK_SIZE) - 1;
  const cy0 = Math.floor(ty0 / CHUNK_SIZE) - 1;
  const cx1 = Math.floor(tx1 / CHUNK_SIZE) + 1;
  const cy1 = Math.floor(ty1 / CHUNK_SIZE) + 1;

  // Screen-space cull margin — generous enough for the largest sprite (dense_forest h≈2)
  const cullMargin = cs * 2.5;
  const cullL = -cullMargin, cullT = -cullMargin;
  const cullR = cw + cullMargin, cullB = ch + cullMargin;

  for (let cy = cy0; cy <= cy1; cy++) {
    for (let cx = cx0; cx <= cx1; cx++) {
      for (const p of getChunk(cx, cy).props) {
        // Prop bottom-center in pixel-world-space
        const pxPx = p.px * BASE_CELL;
        const pyPx = p.py * BASE_CELL;
        const { x: sx, y: sy } = worldToScreen(pxPx, pyPx);

        // Screen-space pixel size
        const pw = p.w * cs, ph = p.h * cs;
        // Bottom-center anchor → top-left draw origin
        const drawX = sx - pw * 0.5;
        const drawY = sy - ph;

        // Frustum cull
        if (drawX + pw < cullL || drawX > cullR || drawY + ph < cullT || drawY > cullB) continue;

        // Suppress proc prop if an entity occupies the same tile
        const gx = Math.floor(p.px), gy = Math.floor(p.py);
        const tileKey = `${gx},${gy}`;
        const existing = entityMap[tileKey];
        if (existing && existing.type !== 'decoration') continue;
        if (_dbDecoSet.has(tileKey)) continue;

        const spr = SPR[p.spr];
        if (!spr || !spr.complete || !spr.naturalWidth) continue;
        ctx.drawImage(spr, drawX, drawY, pw, ph);
      }
    }
  }

  // 3. DB decorations — use ASSET_SIZE for proper proportions
  for (const item of Object.values(entityMap)) {
    if (item.type !== 'decoration') continue;
    const { x: sx, y: sy } = worldToScreen(item.grid_x * BASE_CELL, item.grid_y * BASE_CELL);
    const spr = SPR[item.decoration_type] || SPR['trees'];
    if (!spr || !spr.complete || !spr.naturalWidth) continue;
    const [aw, ah] = ASSET_SIZE[item.decoration_type] || [1.0, 1.0];
    const scale    = item.display_scale ?? 1.0;
    const pw = aw * scale * cs, ph = ah * scale * cs;
    // Bottom-center anchor on the tile center
    ctx.drawImage(spr, sx + cs * 0.5 - pw * 0.5, sy + cs - ph, pw, ph);
  }

  // 4. Edge fog (before entities so border castles remain visible)
  drawFog();

  // 5. Interactive entities (castles, forts, camps)
  const fontSize = Math.max(8, Math.min(13, cs * 0.18));
  ctx.font = `bold ${fontSize}px sans-serif`;
  ctx.textAlign    = 'center';
  ctx.textBaseline = 'bottom';

  for (const item of Object.values(entityMap)) {
    if (item.type === 'decoration') continue;
    // Widen the cull range since entity sprites overflow their tile
    if (item.grid_x < tx0 - 1 || item.grid_x > tx1 + 1 ||
        item.grid_y < ty0 - 1 || item.grid_y > ty1 + 1) continue;

    const { x: sx, y: sy } = worldToScreen(item.grid_x * BASE_CELL, item.grid_y * BASE_CELL);
    let label = '', starStr = '';

    if (item.type === 'castle') {
      label = item.owner_id === PLAYER_ID ? 'Your Castle' : (item.owner_name || '?');
    } else if (item.type === 'fort') {
      if      (item.owner_id === PLAYER_ID) { label = 'Your Fort'; }
      else if (item.owner_id)               { label = item.owner_name || (item.is_npc ? 'NPC Fort' : 'Enemy Fort'); }
      else                                  { label = 'Abandoned Fort'; starStr = '\u2605'.repeat(Math.min(item.star_level || 0, 4)); }
    } else if (item.type === 'monster_camp') {
      label = 'Monster Camp'; starStr = '\u2605'.repeat(Math.min(item.star_level || 0, 4));
    }

    // Filter ring remains, but the state-colour box is removed.
    let ringColor = null;
    if      (_viewFilter === 'own' && item.owner_id === PLAYER_ID)                              ringColor = '#22d3ee';
    else if (_viewFilter && _viewFilter.type === 'friend' && item.owner_id === _viewFilter.id) ringColor = '#f59e0b';
    if (ringColor) {
      ctx.strokeStyle = ringColor;
      ctx.lineWidth   = Math.max(2, cs * 0.05);
      ctx.strokeRect(sx + 1, sy + 1, cs - 2, cs - 2);
    }

    // Entity sprite — rendered larger than tile for visual presence
    const spr = SPR[item.type];
    if (spr && spr.complete && spr.naturalWidth) {
      const mult = ENTITY_SPR_MULT[item.type] ?? 1.0;
      const sw = cs * mult, sh = cs * mult;
      ctx.drawImage(spr, sx + (cs - sw) * 0.5, sy + (cs - sh) * 0.5, sw, sh);
    }

    if (item.type === 'fort') drawFortBanners(item, sx, sy, cs);

    if (showLabels || cs >= 38) {
      const txt = label + (starStr ? ' ' + starStr : '');
      const tw  = ctx.measureText(txt).width + 6;
      ctx.fillStyle = 'rgba(0,0,0,0.78)';
      ctx.fillRect(sx + cs / 2 - tw / 2, sy - fontSize - 4, tw, fontSize + 4);
      ctx.fillStyle = '#e5e7eb';
      ctx.fillText(txt, sx + cs / 2, sy - 2);
    }
  }

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
