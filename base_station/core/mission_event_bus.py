"""
Mission Event Bus - Event publishing and tracking for JARVIS swarm operations.

Event types:
- drone_spawned: Drone entered operation
- drone_destroyed: Drone lost (EMP, collision, etc)
- drone_comms_lost: Lost connectivity
- drone_comms_restored: Regained connectivity
- target_discovered: Found enemy/structure
- target_destroyed: Enemy eliminated
- target_confirmed: Visual confirmation
- patrol_started: Drone began patrol
- patrol_ended: Drone patrol complete
- command_executed: Command propagated to swarm
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class EventSeverity(Enum):
    """Event severity classifications."""
    INFO = "info"           # Routine operations
    WARNING = "warning"     # Degraded comms, low fuel
    CRITICAL = "critical"   # Target detected, drone destroyed
    ALERT = "alert"         # Immediate action required


class EventType(Enum):
    """All possible mission event types."""
    DRONE_SPAWNED = "drone_spawned"
    DRONE_DESTROYED = "drone_destroyed"
    DRONE_COMMS_LOST = "drone_comms_lost"
    DRONE_COMMS_RESTORED = "drone_comms_restored"
    DRONE_BEHAVIOR_CHANGED = "drone_behavior_changed"
    TARGET_DISCOVERED = "target_discovered"
    TARGET_DESTROYED = "target_destroyed"
    TARGET_CONFIRMED = "target_confirmed"
    PATROL_STARTED = "patrol_started"
    PATROL_ENDED = "patrol_ended"
    COMMAND_EXECUTED = "command_executed"
    GOSSIP_INITIATED = "gossip_initiated"
    GOSSIP_PROPAGATION = "gossip_propagation"
    GOSSIP_ACKNOWLEDGED = "gossip_acknowledged"


@dataclass
class MissionEvent:
    """
    Single mission event with full context.
    
    Attributes:
        timestamp_ms: Milliseconds since simulation start
        event_type: EventType enum
        severity: EventSeverity enum
        drone_id: ID of primary drone involved
        grid_position: (row_idx, col_idx) where event occurred
        entity_id: Optional secondary entity (target, command, etc)
        entity_type: Type of secondary entity (tank, building, etc)
        message: Human-readable event description
        details: Additional context as dict
    """
    timestamp_ms: int
    event_type: EventType
    severity: EventSeverity
    drone_id: str
    grid_position: tuple  # (row_idx, col_idx)
    message: str
    entity_id: Optional[str] = None
    entity_type: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Export event as dict for JSON serialization."""
        return {
            "timestamp_ms": self.timestamp_ms,
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "drone_id": self.drone_id,
            "grid_position": self.grid_position,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "message": self.message,
            "details": self.details,
        }

    def to_json(self) -> str:
        """Export event as JSON string."""
        return json.dumps(self.to_dict())

    def to_console_string(self) -> str:
        """Format event for console display."""
        minutes = self.timestamp_ms // 60000
        seconds = (self.timestamp_ms % 60000) // 1000
        millis = self.timestamp_ms % 1000
        
        time_str = f"{minutes:02d}:{seconds:02d}.{millis:03d}"
        return f"[{time_str}] {self.drone_id}: {self.message}"


class EventBus:
    """
    Central event publisher and subscriber system for mission events.
    
    Features:
    - Publish events with full context
    - Subscribe to event types or all events
    - Event history with query support
    - Callback notifications
    """

    def __init__(self, max_history: int = 1000):
        """
        Initialize event bus.
        
        Args:
            max_history: Maximum events to retain in history
        """
        self.max_history = max_history
        self._history: List[MissionEvent] = []
        self._subscribers: Dict[EventType, List[Callable[[MissionEvent], None]]] = {
            et: [] for et in EventType
        }
        self._universal_subscribers: List[Callable[[MissionEvent], None]] = []

    def publish(self, event: MissionEvent) -> None:
        """
        Publish event to all subscribers.
        
        Args:
            event: MissionEvent to publish
        """
        # Add to history (respecting max_history limit)
        self._history.append(event)
        if len(self._history) > self.max_history:
            self._history.pop(0)
        
        # Notify type-specific subscribers
        if event.event_type in self._subscribers:
            for callback in self._subscribers[event.event_type]:
                try:
                    callback(event)
                except Exception as e:
                    print(f"Error in event callback: {e}")
        
        # Notify universal subscribers
        for callback in self._universal_subscribers:
            try:
                callback(event)
            except Exception as e:
                print(f"Error in universal event callback: {e}")

    def subscribe(
        self,
        callback: Callable[[MissionEvent], None],
        event_type: Optional[EventType] = None
    ) -> None:
        """
        Subscribe to events.
        
        Args:
            callback: Function to call when event published
            event_type: Specific event type to listen for, or None for all
        """
        if event_type is None:
            self._universal_subscribers.append(callback)
        else:
            self._subscribers[event_type].append(callback)

    def unsubscribe(
        self,
        callback: Callable[[MissionEvent], None],
        event_type: Optional[EventType] = None
    ) -> None:
        """
        Unsubscribe from events.
        
        Args:
            callback: Function to remove
            event_type: Specific event type, or None for all
        """
        if event_type is None:
            if callback in self._universal_subscribers:
                self._universal_subscribers.remove(callback)
        else:
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)

    # ==================== Event Factories ====================

    def drone_spawned(
        self,
        timestamp_ms: int,
        drone_id: str,
        grid_position: tuple,
        drone_type: str,
    ) -> MissionEvent:
        """Create drone_spawned event."""
        event = MissionEvent(
            timestamp_ms=timestamp_ms,
            event_type=EventType.DRONE_SPAWNED,
            severity=EventSeverity.INFO,
            drone_id=drone_id,
            grid_position=grid_position,
            entity_type=drone_type,
            message=f"{drone_id} ({drone_type}) spawned at grid {grid_position}",
            details={"drone_type": drone_type},
        )
        self.publish(event)
        return event

    def drone_destroyed(
        self,
        timestamp_ms: int,
        drone_id: str,
        grid_position: tuple,
        cause: str = "unknown",
    ) -> MissionEvent:
        """Create drone_destroyed event."""
        event = MissionEvent(
            timestamp_ms=timestamp_ms,
            event_type=EventType.DRONE_DESTROYED,
            severity=EventSeverity.CRITICAL,
            drone_id=drone_id,
            grid_position=grid_position,
            message=f"{drone_id} destroyed at {grid_position} ({cause})",
            details={"cause": cause},
        )
        self.publish(event)
        return event

    def drone_comms_lost(
        self,
        timestamp_ms: int,
        drone_id: str,
        grid_position: tuple,
        reason: str = "out-of-range",
    ) -> MissionEvent:
        """Create drone_comms_lost event."""
        event = MissionEvent(
            timestamp_ms=timestamp_ms,
            event_type=EventType.DRONE_COMMS_LOST,
            severity=EventSeverity.WARNING,
            drone_id=drone_id,
            grid_position=grid_position,
            message=f"{drone_id} lost comms at {grid_position} ({reason})",
            details={"reason": reason},
        )
        self.publish(event)
        return event

    def drone_comms_restored(
        self,
        timestamp_ms: int,
        drone_id: str,
        grid_position: tuple,
    ) -> MissionEvent:
        """Create drone_comms_restored event."""
        event = MissionEvent(
            timestamp_ms=timestamp_ms,
            event_type=EventType.DRONE_COMMS_RESTORED,
            severity=EventSeverity.INFO,
            drone_id=drone_id,
            grid_position=grid_position,
            message=f"{drone_id} comms restored at {grid_position}",
        )
        self.publish(event)
        return event

    def drone_behavior_changed(
        self,
        timestamp_ms: int,
        drone_id: str,
        grid_position: tuple,
        new_behavior: str,
        old_behavior: str,
    ) -> MissionEvent:
        """Create drone_behavior_changed event."""
        event = MissionEvent(
            timestamp_ms=timestamp_ms,
            event_type=EventType.DRONE_BEHAVIOR_CHANGED,
            severity=EventSeverity.INFO,
            drone_id=drone_id,
            grid_position=grid_position,
            message=f"{drone_id} behavior: {old_behavior} -> {new_behavior}",
            details={"old_behavior": old_behavior, "new_behavior": new_behavior},
        )
        self.publish(event)
        return event

    def target_discovered(
        self,
        timestamp_ms: int,
        drone_id: str,
        grid_position: tuple,
        target_id: str,
        target_type: str,
        confidence: float,
    ) -> MissionEvent:
        """Create target_discovered event."""
        event = MissionEvent(
            timestamp_ms=timestamp_ms,
            event_type=EventType.TARGET_DISCOVERED,
            severity=EventSeverity.CRITICAL,
            drone_id=drone_id,
            grid_position=grid_position,
            entity_id=target_id,
            entity_type=target_type,
            message=f"{drone_id} discovered {target_type} at {grid_position} ({confidence:.0%} confidence)",
            details={"confidence": confidence, "target_type": target_type},
        )
        self.publish(event)
        return event

    def target_destroyed(
        self,
        timestamp_ms: int,
        drone_id: str,
        grid_position: tuple,
        target_id: str,
        target_type: str,
    ) -> MissionEvent:
        """Create target_destroyed event."""
        event = MissionEvent(
            timestamp_ms=timestamp_ms,
            event_type=EventType.TARGET_DESTROYED,
            severity=EventSeverity.CRITICAL,
            drone_id=drone_id,
            grid_position=grid_position,
            entity_id=target_id,
            entity_type=target_type,
            message=f"{drone_id} destroyed {target_type} at {grid_position}",
        )
        self.publish(event)
        return event

    def target_confirmed(
        self,
        timestamp_ms: int,
        drone_id: str,
        grid_position: tuple,
        target_id: str,
        status: str,
    ) -> MissionEvent:
        """Create target_confirmed event."""
        event = MissionEvent(
            timestamp_ms=timestamp_ms,
            event_type=EventType.TARGET_CONFIRMED,
            severity=EventSeverity.INFO,
            drone_id=drone_id,
            grid_position=grid_position,
            entity_id=target_id,
            message=f"{drone_id} confirmed {target_id} at {grid_position} - {status}",
            details={"status": status},
        )
        self.publish(event)
        return event

    def patrol_started(
        self,
        timestamp_ms: int,
        drone_id: str,
        grid_position: tuple,
        waypoints: List[tuple],
    ) -> MissionEvent:
        """Create patrol_started event."""
        event = MissionEvent(
            timestamp_ms=timestamp_ms,
            event_type=EventType.PATROL_STARTED,
            severity=EventSeverity.INFO,
            drone_id=drone_id,
            grid_position=grid_position,
            message=f"{drone_id} began patrol from {grid_position} ({len(waypoints)} waypoints)",
            details={"waypoint_count": len(waypoints)},
        )
        self.publish(event)
        return event

    def patrol_ended(
        self,
        timestamp_ms: int,
        drone_id: str,
        grid_position: tuple,
        reason: str = "completed",
    ) -> MissionEvent:
        """Create patrol_ended event."""
        event = MissionEvent(
            timestamp_ms=timestamp_ms,
            event_type=EventType.PATROL_ENDED,
            severity=EventSeverity.INFO,
            drone_id=drone_id,
            grid_position=grid_position,
            message=f"{drone_id} ended patrol at {grid_position} ({reason})",
            details={"reason": reason},
        )
        self.publish(event)
        return event

    def command_executed(
        self,
        timestamp_ms: int,
        drone_id: str,
        grid_position: tuple,
        command: str,
        success: bool,
    ) -> MissionEvent:
        """Create command_executed event."""
        status = "success" if success else "failed"
        severe = EventSeverity.INFO if success else EventSeverity.WARNING
        event = MissionEvent(
            timestamp_ms=timestamp_ms,
            event_type=EventType.COMMAND_EXECUTED,
            severity=severe,
            drone_id=drone_id,
            grid_position=grid_position,
            message=f"{drone_id} executed '{command}' - {status}",
            details={"command": command, "success": success},
        )
        self.publish(event)
        return event

    def gossip_initiated(
        self,
        drone_id: str,
        message_id: str,
        target_count: int,
        priority: str,
        grid_position: tuple,
    ) -> MissionEvent:
        """Create gossip_initiated event."""
        timestamp_ms = int(datetime.now().timestamp() * 1000)
        event = MissionEvent(
            timestamp_ms=timestamp_ms,
            event_type=EventType.GOSSIP_INITIATED,
            severity=EventSeverity.INFO,
            drone_id=drone_id,
            grid_position=grid_position,
            entity_id=message_id,
            message=f"{drone_id} initiated gossip broadcast (msg={message_id}, targets={target_count}, priority={priority})",
            details={"message_id": message_id, "target_count": target_count, "priority": priority},
        )
        self.publish(event)
        return event

    def gossip_propagation(
        self,
        drone_id: str,
        message_id: str,
        target_drone: str,
        hop_number: int,
        grid_position: tuple,
    ) -> MissionEvent:
        """Create gossip_propagation event."""
        timestamp_ms = int(datetime.now().timestamp() * 1000)
        event = MissionEvent(
            timestamp_ms=timestamp_ms,
            event_type=EventType.GOSSIP_PROPAGATION,
            severity=EventSeverity.INFO,
            drone_id=drone_id,
            grid_position=grid_position,
            entity_id=target_drone,
            message=f"Message propagated: {drone_id} -> {target_drone} (msg={message_id}, hop={hop_number})",
            details={"message_id": message_id, "target_drone": target_drone, "hop_number": hop_number},
        )
        self.publish(event)
        return event

    def gossip_acknowledged(
        self,
        drone_id: str,
        message_id: str,
        grid_position: tuple,
    ) -> MissionEvent:
        """Create gossip_acknowledged event."""
        timestamp_ms = int(datetime.now().timestamp() * 1000)
        event = MissionEvent(
            timestamp_ms=timestamp_ms,
            event_type=EventType.GOSSIP_ACKNOWLEDGED,
            severity=EventSeverity.INFO,
            drone_id=drone_id,
            grid_position=grid_position,
            entity_id=message_id,
            message=f"{drone_id} acknowledged message (msg={message_id})",
            details={"message_id": message_id},
        )
        self.publish(event)
        return event

    # ==================== History & Queries ====================

    def get_history(self, limit: int = 100) -> List[MissionEvent]:
        """Get most recent events."""
        return self._history[-limit:]

    def get_history_by_type(self, event_type: EventType, limit: int = 100) -> List[MissionEvent]:
        """Get recent events of specific type."""
        filtered = [e for e in self._history if e.event_type == event_type]
        return filtered[-limit:]

    def get_history_by_drone(self, drone_id: str, limit: int = 100) -> List[MissionEvent]:
        """Get recent events involving specific drone."""
        filtered = [e for e in self._history if e.drone_id == drone_id]
        return filtered[-limit:]

    def get_history_by_severity(self, severity: EventSeverity, limit: int = 100) -> List[MissionEvent]:
        """Get recent events of specific severity."""
        filtered = [e for e in self._history if e.severity == severity]
        return filtered[-limit:]

    def get_history_as_json(self, limit: int = 100) -> str:
        """Export recent history as JSON."""
        history = self.get_history(limit)
        return json.dumps([e.to_dict() for e in history], indent=2)

    def clear_history(self) -> None:
        """Clear all event history."""
        self._history.clear()

    @property
    def event_count(self) -> int:
        """Total events published."""
        return len(self._history)

    @property
    def latest_event(self) -> Optional[MissionEvent]:
        """Get most recent event."""
        return self._history[-1] if self._history else None


# ==================== Global Event Bus Instance ====================

global_event_bus = EventBus()


# ==================== Example Usage ====================

if __name__ == "__main__":
    # Create bus
    bus = EventBus()
    
    # Subscribe to all events
    def print_event(event: MissionEvent):
        print(f"  {event.to_console_string()}")
    
    bus.subscribe(print_event)
    
    # Publish sample events
    print("Publishing test events:\n")
    
    bus.drone_spawned(0, "recon-1", (0, 0), "recon-drone")
    bus.patrol_started(100, "recon-1", (0, 0), [(0, 5), (3, 5), (5, 3)])
    bus.target_discovered(5000, "recon-1", (2, 3), "tank-1", "tank", 0.95)
    bus.drone_destroyed(8000, "attack-1", (5, 8), cause="overheated")
    bus.target_destroyed(9000, "attack-2", (2, 3), "tank-1", "tank")
    
    # Query history
    print(f"\n\nTotal events: {bus.event_count}")
    print(f"\nLast event: {bus.latest_event.to_console_string()}")
    
    # Get by type
    discoveries = bus.get_history_by_type(EventType.TARGET_DISCOVERED)
    print(f"\nTarget discoveries: {len(discoveries)}")
    
    print(f"\n\nEvents by recon-1:")
    for event in bus.get_history_by_drone("recon-1"):
        print(f"  {event.to_console_string()}")
