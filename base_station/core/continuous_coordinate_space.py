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

    def location_to_point(self, raw_location: str | None) -> Tuple[float, float]:
        """
        Map a coarse textual mission target to a continuous point.

        Supported examples:
        - `Grid Alpha`
        - `Grid Bravo`
        - `Grid Charlie`
        - `Grid Alpha 1`
        - `Grid Bravo 2`
        - `Grid Charlie 3`
        """
        if not raw_location:
            return (self.SPACE_SIZE / 2.0, self.SPACE_SIZE / 2.0)

        normalized = re.sub(r"[^A-Z0-9]+", " ", raw_location.upper()).strip()
        parts = normalized.split()
        if not parts:
            return (self.SPACE_SIZE / 2.0, self.SPACE_SIZE / 2.0)

        if parts[0] == "GRID":
            parts = parts[1:]

        col_lookup = {"ALPHA": 0, "BRAVO": 1, "CHARLIE": 2}
        col_idx = col_lookup.get(parts[0], 1)
        row_idx = 1

        if len(parts) > 1 and parts[1].isdigit():
            row_idx = max(0, min(2, int(parts[1]) - 1))

        third = self.SPACE_SIZE / 3.0
        x = third * (col_idx + 0.5)
        y = third * (row_idx + 0.5)
        return self.clamp_position(x, y)
