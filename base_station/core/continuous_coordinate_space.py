"""
ContinuousCoordinateSpace - continuous 1000x1000 world-space utilities.

The backend models every entity with real-valued `(x, y)` positions inside a
`0..1000` square. The frontend can project that space onto any display grid
without the backend needing to know about presentation cells.
"""

from __future__ import annotations

import math
import re
from typing import Tuple


DISPLAY_ROWS = ["Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Golf", "Hotel"]
DISPLAY_ROW_LOOKUP = {label.upper(): index for index, label in enumerate(DISPLAY_ROWS)}
DISPLAY_NUMBER_WORDS = {
    "ONE": 1,
    "TWO": 2,
    "THREE": 3,
    "FOUR": 4,
    "FIVE": 5,
    "SIX": 6,
    "SEVEN": 7,
    "EIGHT": 8,
}


class ContinuousCoordinateSpace:
    """Coordinate helpers for a continuous 2D world."""

    SPACE_SIZE = 1000.0
    DISPLAY_GRID_SIZE = 8
    DISPLAY_CELL_SIZE = SPACE_SIZE / DISPLAY_GRID_SIZE

    def clamp_position(self, x: float, y: float) -> Tuple[float, float]:
        """Clamp a point to the valid world bounds."""
        return (
            max(0.0, min(self.SPACE_SIZE, float(x))),
            max(0.0, min(self.SPACE_SIZE, float(y))),
        )

    def distance(self, pos1: Tuple[float, float], pos2: Tuple[float, float]) -> float:
        """Return Euclidean distance between two continuous positions."""
        return math.dist(pos1, pos2)

    def interpolate(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        progress: float,
    ) -> Tuple[float, float]:
        """Interpolate between two continuous positions."""
        progress = max(0.0, min(1.0, progress))
        return self.clamp_position(
            start[0] + (end[0] - start[0]) * progress,
            start[1] + (end[1] - start[1]) * progress,
        )

    def is_in_range(
        self,
        source_pos: Tuple[float, float],
        target_pos: Tuple[float, float],
        range_units: float,
    ) -> bool:
        """Return whether a target is within transmission range."""
        return self.distance(source_pos, target_pos) <= float(range_units)

    def display_sector_indices(self, position: Tuple[float, float]) -> Tuple[int, int]:
        """Project a world-space position into the frontend's 8x8 display grid."""
        x, y = self.clamp_position(*position)
        col = min(self.DISPLAY_GRID_SIZE - 1, int(x / self.DISPLAY_CELL_SIZE))
        row = min(self.DISPLAY_GRID_SIZE - 1, int(y / self.DISPLAY_CELL_SIZE))
        return row, col

    def display_sector_label(self, position: Tuple[float, float]) -> str:
        """Return a human-readable 8x8 sector label such as `Bravo-3`."""
        row, col = self.display_sector_indices(position)
        return f"{DISPLAY_ROWS[row]}-{col + 1}"

    def sector_center(self, row_idx: int, col_idx: int) -> Tuple[float, float]:
        """Return the continuous-space center of a single 8x8 display sector."""
        safe_row = max(0, min(self.DISPLAY_GRID_SIZE - 1, int(row_idx)))
        safe_col = max(0, min(self.DISPLAY_GRID_SIZE - 1, int(col_idx)))
        return self.clamp_position(
            (safe_col + 0.5) * self.DISPLAY_CELL_SIZE,
            (safe_row + 0.5) * self.DISPLAY_CELL_SIZE,
        )

    def location_to_display_indices(self, raw_location: str | None) -> Tuple[int, int | None] | None:
        """Parse spoken/display sector labels into `(row, column)` display indices."""
        if not raw_location:
            return None

        normalized = re.sub(r"[^A-Z0-9]+", " ", raw_location.upper()).strip()
        parts = normalized.split()
        if not parts:
            return None

        while parts and parts[0] in {"GRID", "SECTOR"}:
            parts = parts[1:]

        if not parts:
            return None

        row_idx = DISPLAY_ROW_LOOKUP.get(parts[0])
        if row_idx is None:
            return None

        if len(parts) == 1:
            return row_idx, None

        column_token = parts[1]
        if column_token.isdigit():
            column_number = int(column_token)
        else:
            column_number = DISPLAY_NUMBER_WORDS.get(column_token, 0)

        if column_number <= 0:
            return row_idx, None

        col_idx = max(0, min(self.DISPLAY_GRID_SIZE - 1, column_number - 1))
        return row_idx, col_idx

    def location_to_point(self, raw_location: str | None) -> Tuple[float, float]:
        """
        Map a spoken/display mission target to a continuous point.

        Supported examples:
        - `Grid Alpha`
        - `Grid Bravo`
        - `Grid Hotel`
        - `Grid Alpha 1`
        - `Grid Delta 6`
        - `Grid Hotel 8`
        """
        if not raw_location:
            return (self.SPACE_SIZE / 2.0, self.SPACE_SIZE / 2.0)

        indices = self.location_to_display_indices(raw_location)
        if indices is None:
            return (self.SPACE_SIZE / 2.0, self.SPACE_SIZE / 2.0)

        row_idx, col_idx = indices
        if col_idx is None:
            return self.clamp_position(
                self.SPACE_SIZE / 2.0,
                (row_idx + 0.5) * self.DISPLAY_CELL_SIZE,
            )

        return self.sector_center(row_idx, col_idx)
