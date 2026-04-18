"""
GridCoordinateSystem - Bidirectional coordinate conversion and distance calculations.

NATO Phonetic Grid:
- Rows: Alpha(0) - Zulu(25)
- Columns: 1-26 (0-indexed as 0-25)
- Total: 26x26 = 676 cells

Distance: Euclidean (sqrt((x2-x1)^2 + (y2-y1)^2))
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple, Union

# NATO Phonetic Alphabet indexed 0-25
NATO_PHONETIC = [
    "Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot",
    "Golf", "Hotel", "India", "Juliet", "Kilo", "Lima",
    "Mike", "November", "Oscar", "Papa", "Quebec", "Romeo",
    "Sierra", "Tango", "Uniform", "Victor", "Whiskey", "X-ray",
    "Yankee", "Zulu"
]

# Reverse lookup for NATO names to indices
NATO_TO_INDEX = {name: idx for idx, name in enumerate(NATO_PHONETIC)}


class GridCoordinateSystem:
    """
    Bidirectional grid <-> pixel conversion and distance calculations.
    
    Grid coordinates: (row_idx: 0-25, col_idx: 0-25)
    Pixel coordinates: (x: 0-750, y: 0-750) with 30px cells
    Grid notation: "Alpha-1" to "Zulu-26"
    """

    GRID_SIZE = 26  # 26x26 grid (A-Z, 1-26)
    CELL_SIZE_PX = 30  # Pixels per cell
    CANVAS_SIZE_PX = GRID_SIZE * CELL_SIZE_PX  # 780x780

    def __init__(self, cell_size_px: int = 30):
        """
        Initialize coordinate system.
        
        Args:
            cell_size_px: Size of each grid cell in pixels (default 30)
        """
        self.cell_size_px = cell_size_px

    # ==================== Conversion Utilities ====================

    @staticmethod
    def row_index_to_nato(row_idx: int) -> str:
        """Convert row index (0-25) to NATO phonetic (Alpha-Zulu)."""
        if not (0 <= row_idx < 26):
            raise ValueError(f"Row index must be 0-25, got {row_idx}")
        return NATO_PHONETIC[row_idx]

    @staticmethod
    def nato_to_row_index(nato_name: str) -> int:
        """Convert NATO phonetic to row index (0-25)."""
        if nato_name not in NATO_TO_INDEX:
            raise ValueError(f"Invalid NATO phonetic: {nato_name}")
        return NATO_TO_INDEX[nato_name]

    @staticmethod
    def parse_grid_notation(grid_str: str) -> Tuple[int, int]:
        """
        Parse grid notation to (row_idx, col_idx).
        
        Examples:
            "Alpha-1" -> (0, 0)
            "Bravo-12" -> (1, 11)
            "Zulu-26" -> (25, 25)
        
        Args:
            grid_str: String like "Alpha-1" or "A1" (case-insensitive)
        
        Returns:
            (row_idx, col_idx) tuple
        """
        grid_str = grid_str.strip()
        
        # Try full NATO format: "Alpha-1"
        if "-" in grid_str:
            parts = grid_str.split("-")
            if len(parts) == 2:
                nato_name, col_str = parts
                try:
                    row_idx = GridCoordinateSystem.nato_to_row_index(nato_name.strip())
                    col_idx = int(col_str.strip()) - 1  # Convert 1-indexed to 0-indexed
                    if not (0 <= col_idx < 26):
                        raise ValueError(f"Column must be 1-26, got {col_idx + 1}")
                    return (row_idx, col_idx)
                except (ValueError, KeyError) as e:
                    raise ValueError(f"Invalid grid notation: {grid_str}") from e
        
        # Try short format: "A1" or "Z26"
        if len(grid_str) >= 2:
            nato_name = grid_str[0]
            col_str = grid_str[1:]
            try:
                row_idx = GridCoordinateSystem.nato_to_row_index(nato_name.upper())
                col_idx = int(col_str) - 1
                if not (0 <= col_idx < 26):
                    raise ValueError(f"Column must be 1-26, got {col_idx + 1}")
                return (row_idx, col_idx)
            except (ValueError, KeyError) as e:
                raise ValueError(f"Invalid grid notation: {grid_str}") from e
        
        raise ValueError(f"Invalid grid notation: {grid_str}")

    @staticmethod
    def build_grid_notation(row_idx: int, col_idx: int) -> str:
        """
        Build grid notation from (row_idx, col_idx).
        
        Examples:
            (0, 0) -> "Alpha-1"
            (1, 11) -> "Bravo-12"
            (25, 25) -> "Zulu-26"
        
        Args:
            row_idx: Row index (0-25)
            col_idx: Column index (0-25)
        
        Returns:
            String like "Alpha-1"
        """
        if not (0 <= row_idx < 26) or not (0 <= col_idx < 26):
            raise ValueError(f"Indices must be 0-25, got ({row_idx}, {col_idx})")
        row_name = GridCoordinateSystem.row_index_to_nato(row_idx)
        col_num = col_idx + 1  # Convert 0-indexed to 1-indexed
        return f"{row_name}-{col_num}"

    # ==================== Grid <-> Pixel Conversion ====================

    def grid_to_pixel(self, row_idx: int, col_idx: int) -> Tuple[float, float]:
        """
        Convert grid coordinates to pixel coordinates.
        
        Cell (0,0) at pixel center (15, 15) [half cell_size]
        Cell (0,1) at pixel center (45, 15) [cell_size + 15]
        
        Args:
            row_idx: Row index (0-25)
            col_idx: Column index (0-25)
        
        Returns:
            (px_x, px_y) tuple - pixel coordinates to cell center
        """
        if not (0 <= row_idx < 26) or not (0 <= col_idx < 26):
            raise ValueError(f"Indices must be 0-25, got ({row_idx}, {col_idx})")
        
        x = col_idx * self.cell_size_px + self.cell_size_px // 2
        y = row_idx * self.cell_size_px + self.cell_size_px // 2
        return (float(x), float(y))

    def pixel_to_grid(self, px_x: float, px_y: float) -> Tuple[int, int]:
        """
        Convert pixel coordinates to grid coordinates.
        
        Args:
            px_x: Pixel X coordinate (0-780)
            px_y: Pixel Y coordinate (0-780)
        
        Returns:
            (row_idx, col_idx) tuple - grid coordinates
        """
        col_idx = int(px_x // self.cell_size_px)
        row_idx = int(px_y // self.cell_size_px)
        
        # Clamp to grid bounds
        col_idx = max(0, min(25, col_idx))
        row_idx = max(0, min(25, row_idx))
        
        return (row_idx, col_idx)

    # ==================== Distance Calculations ====================

    @staticmethod
    def euclidean_distance(
        pos1: Union[Tuple[int, int], Tuple[float, float]],
        pos2: Union[Tuple[int, int], Tuple[float, float]]
    ) -> float:
        """
        Calculate Euclidean distance between two grid positions.
        
        Distance = sqrt((x2-x1)^2 + (y2-y1)^2)
        
        Args:
            pos1: (row_idx, col_idx) or (px_x, px_y)
            pos2: (row_idx, col_idx) or (px_x, px_y)
        
        Returns:
            Distance in grid units (cells) or pixels
        """
        dx = pos2[1] - pos1[1]  # col difference (x-axis)
        dy = pos2[0] - pos1[0]  # row difference (y-axis)
        return math.sqrt(dx * dx + dy * dy)

    def distance_in_cells(self, grid_pos1: Tuple[int, int], grid_pos2: Tuple[int, int]) -> float:
        """
        Calculate distance between two grid positions in cells.
        
        Args:
            grid_pos1: (row_idx, col_idx)
            grid_pos2: (row_idx, col_idx)
        
        Returns:
            Distance in grid cells
        """
        return self.euclidean_distance(grid_pos1, grid_pos2)

    def distance_in_pixels(self, px_pos1: Tuple[float, float], px_pos2: Tuple[float, float]) -> float:
        """
        Calculate distance between two pixel positions in pixels.
        
        Args:
            px_pos1: (px_x, px_y)
            px_pos2: (px_x, px_y)
        
        Returns:
            Distance in pixels
        """
        return self.euclidean_distance(px_pos1, px_pos2)

    # ==================== Transmission Range Checks ====================

    def is_in_range(
        self,
        source_pos: Tuple[int, int],
        target_pos: Tuple[int, int],
        range_cells: float
    ) -> bool:
        """
        Check if target is within transmission range of source.
        
        Args:
            source_pos: (row_idx, col_idx) of sender
            target_pos: (row_idx, col_idx) of receiver
            range_cells: Maximum transmission range in cells
        
        Returns:
            True if target is within range
        """
        distance = self.distance_in_cells(source_pos, target_pos)
        return distance <= range_cells

    def get_neighbors_in_range(
        self,
        source_pos: Tuple[int, int],
        range_cells: float,
        exclude_self: bool = True
    ) -> List[Tuple[int, int]]:
        """
        Get all grid cells within transmission range of source.
        
        Args:
            source_pos: (row_idx, col_idx) of sender
            range_cells: Maximum transmission range in cells
            exclude_self: If True, exclude source position from results
        
        Returns:
            List of (row_idx, col_idx) tuples within range
        """
        neighbors = []
        source_row, source_col = source_pos
        
        # Calculate bounding box for efficiency
        min_row = max(0, int(source_row - range_cells))
        max_row = min(25, int(source_row + range_cells) + 1)
        min_col = max(0, int(source_col - range_cells))
        max_col = min(25, int(source_col + range_cells) + 1)
        
        for row in range(min_row, max_row):
            for col in range(min_col, max_col):
                if exclude_self and (row, col) == source_pos:
                    continue
                if self.is_in_range(source_pos, (row, col), range_cells):
                    neighbors.append((row, col))
        
        return neighbors

    # ==================== Waypoint Generation ====================

    def generate_path(
        self,
        start_pos: Tuple[int, int],
        end_pos: Tuple[int, int],
        points_per_cell: int = 4
    ) -> List[Tuple[float, float]]:
        """
        Generate smooth path from start to end as pixel coordinates.
        
        Uses linear interpolation between waypoints for smooth movement.
        
        Args:
            start_pos: (row_idx, col_idx) starting grid position
            end_pos: (row_idx, col_idx) ending grid position
            points_per_cell: Interpolation points per grid cell
        
        Returns:
            List of (px_x, px_y) tuples for animation
        """
        start_px = self.grid_to_pixel(start_pos[0], start_pos[1])
        end_px = self.grid_to_pixel(end_pos[0], end_pos[1])
        
        # Calculate straight-line distance in pixels
        distance = self.distance_in_pixels(start_px, end_px)
        
        # Generate interpolation points
        if distance == 0:
            return [start_px]
        
        # Number of points = distance / (cell_size / points_per_cell)
        num_points = max(2, int((distance / self.cell_size_px) * points_per_cell))
        
        path = []
        for i in range(num_points):
            t = i / (num_points - 1)  # 0.0 to 1.0
            px_x = start_px[0] + (end_px[0] - start_px[0]) * t
            px_y = start_px[1] + (end_px[1] - start_px[1]) * t
            path.append((px_x, px_y))
        
        return path

    def generate_patrol_path(
        self,
        waypoints: List[Tuple[int, int]],
        points_per_cell: int = 4
    ) -> List[Tuple[float, float]]:
        """
        Generate smooth patrol path through multiple waypoints.
        
        Args:
            waypoints: List of (row_idx, col_idx) tuples
            points_per_cell: Interpolation points per grid cell
        
        Returns:
            List of (px_x, px_y) tuples for continuous animation
        """
        full_path = []
        
        for i in range(len(waypoints) - 1):
            segment = self.generate_path(waypoints[i], waypoints[i + 1], points_per_cell)
            # Skip first point of subsequent segments to avoid duplication
            if i > 0:
                segment = segment[1:]
            full_path.extend(segment)
        
        return full_path

    # ==================== Grid Utilities ====================

    def get_all_cells(self) -> List[Tuple[int, int]]:
        """Get all 676 grid cells as (row_idx, col_idx) tuples."""
        cells = []
        for row in range(26):
            for col in range(26):
                cells.append((row, col))
        return cells

    def get_grid_bounds(self) -> Dict[str, int]:
        """Get canvas bounds in pixels."""
        return {
            "min_x": 0,
            "max_x": self.CANVAS_SIZE_PX,
            "min_y": 0,
            "max_y": self.CANVAS_SIZE_PX,
            "cell_size": self.cell_size_px,
            "grid_size": 26,
        }

    def clamp_to_grid(self, row_idx: int, col_idx: int) -> Tuple[int, int]:
        """Clamp grid coordinates to valid range."""
        return (max(0, min(25, row_idx)), max(0, min(25, col_idx)))


# ==================== Example Usage ====================

if __name__ == "__main__":
    grid = GridCoordinateSystem()
    
    # Test NATO conversion
    print("NATO Conversion:")
    print(f"  Row 0 -> {grid.row_index_to_nato(0)}")
    print(f"  'Bravo' -> Row {grid.nato_to_row_index('Bravo')}")
    
    # Test grid notation
    print("\nGrid Notation:")
    print(f"  (0, 0) -> {grid.build_grid_notation(0, 0)}")
    print(f"  'Alpha-1' -> {grid.parse_grid_notation('Alpha-1')}")
    print(f"  'Zulu-26' -> {grid.parse_grid_notation('Zulu-26')}")
    
    # Test coordinate conversion
    print("\nCoordinate Conversion:")
    px = grid.grid_to_pixel(0, 0)
    print(f"  Grid (0, 0) -> Pixel {px}")
    back = grid.pixel_to_grid(px[0], px[1])
    print(f"  Pixel {px} -> Grid {back}")
    
    # Test distance calculations
    print("\nDistance Calculations:")
    d = grid.distance_in_cells((0, 0), (3, 4))
    print(f"  Distance (0,0) to (3,4): {d:.2f} cells")
    
    # Test transmission range
    print("\nTransmission Range (5 cells):")
    neighbors = grid.get_neighbors_in_range((13, 13), 5)
    print(f"  Neighbors of (13, 13): {len(neighbors)} cells")
    print(f"  (13, 17) in range? {grid.is_in_range((13, 13), (13, 17), 5)}")
    print(f"  (13, 19) in range? {grid.is_in_range((13, 13), (13, 19), 5)}")
    
    # Test path generation
    print("\nPath Generation:")
    path = grid.generate_path((0, 0), (3, 4), 2)
    print(f"  Path from (0,0) to (3,4): {len(path)} points")
    print(f"  First: {path[0]}, Last: {path[-1]}")
