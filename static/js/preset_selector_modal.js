function presetModalCardGrid(preset, options = {}) {
  const rows = Number.isInteger(options.rows) ? options.rows : 4;
  const cols = Number.isInteger(options.cols) ? options.cols : 9;
  const teamACols = Array.isArray(options.teamACols) ? options.teamACols : [0, 1, 2, 3];
  const teamBCols = Array.isArray(options.teamBCols) ? options.teamBCols : [5, 6, 7, 8];
  const mode = options.mode || 'both';

  const unitMap = {};
  for (const u of (preset.army_a || [])) {
    unitMap[`${u.row},${u.col}`] = u;
  }
  for (const u of (preset.army_b || [])) {
    unitMap[`${u.row},${u.col}`] = u;
  }

  return {
    preset,
    canClickBattlefieldCells: false,
    allowNeutralUnits: false,
    showNeutralOccupiedMarker: false,
    showEmptyBattlefieldMarker: false,
    showColumnFillControls: false,
    showBattlefieldLegend: false,
    battlefieldContainerClass: 'px-0',
    battlefieldIconClass: 'w-4 h-4',
    battlefieldFallbackClass: 'text-[10px]',
    battlefieldStatClass: 'text-[9px]',

    getBattlefieldRows() {
      return rows;
    },

    getBattlefieldCols() {
      return cols;
    },

    isBattlefieldColumnVisible(c) {
      if (mode === 'team_a') return teamACols.includes(c);
      return true;
    },

    isNeutral(c) {
      if (mode === 'team_a') return !teamACols.includes(c);
      return !teamACols.includes(c) && !teamBCols.includes(c);
    },

    getBattlefieldCell(r, c) {
      if (mode === 'team_a') {
        return (preset.army_a || []).find((u) => u.row === r && u.col === c) || null;
      }
      return unitMap[`${r},${c}`] || null;
    },

    getBattlefieldCellClass(r, c) {
      void r;
      const occupied = !!this.getBattlefieldCell(r, c);
      if (this.isNeutral(c)) return occupied ? 'bc-cell-neutral opacity-70' : 'bc-cell-neutral opacity-50';
      if (teamACols.includes(c)) return occupied ? 'bc-cell-a ring-1 ring-inset ring-white/30' : 'bc-cell-a';
      return occupied ? 'bc-cell-b ring-1 ring-inset ring-white/30' : 'bc-cell-b';
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

    troopIcon(type) {
      void type;
      return '';
    },

    getBattlefieldCellVisual(cell, r, c) {
      void cell;
      void r;
      void c;
      return '';
    },

    typeAbbrev(type) {
      const map = {
        Barbarian: 'B', Archer: 'AR', Troll: 'TR', Wraith: 'WR',
        Longbowman: 'LB', Hussar: 'HS', Cannon: 'CN', 'Archer Tower': 'AT',
        Demon: 'DM', Pegasus: 'PG',
      };
      return map[type] || type.replace(/[^A-Za-z]/g, '').slice(0, 3).toUpperCase();
    },

    getBattlefieldCellFallback(cell) {
      return this.typeAbbrev(cell.type);
    },

    fmtQty(n) {
      if (!n || n < 1) return '0';
      if (n >= 1000000000) return (n / 1000000000).toFixed(1).replace(/\.0$/, '') + 'B';
      if (n >= 1000000) return (n / 1000000).toFixed(1).replace(/\.0$/, '') + 'M';
      if (n >= 1000) return (n / 1000).toFixed(1).replace(/\.0$/, '') + 'k';
      return String(n);
    },

    getBattlefieldCellText(cell) {
      return 'x' + this.fmtQty(cell.quantity || 1);
    },
  };
}
