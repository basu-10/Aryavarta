"""
grid.py — Grid manages cell occupancy on the battlefield.

Responsibilities:
- Track which unit occupies each (row, col) cell.
- Validate bounds.
- Provide helpers for querying free / occupied cells.
"""

from __future__ import annotations
from typing import Optional


class Grid:
    def __init__(self, rows: int, cols: int) -> None:
        self.rows = rows
        self.cols = cols
        # (row, col) -> unit_id
        self._occupancy: dict[tuple[int, int], str] = {}

    # ------------------------------------------------------------------ #
    # Mutation                                                             #
    # ------------------------------------------------------------------ #

    def place(self, unit_id: str, row: int, col: int) -> bool:
        """Place unit on cell. Returns False if out-of-bounds or occupied."""
        if not self.in_bounds(row, col):
            return False
        if self.is_occupied(row, col):
            return False
        self._occupancy[(row, col)] = unit_id
        return True

    def remove(self, row: int, col: int) -> Optional[str]:
        """Remove and return the unit_id from a cell (None if empty)."""
        return self._occupancy.pop((row, col), None)

    def move_unit(self, old_row: int, old_col: int, new_row: int, new_col: int) -> bool:
        """
        Atomically move a unit from old cell to new cell.
        Returns False if new cell is out-of-bounds or occupied.
        """
        if not self.in_bounds(new_row, new_col):
            return False
        if self.is_occupied(new_row, new_col):
            return False
        unit_id = self._occupancy.pop((old_row, old_col), None)
        if unit_id is None:
            return False
        self._occupancy[(new_row, new_col)] = unit_id
        return True

    # ------------------------------------------------------------------ #
    # Query                                                                #
    # ------------------------------------------------------------------ #

    def is_occupied(self, row: int, col: int) -> bool:
        return (row, col) in self._occupancy

    def in_bounds(self, row: int, col: int) -> bool:
        return 0 <= row < self.rows and 0 <= col < self.cols

    def get_unit_id(self, row: int, col: int) -> Optional[str]:
        return self._occupancy.get((row, col))

    def occupied_cells(self) -> list[tuple[int, int]]:
        return list(self._occupancy.keys())

    def snapshot(self) -> dict[tuple[int, int], str]:
        """Return a shallow copy of the occupancy map (for movement planning)."""
        return dict(self._occupancy)

    def __repr__(self) -> str:  # pragma: no cover
        rows = []
        for r in range(self.rows):
            row = []
            for c in range(self.cols):
                uid = self._occupancy.get((r, c), ".")
                # Truncate to 4 chars for display
                row.append(f"{uid[:4]:4s}" if uid != "." else "  . ")
            rows.append("|" + "|".join(row) + "|")
        return "\n".join(rows)
