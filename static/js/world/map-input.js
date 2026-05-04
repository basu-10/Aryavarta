// ── Pointer drag (pan) ─────────────────────────────────────────────────
let _drag = null, _camAtDrag = null, _wasDragging = false;

canvas.addEventListener('pointerdown', e => {
  if (e.button === 2) return;
  _drag = { x: e.clientX, y: e.clientY };
  _camAtDrag = { x: cam.x, y: cam.y };
  _wasDragging = false;
  canvas.setPointerCapture(e.pointerId);
});
canvas.addEventListener('pointermove', e => {
  if (!_drag) return;
  const dx = e.clientX - _drag.x, dy = e.clientY - _drag.y;
  if (!_wasDragging && (Math.abs(dx) > 4 || Math.abs(dy) > 4)) _wasDragging = true;
  if (!_wasDragging) return;
  cam.x = _camAtDrag.x - dx / cam.zoom;
  cam.y = _camAtDrag.y - dy / cam.zoom;
  clampCamera();
  draw();
});
canvas.addEventListener('pointerup',     e => { if (!_wasDragging && _drag) handleCanvasClick(e); _drag = null; _camAtDrag = null; });
canvas.addEventListener('pointercancel', () => { _drag = null; _camAtDrag = null; });

// ── Wheel zoom (toward cursor) ─────────────────────────────────────────
canvas.addEventListener('wheel', e => {
  e.preventDefault();
  const rect = canvas.getBoundingClientRect();
  const sx = e.clientX - rect.left, sy = e.clientY - rect.top;
  const { x: wx, y: wy } = screenToWorld(sx, sy);
  cam.zoom = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, cam.zoom + (e.deltaY < 0 ? ZOOM_STEP : -ZOOM_STEP)));
  cam.x = wx - sx / cam.zoom;
  cam.y = wy - sy / cam.zoom;
  clampCamera();
  updateZoomUI();
  saveCamPref();
  draw();
}, { passive: false });

// ── Keyboard pan ──────────────────────────────────────────────────────
const _keysHeld = new Set();
let   _keyPanRaf = null;

canvas.addEventListener('keydown', e => {
  if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
    e.preventDefault();
    _keysHeld.add(e.key);
    if (!_keyPanRaf) _keyPanRaf = requestAnimationFrame(_keyPanLoop);
  }
});
canvas.addEventListener('keyup', e => _keysHeld.delete(e.key));
window.addEventListener('blur',  () => _keysHeld.clear());

function _keyPanLoop() {
  if (!_keysHeld.size) { _keyPanRaf = null; return; }
  const spd = (BASE_CELL * 5) / cam.zoom / 16;
  if (_keysHeld.has('ArrowLeft'))  cam.x -= spd;
  if (_keysHeld.has('ArrowRight')) cam.x += spd;
  if (_keysHeld.has('ArrowUp'))    cam.y -= spd;
  if (_keysHeld.has('ArrowDown'))  cam.y += spd;
  clampCamera();
  draw();
  _keyPanRaf = requestAnimationFrame(_keyPanLoop);
}

// ── Scroll-button camera pan (accessibility arrow buttons) ─────────────
const SCROLL_SPEED  = 130;
let   _scrollInterval = null;

function startMapScroll(dx, dy) {
  stopMapScroll();
  _scrollInterval = setInterval(() => {
    cam.x += dx * SCROLL_SPEED / cam.zoom;
    cam.y += dy * SCROLL_SPEED / cam.zoom;
    clampCamera();
    draw();
  }, 40);
}
function stopMapScroll() {
  if (_scrollInterval) { clearInterval(_scrollInterval); _scrollInterval = null; }
}

// ── scrollGridToCell — called by "See on Map" in global context menu ────
function scrollGridToCell(gx, gy) {
  cam.x = (gx + 0.5) * BASE_CELL - canvas.width  / 2 / cam.zoom;
  cam.y = (gy + 0.5) * BASE_CELL - canvas.height / 2 / cam.zoom;
  clampCamera();
  saveCamPref();
  draw();
}
