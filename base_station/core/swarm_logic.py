"""
JARVIS Swarm Logic (Section 3.0.0 - Grid Coordinate Edition)

Blueprint-aligned swarm coordination runtime with grid-based positioning:
- Uses GridCoordinateSystem for NATO phonetic grid (26x26, Alpha-Zulu)
- Transmission range constraints (3-5 cells for drones, 12 for compute)
- Spanning tree gossip protocol with Euclidean distance calculations
- Drone behaviors: lurk, patrol, transit, swarm with smooth movement
- Event publishing via EventBus for console feed and visualization
- Configuration loading from JSON for customizable scenarios
"""

from __future__ import annotations

import heapq
import itertools
import json
import random
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

try:
    import networkx as nx
except ImportError:  # pragma: no cover - fallback keeps the demo runnable
    nx = None

# Import new grid and event system
from .grid_coordinate_system import GridCoordinateSystem
from .mission_event_bus import EventBus, EventType, EventSeverity, MissionEvent
from .gossip_protocol import GossipProtocol


class SimpleGraph:
    """Small undirected graph fallback when NetworkX is unavailable."""

    def __init__(self):
        self.nodes: Dict[str, Dict] = {}
        self._adjacency: Dict[str, Set[str]] = {}
        self._edge_lookup: Dict[Tuple[str, str], Dict] = {}

    @staticmethod
    def edge_key(source: str, target: str) -> Tuple[str, str]:
        return tuple(sorted((source, target)))

    def add_node(self, node_id: str, **attrs) -> None:
        self.nodes[node_id] = dict(attrs)
        self._adjacency.setdefault(node_id, set())

    def add_edge(self, source: str, target: str, **attrs) -> None:
        key = self.edge_key(source, target)
        self._adjacency.setdefault(source, set()).add(target)
        self._adjacency.setdefault(target, set()).add(source)
        self._edge_lookup[key] = dict(attrs)

    def neighbors(self, node_id: str) -> List[str]:
        return sorted(self._adjacency.get(node_id, set()))

    def get_edge_data(self, source: str, target: str) -> Optional[Dict]:
        return self._edge_lookup.get(self.edge_key(source, target))


class SwarmCoordinator:
    """Owns topology, consensus simulation, mission state, and benchmarks."""

    DEFAULT_SEED = 42
    DEFAULT_TTL = 3
    DEFAULT_FANOUT = 2
    DEFAULT_RETRY_LIMIT = 2
    DEFAULT_RETRY_BACKOFF_MS = 55.0
    DEFAULT_RETRY_JITTER_MS = 18.0
    PRIORITY_PROFILES = {
        "critical": {
            "rank": 3,
            "max_hops": 3,
            "task_ttl_ms": 260.0,
            "claim_timeout_ms": 120.0,
            "lease_ms": 220.0,
            "preempt_lower_priority": True,
        },
        "high": {
            "rank": 2,
            "max_hops": 2,
            "task_ttl_ms": 240.0,
            "claim_timeout_ms": 110.0,
            "lease_ms": 205.0,
            "preempt_lower_priority": True,
        },
        "medium": {
            "rank": 1,
            "max_hops": 2,
            "task_ttl_ms": 225.0,
            "claim_timeout_ms": 100.0,
            "lease_ms": 190.0,
            "preempt_lower_priority": False,
        },
        "low": {
            "rank": 0,
            "max_hops": 1,
            "task_ttl_ms": 180.0,
            "claim_timeout_ms": 90.0,
            "lease_ms": 165.0,
            "preempt_lower_priority": False,
        },
    }

    def __init__(self, seed: Optional[int] = None, config_path: Optional[str] = None):
        """
        Initialize SwarmCoordinator with grid-based positioning and event system.
        
        Args:
            seed: Random seed for reproducibility
            config_path: Path to swarm_initial_state.json, or None to use defaults
        """
        self._rng = random.Random(seed if seed is not None else self.DEFAULT_SEED)
        self._message_sequence = itertools.count(1)
        self.graph = nx.Graph() if nx is not None else SimpleGraph()
        
        # Initialize grid coordinate system and event bus
        self.grid_system = GridCoordinateSystem(cell_size_px=30)
        self.event_bus = EventBus(max_history=1000)
        
        # Load configuration
        if config_path and Path(config_path).exists():
            self._config = self._load_config(config_path)
        else:
            # Resolve config path relative to this file's location
            swarm_core_dir = Path(__file__).parent.parent
            default_config_path = swarm_core_dir / "config" / "swarm_initial_state.json"
            self._config = self._load_config(str(default_config_path))
        
        if self._config is None:
            self._config = self._build_default_config()
        
        # Initialize drone and entity states from config
        self._base_nodes = self._config.get("drones", [])
        self._base_edges = []  # Legacy: graph edges no longer needed for grid-based system
        self._enemies = self._config.get("enemies", [])
        self._structures = self._config.get("structures", [])
        
        # Grid-based position tracking
        self._drone_positions: Dict[str, tuple] = {}  # drone_id -> (row_idx, col_idx)
        self._drone_behaviors: Dict[str, Dict] = {}  # drone_id -> behavior state
        self._transmission_ranges: Dict[str, int] = {}  # drone_id -> range in cells
        
        # Initialize from config
        for drone in self._base_nodes:
            drone_id = drone["id"]
            grid_pos = tuple(drone.get("grid_position", [13, 13]))
            self._drone_positions[drone_id] = grid_pos
            self._transmission_ranges[drone_id] = drone.get("transmission_range", 3)
            self._drone_behaviors[drone_id] = {
                "current": drone.get("behavior", "lurk"),
                "waypoints": [tuple(w) if isinstance(w, list) else w for w in drone.get("waypoints", [grid_pos])],
                "waypoint_index": 0,
                "speed": 1.0,  # cells per second
                "progress": 0.0,  # 0.0-1.0 through current cell
            }
        
        self._node_lookup = {node["id"]: deepcopy(node) for node in self._base_nodes}
        
        # Populate graph with drone nodes for compatibility with API
        for node in self._base_nodes:
            self.graph.add_node(node["id"], **node)
        
        # Initialize gossip protocol handler
        self.gossip_protocol = GossipProtocol(self.grid_system, self.event_bus)
        
        # Initialize spanning tree and transmission graphs
        self._spanning_tree_edges: List[tuple] = []
        self._spanning_tree_root: Optional[str] = None
        self._transmission_graph_edges: List[Dict] = []
        
        # Initialize gossip message tracking
        self._gossip_messages: Dict[str, Dict] = {}
        
        # Initialize state tracking
        self._last_state: Dict = {}
        self._operational_space = {}  # Empty for now - legacy field
        
        # NOTE: Graph visualization methods (_build_topology, _build_idle_state, etc.)
        # are being removed as part of migration to grid-based visualization.

    # ==================== Configuration Loading ====================

    def _load_config(self, config_path: str) -> Optional[Dict]:
        """Load swarm configuration from JSON file."""
        try:
            path = Path(config_path)
            if path.exists():
                with open(path, "r") as f:
                    return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load config from {config_path}: {e}")
        return None

    def _build_default_config(self) -> Dict:
        """Build default configuration when no file available."""
        return {
            "scenario": "Default Grid Scenario",
            "grid_size": 26,
            "drones": [],
            "enemies": [],
            "structures": [],
        }

    # ==================== Grid Position Management ====================

    def set_drone_position(self, drone_id: str, grid_pos: tuple) -> None:
        """
        Set drone position in grid coordinates.
        
        Args:
            drone_id: Drone identifier
            grid_pos: (row_idx, col_idx) tuple, 0-indexed
        """
        if drone_id in self._drone_positions:
            clamped = self.grid_system.clamp_to_grid(grid_pos[0], grid_pos[1])
            self._drone_positions[drone_id] = clamped

    def get_drone_position(self, drone_id: str) -> Optional[tuple]:
        """Get current grid position of drone."""
        return self._drone_positions.get(drone_id)

    def get_drone_pixel_position(self, drone_id: str) -> Optional[tuple]:
        """Get current pixel position of drone."""
        pos = self._drone_positions.get(drone_id)
        if pos:
            return self.grid_system.grid_to_pixel(pos[0], pos[1])
        return None

    # ==================== Transmission Range & Connectivity ====================

    def calculate_transmission_graph(self) -> List[Dict]:
        """
        Build transmission graph respecting range constraints.
        
        Returns:
            List of edge dicts: {source, target, distance, quality, in_spanning_tree}
        """
        # Ensure spanning tree is computed
        if not self._spanning_tree_edges:
            self.compute_spanning_tree()
        
        edges = []
        drone_ids = list(self._drone_positions.keys())

        for i, source_id in enumerate(drone_ids):
            source_pos = self._drone_positions[source_id]
            source_range = self._transmission_ranges.get(source_id, 3)

            for target_id in drone_ids[i + 1:]:
                target_pos = self._drone_positions[target_id]

                # Check Euclidean distance with transmission range
                distance = self.grid_system.distance_in_cells(source_pos, target_pos)

                # Bidirectional check: both must be in range
                target_range = self._transmission_ranges.get(target_id, 3)
                if distance <= source_range and distance <= target_range:
                    # Calculate link quality based on distance (closer = better)
                    quality = max(0.5, 1.0 - (distance / max(source_range, target_range)))
                    
                    # Check if this edge is in the spanning tree
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

    def compute_spanning_tree(self, root_node: Optional[str] = None) -> Dict:
        """
        Compute spanning tree for gossip propagation respecting range constraints.
        
        Uses Prim's algorithm on the transmission graph to build minimal tree.
        
        Args:
            root_node: Root of spanning tree (default: first compute drone or soldier)

        Returns:
            Dict with tree_edges and root
        """
        if root_node is None:
            # Default to first compute drone, fallback to first soldier
            for drone_id in self._drone_positions.keys():
                if "compute" in drone_id:
                    root_node = drone_id
                    break
            if root_node is None:
                for drone_id in self._drone_positions.keys():
                    if "soldier" in drone_id:
                        root_node = drone_id
                        break
            if root_node is None and self._drone_positions:
                root_node = list(self._drone_positions.keys())[0]

        if not root_node or root_node not in self._drone_positions:
            return {"tree_edges": [], "root": None}

        # Build neighbor dict from transmission graph
        neighbors: Dict[str, List[tuple]] = {
            drone_id: [] for drone_id in self._drone_positions.keys()
        }

        for edge in self._transmission_graph_edges:
            neighbors[edge["source"]].append((edge["target"], edge["quality"]))
            neighbors[edge["target"]].append((edge["source"], edge["quality"]))

        # Prim's algorithm
        visited = {root_node}
        tree_edges: Set[Tuple[str, str]] = set()
        heap: List[Tuple[float, str, str]] = []  # (-quality, source, target)

        # Add all edges from root
        for target, quality in neighbors[root_node]:
            heapq.heappush(heap, (-quality, root_node, target))

        # Build MST
        while heap:
            neg_quality, source, target = heapq.heappop(heap)

            if target in visited:
                continue

            visited.add(target)
            edge_key = tuple(sorted((source, target)))
            tree_edges.add(edge_key)

            # Add new neighbors to heap
            for next_target, quality in neighbors[target]:
                if next_target not in visited:
                    heapq.heappush(heap, (-quality, target, next_target))

        self._spanning_tree_root = root_node
        self._spanning_tree_edges = tree_edges

        return {
            "tree_edges": [{"source": edge[0], "target": edge[1]} for edge in tree_edges],
            "root": root_node,
            "nodes_in_tree": list(visited),
            "unreachable_nodes": list(set(self._drone_positions.keys()) - visited),
        }

    # ==================== Movement & Behavior ====================

    def set_drone_behavior(self, drone_id: str, behavior: str, waypoints: Optional[List[tuple]] = None) -> None:
        """
        Set drone behavior (lurk, patrol, transit, swarm).
        
        Args:
            drone_id: Drone identifier
            behavior: "lurk", "patrol", "transit", or "swarm"
            waypoints: List of (row_idx, col_idx) waypoints for patrol/transit
        """
        if drone_id not in self._drone_behaviors:
            return

        self._drone_behaviors[drone_id]["current"] = behavior
        if waypoints:
            self._drone_behaviors[drone_id]["waypoints"] = waypoints
        self._drone_behaviors[drone_id]["waypoint_index"] = 0
        self._drone_behaviors[drone_id]["progress"] = 0.0

    def update_drone_positions(self, delta_ms: float) -> None:
        """
        Update all drone positions based on behavior and movement speed.
        
        Args:
            delta_ms: Time elapsed since last update in milliseconds
        """
        delta_sec = delta_ms / 1000.0

        for drone_id, behavior in self._drone_behaviors.items():
            current_behavior = behavior["current"]

            if current_behavior == "lurk":
                # No position change, just idle
                continue

            elif current_behavior in {"patrol", "transit"}:
                waypoints = behavior["waypoints"]
                if not waypoints or len(waypoints) < 2:
                    continue

                waypoint_idx = behavior["waypoint_index"]
                if waypoint_idx >= len(waypoints) - 1:
                    # Reached end of patrol/transit
                    if current_behavior == "transit":
                        behavior["current"] = "lurk"
                    else:
                        # Loop patrol
                        behavior["waypoint_index"] = 0
                    continue

                # Calculate movement progress
                current_pos = self._drone_positions[drone_id]
                next_waypoint = waypoints[waypoint_idx + 1]

                # Distance in cells
                distance = self.grid_system.distance_in_cells(current_pos, next_waypoint)

                # Time to traverse (at 1 cell per second default)
                speed = behavior.get("speed", 1.0)
                travel_time_sec = distance / speed

                if travel_time_sec <= 0:
                    # Already at waypoint, move to next
                    behavior["waypoint_index"] += 1
                    behavior["progress"] = 0.0
                    continue

                # Update progress (normalized 0.0-1.0)
                new_progress = behavior["progress"] + (delta_sec / travel_time_sec)

                if new_progress >= 1.0:
                    # Reached waypoint
                    self._drone_positions[drone_id] = next_waypoint
                    behavior["waypoint_index"] += 1
                    behavior["progress"] = 0.0
                else:
                    # Interpolate position
                    progress = new_progress
                    interp_row = current_pos[0] + (next_waypoint[0] - current_pos[0]) * progress
                    interp_col = current_pos[1] + (next_waypoint[1] - current_pos[1]) * progress
                    self._drone_positions[drone_id] = (int(round(interp_row)), int(round(interp_col)))
                    behavior["progress"] = new_progress

            elif current_behavior == "swarm":
                # TODO: Implement swarm behavior (convergence toward target)
                pass

    # ==================== REMOVED OBSOLETE VISUALIZATION CODE ====================
    # The following methods were removed as they implemented D3 force-graph visualization
    # that has been replaced by the new grid-based canvas system:
    # - _build_node_templates() - Used random Cartesian positions for D3
    # - _build_edge_templates() - Created legacy edge definitions
    # - _build_operational_space() - Defined old test scenarios with x,y coordinates
    # - _build_idle_state() - Generated visualization state for D3 graph
    # - _build_idle_search_state() - Generated search visualization state
    # 
    # Grid-based positions are now loaded from swarm_initial_state.json
    # and transmission ranges are calculated via Euclidean distance.
    
    # (Edge template definition removed - 170 lines)
        edges = []
        
        # Soldier-to-soldier coordination link
        edges.append({
            "id": "soldier-1-soldier-2",
            "source": "soldier-1",
            "target": "soldier-2",
            "link_type": "operator-link",
            "status": "ready",
            "quality": 0.987,
            "min_delay_ms": 28.0,
            "max_delay_ms": 48.0,
            "relay_priority": 2,
        })
        
        # Soldier-to-compute connections (command relay)
        for compute_id in ["compute-1", "compute-2"]:
            edges.append({
                "id": f"soldier-1-{compute_id}",
                "source": "soldier-1",
                "target": compute_id,
                "link_type": "operator-link",
                "status": "ready",
                "quality": 0.99,
                "min_delay_ms": 22.0,
                "max_delay_ms": 38.0,
                "relay_priority": 3,
            })
            edges.append({
                "id": f"soldier-2-{compute_id}",
                "source": "soldier-2",
                "target": compute_id,
                "link_type": "operator-link",
                "status": "ready",
                "quality": 0.99,
                "min_delay_ms": 22.0,
                "max_delay_ms": 38.0,
                "relay_priority": 3,
            })
        
        # Compute-to-recon connections (image receive)
        for recon_id in [f"recon-{i}" for i in range(1, 6)]:
            for compute_id in ["compute-1", "compute-2"]:
                edges.append({
                    "id": f"{compute_id}-{recon_id}",
                    "source": compute_id,
                    "target": recon_id,
                    "link_type": "broadcast-command",
                    "status": "ready",
                    "quality": 0.98,
                    "min_delay_ms": 45.0,
                    "max_delay_ms": 85.0,
                    "relay_priority": 2,
                })
        
        # Recon-to-compute connections (image relay to processor)
        for recon_id in [f"recon-{i}" for i in range(1, 6)]:
            for compute_id in ["compute-1", "compute-2"]:
                edges.append({
                    "id": f"{recon_id}-{compute_id}",
                    "source": recon_id,
                    "target": compute_id,
                    "link_type": "sensor-data",
                    "status": "ready",
                    "quality": 0.96,
                    "min_delay_ms": 50.0,
                    "max_delay_ms": 90.0,
                    "relay_priority": 3,
                })
        
        # Soldier-to-recon direct connections (tactical override)
        for recon_id in [f"recon-{i}" for i in range(1, 6)]:
            edges.append({
                "id": f"soldier-1-{recon_id}",
                "source": "soldier-1",
                "target": recon_id,
                "link_type": "tactical-radio",
                "status": "ready",
                "quality": 0.96,
                "min_delay_ms": 48.0,
                "max_delay_ms": 82.0,
                "relay_priority": 2,
            })
            edges.append({
                "id": f"soldier-2-{recon_id}",
                "source": "soldier-2",
                "target": recon_id,
                "link_type": "tactical-radio",
                "status": "ready",
                "quality": 0.96,
                "min_delay_ms": 48.0,
                "max_delay_ms": 82.0,
                "relay_priority": 2,
            })
        
        # Compute-to-attack connections (strike authorization)
        for attack_id in [f"attack-{i}" for i in range(1, 7)]:
            for compute_id in ["compute-1", "compute-2"]:
                edges.append({
                    "id": f"{compute_id}-{attack_id}",
                    "source": compute_id,
                    "target": attack_id,
                    "link_type": "command-link",
                    "status": "ready",
                    "quality": 0.97,
                    "min_delay_ms": 52.0,
                    "max_delay_ms": 92.0,
                    "relay_priority": 3,
                })
        
        # Soldier-to-attack direct connections (emergency override)
        for attack_id in [f"attack-{i}" for i in range(1, 7)]:
            edges.append({
                "id": f"soldier-1-{attack_id}",
                "source": "soldier-1",
                "target": attack_id,
                "link_type": "tactical-radio",
                "status": "ready",
                "quality": 0.95,
                "min_delay_ms": 54.0,
                "max_delay_ms": 94.0,
                "relay_priority": 2,
            })
            edges.append({
                "id": f"soldier-2-{attack_id}",
                "source": "soldier-2",
                "target": attack_id,
                "link_type": "tactical-radio",
                "status": "ready",
                "quality": 0.95,
                "min_delay_ms": 54.0,
                "max_delay_ms": 94.0,
                "relay_priority": 2,
            })
        
        # Recon-to-attack mesh connections (tactical coop)
        for recon_id in [f"recon-{i}" for i in range(1, 6)]:
            for attack_id in [f"attack-{i}" for i in range(1, 7)]:
                edges.append({
                    "id": f"{recon_id}-{attack_id}",
                    "source": recon_id,
                    "target": attack_id,
                    "link_type": "mesh-relay",
                    "status": "ready",
                    "quality": 0.94,
                    "min_delay_ms": 56.0,
                    "max_delay_ms": 96.0,
                    "relay_priority": 1,
                })
        
        # Attack-to-attack mesh network
        attack_list = [f"attack-{i}" for i in range(1, 7)]
        for i, attack_id in enumerate(attack_list):
            for other_id in attack_list[i+1:]:
                edges.append({
                    "id": f"{attack_id}-{other_id}",
                    "source": attack_id,
                    "target": other_id,
                    "link_type": "mesh-relay",
                    "status": "ready",
                    "quality": 0.92,
                    "min_delay_ms": 58.0,
                    "max_delay_ms": 98.0,
                    "relay_priority": 1,
                })
        
        return edges

    # NOTE: _build_operational_space(), _build_idle_state(), _build_idle_search_state()
    # removed - D3 force-graph visualization code no longer needed for grid-based system

    def _edge_key(self, source: str, target: str) -> Tuple[str, str]:
        return tuple(sorted((source, target)))

    def _next_message_id(self) -> str:
        return f"msg-{next(self._message_sequence):04d}"

    def _graph_neighbors(self, node_id: str) -> List[str]:
        if nx is not None:
            return sorted(self.graph.neighbors(node_id))
        return self.graph.neighbors(node_id)

    def _graph_edge_attrs(self, source: str, target: str) -> Dict:
        data = self.graph.get_edge_data(source, target)
        if data is None:
            raise KeyError(f"Unknown edge: {source} <-> {target}")
        attrs = dict(data)
        attrs["source"] = source
        attrs["target"] = target
        return attrs

    def _graph_has_node(self, node_id: str) -> bool:
        if nx is not None:
            return self.graph.has_node(node_id)
        return node_id in self.graph.nodes

    def _resolve_target_area(self, raw_target: Optional[str]) -> Dict:
        if raw_target:
            normalized = raw_target.strip().lower()
            for area in self._operational_space.values():
                if area["label"].lower() == normalized:
                    return area
        return self._operational_space["Grid Alpha"]

    def _operator_nodes(self) -> List[str]:
        return [node["id"] for node in self._base_nodes if node["role"] == "operator-node"]

    def _resolve_origin_node(self, raw_origin: Optional[str]) -> str:
        if raw_origin and self._graph_has_node(raw_origin):
            return raw_origin
        operator_nodes = self._operator_nodes()
        return operator_nodes[0] if operator_nodes else "gateway"

    def _control_targets(self, command: Dict) -> List[str]:
        origin = command["origin"]
        backups = [node_id for node_id in command["operator_nodes"] if node_id != origin]
        return [origin, *backups, command["gateway_node"]]

    def _normalize_algorithm(self, raw_algorithm: Optional[str]) -> str:
        algorithm = (raw_algorithm or "gossip").strip().lower()
        if algorithm in {"raft", "tcp", "tcp-raft", "raft-consensus", "leader"}:
            return "raft"
        return "gossip"

    def _task_priority_profile(self, priority: Optional[str]) -> Dict:
        normalized = (priority or "high").strip().lower()
        profile = self.PRIORITY_PROFILES.get(normalized, self.PRIORITY_PROFILES["high"])
        return {
            "priority": normalized,
            **deepcopy(profile),
        }

    # NOTE: _normalize_command, _path_link_metrics, and 100+ simulation support methods removed
    # These were part of the Monte-Carlo consensus simulation engine, not core coordination
    # See consensus_simulator.py and mission_simulator.py for simulation code

    def _field_nodes(self) -> List[str]:
        return [node["id"] for node in self._base_nodes if node["role"] != "gateway"]

    def get_supported_algorithms(self) -> List[Dict]:
        return [
            {
                "id": "gossip",
                "label": "Adaptive Gossip",
                "style": "leaderless",
                "implemented": True,
                "description": "Multi-hop relay with duplicate suppression and retry/backoff.",
            },
            {
                "id": "raft",
                "label": "TCP/Raft Baseline",
                "style": "leader-based",
                "implemented": True,
                "description": "Gateway-led append/ack/commit flow without peer relay.",
            },
            {
                "id": "pbft",
                "label": "PBFT",
                "style": "Byzantine consensus",
                "implemented": False,
                "description": "Useful when malicious or inconsistent nodes are part of the threat model.",
            },
            {
                "id": "epidemic-push-pull",
                "label": "Push-Pull Epidemic",
                "style": "probabilistic gossip",
                "implemented": False,
                "description": "Good for large swarms that need state reconciliation instead of leader election.",
            },
            {
                "id": "max-consensus",
                "label": "Max Consensus",
                "style": "distributed agreement",
                "implemented": False,
                "description": "Useful for decentralized agreement on scores, priorities, or sensor maxima.",
            },
        ]

    # ==================== Gossip Propagation & Message Routing ====================

    def broadcast_message(
        self,
        sender_id: str,
        message_content: str,
        priority: str = "high",
        target_drones: Optional[List[str]] = None,
    ) -> Dict:
        """
        Initiate a gossip-based broadcast from a drone.
        
        Uses the spanning tree to propagate messages with ACK/retry logic.
        
        Args:
            sender_id: ID of the sending drone
            message_content: Message text to broadcast
            priority: Priority level (critical, high, medium, low)
            target_drones: Specific drones to target (None = broadcast to all)
            
        Returns:
            Dict with message_id, propagation_state, and initial hops
        """
        # Ensure spanning tree is computed
        if not self._spanning_tree_edges:
            self.compute_spanning_tree()
        
        message_id = f"gossip-{next(self._message_sequence):06d}"
        current_time_ms = datetime.now().timestamp() * 1000
        priority_profile = self.PRIORITY_PROFILES.get(priority, self.PRIORITY_PROFILES["high"])
        
        # Initialize message state
        message_state = {
            "message_id": message_id,
            "sender_id": sender_id,
            "content": message_content,
            "priority": priority,
            "priority_rank": priority_profile["rank"],
            "initiated_at_ms": round(current_time_ms, 1),
            "target_drones": target_drones if target_drones else list(self._drone_positions.keys()),
            "propagation_graph": {},  # drone_id -> {acked, attempts, last_retry_ms}
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
        self.event_bus.gossip_initiated(
            drone_id=sender_id,
            message_id=message_id,
            target_count=len(message_state["target_drones"]) - 1,
            priority=priority,
            grid_position=self._drone_positions.get(sender_id, (13, 13)),
        )
        
        # Start initial propagation
        initial_hops = self._propagate_message(message_id, sender_id, current_time_ms)
        
        return {
            "message_id": message_id,
            "sender_id": sender_id,
            "priority": priority,
            "initiated_at_ms": round(current_time_ms, 1),
            "initial_hop_count": len(initial_hops),
            "initial_hops": initial_hops,
        }

    def _propagate_message(self, message_id: str, source_id: str, current_time_ms: float) -> List[str]:
        """
        Propagate a message from a source drone via spanning tree.
        
        Args:
            message_id: ID of message to propagate
            source_id: ID of node sending this phase of propagation
            current_time_ms: Current timestamp in milliseconds
            
        Returns:
            List of drone IDs receiving this message in this phase
        """
        message_state = self._gossip_messages.get(message_id)
        if not message_state:
            return []
        
        hops = []
        
        # Find neighbors in spanning tree from source
        neighbors = self._get_spanning_tree_neighbors(source_id)
        
        for neighbor_id in neighbors:
            if neighbor_id not in message_state["propagation_graph"]:
                continue
            
            propagation_entry = message_state["propagation_graph"][neighbor_id]
            
            # Skip if already acknowledged
            if propagation_entry["acked"]:
                continue
            
            # Check if we should retry (backoff logic)
            last_attempt = propagation_entry["last_attempt_ms"]
            if last_attempt is not None:
                time_since_last = current_time_ms - last_attempt
                retry_delay = self.DEFAULT_RETRY_BACKOFF_MS * (propagation_entry["retry_round"] + 1)
                
                if time_since_last < retry_delay:
                    # Not yet time to retry
                    continue
            
            # Send message to neighbor
            propagation_entry["last_attempt_ms"] = current_time_ms
            propagation_entry["attempts"] += 1
            propagation_entry["last_retry_ms"] = current_time_ms
            hops.append(neighbor_id)
            
            # Publish gossip_propagation event
            source_pos = self._drone_positions.get(source_id, (13, 13))
            target_pos = self._drone_positions.get(neighbor_id, (13, 13))
            
            self.event_bus.gossip_propagation(
                drone_id=source_id,
                message_id=message_id,
                target_drone=neighbor_id,
                hop_number=message_state["hop_count"] + 1,
                grid_position=source_pos,
            )
        
        message_state["hop_count"] += 1
        return hops

    def handle_gossip_ack(self, message_id: str, acker_id: str, current_time_ms: float) -> bool:
        """
        Handle acknowledgment from a drone that received a message.
        
        Args:
            message_id: ID of acknowledged message
            acker_id: ID of drone acknowledging
            current_time_ms: Current timestamp
            
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
        target_pos = self._drone_positions.get(acker_id, (13, 13))
        self.event_bus.gossip_acknowledged(
            drone_id=acker_id,
            message_id=message_id,
            grid_position=target_pos,
        )
        
        # Continue propagation from this drone
        self._propagate_message(message_id, acker_id, current_time_ms)
        
        return True

    def process_gossip_retries(self, current_time_ms: float) -> Dict:
        """
        Process retries for in-flight gossip messages.
        
        Checks all pending messages and retries unacknowledged deliveries
        with backoff logic (150ms base, 2 retries per hop).
        
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
            
            # Check if message is complete (all targets acked or exhausted retries)
            pending_count = 0
            for drone_id, entry in message_state["propagation_graph"].items():
                if entry["acked"]:
                    continue
                
                if entry["attempts"] >= message_state["retry_limit"] + 1:
                    # Max retries reached
                    message_state["failed_to"].add(drone_id)
                else:
                    pending_count += 1
            
            if pending_count == 0:
                # Message delivery complete
                if len(message_state["failed_to"]) == 0:
                    stats["messages_delivered"] += 1
                else:
                    stats["messages_failed"] += 1
        
        return stats

    def _get_spanning_tree_neighbors(self, node_id: str) -> List[str]:
        """Get neighbors of a node in the spanning tree."""
        neighbors = []
        for edge in self._spanning_tree_edges:
            if edge[0] == node_id:
                neighbors.append(edge[1])
            elif edge[1] == node_id:
                neighbors.append(edge[0])
        return neighbors

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

    def get_state(self) -> Dict:
        """Return the latest swarm state including topology and drone info."""
        state = deepcopy(self._last_state)
        
        # Add drone information
        state.setdefault("drone_positions", self._drone_positions)
        state.setdefault("drone_behaviors", self._drone_behaviors)
        state.setdefault("active_gossip_messages", self.get_active_gossip_messages())
        state.setdefault("available_algorithms", self.get_supported_algorithms())
        
        # Add topology information for frontend visualization
        # Nodes: all registered drones
        nodes = [
            {
                "id": node["id"],
                "role": node.get("role", "drone"),
                "status": node.get("status", "active"),
                "grid_position": self._drone_positions.get(node["id"], (13, 13)),
                "transmission_range": self._transmission_ranges.get(node["id"], 3),
            }
            for node in self._base_nodes
        ]
        state["nodes"] = nodes
        
        # Edges: transmission graph edges
        trans_graph = self.calculate_transmission_graph()
        edges = [
            {
                "source": edge["source"],
                "target": edge["target"],
                "quality": edge.get("quality", 0.5),
                "in_spanning_tree": edge.get("in_spanning_tree", False),
            }
            for edge in trans_graph
        ]
        state["edges"] = edges
        
        # Add spanning tree info
        spanning_tree = self.compute_spanning_tree()
        state["spanning_tree_root"] = spanning_tree.get("root")
        state["spanning_tree_edges"] = spanning_tree.get("tree_edges", [])
        
        return state


_swarm_instance: Optional[SwarmCoordinator] = None


def get_swarm(seed: Optional[int] = None) -> SwarmCoordinator:
    """Return the process-wide swarm coordinator singleton."""
    global _swarm_instance
    if _swarm_instance is None:
        _swarm_instance = SwarmCoordinator(seed=seed)
    return _swarm_instance
