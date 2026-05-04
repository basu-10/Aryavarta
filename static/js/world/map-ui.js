// ── Preferences ────────────────────────────────────────────────────────
// WORLD_SEED is set by the inline script in the template (= world.id)
const WORLD_MAP_PREFS = {
  showLabels: 'battlecells.world.showLabels',
  legendOpen: 'battlecells.world.legendOpen',
  cam:        `battlecells.world.cam.${WORLD_SEED}`,
};

function readBoolPref(k, fb)  { try { const v = localStorage.getItem(k); return v === null ? fb : v === 'true'; } catch { return fb; } }
function writeBoolPref(k, v)  { try { localStorage.setItem(k, String(Boolean(v))); } catch {} }
function saveCamPref()        { try { localStorage.setItem(WORLD_MAP_PREFS.cam, JSON.stringify({ x: cam.x, y: cam.y, zoom: cam.zoom })); } catch {} }
function restoreCamPref() {
  try {
    const s = JSON.parse(localStorage.getItem(WORLD_MAP_PREFS.cam) || 'null');
    if (s) {
      cam.x    = s.x    ?? cam.x;
      cam.y    = s.y    ?? cam.y;
      cam.zoom = s.zoom != null ? Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, s.zoom)) : cam.zoom;
    }
  } catch {}
}

// ── Entity popup ───────────────────────────────────────────────────────
let popupAnchor = { x: 12, y: 12 };

function handleCanvasClick(e) {
  const rect = canvas.getBoundingClientRect();
  const sx = e.clientX - rect.left, sy = e.clientY - rect.top;
  const { x: wx, y: wy } = screenToWorld(sx, sy);
  const gx = Math.floor(wx / BASE_CELL), gy = Math.floor(wy / BASE_CELL);

  if (gx < 0 || gy < 0 || gx >= WORLD_W || gy >= WORLD_H) { closeEntityPopup(); return; }

  const item = entityMap[`${gx},${gy}`];
  if (item && item.type !== 'decoration') {
    const shell     = document.getElementById('world-map-shell');
    const shellRect = shell.getBoundingClientRect();
    const canvRect  = canvas.getBoundingClientRect();
    popupAnchor = {
      x: canvRect.left - shellRect.left + sx + 10,
      y: canvRect.top  - shellRect.top  + sy - 4,
    };
    const popup = document.getElementById('entity-popup');
    popup.classList.remove('hidden');
    popup.style.left = `${popupAnchor.x}px`;
    popup.style.top  = `${popupAnchor.y}px`;
    htmx.ajax('GET', `/world/item/${item.type}/${item.id}`, { target: '#entity-popup', swap: 'innerHTML' });
  } else {
    closeEntityPopup();
  }
}

function clampPopup() {
  const shell = document.getElementById('world-map-shell');
  const popup = document.getElementById('entity-popup');
  if (popup.classList.contains('hidden')) return;
  const maxX = Math.max(8, shell.clientWidth  - popup.offsetWidth  - 8);
  const maxY = Math.max(8, shell.clientHeight - popup.offsetHeight - 8);
  popup.style.left = `${Math.min(maxX, Math.max(8, popupAnchor.x))}px`;
  popup.style.top  = `${Math.min(maxY, Math.max(8, popupAnchor.y))}px`;
}

function closeEntityPopup() { document.getElementById('entity-popup').classList.add('hidden'); }

document.body.addEventListener('htmx:afterSwap', e => { if (e.target.id === 'entity-popup') clampPopup(); });
document.addEventListener('click', e => {
  const popup = document.getElementById('entity-popup');
  if (popup.classList.contains('hidden')) return;
  if (e.target.closest('#entity-popup') || e.target.id === 'world-canvas') return;
  closeEntityPopup();
});
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeEntityPopup(); });
window.addEventListener('resize', clampPopup);

// ── Zoom controls (buttons + slider) ──────────────────────────────────
function setZoom(z) {
  const cx = canvas.width / 2, cy = canvas.height / 2;
  const { x: wx, y: wy } = screenToWorld(cx, cy);
  cam.zoom = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, Math.round(z / ZOOM_STEP) * ZOOM_STEP));
  cam.x = wx - cx / cam.zoom;
  cam.y = wy - cy / cam.zoom;
  clampCamera();
  updateZoomUI();
  saveCamPref();
  draw();
}

function updateZoomUI() {
  const pct   = Math.round(cam.zoom * 100);
  const range = document.getElementById('zoom-range');
  const reset = document.getElementById('zoom-reset');
  if (range) range.value      = String(pct);
  if (reset) reset.textContent = `${pct}%`;
}

document.getElementById('zoom-in').addEventListener('click',    () => setZoom(cam.zoom + ZOOM_STEP));
document.getElementById('zoom-out').addEventListener('click',   () => setZoom(cam.zoom - ZOOM_STEP));
document.getElementById('zoom-reset').addEventListener('click', () => setZoom(1.0));
document.getElementById('zoom-range').addEventListener('input', e => setZoom(Number(e.target.value) / 100));

// ── Map data ───────────────────────────────────────────────────────────
async function loadMap() {
  const res  = await fetch('/api/world/map');
  const data = await res.json();
  entityMap  = {};
  _dbDecoSet = new Set();
  for (const item of (data.items || [])) {
    entityMap[`${item.grid_x},${item.grid_y}`] = item;
    if (item.type === 'decoration') _dbDecoSet.add(`${item.grid_x},${item.grid_y}`);
  }
  draw();
}

// ── Friends ────────────────────────────────────────────────────────────
async function loadFriends() {
  try {
    const res  = await fetch('/api/friends');
    const data = await res.json();
    _friends   = data.friends || [];
    renderFriendsList();
  } catch (_) {}
}

function renderFriendsList() {
  const inner = document.getElementById('friends-list-inner');
  if (!inner) return;
  inner.innerHTML = _friends.length
    ? _friends.map(f => `<button type="button" onclick="setFriendFilter(${f.id},'${escHtml(f.username)}')" class="w-full text-left px-3 py-1.5 hover:bg-gray-800 text-xs text-gray-200">${escHtml(f.username)}</button>`).join('')
    : '<span class="px-3 py-2 block text-gray-500">No friends yet</span>';
}

function escHtml(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }

// ── Filter helpers ─────────────────────────────────────────────────────
function toggleFriendsMenu() {
  const menu = document.getElementById('friends-menu');
  menu.classList.toggle('hidden');
  if (!menu.classList.contains('hidden')) loadFriends();
}
document.addEventListener('click', e => {
  const wrap = document.getElementById('friends-dropdown-wrap');
  if (wrap && !wrap.contains(e.target)) document.getElementById('friends-menu').classList.add('hidden');
});

function setFriendFilter(friendId, friendName) {
  document.getElementById('friends-menu').classList.add('hidden');
  const btn = document.getElementById('btn-friends');
  if (_viewFilter && _viewFilter.type === 'friend' && _viewFilter.id === friendId) {
    _viewFilter = null;
    btn.textContent = '👥 Friends ▾';
    btn.classList.remove('bg-yellow-700', 'border-yellow-500', 'text-yellow-100');
    btn.classList.add('bg-gray-800', 'border-gray-700', 'text-gray-200');
  } else {
    _viewFilter = { type: 'friend', id: friendId };
    btn.textContent = `👥 ${friendName} ✕`;
    btn.classList.add('bg-yellow-700', 'border-yellow-500', 'text-yellow-100');
    btn.classList.remove('bg-gray-800', 'border-gray-700', 'text-gray-200');
    const btnMine = document.getElementById('btn-show-mine');
    btnMine.classList.remove('bg-cyan-700', 'border-cyan-500', 'text-cyan-100');
    btnMine.classList.add('bg-gray-800', 'border-gray-700', 'text-gray-200');
    const match = Object.values(entityMap).find(it => it.owner_id === friendId);
    if (match) scrollGridToCell(match.grid_x, match.grid_y);
  }
  draw();
}

function toggleFilter(mode) {
  _viewFilter = _viewFilter === mode ? null : mode;
  const btnMine = document.getElementById('btn-show-mine');
  const active  = _viewFilter === 'own';
  btnMine.classList.toggle('bg-cyan-700',     active);
  btnMine.classList.toggle('border-cyan-500', active);
  btnMine.classList.toggle('text-cyan-100',   active);
  btnMine.classList.toggle('bg-gray-800',     !active);
  btnMine.classList.toggle('border-gray-700', !active);
  btnMine.classList.toggle('text-gray-200',   !active);
  const btnFr = document.getElementById('btn-friends');
  btnFr.textContent = '👥 Friends ▾';
  btnFr.classList.remove('bg-yellow-700', 'border-yellow-500', 'text-yellow-100');
  btnFr.classList.add('bg-gray-800', 'border-gray-700', 'text-gray-200');
  if (active) {
    const mine = Object.values(entityMap).find(it => it.owner_id === PLAYER_ID && it.type === 'castle');
    if (mine) scrollGridToCell(mine.grid_x, mine.grid_y);
  }
  draw();
}

function toggleZoomAll() {
  if (_zoomAllMode) {
    _zoomAllMode = false;
    document.getElementById('btn-zoom-all').textContent = '⊡ Zoom All';
    setZoom(1.0);
    return;
  }
  const entities = Object.values(entityMap).filter(e => e.type !== 'decoration');
  if (!entities.length) return;
  const xs = entities.map(e => e.grid_x), ys = entities.map(e => e.grid_y);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const spanX = Math.max(1, maxX - minX + 2), spanY = Math.max(1, maxY - minY + 2);
  cam.zoom = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX,
    Math.min(canvas.width / (spanX * BASE_CELL), canvas.height / (spanY * BASE_CELL)),
  ));
  _zoomAllMode = true;
  document.getElementById('btn-zoom-all').textContent = '↩ Restore';
  scrollGridToCell(Math.round((minX + maxX) / 2), Math.round((minY + maxY) / 2));
  updateZoomUI();
}

// ── Legend ────────────────────────────────────────────────────────────
const LEGEND_ITEMS = [
  { label: 'Your Castle',     color: EC.castle_own,   icon: 'castle' },
  { label: 'Enemy Castle',    color: EC.castle_other, icon: 'castle' },
  { label: 'Your Fort',       color: EC.fort_own,     icon: 'fort' },
  { label: 'Enemy Fort',      color: EC.fort_enemy,   icon: 'fort' },
  { label: 'Abandoned Fort',  color: EC.fort_monster, icon: 'fort' },
  { label: 'Monster Camp',    color: EC.camp,         icon: 'monster_camp' },
];
const LOCATION_ICON = {
  castle:       `${THEME_PATH}/locations/castle.svg`,
  fort:         `${THEME_PATH}/locations/fort.svg`,
  monster_camp: `${THEME_PATH}/locations/monster-camp.svg`,
};

function renderLegendTile(col, iconKey) {
  const bg = ecRgba(col);
  const iconPath = LOCATION_ICON[iconKey] || '';
  const icon = iconPath
    ? `<img src="${iconPath}" alt="" aria-hidden="true" style="position:absolute;top:8%;left:8%;width:84%;height:84%;object-fit:contain;pointer-events:none;">`
    : '';
  return `<span class="relative inline-block w-5 h-5 rounded-sm shrink-0 border border-white/15" style="background:${bg};">${icon}</span>`;
}

function renderLegend() {
  const body = document.getElementById('legend-body');
  if (!body) return;
  body.innerHTML = LEGEND_ITEMS.map(item =>
    `<div class="flex items-center gap-2 min-w-0">${renderLegendTile(item.color, item.icon)}<span class="truncate">${item.label}</span></div>`
  ).join('');
}

function syncLegendUi() {
  const body  = document.getElementById('legend-body');
  const caret = document.getElementById('legend-caret');
  body.classList.toggle('hidden', !legendOpen);
  caret.textContent = legendOpen ? '▾' : '▸';
}

document.getElementById('legend-toggle').addEventListener('click', () => {
  legendOpen = !legendOpen;
  writeBoolPref(WORLD_MAP_PREFS.legendOpen, legendOpen);
  syncLegendUi();
});

// ── Labels toggle ──────────────────────────────────────────────────────
document.getElementById('toggle-labels').addEventListener('change', e => {
  showLabels = e.target.checked;
  writeBoolPref(WORLD_MAP_PREFS.showLabels, showLabels);
  draw();
});

// ── Boot ───────────────────────────────────────────────────────────────
function restoreMapPrefs() {
  showLabels = readBoolPref(WORLD_MAP_PREFS.showLabels, false);
  legendOpen = readBoolPref(WORLD_MAP_PREFS.legendOpen, true);
  const toggle = document.getElementById('toggle-labels');
  if (toggle) toggle.checked = showLabels;
  syncLegendUi();
}

restoreMapPrefs();
restoreCamPref();
renderLegend();
resizeCanvas();   // sizes canvas, clamps camera, triggers first draw
loadMap();
loadFriends();
updateZoomUI();
setInterval(loadMap, 10000);
