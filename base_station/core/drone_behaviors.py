"""
Drone Behaviors Module - Grid-based Movement and Behavior Management

Handles all drone-specific behaviors:
- Position tracking and movement
- Patrol and transit behavior
- Waypoint navigation with smooth interpolation
- Behavior state transitions

Decoupled from SwarmCoordinator for clarity and testability.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .grid_coordinate_system import GridCoordinateSystem


class DroneState:
    """Tracks the state of a single drone."""
    
    def __init__(
        self,
        drone_id: str,
        grid_position: Tuple[int, int],
        behavior: str = "lurk",
        waypoints: Optional[List[Tuple[int, int]]] = None,
        speed: float = 1.0,  # cells per second
    ):
        """
        Initialize drone state.
        
        Args:
            drone_id: Unique identifier
            grid_position: (row_idx, col_idx) in grid coordinates
            behavior: "lurk", "patrol", "transit", or "swarm"
            waypoints: List of waypoints for patrol/transit
            speed: Movement speed in cells per second
        """
        self.drone_id = drone_id
        self.position = grid_position
        self.behavior = behavior
        self.waypoints = waypoints or [grid_position]
        self.waypoint_index = 0
        self.speed = speed
        self.progress = 0.0  # 0.0-1.0 through current movement
    
    def to_dict(self) -> Dict:
        """Export state as dictionary."""
        return {
            "drone_id": self.drone_id,
            "position": self.position,
            "behavior": self.behavior,
            "waypoint_index": self.waypoint_index,
            "progress": self.progress,
            "waypoints": self.waypoints,
            "speed": self.speed,
        }


class DroneMovement:
    """Manages drone movement and behavior transitions."""
    
    def __init__(self, grid_system: GridCoordinateSystem):
        """
        Initialize movement manager.
        
        Args:
            grid_system: GridCoordinateSystem for coordinate operations
        """
        self.grid_system = grid_system
    
    def update_positions(
        self,
        drone_states: Dict[str, DroneState],
        delta_ms: float,
    ) -> None:
        """
        Update all drone positions based on behaviors and waypoints.
        
        Args:
            drone_states: Dict of DroneState objects by drone_id
            delta_ms: Time elapsed since last update in milliseconds
        """
        delta_sec = delta_ms / 1000.0

        for drone_id, state in drone_states.items():
            if state.behavior == "lurk":
                # No movement
                continue

            elif state.behavior in {"patrol", "transit"}:
                self._move_along_path(state, delta_sec)

            elif state.behavior == "swarm":
                # TODO: Implement swarm behavior (convergence toward target)
                pass

    def _move_along_path(self, state: DroneState, delta_sec: float) -> None:
        """
        Move drone along waypoint path with smooth interpolation.
        
        Args:
            state: DroneState to update
            delta_sec: Time delta in seconds
        """
        waypoints = state.waypoints
        if not waypoints or len(waypoints) < 2:
            return

        waypoint_idx = state.waypoint_index
        if waypoint_idx >= len(waypoints) - 1:
            # Reached end of path
            if state.behavior == "transit":
                state.behavior = "lurk"
            else:
                # Loop patrol
                state.waypoint_index = 0
            return

        # Calculate movement progress
        current_pos = state.position
        next_waypoint = waypoints[waypoint_idx + 1]

        # Distance in cells
        distance = self.grid_system.distance_in_cells(current_pos, next_waypoint)

        # Time to traverse (at speed cells per second)
        travel_time_sec = distance / state.speed if state.speed > 0 else float('inf')

        if travel_time_sec <= 0:
            # Already at waypoint, move to next
            state.waypoint_index += 1
            state.progress = 0.0
            return

        # Update progress (normalized 0.0-1.0)
        new_progress = state.progress + (delta_sec / travel_time_sec)

        if new_progress >= 1.0:
            # Reached waypoint
            state.position = next_waypoint
            state.waypoint_index += 1
            state.progress = 0.0
        else:
            # Interpolate position
            progress = new_progress
            interp_row = current_pos[0] + (next_waypoint[0] - current_pos[0]) * progress
            interp_col = current_pos[1] + (next_waypoint[1] - current_pos[1]) * progress
            state.position = (int(round(interp_row)), int(round(interp_col)))
            state.progress = new_progress

    def set_behavior(
        self,
        state: DroneState,
        behavior: str,
        waypoints: Optional[List[Tuple[int, int]]] = None,
    ) -> None:
        """
        Change drone behavior and optionally set new waypoints.
        
        Args:
            state: DroneState to update
            behavior: New behavior ("lurk", "patrol", "transit", "swarm")
            waypoints: New waypoints if provided
        """
        state.behavior = behavior
        if waypoints:
            state.waypoints = waypoints
        state.waypoint_index = 0
        state.progress = 0.0
