"""
Gossip Protocol Module - Phase 3 Message Propagation System

Implements gossip-based message dissemination with:
- Spanning tree computation (Prim's algorithm)
- ACK/retry logic with exponential backoff
- Multi-hop message routing
- Event publishing for mission timeline

All gossip-related operations are decoupled here for clarity and testability.
"""

from __future__ import annotations

import heapq
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

from .grid_coordinate_system import GridCoordinateSystem
from .mission_event_bus import EventBus


class GossipProtocol:
    """
    Gossip message propagation system with spanning tree routing.
    
    Attributes:
        grid_system: GridCoordinateSystem for coordinate operations
        event_bus: EventBus for mission event publishing
    """
    
    # Constants
    DEFAULT_RETRY_LIMIT = 2
    DEFAULT_RETRY_BACKOFF_MS = 150.0
    
    def __init__(self, grid_system: GridCoordinateSystem, event_bus: EventBus):
        """
        Initialize gossip protocol handler.
        
        Args:
            grid_system: GridCoordinateSystem instance
            event_bus: EventBus instance for event publishing
        """
        self.grid_system = grid_system
        self.event_bus = event_bus
        
        # Message tracking
        self._gossip_messages: Dict[str, Dict] = {}
        self._gossip_sequence = iter(range(1, 1000000))
        
        # Spanning tree state
        self._spanning_tree_root: Optional[str] = None
        self._spanning_tree_edges: Set[Tuple[str, str]] = set()
        self._transmission_graph_edges: List[Dict] = []
    
    def compute_spanning_tree(
        self,
        drone_positions: Dict[str, tuple],
        transmission_ranges: Dict[str, int],
        root_node: Optional[str] = None,
    ) -> Dict:
        """
        Compute spanning tree for gossip propagation using Prim's algorithm.
        
        Args:
            drone_positions: Dict mapping drone_id -> (row_idx, col_idx)
            transmission_ranges: Dict mapping drone_id -> range_in_cells
            root_node: Root of spanning tree (auto-select if None)
            
        Returns:
            Dict with tree_edges, root, nodes_in_tree, unreachable_nodes
        """
        if root_node is None:
            # Default to first compute drone, fallback to first soldier
            for drone_id in drone_positions.keys():
                if "compute" in drone_id:
                    root_node = drone_id
                    break
            if root_node is None:
                for drone_id in drone_positions.keys():
                    if "soldier" in drone_id:
                        root_node = drone_id
                        break
            if root_node is None and drone_positions:
                root_node = list(drone_positions.keys())[0]

        if not root_node or root_node not in drone_positions:
            return {"tree_edges": [], "root": None, "nodes_in_tree": [], "unreachable_nodes": list(drone_positions.keys())}

        # Build neighbor dict from transmission graph
        neighbors: Dict[str, List[tuple]] = {
            drone_id: [] for drone_id in drone_positions.keys()
        }

        for edge in self._transmission_graph_edges:
            neighbors[edge["source"]].append((edge["target"], edge["quality"]))
            neighbors[edge["target"]].append((edge["source"], edge["quality"]))

        # Prim's algorithm
        visited = {root_node}
        tree_edges: Set[Tuple[str, str]] = set()
        heap: List[Tuple[float, str, str]] = []

        for target, quality in neighbors.get(root_node, []):
            heapq.heappush(heap, (-quality, root_node, target))

        while heap:
            neg_quality, source, target = heapq.heappop(heap)

            if target in visited:
                continue

            visited.add(target)
            edge_key = tuple(sorted((source, target)))
            tree_edges.add(edge_key)

            for next_target, quality in neighbors.get(target, []):
                if next_target not in visited:
                    heapq.heappush(heap, (-quality, target, next_target))

        self._spanning_tree_root = root_node
        self._spanning_tree_edges = tree_edges

        return {
            "tree_edges": [{"source": edge[0], "target": edge[1]} for edge in tree_edges],
            "root": root_node,
            "nodes_in_tree": list(visited),
            "unreachable_nodes": list(set(drone_positions.keys()) - visited),
        }

    def calculate_transmission_graph(
        self,
        drone_positions: Dict[str, tuple],
        transmission_ranges: Dict[str, int],
    ) -> List[Dict]:
        """
        Build transmission graph respecting range constraints.
        
        Args:
            drone_positions: Dict mapping drone_id -> (row_idx, col_idx)
            transmission_ranges: Dict mapping drone_id -> range_in_cells
            
        Returns:
            List of edge dicts with source, target, distance, quality, in_spanning_tree
        """
        edges = []
        drone_ids = list(drone_positions.keys())

        for i, source_id in enumerate(drone_ids):
            source_pos = drone_positions[source_id]
            source_range = transmission_ranges.get(source_id, 3)

            for target_id in drone_ids[i + 1:]:
                target_pos = drone_positions[target_id]
                distance = self.grid_system.distance_in_cells(source_pos, target_pos)
                target_range = transmission_ranges.get(target_id, 3)
                
                if distance <= source_range and distance <= target_range:
                    quality = max(0.5, 1.0 - (distance / max(source_range, target_range)))
                    edge_key = tuple(sorted((source_id, target_id)))
                    in_tree = edge_key in self._spanning_tree_edges
                    
                    edges.append({
                        "source": source_id,
                        "target": target_id,
                        "distance": round(distance, 2),
                        "quality": round(quality, 3),
                        "in_spanning_tree": in_tree,
                    })

        self._transmission_graph_edges = edges
        return edges

    def broadcast_message(
        self,
        sender_id: str,
        message_content: str,
        priority: str = "high",
        target_drones: Optional[List[str]] = None,
        drone_positions: Optional[Dict[str, tuple]] = None,
    ) -> Dict:
        """
        Initiate a gossip-based broadcast from a drone.
        
        Args:
            sender_id: ID of the sending drone
            message_content: Message text to broadcast
            priority: Priority level (critical, high, medium, low)
            target_drones: Specific drones to target (None = broadcast to all)
            drone_positions: Dict of drone positions for event publishing
            
        Returns:
            Dict with message_id, priority, initiated_at_ms, initial_hop_count
        """
        # Ensure spanning tree is computed
        if not self._spanning_tree_edges:
            self.compute_spanning_tree({}, {})
        
        message_id = f"gossip-{next(self._gossip_sequence):06d}"
        current_time_ms = datetime.now().timestamp() * 1000
        
        # Initialize message state
        message_state = {
            "message_id": message_id,
            "sender_id": sender_id,
            "content": message_content,
            "priority": priority,
            "initiated_at_ms": round(current_time_ms, 1),
            "target_drones": target_drones if target_drones else [],
            "propagation_graph": {},
            "hop_count": 0,
            "delivered_to": set(),
            "failed_to": set(),
            "retry_limit": self.DEFAULT_RETRY_LIMIT,
            "retry_backoff_ms": self.DEFAULT_RETRY_BACKOFF_MS,
        }
        
        # Initialize propagation state for all target drones
        for drone_id in message_state["target_drones"]:
            if drone_id != sender_id:
                message_state["propagation_graph"][drone_id] = {
                    "acked": False,
                    "attempts": 0,
                    "last_attempt_ms": None,
                    "last_retry_ms": None,
                    "retry_round": 0,
                }
        
        # Store message state
        self._gossip_messages[message_id] = message_state
        
        # Publish gossip_initiated event
        grid_pos = drone_positions.get(sender_id, (13, 13)) if drone_positions else (13, 13)
        self.event_bus.gossip_initiated(
            drone_id=sender_id,
            message_id=message_id,
            target_count=len(message_state["target_drones"]) - 1,
            priority=priority,
            grid_position=grid_pos,
        )
        
        return {
            "message_id": message_id,
            "sender_id": sender_id,
            "priority": priority,
            "initiated_at_ms": round(current_time_ms, 1),
            "initial_hop_count": len(message_state["target_drones"]) - 1,
        }

    def handle_gossip_ack(
        self,
        message_id: str,
        acker_id: str,
        current_time_ms: float,
        drone_positions: Optional[Dict[str, tuple]] = None,
    ) -> bool:
        """
        Handle acknowledgment from a drone that received a message.
        
        Args:
            message_id: ID of acknowledged message
            acker_id: ID of drone acknowledging
            current_time_ms: Current timestamp
            drone_positions: Dict of drone positions for event publishing
            
        Returns:
            True if ack was processed, False if invalid
        """
        message_state = self._gossip_messages.get(message_id)
        if not message_state:
            return False
        
        propagation_entry = message_state["propagation_graph"].get(acker_id)
        if not propagation_entry:
            return False
        
        # Mark as acknowledged
        propagation_entry["acked"] = True
        propagation_entry["ack_received_ms"] = round(current_time_ms, 1)
        message_state["delivered_to"].add(acker_id)
        
        # Publish gossip_acknowledged event
        grid_pos = drone_positions.get(acker_id, (13, 13)) if drone_positions else (13, 13)
        self.event_bus.gossip_acknowledged(
            drone_id=acker_id,
            message_id=message_id,
            grid_position=grid_pos,
        )
        
        return True

    def process_gossip_retries(self, current_time_ms: float) -> Dict:
        """
        Process retries for in-flight gossip messages with backoff logic.
        
        Args:
            current_time_ms: Current timestamp in milliseconds
            
        Returns:
            Dict with retry statistics
        """
        stats = {
            "messages_processed": 0,
            "total_retries_sent": 0,
            "messages_delivered": 0,
            "messages_failed": 0,
        }
        
        for message_id, message_state in list(self._gossip_messages.items()):
            stats["messages_processed"] += 1
            
            # Check if message is complete
            pending_count = 0
            for drone_id, entry in message_state["propagation_graph"].items():
                if entry["acked"]:
                    continue
                
                if entry["attempts"] >= message_state["retry_limit"] + 1:
                    message_state["failed_to"].add(drone_id)
                else:
                    pending_count += 1
            
            if pending_count == 0:
                if len(message_state["failed_to"]) == 0:
                    stats["messages_delivered"] += 1
                else:
                    stats["messages_failed"] += 1
        
        return stats

    def get_gossip_message_state(self, message_id: str) -> Optional[Dict]:
        """Get the current state of a gossip message."""
        msg_state = self._gossip_messages.get(message_id)
        if not msg_state:
            return None
        
        return {
            "message_id": message_id,
            "sender_id": msg_state["sender_id"],
            "content": msg_state["content"],
            "priority": msg_state["priority"],
            "initiated_at_ms": msg_state["initiated_at_ms"],
            "hop_count": msg_state["hop_count"],
            "delivered_to": list(msg_state["delivered_to"]),
            "failed_to": list(msg_state["failed_to"]),
            "pending_drones": [
                drone_id for drone_id, entry in msg_state["propagation_graph"].items()
                if not entry["acked"] and entry["attempts"] < msg_state["retry_limit"] + 1
            ],
        }

    def get_active_gossip_messages(self) -> List[Dict]:
        """Get all active gossip messages."""
        return [self.get_gossip_message_state(msg_id) for msg_id in self._gossip_messages.keys()]
