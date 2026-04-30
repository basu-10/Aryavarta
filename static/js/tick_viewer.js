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
    playSpeed: 600,  // ms per tick
    _playTimer: null,

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

    // ── Lifecycle ─────────────────────────────────────────────────────── //
    init() {
      this.ticks = TICK_DATA;
      this.totalTicks = TOTAL_TICKS;
      this.winner = WINNER;
      this.GRID_ROWS = GRID_ROWS;
      this.GRID_COLS = GRID_COLS;
      // Scroll log to current tick whenever currentTick changes
      this.$watch('currentTick', () => this._scrollLogToTick());
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
      // Column 4 is no-man's land (TEAM_A_COLS=[0..3], TEAM_B_COLS=[5..8])
      return c === 4;
    },

    getCell(r, c) {
      const key = `${r},${c}`;
      return this.currentSnap.cells ? (this.currentSnap.cells[key] || null) : null;
    },

    getCellClass(r, c) {
      if (this.isNeutral(c)) return 'bc-cell-neutral';
      const teamCls = c < 4 ? 'bc-cell-a' : 'bc-cell-b';
      const cell = this.getCell(r, c);
      if (cell) return teamCls + ' ring-1 ring-inset ring-white/20';
      return teamCls;
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

    hpBar(cell) {
      if (!cell) return '';
      return `${cell.hp}/${cell.max_hp} HP`;
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
