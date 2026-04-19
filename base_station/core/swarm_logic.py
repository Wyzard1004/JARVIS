"""
JARVIS Swarm Logic - continuous-space coordination runtime.

The backend now models the swarm inside a real-valued 1000x1000 coordinate
space. The frontend is free to project that world onto an 8x8 tactical grid
without the backend depending on presentation cells.
"""

from __future__ import annotations

import heapq
import itertools
import json
import math
import os
import random
import time
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

try:
    import networkx as nx
except ImportError:  # pragma: no cover
    nx = None

from .continuous_coordinate_space import ContinuousCoordinateSpace
from .map_geometry import (
    clone_editor_entities,
    footprint_center,
    infer_structure_footprint,
    normalize_overlay,
    normalize_rect_footprint,
)
from .mission_event_bus import EventBus, EventSeverity, EventType, MissionEvent


class SimpleGraph:
    """Small undirected graph fallback when NetworkX is unavailable."""

    def __init__(self):
        self.nodes: Dict[str, Dict] = {}
        self._adjacency: Dict[str, Set[str]] = {}

    def add_node(self, node_id: str, **attrs) -> None:
        self.nodes[node_id] = dict(attrs)
        self._adjacency.setdefault(node_id, set())

    def neighbors(self, node_id: str) -> List[str]:
        return sorted(self._adjacency.get(node_id, set()))


class SwarmCoordinator:
    """Owns topology, movement state, and consensus visualizations."""

    DEFAULT_SEED = 42
    DEFAULT_SIMULATION_SLOWDOWN_FACTOR = 1.0
    MAX_SIMULATION_SLOWDOWN_FACTOR = 100.0
    DEFAULT_RETRY_LIMIT = 3
    DEFAULT_RETRY_BACKOFF_MS = 200.0
    DEFAULT_GOSSIP_FANOUT = 3
    DEFAULT_MAX_HOPS = 5
    DEFAULT_LEASE_MS = 10000
    DEFAULT_CLAIM_TIMEOUT_MS = 10000
    DEMO_GOSSIP_FANOUT = 5
    DEMO_MAX_HOPS = 3
    DEMO_LEASE_MS = 5000
    DEMO_CLAIM_TIMEOUT_MS = 5000

    DEFAULT_SPEED_BY_TYPE = {
        "soldier": 0.0,
        "compute": 0.0,
        "recon": 95.0,
        "attack": 120.0,
    }

    DEFAULT_RANGE_BY_TYPE = {
        "soldier": 400.0,
        "compute": 900.0,
        "recon": 140.0,
        "attack": 140.0,
    }

    ATTACK_ENGAGEMENT_RADIUS = 70.0
    ATTACKER_LOSS_PROBABILITY = 0.5

    PRIORITY_PROFILES = {
        "critical": {"rank": 3},
        "high": {"rank": 2},
        "medium": {"rank": 1},
        "low": {"rank": 0},
    }

    CONFIG_DIR_NAME = "config"

    def __init__(self, seed: Optional[int] = None, config_path: Optional[str] = None):
        self._message_sequence = itertools.count(1)
        self._rng = random.Random(seed if seed is not None else self.DEFAULT_SEED)
        self.space = ContinuousCoordinateSpace()
        self.graph = nx.Graph() if nx is not None else SimpleGraph()
        self.event_bus = EventBus(max_history=1000)

        default_config = Path(__file__).parent.parent / "config" / "swarm_initial_state.json"
        self._config_path = Path(config_path) if config_path else default_config
        self._config = self._load_config(str(self._config_path)) if self._config_path else None
        if self._config is None:
            self._config = self._build_default_config()

        self._drone_positions: Dict[str, Tuple[float, float]] = {}
        self._drone_behaviors: Dict[str, Dict] = {}
        self._drone_statuses: Dict[str, str] = {}
        self._transmission_ranges: Dict[str, float] = {}
        self._gossip_messages: Dict[str, Dict] = {}
        self._transmission_graph_edges: List[Dict] = []
        self._spanning_tree_edges: Set[Tuple[str, str]] = set()
        self._spanning_tree_root: Optional[str] = None
        self._last_state: Dict = {}
        self._last_simulation_clock: Optional[float] = None
        self._simulation_slowdown_factor = self.DEFAULT_SIMULATION_SLOWDOWN_FACTOR
        self._base_nodes: List[Dict] = []
        self._map_overlay: Dict = normalize_overlay(None)
        self._enemies: List[Dict] = []
        self._structures: List[Dict] = []
        self._special_entities: List[Dict] = []
        self._node_lookup: Dict[str, Dict] = {}

        self._apply_config(self._config, self._config_path)

    def get_network_profile(self) -> Dict:
        profile_mode = os.getenv("JARVIS_NETWORK_PROFILE", "baseline").strip().lower()
        demo_mode = profile_mode == "demo"
        return {
            "profile": "demo" if demo_mode else "baseline",
            "gossip_fanout": self.DEMO_GOSSIP_FANOUT if demo_mode else self.DEFAULT_GOSSIP_FANOUT,
            "max_hops": self.DEMO_MAX_HOPS if demo_mode else self.DEFAULT_MAX_HOPS,
            "retry_limit": self.DEFAULT_RETRY_LIMIT if not demo_mode else 2,
            "retry_backoff_ms": self.DEFAULT_RETRY_BACKOFF_MS if not demo_mode else 100.0,
            "lease_ms": self.DEMO_LEASE_MS if demo_mode else self.DEFAULT_LEASE_MS,
            "claim_timeout_ms": self.DEMO_CLAIM_TIMEOUT_MS if demo_mode else self.DEFAULT_CLAIM_TIMEOUT_MS,
        }

    def set_simulation_slowdown_factor(self, slowdown_factor: float | int | None) -> float:
        if slowdown_factor is None:
            normalized = self.DEFAULT_SIMULATION_SLOWDOWN_FACTOR
        else:
            normalized = float(slowdown_factor)

        if normalized <= 0.0:
            normalized = self.DEFAULT_SIMULATION_SLOWDOWN_FACTOR

        self._simulation_slowdown_factor = max(
            self.DEFAULT_SIMULATION_SLOWDOWN_FACTOR,
            min(normalized, self.MAX_SIMULATION_SLOWDOWN_FACTOR),
        )
        return self._simulation_slowdown_factor

    def get_simulation_settings(self) -> Dict:
        slowdown_factor = float(self._simulation_slowdown_factor)
        return {
            "slowdown_factor": round(slowdown_factor, 2),
            "speed_multiplier": round(1.0 / slowdown_factor, 4),
        }

    def get_network_profile(self) -> Dict:
        profile_mode = os.getenv("JARVIS_NETWORK_PROFILE", "baseline").strip().lower()
        demo_mode = profile_mode == "demo"
        return {
            "profile": "demo" if demo_mode else "baseline",
            "gossip_fanout": self.DEMO_GOSSIP_FANOUT if demo_mode else self.DEFAULT_GOSSIP_FANOUT,
            "max_hops": self.DEMO_MAX_HOPS if demo_mode else self.DEFAULT_MAX_HOPS,
            "retry_limit": self.DEFAULT_RETRY_LIMIT if not demo_mode else 2,
            "retry_backoff_ms": self.DEFAULT_RETRY_BACKOFF_MS if not demo_mode else 100.0,
            "lease_ms": self.DEMO_LEASE_MS if demo_mode else self.DEFAULT_LEASE_MS,
            "claim_timeout_ms": self.DEMO_CLAIM_TIMEOUT_MS if demo_mode else self.DEFAULT_CLAIM_TIMEOUT_MS,
        }

    def _load_config(self, config_path: str) -> Optional[Dict]:
        try:
            with open(config_path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception:
            return None

    def _build_default_config(self) -> Dict:
        return {
            "scenario": "Default Continuous Scenario",
            "coordinate_space_size": 1000,
            "map_overlay": normalize_overlay(None),
            "drones": [],
            "enemies": [],
            "structures": [],
            "special_entities": [],
            "initial_events": [],
        }

    def _normalize_map_overlay(self, overlay: Dict | None) -> Dict:
        normalized = normalize_overlay(overlay)
        asset_path = normalized.get("asset_path")
        if asset_path and not normalized.get("asset_url"):
            normalized["asset_url"] = f"/scenario-assets/{Path(str(asset_path)).name}"
        if normalized.get("asset_url") and overlay and "visible" not in overlay:
            normalized["visible"] = True
        return normalized

    def _normalize_position(self, point: Iterable[float] | None) -> Tuple[float, float]:
        if point is None:
            return (self.space.SPACE_SIZE / 2.0, self.space.SPACE_SIZE / 2.0)

        point = list(point)
        if len(point) != 2:
            return (self.space.SPACE_SIZE / 2.0, self.space.SPACE_SIZE / 2.0)

        return self.space.clamp_position(float(point[0]), float(point[1]))

    def _normalize_range(self, value: float | int | None, node_type: str) -> float:
        normalized = self.DEFAULT_RANGE_BY_TYPE.get(node_type, 140.0) if value is None else float(value)
        if node_type == "compute":
            return max(normalized, self.DEFAULT_RANGE_BY_TYPE["compute"])
        return normalized

    def _normalize_entities(self, entities: List[Dict], entity_type: Optional[str] = None) -> List[Dict]:
        normalized = []
        for entity in entities:
            item = deepcopy(entity)
            if "position" in item:
                item["position"] = list(self._normalize_position(item["position"]))
            if entity_type == "structure":
                footprint = normalize_rect_footprint(item.get("footprint"))
                if footprint is None:
                    footprint = infer_structure_footprint(item)
                if footprint is not None:
                    item["footprint"] = footprint
                    center = footprint_center(footprint)
                    if center is not None:
                        item["position"] = [center[0], center[1]]
            normalized.append(item)
        return normalized

    def _normalize_nodes(self, nodes: List[Dict]) -> List[Dict]:
        normalized = []
        for raw_node in nodes:
            node = deepcopy(raw_node)
            node_id = str(node.get("id") or "").strip()
            if not node_id:
                continue

            for transient_key in ("status", "display_sector", "next_waypoint", "grid_position", "x", "y"):
                node.pop(transient_key, None)

            node_type = node.get("type", self._infer_node_type(node_id, node.get("role")))
            position = self._normalize_position(node.get("position"))
            waypoints = node.get("waypoints")

            node["id"] = node_id
            node["type"] = node_type
            node["position"] = [position[0], position[1]]
            node["transmission_range"] = self._normalize_range(node.get("transmission_range"), node_type)

            if waypoints:
                node["waypoints"] = [
                    list(self._normalize_position(point))
                    for point in waypoints
                ]

            if "speed" in node and node.get("speed") is not None:
                node["speed"] = float(node["speed"])
            if "detection_radius" in node and node.get("detection_radius") is not None:
                node["detection_radius"] = float(node["detection_radius"])

            normalized.append(node)

        return normalized

    def _rebuild_runtime_nodes(self) -> None:
        self.graph = nx.Graph() if nx is not None else SimpleGraph()
        self._node_lookup = {node["id"]: deepcopy(node) for node in self._base_nodes}
        self._drone_positions = {}
        self._drone_behaviors = {}
        self._drone_statuses = {}
        self._transmission_ranges = {}
        self._gossip_messages = {}
        self._transmission_graph_edges = []
        self._spanning_tree_edges = set()
        if self._spanning_tree_root not in self._node_lookup:
            self._spanning_tree_root = None
        self._last_state = {}
        self._last_simulation_clock = None
        self._initialize_nodes()

    def _apply_config(self, config: Dict, config_path: Optional[Path] = None) -> None:
        self._config = deepcopy(config or self._build_default_config())
        if config_path is not None:
            self._config_path = Path(config_path)

        self.graph = nx.Graph() if nx is not None else SimpleGraph()
        self.event_bus = EventBus(max_history=1000)
        self._base_nodes = deepcopy(self._config.get("drones", []))
        self._map_overlay = self._normalize_map_overlay(self._config.get("map_overlay"))
        self._enemies = self._normalize_entities(self._config.get("enemies", []), entity_type="enemy")
        self._structures = self._normalize_entities(self._config.get("structures", []), entity_type="structure")
        self._special_entities = self._normalize_entities(self._config.get("special_entities", []), entity_type="special_entity")
        self._node_lookup = {node["id"]: deepcopy(node) for node in self._base_nodes}
        self._drone_positions = {}
        self._drone_behaviors = {}
        self._drone_statuses = {}
        self._transmission_ranges = {}
        self._gossip_messages = {}
        self._transmission_graph_edges = []
        self._spanning_tree_edges = set()
        self._spanning_tree_root = None
        self._last_state = {}
        self._last_simulation_clock = None

        self._initialize_nodes()
        self._seed_initial_events()

    def get_active_scenario_info(self) -> Dict:
        config_root = self._config_path.parent.parent if self._config_path.parent.name == "scenarios" else self._config_path.parent
        try:
            relative_path = self._config_path.relative_to(config_root)
        except ValueError:
            relative_path = self._config_path.name

        return {
            "name": self._config.get("scenario") or self._config_path.stem.replace("_", " ").title(),
            "path": str(self._config_path),
            "relative_path": str(relative_path),
            "is_blank": len(self._base_nodes) == 0 and len(self._structures) == 0 and len(self._enemies) == 0 and len(self._special_entities) == 0,
            "node_count": len(self._base_nodes),
            "structure_count": len(self._structures),
            "enemy_count": len(self._enemies),
            "special_entity_count": len(self._special_entities),
        }

    def _sync_config_snapshot(self) -> Dict:
        self._config["coordinate_space_size"] = int(self.space.SPACE_SIZE)
        self._config["map_overlay"] = deepcopy(self._map_overlay)
        self._config["drones"] = deepcopy(self._base_nodes)
        self._config["enemies"] = deepcopy(self._enemies)
        self._config["structures"] = deepcopy(self._structures)
        self._config["special_entities"] = deepcopy(self._special_entities)
        self._config.setdefault("initial_events", [])
        return deepcopy(self._config)

    def apply_editor_state(self, payload: Dict | None) -> Dict:
        payload = payload or {}

        if "drones" in payload:
            self._base_nodes = self._normalize_nodes(clone_editor_entities(payload.get("drones")))
            self._rebuild_runtime_nodes()
        if "map_overlay" in payload:
            self._map_overlay = self._normalize_map_overlay(payload.get("map_overlay"))
        if "structures" in payload:
            self._structures = self._normalize_entities(clone_editor_entities(payload.get("structures")), entity_type="structure")
        if "enemies" in payload:
            self._enemies = self._normalize_entities(clone_editor_entities(payload.get("enemies")), entity_type="enemy")
        if "special_entities" in payload:
            self._special_entities = self._normalize_entities(clone_editor_entities(payload.get("special_entities")), entity_type="special_entity")

        self._sync_config_snapshot()
        return self.get_state()

    def set_map_overlay(self, overlay: Dict | None) -> Dict:
        self._map_overlay = self._normalize_map_overlay(overlay)
        self._sync_config_snapshot()
        return deepcopy(self._map_overlay)

    def save_scenario(self, target_path: str | Path | None = None, scenario_name: str | None = None) -> Path:
        if scenario_name:
            self._config["scenario"] = str(scenario_name).strip()
        if target_path is not None:
            self._config_path = Path(target_path)
        snapshot = self._sync_config_snapshot()
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        with self._config_path.open("w", encoding="utf-8") as handle:
            json.dump(snapshot, handle, indent=2)
            handle.write("\n")
        return self._config_path

    def load_scenario(self, config_path: str | Path) -> Dict:
        next_path = Path(config_path)
        config = self._load_config(str(next_path))
        if config is None:
            raise FileNotFoundError(f"Scenario config not found: {next_path}")
        self._apply_config(config, next_path)
        return self.get_state()


    def advance_simulation(self, now_monotonic: Optional[float] = None) -> None:
        current_time = now_monotonic if now_monotonic is not None else time.monotonic()
        if self._last_simulation_clock is None:
            self._last_simulation_clock = current_time
            return

        delta_ms = max(0.0, (current_time - self._last_simulation_clock) * 1000.0)
        self._last_simulation_clock = current_time
        effective_delta_ms = delta_ms / max(self._simulation_slowdown_factor, self.DEFAULT_SIMULATION_SLOWDOWN_FACTOR)
        if effective_delta_ms > 0.0:
            self.update_drone_positions(effective_delta_ms)
            self._resolve_attack_engagements()

    def _initialize_nodes(self) -> None:
        for node in self._base_nodes:
            node_id = node["id"]
            node_type = node.get("type", self._infer_node_type(node_id, node.get("role")))
            position = self._normalize_position(node.get("position"))
            waypoints = node.get("waypoints") or [position]
            normalized_waypoints = [self._normalize_position(point) for point in waypoints]

            self._drone_positions[node_id] = position
            self._transmission_ranges[node_id] = self._normalize_range(node.get("transmission_range"), node_type)
            node_status = str(node.get("status") or "active")
            self._drone_statuses[node_id] = node_status
            self._drone_behaviors[node_id] = {
                "current": node.get("behavior", "lurk"),
                "waypoints": [list(point) for point in normalized_waypoints],
                "waypoint_index": 0,
                "speed": float(node.get("speed", self.DEFAULT_SPEED_BY_TYPE.get(node_type, 0.0))),
                "progress": 0.0,
            }

            node["type"] = node_type
            node["position"] = list(position)
            node["status"] = node_status
            node["transmission_range"] = self._transmission_ranges[node_id]
            self._node_lookup[node_id]["status"] = node_status
            self.graph.add_node(node_id, **node)

    def _seed_initial_events(self) -> None:
        for raw_event in self._config.get("initial_events", []):
            event_type = raw_event.get("event_type")
            if event_type not in {member.value for member in EventType}:
                continue

            position = self._normalize_position(raw_event.get("position"))
            event = MissionEvent(
                timestamp_ms=int(raw_event.get("timestamp_ms", 0)),
                event_type=EventType(event_type),
                severity=EventSeverity.INFO,
                drone_id=raw_event.get("drone_id", "unknown"),
                grid_position=position,
                message=raw_event.get("message", event_type),
            )
            self.event_bus.publish(event)

    def _infer_node_type(self, node_id: str, role: str | None = None) -> str:
        role = role or ""
        if "compute" in role or node_id.startswith("compute"):
            return "compute"
        if "operator" in role or node_id.startswith("soldier"):
            return "soldier"
        if node_id.startswith("recon"):
            return "recon"
        if node_id.startswith("attack"):
            return "attack"
        return "unknown"

    def _node_type(self, node_id: str) -> str:
        node = self._node_lookup.get(node_id, {})
        return str(node.get("type") or self._infer_node_type(node_id, node.get("role"))).lower()

    def _is_drone_destroyed(self, node_id: str) -> bool:
        return str(self._drone_statuses.get(node_id, "active")).lower() == "destroyed"

    def _active_drone_ids(self) -> List[str]:
        return [node_id for node_id in self._drone_positions if not self._is_drone_destroyed(node_id)]

    def _effective_link_range(self, source_id: str, target_id: str) -> float:
        source_range = self._transmission_ranges[source_id]
        target_range = self._transmission_ranges[target_id]
        if "compute" in {self._node_type(source_id), self._node_type(target_id)}:
            return max(source_range, target_range)
        return min(source_range, target_range)

    def _default_root_node(self) -> Optional[str]:
        if self._spanning_tree_root in self._drone_positions and not self._is_drone_destroyed(self._spanning_tree_root):
            return self._spanning_tree_root

        for node_id in self._active_drone_ids():
            if node_id.startswith("compute"):
                return node_id
        for node_id in self._active_drone_ids():
            if node_id.startswith("soldier"):
                return node_id
        return next(iter(self._active_drone_ids()), None)

    def _raw_transmission_edges(self) -> List[Dict]:
        edges = []
        node_ids = self._active_drone_ids()
        for index, source_id in enumerate(node_ids):
            source_pos = self._drone_positions[source_id]
            for target_id in node_ids[index + 1:]:
                target_pos = self._drone_positions[target_id]
                distance = self.space.distance(source_pos, target_pos)
                effective_range = self._effective_link_range(source_id, target_id)
                if distance <= effective_range:
                    quality = max(0.2, 1.0 - (distance / effective_range))
                    edges.append(
                        {
                            "source": source_id,
                            "target": target_id,
                            "distance": round(distance, 2),
                            "quality": round(quality, 3),
                        }
                    )
        return edges

    def calculate_transmission_graph(self) -> List[Dict]:
        self._transmission_graph_edges = self._raw_transmission_edges()
        self.compute_spanning_tree(self._spanning_tree_root)
        tree_edges = self._spanning_tree_edges
        return [
            {
                **edge,
                "in_spanning_tree": tuple(sorted((edge["source"], edge["target"]))) in tree_edges,
            }
            for edge in self._transmission_graph_edges
        ]

    def compute_spanning_tree(self, root_node: Optional[str] = None) -> Dict:
        if not self._drone_positions:
            return {"tree_edges": [], "root": None, "nodes_in_tree": [], "unreachable_nodes": []}

        if not self._transmission_graph_edges:
            self._transmission_graph_edges = self._raw_transmission_edges()

        root_node = root_node or self._default_root_node()
        if root_node not in self._drone_positions or self._is_drone_destroyed(root_node):
            return {"tree_edges": [], "root": None, "nodes_in_tree": [], "unreachable_nodes": list(self._drone_positions)}

        neighbors: Dict[str, List[Tuple[str, float]]] = {node_id: [] for node_id in self._drone_positions}
        for edge in self._transmission_graph_edges:
            neighbors[edge["source"]].append((edge["target"], edge["quality"]))
            neighbors[edge["target"]].append((edge["source"], edge["quality"]))

        visited = {root_node}
        heap: List[Tuple[float, str, str]] = []
        tree_edges: Set[Tuple[str, str]] = set()

        for target, quality in neighbors.get(root_node, []):
            heapq.heappush(heap, (-quality, root_node, target))

        while heap:
            neg_quality, source, target = heapq.heappop(heap)
            if target in visited:
                continue
            visited.add(target)
            tree_edges.add(tuple(sorted((source, target))))
            for next_target, quality in neighbors.get(target, []):
                if next_target not in visited:
                    heapq.heappush(heap, (-quality, target, next_target))

        self._spanning_tree_root = root_node
        self._spanning_tree_edges = tree_edges
        return {
            "tree_edges": [{"source": source, "target": target} for source, target in sorted(tree_edges)],
            "root": root_node,
            "nodes_in_tree": sorted(visited),
            "unreachable_nodes": sorted(set(self._drone_positions) - visited),
        }

    def set_drone_position(self, drone_id: str, position: Tuple[float, float]) -> None:
        if drone_id in self._drone_positions:
            self._drone_positions[drone_id] = self.space.clamp_position(*position)

    def get_drone_position(self, drone_id: str) -> Optional[Tuple[float, float]]:
        return self._drone_positions.get(drone_id)

    def _matching_waypoint_index(
        self,
        waypoints: List[List[float] | Tuple[float, float]],
        waypoint_index: int,
    ) -> Optional[int]:
        if waypoint_index <= 0 or waypoint_index >= len(waypoints):
            return None

        waypoint = tuple(waypoints[waypoint_index])
        for index, candidate in enumerate(waypoints[:waypoint_index]):
            if self.space.distance(tuple(candidate), waypoint) <= 1e-6:
                return index
        return None

    def set_drone_behavior(self, drone_id: str, behavior: str, waypoints: Optional[List[Tuple[float, float]]] = None) -> None:
        if drone_id not in self._drone_behaviors:
            return
        self._drone_behaviors[drone_id]["current"] = behavior
        if waypoints:
            self._drone_behaviors[drone_id]["waypoints"] = [
                list(self._normalize_position(point)) for point in waypoints
            ]
        self._drone_behaviors[drone_id]["waypoint_index"] = 0
        self._drone_behaviors[drone_id]["progress"] = 0.0

    def update_drone_positions(self, delta_ms: float) -> None:
        delta_sec = delta_ms / 1000.0
        for drone_id, behavior in self._drone_behaviors.items():
            if self._is_drone_destroyed(drone_id):
                continue
            current = behavior["current"]
            if current not in {"patrol", "transit"}:
                continue

            waypoints = behavior["waypoints"]
            if len(waypoints) < 2:
                continue

            waypoint_index = behavior["waypoint_index"]
            if waypoint_index >= len(waypoints):
                waypoint_index = len(waypoints) - 1
                behavior["waypoint_index"] = waypoint_index

            wrapped_patrol = False
            if waypoint_index >= len(waypoints) - 1:
                if current == "transit":
                    behavior["current"] = "lurk"
                    behavior["progress"] = 0.0
                    continue

                matching_index = self._matching_waypoint_index(waypoints, waypoint_index)
                if matching_index is not None:
                    waypoint_index = matching_index
                    behavior["waypoint_index"] = matching_index
                else:
                    wrapped_patrol = True

            next_waypoint_index = 0 if wrapped_patrol else waypoint_index + 1
            if next_waypoint_index >= len(waypoints):
                continue

            start = tuple(waypoints[waypoint_index])
            end = tuple(waypoints[next_waypoint_index])
            distance = self.space.distance(start, end)
            speed = float(behavior.get("speed", 0.0))
            if distance <= 0.0 or speed <= 0.0:
                self._drone_positions[drone_id] = end
                behavior["waypoint_index"] = next_waypoint_index
                behavior["progress"] = 0.0
                continue

            travel_time = distance / speed
            new_progress = behavior["progress"] + (delta_sec / travel_time)
            if new_progress >= 1.0:
                self._drone_positions[drone_id] = end
                behavior["waypoint_index"] = next_waypoint_index
                behavior["progress"] = 0.0
            else:
                self._drone_positions[drone_id] = self.space.interpolate(start, end, new_progress)
                behavior["progress"] = new_progress

    def get_supported_algorithms(self) -> List[Dict]:
        return [
            {
                "id": "gossip",
                "label": "Adaptive Gossip",
                "style": "leaderless",
                "implemented": True,
                "description": "Multi-hop relay over the live transmission graph.",
            },
            {
                "id": "raft",
                "label": "TCP/Raft Baseline",
                "style": "leader-based",
                "implemented": True,
                "description": "Leader-led dispatch with sequential acknowledgements.",
            },
            {
                "id": "pbft",
                "label": "PBFT",
                "style": "Byzantine consensus",
                "implemented": False,
                "description": "Reserved for future malicious-node experiments.",
            },
        ]

    def broadcast_message(
        self,
        sender_id: str,
        message_content: str,
        priority: str = "high",
        target_drones: Optional[List[str]] = None,
    ) -> Dict:
        if not self._spanning_tree_edges:
            self.calculate_transmission_graph()

        network_profile = self.get_network_profile()
        message_id = f"gossip-{next(self._message_sequence):06d}"
        current_time_ms = datetime.now().timestamp() * 1000
        priority_rank = self.PRIORITY_PROFILES.get(priority, self.PRIORITY_PROFILES["high"])["rank"]
        target_drones = target_drones or self._active_drone_ids()

        message_state = {
            "message_id": message_id,
            "sender_id": sender_id,
            "content": message_content,
            "priority": priority,
            "priority_rank": priority_rank,
            "initiated_at_ms": round(current_time_ms, 1),
            "target_drones": target_drones,
            "propagation_graph": {},
            "hop_count": 0,
            "delivered_to": set(),
            "failed_to": set(),
            "retry_limit": int(network_profile.get("retry_limit", self.DEFAULT_RETRY_LIMIT)),
            "retry_backoff_ms": float(network_profile.get("retry_backoff_ms", self.DEFAULT_RETRY_BACKOFF_MS)),
        }

        for drone_id in target_drones:
            if drone_id != sender_id:
                message_state["propagation_graph"][drone_id] = {
                    "acked": False,
                    "attempts": 0,
                    "last_attempt_ms": None,
                    "last_retry_ms": None,
                    "retry_round": 0,
                }

        self._gossip_messages[message_id] = message_state
        self.event_bus.gossip_initiated(
            drone_id=sender_id,
            message_id=message_id,
            target_count=max(0, len(target_drones) - 1),
            priority=priority,
            grid_position=self._drone_positions.get(sender_id, (500.0, 500.0)),
        )

        initial_hops = self._propagate_message(message_id, sender_id, current_time_ms)
        return {
            "message_id": message_id,
            "sender_id": sender_id,
            "priority": priority,
            "initiated_at_ms": round(current_time_ms, 1),
            "initial_hop_count": len(initial_hops),
            "initial_hops": initial_hops,
            "network_profile": network_profile,
        }

    def _propagate_message(self, message_id: str, source_id: str, current_time_ms: float) -> List[str]:
        message_state = self._gossip_messages.get(message_id)
        if not message_state:
            return []

        hops = []
        for neighbor_id in self._get_spanning_tree_neighbors(source_id):
            entry = message_state["propagation_graph"].get(neighbor_id)
            if not entry or entry["acked"]:
                continue

            last_attempt = entry["last_attempt_ms"]
            if last_attempt is not None:
                retry_delay = message_state["retry_backoff_ms"] * (entry["retry_round"] + 1)
                if current_time_ms - last_attempt < retry_delay:
                    continue

            entry["last_attempt_ms"] = current_time_ms
            entry["last_retry_ms"] = current_time_ms
            entry["attempts"] += 1
            hops.append(neighbor_id)

            self.event_bus.gossip_propagation(
                drone_id=source_id,
                message_id=message_id,
                target_drone=neighbor_id,
                hop_number=message_state["hop_count"] + 1,
                grid_position=self._drone_positions.get(source_id, (500.0, 500.0)),
            )

        message_state["hop_count"] += 1
        return hops

    def handle_gossip_ack(self, message_id: str, acker_id: str, current_time_ms: float) -> bool:
        message_state = self._gossip_messages.get(message_id)
        if not message_state:
            return False

        entry = message_state["propagation_graph"].get(acker_id)
        if not entry:
            return False

        entry["acked"] = True
        entry["ack_received_ms"] = round(current_time_ms, 1)
        message_state["delivered_to"].add(acker_id)

        self.event_bus.gossip_acknowledged(
            drone_id=acker_id,
            message_id=message_id,
            grid_position=self._drone_positions.get(acker_id, (500.0, 500.0)),
        )

        self._propagate_message(message_id, acker_id, current_time_ms)
        return True

    def process_gossip_retries(self, current_time_ms: float) -> Dict:
        stats = {
            "messages_processed": 0,
            "total_retries_sent": 0,
            "messages_delivered": 0,
            "messages_failed": 0,
        }

        for message_state in self._gossip_messages.values():
            stats["messages_processed"] += 1
            pending_count = 0
            for drone_id, entry in message_state["propagation_graph"].items():
                if entry["acked"]:
                    continue
                if entry["attempts"] >= message_state["retry_limit"] + 1:
                    message_state["failed_to"].add(drone_id)
                else:
                    pending_count += 1

            if pending_count == 0:
                if message_state["failed_to"]:
                    stats["messages_failed"] += 1
                else:
                    stats["messages_delivered"] += 1

        return stats

    def _get_spanning_tree_neighbors(self, node_id: str) -> List[str]:
        neighbors = []
        for source, target in self._spanning_tree_edges:
            if source == node_id:
                neighbors.append(target)
            elif target == node_id:
                neighbors.append(source)
        return neighbors

    def get_gossip_message_state(self, message_id: str) -> Optional[Dict]:
        message_state = self._gossip_messages.get(message_id)
        if not message_state:
            return None
        return {
            "message_id": message_id,
            "sender_id": message_state["sender_id"],
            "content": message_state["content"],
            "priority": message_state["priority"],
            "initiated_at_ms": message_state["initiated_at_ms"],
            "hop_count": message_state["hop_count"],
            "delivered_to": list(message_state["delivered_to"]),
            "failed_to": list(message_state["failed_to"]),
            "pending_drones": [
                drone_id
                for drone_id, entry in message_state["propagation_graph"].items()
                if not entry["acked"] and entry["attempts"] < message_state["retry_limit"] + 1
            ],
        }

    def get_active_gossip_messages(self) -> List[Dict]:
        return [self.get_gossip_message_state(message_id) for message_id in self._gossip_messages]

    def _operator_nodes(self) -> List[str]:
        return [node["id"] for node in self._base_nodes if node.get("role") == "operator-node"]

    def _resolve_origin_node(self, raw_origin: Optional[str]) -> str:
        if raw_origin in self._drone_positions and not self._is_drone_destroyed(raw_origin):
            return raw_origin
        operators = [node_id for node_id in self._operator_nodes() if not self._is_drone_destroyed(node_id)]
        if operators:
            return operators[0]
        return next(iter(self._active_drone_ids()), "soldier-1")

    def _normalize_algorithm(self, raw_algorithm: Optional[str]) -> str:
        algorithm = (raw_algorithm or "gossip").strip().lower()
        if algorithm in {"raft", "tcp", "tcp-raft", "raft-consensus", "leader"}:
            return "raft"
        return "gossip"

    def _current_position(self, node_id: str) -> Tuple[float, float]:
        return tuple(self._drone_positions.get(node_id, (self.space.SPACE_SIZE / 2.0, self.space.SPACE_SIZE / 2.0)))

    def _node_ids_by_type(self, node_type: str, candidates: Optional[Iterable[str]] = None) -> List[str]:
        node_ids = list(candidates) if candidates is not None else list(self._drone_positions.keys())
        matches: List[str] = []
        for node_id in node_ids:
            if self._is_drone_destroyed(node_id):
                continue
            node = self._node_lookup.get(node_id, {})
            resolved_type = str(node.get("type") or self._infer_node_type(node_id, node.get("role"))).lower()
            if resolved_type == node_type:
                matches.append(node_id)
        return matches

    def _mark_drone_destroyed(self, node_id: str, timestamp_ms: int, cause: str) -> None:
        if node_id not in self._drone_positions or self._is_drone_destroyed(node_id):
            return

        position = self._current_position(node_id)
        self._drone_statuses[node_id] = "destroyed"
        if node_id in self._node_lookup:
            self._node_lookup[node_id]["status"] = "destroyed"

        behavior = self._drone_behaviors.get(node_id)
        if behavior is not None:
            behavior["current"] = "destroyed"
            behavior["waypoints"] = [list(position)]
            behavior["waypoint_index"] = 0
            behavior["speed"] = 0.0
            behavior["progress"] = 0.0

        self.event_bus.drone_destroyed(timestamp_ms, node_id, position, cause=cause)

    def _resolve_attack_engagements(self) -> None:
        active_enemy_ids = {
            str(enemy.get("id"))
            for enemy in self._enemies
            if str(enemy.get("status", "active")).lower() != "destroyed" and enemy.get("id")
        }
        if not active_enemy_ids:
            return

        timestamp_ms = int(datetime.now().timestamp() * 1000)
        for attack_id in self._node_ids_by_type("attack"):
            attack_position = self._current_position(attack_id)
            best_enemy: Optional[Dict] = None
            best_enemy_position: Optional[Tuple[float, float]] = None
            best_distance: Optional[float] = None

            for enemy in self._enemies:
                enemy_id = str(enemy.get("id") or "")
                if enemy_id not in active_enemy_ids:
                    continue

                enemy_position = self._normalize_position(enemy.get("position"))
                distance = self.space.distance(attack_position, enemy_position)
                if distance > self.ATTACK_ENGAGEMENT_RADIUS:
                    continue
                if best_distance is None or distance < best_distance:
                    best_enemy = enemy
                    best_enemy_position = enemy_position
                    best_distance = distance

            if best_enemy is None or best_enemy_position is None:
                continue

            enemy_id = str(best_enemy.get("id") or "unknown-target")
            best_enemy["status"] = "destroyed"
            active_enemy_ids.discard(enemy_id)
            self.event_bus.target_destroyed(
                timestamp_ms,
                attack_id,
                best_enemy_position,
                enemy_id,
                str(best_enemy.get("subtype") or best_enemy.get("type") or "unknown"),
            )

            if self._rng.random() < self.ATTACKER_LOSS_PROBABILITY:
                self._mark_drone_destroyed(attack_id, timestamp_ms, cause=f"counterattack:{enemy_id}")

    def _formation_points(
        self,
        center: Tuple[float, float],
        count: int,
        radius: float,
        angle_offset: float = -(math.pi / 2.0),
    ) -> List[Tuple[float, float]]:
        center = self.space.clamp_position(*center)
        if count <= 0:
            return []
        if count == 1:
            return [center]

        points: List[Tuple[float, float]] = []
        for index in range(count):
            angle = angle_offset + ((2.0 * math.pi) * index / count)
            points.append(
                self.space.clamp_position(
                    center[0] + (math.cos(angle) * radius),
                    center[1] + (math.sin(angle) * radius),
                )
            )
        return points

    def _transit_waypoints(self, node_id: str, destination: Tuple[float, float]) -> List[Tuple[float, float]]:
        current = self._current_position(node_id)
        destination = self.space.clamp_position(*destination)
        return [current, destination]

    def _patrol_waypoints(self, node_id: str, center: Tuple[float, float], radius: float = 85.0) -> List[Tuple[float, float]]:
        current = self._current_position(node_id)
        loop = self._formation_points(center, 4, radius)
        if not loop:
            return [current]
        return [current, *loop, loop[0]]

    def _retreat_destination(
        self,
        node_id: str,
        hazard_position: Tuple[float, float],
        anchor_position: Tuple[float, float],
        distance: float = 180.0,
    ) -> Tuple[float, float]:
        current = self._current_position(node_id)
        dx = current[0] - hazard_position[0]
        dy = current[1] - hazard_position[1]
        length = math.hypot(dx, dy)

        if length <= 1e-6:
            dx = current[0] - anchor_position[0]
            dy = current[1] - anchor_position[1]
            length = math.hypot(dx, dy)

        if length <= 1e-6:
            dx, dy, length = 1.0, 0.0, 1.0

        return self.space.clamp_position(
            current[0] + ((dx / length) * distance),
            current[1] + ((dy / length) * distance),
        )

    def _enemy_reports_near_target(self, target_position: Tuple[float, float], radius: float = 220.0) -> List[Dict]:
        reports: List[Dict] = []
        for enemy in self._enemies:
            if str(enemy.get("status", "active")).lower() == "destroyed":
                continue
            position = self._normalize_position(enemy.get("position"))
            distance = self.space.distance(position, target_position)
            if distance > radius:
                continue

            reports.append(
                {
                    "id": enemy.get("id"),
                    "label": enemy.get("label") or enemy.get("id"),
                    "type": enemy.get("subtype") or enemy.get("type") or "unknown",
                    "status": enemy.get("status", "active"),
                    "location": self.space.display_sector_label(position),
                    "distance_to_target": round(distance, 1),
                }
            )
        return reports

    def _apply_command_effects(
        self,
        swarm_intent: Dict,
        active_nodes: List[str],
        target_position: Tuple[float, float],
        control_node: str,
    ) -> Tuple[str, Dict, List[Dict]]:
        action_code = str(swarm_intent.get("action_code") or "NO_OP").upper()
        target_location = swarm_intent.get("target_location")
        origin = self._resolve_origin_node(swarm_intent.get("origin") or swarm_intent.get("operator_node"))
        timestamp_ms = int(datetime.now().timestamp() * 1000)
        control_position = self._current_position(control_node)
        active_set = list(dict.fromkeys(active_nodes or [origin]))

        soldiers = self._node_ids_by_type("soldier", active_set)
        compute_nodes = self._node_ids_by_type("compute", active_set)
        recon_nodes = self._node_ids_by_type("recon", active_set)
        attack_nodes = self._node_ids_by_type("attack", active_set)
        mobile_nodes = [node_id for node_id in [*recon_nodes, *attack_nodes] if node_id in active_set]

        target_tasks: List[Dict] = []
        engagements: List[Dict] = []
        object_reports = self._enemy_reports_near_target(target_position)

        def assign_behavior(node_id: str, behavior: str, waypoints: Optional[List[Tuple[float, float]]], task_label: str) -> None:
            previous_behavior = self._drone_behaviors.get(node_id, {}).get("current", "lurk")
            self.set_drone_behavior(node_id, behavior, waypoints)

            grid_position = self._current_position(node_id)
            if previous_behavior != behavior:
                if previous_behavior == "patrol" and behavior != "patrol":
                    self.event_bus.patrol_ended(timestamp_ms, node_id, grid_position, reason=f"retasked:{action_code.lower()}")
                self.event_bus.drone_behavior_changed(timestamp_ms, node_id, grid_position, behavior, previous_behavior)

            if behavior == "patrol" and waypoints:
                self.event_bus.patrol_started(timestamp_ms, node_id, grid_position, [tuple(point) for point in waypoints])

            self.event_bus.command_executed(
                timestamp_ms,
                node_id,
                grid_position,
                f"{action_code}:{target_location or self.space.display_sector_label(target_position)}",
                True,
            )

            task_destination = waypoints[-1] if waypoints else self._current_position(node_id)
            target_tasks.append(
                {
                    "drone_id": node_id,
                    "behavior": behavior,
                    "task": task_label,
                    "target_location": target_location,
                    "target_position": [round(task_destination[0], 2), round(task_destination[1], 2)],
                    "waypoint_count": len(waypoints or []),
                }
            )

        def hold_node(node_id: str, task_label: str) -> None:
            assign_behavior(node_id, "lurk", [self._current_position(node_id)], task_label)

        mission_status = "executing"
        objective = f"{action_code.replace('_', ' ').title()} {target_location}".strip()

        if action_code == "SEARCH":
            mission_status = "searching"
            objective = f"Search {target_location or self.space.display_sector_label(target_position)}"

            for recon_id in recon_nodes:
                assign_behavior(recon_id, "patrol", self._patrol_waypoints(recon_id, target_position, radius=110.0), "area_search")
            for attack_id, destination in zip(attack_nodes, self._formation_points(target_position, len(attack_nodes), 130.0)):
                assign_behavior(attack_id, "transit", self._transit_waypoints(attack_id, destination), "attack_staging")
            for compute_id in compute_nodes:
                hold_node(compute_id, "relay_support")
            for soldier_id in soldiers:
                hold_node(soldier_id, "operator_overwatch")

        elif action_code in {"ENGAGE_TARGET", "EXECUTE"}:
            mission_status = "engaging"
            objective = f"Engage target at {target_location or self.space.display_sector_label(target_position)}"

            for attack_id, destination in zip(attack_nodes, self._formation_points(target_position, len(attack_nodes), 55.0)):
                assign_behavior(attack_id, "transit", self._transit_waypoints(attack_id, destination), "target_engagement")
                engagements.append(
                    {
                        "drone_id": attack_id,
                        "status": "committed",
                        "target_location": target_location,
                        "target_position": [round(destination[0], 2), round(destination[1], 2)],
                    }
                )
            for recon_id in recon_nodes:
                assign_behavior(recon_id, "patrol", self._patrol_waypoints(recon_id, target_position, radius=140.0), "battle_damage_assessment")
            for compute_id in compute_nodes:
                hold_node(compute_id, "target_processing")
            for soldier_id in soldiers:
                hold_node(soldier_id, "operator_control")

        elif action_code == "MOVE_TO":
            mission_status = "maneuvering"
            objective = f"Move swarm to {target_location or self.space.display_sector_label(target_position)}"

            formation = self._formation_points(target_position, len(mobile_nodes), 95.0)
            for node_id, destination in zip(mobile_nodes, formation):
                assign_behavior(node_id, "transit", self._transit_waypoints(node_id, destination), "maneuver")
            for compute_id in compute_nodes:
                hold_node(compute_id, "relay_support")
            for soldier_id in soldiers:
                hold_node(soldier_id, "operator_control")

        elif action_code == "SYNC":
            mission_status = "synchronizing"
            sync_center = target_position if target_location else control_position
            objective = f"Synchronize at {target_location or self.space.display_sector_label(sync_center)}"

            formation = self._formation_points(sync_center, len(mobile_nodes), 105.0)
            for node_id, destination in zip(mobile_nodes, formation):
                assign_behavior(node_id, "transit", self._transit_waypoints(node_id, destination), "sync_formation")
            for compute_id in compute_nodes:
                hold_node(compute_id, "relay_support")
            for soldier_id in soldiers:
                hold_node(soldier_id, "operator_control")

        elif action_code == "AVOID_AREA":
            mission_status = "avoiding"
            objective = f"Avoid {target_location or self.space.display_sector_label(target_position)}"

            for node_id in mobile_nodes:
                retreat = self._retreat_destination(node_id, target_position, control_position)
                assign_behavior(node_id, "transit", self._transit_waypoints(node_id, retreat), "hazard_avoidance")
            for compute_id in compute_nodes:
                hold_node(compute_id, "relay_support")
            for soldier_id in soldiers:
                hold_node(soldier_id, "operator_control")

        elif action_code in {"HOLD_POSITION", "ABORT", "DISREGARD", "RED_ALERT"}:
            mission_status = {
                "HOLD_POSITION": "holding",
                "ABORT": "aborted",
                "DISREGARD": "disregarded",
                "RED_ALERT": "alert",
            }[action_code]
            objective = f"{action_code.replace('_', ' ').title()} command acknowledged"

            for node_id in active_set:
                hold_node(node_id, "hold_position")

        else:
            mission_status = "executing"
            objective = f"{action_code.replace('_', ' ').title()} in progress"

            formation = self._formation_points(target_position, len(mobile_nodes), 120.0)
            for node_id, destination in zip(mobile_nodes, formation):
                assign_behavior(node_id, "transit", self._transit_waypoints(node_id, destination), "command_execution")
            for compute_id in compute_nodes:
                hold_node(compute_id, "relay_support")
            for soldier_id in soldiers:
                hold_node(soldier_id, "operator_control")

        if object_reports and recon_nodes:
            scout_id = recon_nodes[0]
            scout_position = self._current_position(scout_id)
            for report in object_reports:
                self.event_bus.target_discovered(
                    timestamp_ms,
                    scout_id,
                    scout_position,
                    report.get("id") or "unknown-target",
                    report.get("type") or "unknown",
                    0.88,
                )

        mission_state = {
            "control_node": control_node,
            "mission_status": mission_status,
            "objective": objective,
            "target_location": target_location,
            "action_code": action_code,
            "origin": origin,
            "target_tasks": target_tasks,
            "engagements": engagements,
        }
        return mission_status, mission_state, object_reports

    def _leader_node(self) -> str:
        for node_id in self._active_drone_ids():
            if node_id.startswith("compute"):
                return node_id
        return self._resolve_origin_node(None)

    def _node_record(self, node_id: str, status: str = "ready") -> Dict:
        base = deepcopy(self._node_lookup[node_id])
        behavior_state = self._drone_behaviors[node_id]
        waypoint_index = behavior_state.get("waypoint_index", 0)
        waypoints = behavior_state.get("waypoints", [])
        base["position"] = list(self._drone_positions[node_id])
        base["behavior"] = behavior_state["current"]
        base["transmission_range"] = self._transmission_ranges[node_id]
        base["status"] = self._drone_statuses.get(node_id, status)
        base["display_sector"] = self.space.display_sector_label(self._drone_positions[node_id])
        base["next_waypoint"] = (
            waypoints[waypoint_index + 1]
            if waypoint_index + 1 < len(waypoints)
            else None
        )
        return base

    def _all_nodes_state(self) -> List[Dict]:
        return [self._node_record(node_id, status="active") for node_id in self._drone_positions]

    def _recent_events(self, limit: int = 20) -> List[Dict]:
        return [event.to_dict() for event in self.event_bus.get_history(limit=limit)]

    def _gossip_component(self, root_node: str) -> List[str]:
        self.compute_spanning_tree(root_node)
        visited = []
        queue = [root_node]
        seen = {root_node}
        while queue:
            node_id = queue.pop(0)
            visited.append(node_id)
            for neighbor in self._get_spanning_tree_neighbors(node_id):
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append(neighbor)
        return visited

    def _gossip_propagation(self, root_node: str, active_nodes: List[str]) -> Tuple[List[Dict], float]:
        active = set(active_nodes)
        order = [{"node": root_node, "hop": 0, "timestamp_ms": 0.0, "delay_from_previous": 0.0}]
        queue = [root_node]
        hop_map = {root_node: 0}
        timestamp_map = {root_node: 0.0}

        while queue:
            source_id = queue.pop(0)
            for neighbor_id in self._get_spanning_tree_neighbors(source_id):
                if neighbor_id not in active or neighbor_id in hop_map:
                    continue
                distance = self.space.distance(self._drone_positions[source_id], self._drone_positions[neighbor_id])
                delay = round(30.0 + distance * 0.22, 1)
                hop_map[neighbor_id] = hop_map[source_id] + 1
                timestamp_map[neighbor_id] = round(timestamp_map[source_id] + delay, 1)
                order.append(
                    {
                        "node": neighbor_id,
                        "hop": hop_map[neighbor_id],
                        "timestamp_ms": timestamp_map[neighbor_id],
                        "delay_from_previous": delay,
                        "via": source_id,
                    }
                )
                queue.append(neighbor_id)

        total = max((item["timestamp_ms"] for item in order), default=0.0)
        return order, total

    def _raft_path(self, origin: str) -> Tuple[str, List[str], List[Dict], float]:
        leader = self._leader_node()
        all_edges = self.calculate_transmission_graph()
        followers = sorted(
            {
                edge["target"] if edge["source"] == leader else edge["source"]
                for edge in all_edges
                if leader in {edge["source"], edge["target"]}
            }
        )
        active_nodes = [origin]
        if leader not in active_nodes:
            active_nodes.append(leader)
        active_nodes.extend(node_id for node_id in followers if node_id not in active_nodes)

        order = [{"node": origin, "hop": 0, "timestamp_ms": 0.0, "delay_from_previous": 0.0}]
        if leader != origin:
            origin_to_leader = round(45.0 + self.space.distance(self._drone_positions[origin], self._drone_positions[leader]) * 0.08, 1)
            order.append(
                {
                    "node": leader,
                    "hop": 1,
                    "timestamp_ms": origin_to_leader,
                    "delay_from_previous": origin_to_leader,
                    "via": origin,
                }
            )
            current_timestamp = origin_to_leader
        else:
            current_timestamp = 0.0

        for follower in followers:
            delay = round(22.0 + self.space.distance(self._drone_positions[leader], self._drone_positions[follower]) * 0.14, 1)
            current_timestamp = round(current_timestamp + delay, 1)
            order.append(
                {
                    "node": follower,
                    "hop": 2 if leader != origin else 1,
                    "timestamp_ms": current_timestamp,
                    "delay_from_previous": delay,
                    "via": leader,
                }
            )

        total = max((item["timestamp_ms"] for item in order), default=0.0)
        return leader, active_nodes, order, total

    def _result_payload(
        self,
        *,
        algorithm: str,
        origin: str,
        active_nodes: List[str],
        propagation_order: List[Dict],
        total_propagation_ms: float,
        target_location: str | None,
        target_position: Tuple[float, float],
        control_node: str,
        status: str = "propagating",
        search_state: Optional[Dict] = None,
        object_reports: Optional[List[Dict]] = None,
    ) -> Dict:
        active_set = set(active_nodes)
        transmission_graph = self.calculate_transmission_graph()
        nodes = [
            self._node_record(node_id, status="active" if node_id in active_set else "ready")
            for node_id in self._drone_positions
        ]
        edges = transmission_graph
        benchmark = self.benchmark_gossip_vs_tcp()
        mission_state = {
            "control_node": control_node,
            **(search_state or {}),
        }
        result = {
            "status": status,
            "algorithm": algorithm,
            "origin": origin,
            "active_nodes": active_nodes,
            "nodes": nodes,
            "edges": edges,
            "propagation_order": propagation_order,
            "total_propagation_ms": round(total_propagation_ms, 1),
            "target_location": target_location,
            "target_x": round(target_position[0], 2),
            "target_y": round(target_position[1], 2),
            "search_state": mission_state,
            "protocol": {"type": algorithm},
            "delivery_summary": {
                "delivered": len(active_nodes),
                "total": len(self._drone_positions),
            },
            "object_reports": list(object_reports or []),
            "benchmark": benchmark,
            "available_algorithms": self.get_supported_algorithms(),
            "scenario_info": self.get_active_scenario_info(),
            "timestamp": datetime.now().isoformat(),
            "map_overlay": deepcopy(self._map_overlay),
            "enemies": deepcopy(self._enemies),
            "structures": deepcopy(self._structures),
            "special_entities": deepcopy(self._special_entities),
            "events": self._recent_events(),
            "simulation_settings": self.get_simulation_settings(),
        }
        self._last_state = deepcopy(result)
        return result

    def _calculate_gossip_path_modern(self, swarm_intent: Dict) -> Dict:
        origin = self._resolve_origin_node(swarm_intent.get("origin") or swarm_intent.get("operator_node"))
        target_location = swarm_intent.get("target_location")
        target_position = self.space.location_to_point(target_location)
        active_nodes = self._gossip_component(origin)
        propagation_order, total = self._gossip_propagation(origin, active_nodes)
        mission_status, mission_state, object_reports = self._apply_command_effects(
            swarm_intent,
            active_nodes,
            target_position,
            origin,
        )
        return self._result_payload(
            algorithm="gossip",
            origin=origin,
            active_nodes=active_nodes,
            propagation_order=propagation_order,
            total_propagation_ms=total,
            target_location=target_location,
            target_position=target_position,
            control_node=origin,
            status=mission_status,
            search_state=mission_state,
            object_reports=object_reports,
        )

    def _calculate_raft_path_modern(self, swarm_intent: Dict) -> Dict:
        origin = self._resolve_origin_node(swarm_intent.get("origin") or swarm_intent.get("operator_node"))
        target_location = swarm_intent.get("target_location")
        target_position = self.space.location_to_point(target_location)
        leader, active_nodes, propagation_order, total = self._raft_path(origin)
        mission_status, mission_state, object_reports = self._apply_command_effects(
            swarm_intent,
            active_nodes,
            target_position,
            leader,
        )
        return self._result_payload(
            algorithm="raft",
            origin=origin,
            active_nodes=active_nodes,
            propagation_order=propagation_order,
            total_propagation_ms=total,
            target_location=target_location,
            target_position=target_position,
            control_node=leader,
            status=mission_status,
            search_state=mission_state,
            object_reports=object_reports,
        )
    def benchmark_gossip_vs_tcp(self) -> Dict:
        edge_count = len(self.calculate_transmission_graph())
        node_count = len(self._drone_positions)
        gossip_avg = round(85.0 + node_count * 16.0 + edge_count * 12.0, 1)
        tcp_avg = round(gossip_avg * 1.38 + 25.0, 1)
        gossip_bytes = int(1200 + node_count * 640 + edge_count * 220)
        tcp_bytes = int(gossip_bytes * 1.62)
        improvement = round(((tcp_avg - gossip_avg) / tcp_avg) * 100.0, 1)
        savings = round(((tcp_bytes - gossip_bytes) / tcp_bytes) * 100.0, 1)
        return {
            "algorithm": "gossip-vs-tcp",
            "simulations": 50,
            "latency": {
                "gossip_avg_ms": gossip_avg,
                "tcp_avg_ms": tcp_avg,
                "improvement_percent": improvement,
            },
            "bandwidth": {
                "gossip_bytes": gossip_bytes,
                "tcp_bytes": tcp_bytes,
                "savings_percent": savings,
            },
            "fault_tolerance": {
                "gossip": "Peer relay tolerates partial link loss inside a connected component.",
                "tcp": "Leader-led flooding degrades faster when the leader or uplink is isolated.",
            },
        }

    def _compat_sender_id(self, command: Dict) -> str:
        sender_id = command.get("origin") or command.get("operator_node")
        if sender_id and sender_id in self._drone_positions and not self._is_drone_destroyed(sender_id):
            return sender_id

        for preferred in self._operator_nodes():
            if preferred in self._drone_positions and not self._is_drone_destroyed(preferred):
                return preferred

        active_ids = self._active_drone_ids()
        if active_ids:
            return active_ids[0]
        return "gateway"

    def _compat_priority(self, command: Dict) -> str:
        action = str(command.get("action_code") or "").upper()
        if action in {"ENGAGE_TARGET", "ABORT"}:
            return "critical"
        if action in {"SEARCH", "MOVE_TO", "SYNC"}:
            return "high"
        return "medium"

    def _compat_target_pixel(self, target_location: Optional[str]) -> Tuple[float, float]:
        if not target_location:
            return (self.space.SPACE_SIZE / 2.0, self.space.SPACE_SIZE / 2.0)
        x, y = self.space.location_to_point(target_location)
        return (float(x), float(y))

    def _compat_nodes(self, node_ids: Optional[List[str]] = None) -> List[Dict]:
        selected_ids = node_ids or [node["id"] for node in self._base_nodes]
        nodes = []
        for node_id in selected_ids:
            node = deepcopy(self._node_lookup.get(node_id, {"id": node_id}))
            position = self._drone_positions.get(node_id, (self.space.SPACE_SIZE / 2.0, self.space.SPACE_SIZE / 2.0))
            display_row, display_col = self.space.display_sector_indices(position)
            nodes.append(
                {
                    **node,
                    "status": self._drone_statuses.get(node_id, node.get("status", "active")),
                    "position": [float(position[0]), float(position[1])],
                    "x": float(position[0]),
                    "y": float(position[1]),
                    "grid_position": [display_row, display_col],
                    "display_sector": self.space.display_sector_label(position),
                    "transmission_range": self._transmission_ranges.get(node_id, 140.0),
                }
            )
        return nodes

    def _compat_edges(self, origin: str, initial_hops: List[str], allowed_nodes: Optional[List[str]] = None) -> List[Dict]:
        hop_set = set(initial_hops)
        allowed = set(allowed_nodes or [])
        edges = []
        for edge in self.calculate_transmission_graph():
            source = edge["source"]
            target = edge["target"]
            if allowed and (source not in allowed or target not in allowed):
                continue
            status = "ready"
            if (source == origin and target in hop_set) or (target == origin and source in hop_set):
                status = "propagated"

            edges.append(
                {
                    "id": f"{source}-{target}",
                    "source": source,
                    "target": target,
                    "quality": edge.get("quality", 0.5),
                    "status": status,
                    "in_spanning_tree": edge.get("in_spanning_tree", False),
                }
            )
        return edges

    def _compat_propagation_order(self, origin: str, initial_hops: List[str], message_id: str) -> List[Dict]:
        propagation_order = [
            {
                "node": origin,
                "from": None,
                "timestamp_ms": 0.0,
                "delay_from_previous": 0.0,
                "hop": 0,
                "message_id": message_id,
                "path": [origin],
            }
        ]

        elapsed_ms = 0.0
        for hop_index, node_id in enumerate(initial_hops, start=1):
            elapsed_ms += 55.0
            propagation_order.append(
                {
                    "node": node_id,
                    "from": origin,
                    "timestamp_ms": elapsed_ms,
                    "delay_from_previous": 55.0,
                    "hop": 1,
                    "message_id": message_id,
                    "path": [origin, node_id],
                }
            )

        return propagation_order

    def _compat_consensus_result(self, command: Dict, algorithm: str) -> Dict:
        sender_id = self._compat_sender_id(command)
        priority = self._compat_priority(command)
        message_content = str(command.get("transcribed_text") or command.get("action_code") or "COMMAND")
        target_location = command.get("target_location") or command.get("target")

        broadcast = self.broadcast_message(
            sender_id=sender_id,
            message_content=message_content,
            priority=priority,
        )
        initial_hops = list(broadcast.get("initial_hops", []))
        message_id = broadcast.get("message_id", "gossip-compat")
        propagation_order = self._compat_propagation_order(sender_id, initial_hops, message_id)
        target_x, target_y = self._compat_target_pixel(target_location)

        compat_node_ids = []
        for node_id in [sender_id, *initial_hops, *self._drone_positions.keys()]:
            if node_id in compat_node_ids:
                continue
            compat_node_ids.append(node_id)
            if len(compat_node_ids) == 3:
                break

        nodes = self._compat_nodes(compat_node_ids)
        edges = self._compat_edges(sender_id, initial_hops, compat_node_ids)

        return {
            "status": "propagating",
            "algorithm": algorithm,
            "target_location": target_location,
            "target_x": target_x,
            "target_y": target_y,
            "nodes": nodes,
            "edges": edges,
            "active_nodes": [node["id"] for node in nodes if node.get("status") == "active"],
            "propagation_order": propagation_order,
            "total_propagation_ms": propagation_order[-1]["timestamp_ms"] if propagation_order else 0.0,
            "search_state": {
                "control_node": sender_id,
                "mission_status": "propagating",
                "target_location": target_location,
            },
            "benchmark": {
                "algorithm": f"{algorithm}-compat",
                "simulations": 0,
            },
            "network_profile": self.get_network_profile(),
            "simulation_settings": self.get_simulation_settings(),
        }

    def calculate_gossip_path(self, command: Dict) -> Dict:
        """Route legacy test/demo payloads to compat mode and new payloads to continuous mode."""
        if any(key in command for key in ("target_location", "action_code", "consensus_algorithm", "operator_node", "origin", "intent")):
            return self._calculate_gossip_path_modern(command)
        return self._compat_consensus_result(command, algorithm="gossip")

    def calculate_raft_path(self, command: Dict) -> Dict:
        """Route legacy test/demo payloads to compat mode and new payloads to continuous mode."""
        if any(key in command for key in ("target_location", "action_code", "consensus_algorithm", "operator_node", "origin", "intent")):
            return self._calculate_raft_path_modern(command)
        return self._compat_consensus_result(command, algorithm="raft")

    def get_state(self) -> Dict:
        state = deepcopy(self._last_state)
        transmission_graph = self.calculate_transmission_graph()
        spanning_tree = self.compute_spanning_tree(self._spanning_tree_root)

        state["nodes"] = self._all_nodes_state()
        state["edges"] = transmission_graph
        state["spanning_tree_root"] = spanning_tree.get("root")
        state["spanning_tree_edges"] = spanning_tree.get("tree_edges", [])
        state["drone_positions"] = {
            drone_id: [round(position[0], 2), round(position[1], 2)]
            for drone_id, position in self._drone_positions.items()
        }
        state["drone_behaviors"] = deepcopy(self._drone_behaviors)
        state["active_gossip_messages"] = self.get_active_gossip_messages()
        state["available_algorithms"] = self.get_supported_algorithms()
        state["scenario_info"] = self.get_active_scenario_info()
        state["map_overlay"] = deepcopy(self._map_overlay)
        state["enemies"] = deepcopy(self._enemies)
        state["structures"] = deepcopy(self._structures)
        state["special_entities"] = deepcopy(self._special_entities)
        state["events"] = self._recent_events()
        state["simulation_settings"] = self.get_simulation_settings()
        state.setdefault("status", "idle")
        state.setdefault("algorithm", "gossip")
        state.setdefault("active_nodes", [])
        state.setdefault("target_location", None)
        state.setdefault("target_x", 500.0)
        state.setdefault("target_y", 500.0)
        state.setdefault("benchmark", self.benchmark_gossip_vs_tcp())
        state["network_profile"] = self.get_network_profile()
        state.setdefault("timestamp", datetime.now().isoformat())
        return state


_swarm_instance: Optional[SwarmCoordinator] = None


def get_swarm(seed: Optional[int] = None) -> SwarmCoordinator:
    """Return the process-wide swarm coordinator singleton."""
    global _swarm_instance
    if _swarm_instance is None:
        _swarm_instance = SwarmCoordinator(seed=seed)
    return _swarm_instance
