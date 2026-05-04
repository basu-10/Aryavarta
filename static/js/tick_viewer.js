/**
 * tick_viewer.js — Alpine.js component for the BattleCells replay stepper.
 *
 * Reads TICK_DATA, GRID_ROWS, GRID_COLS, WINNER, TOTAL_TICKS from the
 * globals injected by results.html.
 *
 * No build step required — loaded as a plain <script> tag after Alpine.
 */

function tickViewer() {
  return {
    // ── State ─────────────────────────────────────────────────────────── //
    ticks: [],
    currentTick: 0,
    totalTicks: 0,
    winner: '',
    playing: false,
    playSpeed: 860,  // ms per tick (about 0.7x of previous default)
    _playTimer: null,
    prevBattleUrl: null,
    nextBattleUrl: null,
    damageBubblesByCell: {},
    _keydownHandler: null,

    // ── Derived (computed from currentTick) ───────────────────────────── //
    get currentSnap() {
      return this.ticks[this.currentTick] || { cells: {}, log: [], units: [] };
    },
    get currentLog() {
      return this.currentSnap.log || [];
    },
    get currentUnits() {
      return this.currentSnap.units || [];
    },

    /** Build a flat list of {type, tick, text, key} entries for the full tick log. */
    get fullTickLog() {
      const entries = [];
      for (let t = 0; t < this.ticks.length; t++) {
        const snap = this.ticks[t];
        const log = (snap && snap.log) || [];
        entries.push({ type: 'header', tick: t, text: `Tick ${t}`, key: `h-${t}` });
        if (log.length === 0) {
          entries.push({ type: 'event', tick: t, text: '(no events)', key: `e-${t}-empty` });
        } else {
          for (let i = 0; i < log.length; i++) {
            entries.push({ type: 'event', tick: t, text: log[i], key: `e-${t}-${i}` });
          }
        }
      }
      return entries;
    },

    // ── HP Pool helpers ────────────────────────────────────────────────── //
    get poolAHp()       { return this.currentSnap.pool_a_hp       ?? 0; },
    get poolBHp()       { return this.currentSnap.pool_b_hp       ?? 0; },
    get poolAInitial()  { return this.currentSnap.pool_a_initial  ?? 1; },
    get poolBInitial()  { return this.currentSnap.pool_b_initial  ?? 1; },
    poolAPercent()  { return Math.max(0, Math.round(this.poolAHp / this.poolAInitial * 100)); },
    poolBPercent()  { return Math.max(0, Math.round(this.poolBHp / this.poolBInitial * 100)); },
    fmtPoolHp(n) {
      if (!n && n !== 0) return '?';
      if (n >= 1_000_000_000) return (n / 1_000_000_000).toFixed(1).replace(/\.0$/, '') + 'B';
      if (n >= 1_000_000)     return (n / 1_000_000).toFixed(1).replace(/\.0$/, '') + 'M';
      if (n >= 1_000)         return (n / 1_000).toFixed(1).replace(/\.0$/, '') + 'k';
      return String(n);
    },

    // ── Lifecycle ─────────────────────────────────────────────────────── //
    init() {
      this.ticks = TICK_DATA;
      this.totalTicks = TOTAL_TICKS;
      this.winner = WINNER;
      this.prevBattleUrl = (typeof PREV_BATTLE_URL !== 'undefined') ? PREV_BATTLE_URL : null;
      this.nextBattleUrl = (typeof NEXT_BATTLE_URL !== 'undefined') ? NEXT_BATTLE_URL : null;
      this.GRID_ROWS = GRID_ROWS;
      this.GRID_COLS = GRID_COLS;
      // Scroll log to current tick whenever currentTick changes
      this.$watch('currentTick', () => {
        // Clear-and-rebuild to avoid stale popup ghosting between frames.
        this._rebuildDamageBubbles();
        this._scrollLogToTick();
      });
      this._bindKeyboardShortcuts();
      this._rebuildDamageBubbles();
    },

    _bindKeyboardShortcuts() {
      if (this._keydownHandler) {
        window.removeEventListener('keydown', this._keydownHandler);
      }
      this._keydownHandler = (e) => this._onKeyDown(e);
      window.addEventListener('keydown', this._keydownHandler);
    },

    _onKeyDown(e) {
      if (this._shouldIgnoreKeyTarget(e)) return;

      const isCtrlNav = (e.ctrlKey || e.metaKey) && (e.key === 'ArrowLeft' || e.key === 'ArrowRight');
      if (isCtrlNav) {
        e.preventDefault();
        if (e.key === 'ArrowLeft') this.goToPrevBattle();
        if (e.key === 'ArrowRight') this.goToNextBattle();
        return;
      }

      if (e.key === ' ') {
        e.preventDefault();
        this.togglePlay();
        return;
      }

      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        this.prev();
        return;
      }

      if (e.key === 'ArrowRight') {
        e.preventDefault();
        this.next();
      }
    },

    _shouldIgnoreKeyTarget(e) {
      const el = e && e.target ? e.target : null;
      if (!el) return false;
      const tag = (el.tagName || '').toLowerCase();
      return el.isContentEditable || ['input', 'textarea', 'select', 'button'].includes(tag);
    },

    goToPrevBattle() {
      if (!this.prevBattleUrl) return;
      window.location.assign(this.prevBattleUrl);
    },

    goToNextBattle() {
      if (!this.nextBattleUrl) return;
      window.location.assign(this.nextBattleUrl);
    },

    _rebuildDamageBubbles() {
      this.damageBubblesByCell = {};

      const snap = this.currentSnap || {};
      const events = snap.events || [];
      if (!events.length) return;

      const unitMap = {};
      for (const u of (snap.units || [])) {
        unitMap[u.unit_id] = u;
      }

      const prev = this.prevSnap();
      const prevUnitMap = {};
      for (const u of (prev && prev.units ? prev.units : [])) {
        prevUnitMap[u.unit_id] = u;
      }

      let bubbleIdx = 0;
      for (const ev of events) {
        if (ev.type !== 'attack') continue;
        const dmg = Number(ev.damage);
        if (!Number.isFinite(dmg) || dmg <= 0) continue;

        const target = unitMap[ev.target_id] || prevUnitMap[ev.target_id];
        if (!target || target.row === undefined || target.col === undefined) continue;

        const cellKey = `${target.row},${target.col}`;
        if (!this.damageBubblesByCell[cellKey]) this.damageBubblesByCell[cellKey] = [];
        this.damageBubblesByCell[cellKey].push({
          id: `dmg-${this.currentTick}-${bubbleIdx++}`,
          text: `-${Math.round(dmg)}`,
        });
      }
    },

    getBattlefieldDamagePopups(r, c) {
      const key = `${r},${c}`;
      return this.damageBubblesByCell[key] || [];
    },

    _scrollLogToTick() {
      this.$nextTick(() => {
        const el = document.getElementById(`tick-log-${this.currentTick}`);
        const container = this.$refs.tickLogScroll;
        if (el && container) {
          const elTop = el.offsetTop;
          const elH = el.offsetHeight;
          const cH = container.clientHeight;
          container.scrollTop = elTop - cH / 2 + elH / 2;
        }
      });
    },

    // ── Navigation ────────────────────────────────────────────────────── //
    next() {
      if (this.currentTick < this.totalTicks) {
        this.currentTick++;
      } else {
        this.stopPlay();
      }
    },

    prev() {
      if (this.currentTick > 0) this.currentTick--;
    },

    goTo(tick) {
      this.currentTick = Math.max(0, Math.min(tick, this.totalTicks));
    },

    // ── Auto-play ─────────────────────────────────────────────────────── //
    togglePlay() {
      if (this.playing) {
        this.stopPlay();
      } else {
        this.startPlay();
      }
    },

    startPlay() {
      if (this.currentTick >= this.totalTicks) {
        this.currentTick = 0;
      }
      this.playing = true;
      this._scheduleNext();
    },

    stopPlay() {
      this.playing = false;
      if (this._playTimer) {
        clearTimeout(this._playTimer);
        this._playTimer = null;
      }
    },

    _scheduleNext() {
      if (!this.playing) return;
      this._playTimer = setTimeout(() => {
        if (this.currentTick < this.totalTicks) {
          this.currentTick++;
          this._scheduleNext();
        } else {
          this.stopPlay();
        }
      }, parseInt(this.playSpeed, 10));
    },

    // ── Grid rendering ────────────────────────────────────────────────── //
    isNeutral(c) {
      // Column 5 is no-man's land; columns 0 and 10 are defense columns
      // Defense cols are shown with a distinct style but are not "neutral" blocked cells
      return c === 5;
    },

    isDefenseCol(c) {
      return c === 0 || c === GRID_COLS - 1;
    },

    getCell(r, c) {
      const key = `${r},${c}`;
      return this.currentSnap.cells ? (this.currentSnap.cells[key] || null) : null;
    },

    getCellClass(r, c) {
      const cell = this.getCell(r, c);
      if (this.isNeutral(c)) {
        return cell ? 'bc-cell-neutral ring-1 ring-inset ring-amber-200/35' : 'bc-cell-neutral';
      }
      // Defense columns use a darker variant of each team's color
      if (c === 0) {
        return cell ? 'bc-cell-a ring-2 ring-inset ring-blue-300/50 opacity-90' : 'bc-cell-a opacity-60';
      }
      if (c === GRID_COLS - 1) {
        return cell ? 'bc-cell-b ring-2 ring-inset ring-red-300/50 opacity-90' : 'bc-cell-b opacity-60';
      }
      const teamCls = c < 5 ? 'bc-cell-a' : 'bc-cell-b';
      if (cell) return teamCls + ' ring-1 ring-inset ring-white/20';
      return teamCls;
    },

    // Shared battlefield component adapters
    canClickBattlefieldCells: false,
    allowNeutralUnits: true,
    showNeutralOccupiedMarker: true,
    showColumnFillControls: false,
    battlefieldIconClass: 'w-14 h-14',
    battlefieldFallbackClass: 'text-xl',
    battlefieldStatClass: 'text-[10px]',
    getBattlefieldRows() {
      return GRID_ROWS;
    },
    getBattlefieldCols() {
      return GRID_COLS;
    },
    isBattlefieldColumnVisible(c) {
      void c;
      return true;
    },
    getBattlefieldCell(r, c) {
      return this.getCell(r, c);
    },
    getBattlefieldCellClass(r, c) {
      return this.getCellClass(r, c);
    },
    getBattlefieldCellStyle(r, c) {
      void r;
      void c;
      return '';
    },
    onBattlefieldCellClick(r, c) {
      void r;
      void c;
    },
    canFillColumn(c) {
      void c;
      return false;
    },
    onFillColumn(c) {
      void c;
    },
    getBattlefieldCellVisual(cell, r, c) {
      return this.troopVisualForCell(cell, r, c);
    },
    getBattlefieldCellFallback(cell) {
      return cell && cell.type ? cell.type : '';
    },
    getBattlefieldCellText(cell) {
      return this.hpBar(cell);
    },

    unitInitial(type) {
      const map = { Barbarian: 'B', Archer: '🏹' };
      return map[type] || type[0];
    },

    troopAssets(type) {
      const map = {
        Archer: {
          icon: '/assets/theme1/troops/human/map-icons/archer.svg',
          animations: {
            idle: '/assets/theme1/troops/human/animations/archer/idle.gif',
            walk: '/assets/theme1/troops/human/animations/archer/walk.gif',
            attack: '/assets/theme1/troops/human/animations/archer/attack.gif',
            hurt: '/assets/theme1/troops/human/animations/archer/hurt.gif',
            death: '/assets/theme1/troops/human/animations/archer/death.gif',
          },
        },
        Barbarian: {
          icon: '/assets/theme1/troops/human/map-icons/archer.svg',
          animations: {
            idle: '/assets/theme1/troops/human/animations/barbarian/idle.gif',
            walk: '/assets/theme1/troops/human/animations/barbarian/walk.gif',
            attack: '/assets/theme1/troops/human/animations/barbarian/attack.gif',
            hurt: '/assets/theme1/troops/human/animations/barbarian/hurt.gif',
            death: '/assets/theme1/troops/human/animations/barbarian/death.gif',
          },
        },
        Longbowman: { icon: '/assets/theme1/troops/human/map-icons/longbowman.svg' },
        Hussar: { icon: '/assets/theme1/troops/human/map-icons/hussar.svg' },
        Troll: { icon: '/assets/theme1/troops/monster/map-icons/troll.svg' },
        Wraith: { icon: '/assets/theme1/troops/monster/map-icons/wraith.svg' },
      };
      return map[type] || null;
    },

    troopIcon(type) {
      const asset = this.troopAssets(type);
      return asset ? (asset.icon || '') : '';
    },

    troopVisual(type, action = 'idle') {
      const asset = this.troopAssets(type);
      if (!asset) return '';
      if (asset.animations && asset.animations[action]) return asset.animations[action];
      return asset.icon || '';
    },

    prevSnap() {
      if (this.currentTick <= 0) return null;
      return this.ticks[this.currentTick - 1] || null;
    },

    prevUnitById(unitId) {
      const prev = this.prevSnap();
      if (!prev || !prev.units) return null;
      return prev.units.find((u) => u.unit_id === unitId) || null;
    },

    findCurrentUnit(r, c, cell) {
      const alive = this.currentUnits.find(
        (u) => u.row === r && u.col === c && u.type === cell.type && u.status !== 'dead'
      );
      if (alive) return alive;
      return this.currentUnits.find(
        (u) => u.row === r && u.col === c && u.type === cell.type
      ) || null;
    },

    cellAction(r, c, cell) {
      const unit = this.findCurrentUnit(r, c, cell);

      if (unit && unit.status === 'dead') return 'death';
      if (unit && unit.action === 'attack') return 'attack';
      if (unit && unit.action === 'move') return 'walk';

      if (unit) {
        const prevUnit = this.prevUnitById(unit.unit_id);
        if (prevUnit && Number(prevUnit.hp) > Number(unit.hp)) return 'hurt';
      }

      const prev = this.prevSnap();
      const prevCell = prev && prev.cells ? (prev.cells[`${r},${c}`] || null) : null;
      if (prevCell && prevCell.type === cell.type && Number(prevCell.hp) > Number(cell.hp)) {
        return 'hurt';
      }

      return 'idle';
    },

    troopVisualForCell(cell, r, c) {
      if (!cell) return '';
      const action = this.cellAction(r, c, cell);
      return this.troopVisual(cell.type, action);
    },

    survivingQty(cell) {
      if (!cell) return 0;
      const qty = cell.quantity || 1;
      if (qty <= 1) return cell.hp > 0 ? 1 : 0;
      const maxHp = cell.max_hp || 1;
      return Math.max(0, Math.floor(cell.hp / (maxHp / qty)));
    },

    hpBar(cell) {
      if (!cell) return '';
      const qty = cell.quantity || 1;
      if (qty > 1) {
        const surviving = this.survivingQty(cell);
        return `×${surviving}/${qty}`;
      }
      return `${cell.hp}/${cell.max_hp} HP`;
    },

    // ── Per-cell action log ────────────────────────────────────────────── //
    /**
     * Build a rich action log for the current tick from the events array.
     * Each entry: { icon, actor, teamA, verb, target, teamB, detail }
     */
    buildActionLog() {
      const snap = this.currentSnap;
      const events = snap.events || [];
      if (!events.length) return [];

      // Build unit lookup: unit_id -> {type, team, row, col, hp, max_hp}
      const unitMap = {};
      for (const u of (snap.units || [])) {
        unitMap[u.unit_id] = u;
      }
      // For deaths, also check previous snap units
      const prevSnap = this.prevSnap();
      const prevUnitMap = {};
      for (const u of (prevSnap && prevSnap.units ? prevSnap.units : [])) {
        prevUnitMap[u.unit_id] = u;
      }

      const entries = [];

      for (const ev of events) {
        if (ev.type === 'attack') {
          const att = unitMap[ev.attacker_id] || prevUnitMap[ev.attacker_id] || {};
          const tgt = unitMap[ev.target_id] || prevUnitMap[ev.target_id] || {};
          const attPos = att.row !== undefined ? `[${att.row},${att.col}]` : '';
          const tgtPos = tgt.row !== undefined ? `[${tgt.row},${tgt.col}]` : '';
          const tgtHpBefore = (prevUnitMap[ev.target_id] || {}).hp;
          const tgtHpAfter  = tgt.hp;
          const hpDetail = (tgtHpBefore !== undefined && tgtHpAfter !== undefined)
            ? `${ev.damage} dmg  (${tgtHpBefore} → ${Math.max(0, tgtHpAfter)} HP)`
            : `${ev.damage} dmg`;
          entries.push({
            icon: '⚔',
            actor:  `${att.type || ev.attacker_id} ${attPos}`,
            teamA:  att.team || 'A',
            verb:   'attacked',
            target: `${tgt.type || ev.target_id} ${tgtPos}`,
            teamB:  tgt.team || 'B',
            detail: hpDetail,
          });
        } else if (ev.type === 'move') {
          const u = unitMap[ev.unit_id] || prevUnitMap[ev.unit_id] || {};
          entries.push({
            icon: '→',
            actor:  `${u.type || ev.unit_id}`,
            teamA:  u.team || 'A',
            verb:   `moved [${ev.from[0]},${ev.from[1]}] → [${ev.to[0]},${ev.to[1]}]`,
            target: null,
            teamB:  null,
            detail: null,
          });
        } else if (ev.type === 'retreat') {
          const u = unitMap[ev.unit_id] || prevUnitMap[ev.unit_id] || {};
          entries.push({
            icon: '↩',
            actor:  `${u.type || ev.unit_id}`,
            teamA:  u.team || 'A',
            verb:   `retreated [${ev.from[0]},${ev.from[1]}] → [${ev.to[0]},${ev.to[1]}]`,
            target: null,
            teamB:  null,
            detail: null,
          });
        } else if (ev.type === 'blocked') {
          const u = unitMap[ev.unit_id] || prevUnitMap[ev.unit_id] || {};
          entries.push({
            icon: '✗',
            actor:  `${u.type || ev.unit_id}`,
            teamA:  u.team || 'A',
            verb:   `blocked at [${ev.pos[0]},${ev.pos[1]}]`,
            target: null,
            teamB:  null,
            detail: null,
          });
        } else if (ev.type === 'pool_attack') {
          const attackerTeam = ev.target_pool === 'B' ? 'A' : 'B';
          entries.push({
            icon: '💥',
            actor:  `Team ${attackerTeam}`,
            teamA:  attackerTeam,
            verb:   `struck Team ${ev.target_pool} base for`,
            target: `${this.fmtPoolHp(ev.damage)} dmg`,
            teamB:  ev.target_pool,
            detail: `pool HP: ${this.fmtPoolHp(ev.pool_hp)}`,
          });
        } else if (ev.type === 'death') {
          const u = unitMap[ev.unit_id] || prevUnitMap[ev.unit_id] || {};
          const pos = u.row !== undefined ? ` [${u.row},${u.col}]` : '';
          entries.push({
            icon: '☠',
            actor:  `${u.type || ev.unit_id}${pos}`,
            teamA:  u.team || 'A',
            verb:   'eliminated',
            target: null,
            teamB:  null,
            detail: null,
          });
        }
      }

      return entries;
    },

    // ── Log rendering ─────────────────────────────────────────────────── //
    logLineClass(line) {
      if (line.includes('eliminated')) return 'text-red-400';
      if (line.includes('attacked')) return 'text-yellow-300';
      if (line.includes('moved')) return 'text-green-400';
      if (line.includes('blocked')) return 'text-gray-500';
      return 'text-gray-400';
    },

    // ── Summary helpers ───────────────────────────────────────────────── //
    winnerLabel() {
      if (this.winner === 'A') return 'Team A (Blue) wins!';
      if (this.winner === 'B') return 'Team B (Red) wins!';
      return 'Draw';
    },

    actionLabel(u) {
      if (u.status === 'dead') return '☠ dead';
      if (u.action === 'attack') {
        return `⚔ attacked ${u.target_id || '?'} (${u.damage_dealt} dmg)`;
      }
      if (u.action === 'move') return '→ moved';
      if (u.action === 'blocked') return '✗ blocked';
      if (u.action === 'hold') return '⏸ holding';
      return u.action || '—';
    },
  };
}
