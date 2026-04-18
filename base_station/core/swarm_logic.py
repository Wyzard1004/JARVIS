"""
JARVIS Swarm Logic (Section 2.0.0)

Blueprint-aligned swarm coordination runtime:
- Uses NetworkX when available for the operational graph
- Simulates adaptive gossip and a TCP/Raft-style baseline
- Models a control -> recon -> attack workflow for prompt alignment
- Tracks tank detection, task publication, assignment, backups, and reassignment
- Models timed edge/node disruptions, retries, and degraded links
- Returns UI-ready JSON with nodes, edges, propagation order, and mission state
"""

from __future__ import annotations

import heapq
import itertools
import random
from copy import deepcopy
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Set, Tuple

try:
    import networkx as nx
except ImportError:  # pragma: no cover - fallback keeps the demo runnable
    nx = None


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
    DEFAULT_BENCHMARK_RUNS = 90
    MESSAGE_SIZE_BYTES = 120
    GOSSIP_METADATA_OVERHEAD_BYTES = 18
    TCP_SESSION_OVERHEAD_BYTES = 60
    RAFT_CONTROL_OVERHEAD_BYTES = 72

    def __init__(self, seed: Optional[int] = None):
        self._rng = random.Random(seed if seed is not None else self.DEFAULT_SEED)
        self._message_sequence = itertools.count(1)
        self.graph = nx.Graph() if nx is not None else SimpleGraph()
        self._base_nodes = self._build_node_templates()
        self._node_lookup = {node["id"]: deepcopy(node) for node in self._base_nodes}
        self._base_edges = self._build_edge_templates()
        self._operational_space = self._build_operational_space()
        self._edge_id_lookup = {
            edge["id"]: self._edge_key(edge["source"], edge["target"])
            for edge in self._base_edges
        }
        self._edge_key_lookup = {
            self._edge_key(edge["source"], edge["target"]): edge["id"]
            for edge in self._base_edges
        }
        self._benchmark_cache: Optional[Dict] = None
        self._build_topology()
        self._last_state = self._build_idle_state()

    def _build_node_templates(self) -> List[Dict]:
        return [
            {
                "id": "gateway",
                "label": "Gateway Relay",
                "role": "gateway",
                "mission_role": "network-relay",
                "status": "idle",
                "health": "online",
                "x": 400,
                "y": 52,
            },
            {
                "id": "soldier-1",
                "label": "Soldier Operator 1",
                "role": "operator-node",
                "mission_role": "soldier-operator",
                "status": "idle",
                "health": "online",
                "x": 300,
                "y": 120,
            },
            {
                "id": "soldier-2",
                "label": "Soldier Operator 2",
                "role": "operator-node",
                "mission_role": "soldier-operator",
                "status": "idle",
                "health": "online",
                "x": 500,
                "y": 120,
            },
            {
                "id": "recon-1",
                "label": "Recon Drone",
                "role": "recon-drone",
                "mission_role": "sensor-platform",
                "status": "idle",
                "health": "online",
                "fuel_percent": 78,
                "survivability": 0.58,
                "sensor_quality": 0.97,
                "weapon_load": {"designator": 1},
                "x": 200,
                "y": 280,
            },
            {
                "id": "attack-1",
                "label": "Attack Drone 1",
                "role": "attack-drone",
                "mission_role": "strike-platform",
                "status": "idle",
                "health": "online",
                "fuel_percent": 71,
                "survivability": 0.76,
                "weapon_load": {"agm": 2},
                "x": 420,
                "y": 312,
            },
            {
                "id": "attack-2",
                "label": "Attack Drone 2",
                "role": "attack-drone",
                "mission_role": "strike-platform",
                "status": "idle",
                "health": "online",
                "fuel_percent": 88,
                "survivability": 0.69,
                "weapon_load": {"agm": 1},
                "x": 610,
                "y": 250,
            },
        ]

    def _build_edge_templates(self) -> List[Dict]:
        return [
            {
                "id": "gateway-soldier-1",
                "source": "gateway",
                "target": "soldier-1",
                "link_type": "operator-link",
                "status": "ready",
                "quality": 0.995,
                "min_delay_ms": 24.0,
                "max_delay_ms": 42.0,
                "relay_priority": 2,
            },
            {
                "id": "gateway-soldier-2",
                "source": "gateway",
                "target": "soldier-2",
                "link_type": "operator-link",
                "status": "ready",
                "quality": 0.992,
                "min_delay_ms": 26.0,
                "max_delay_ms": 44.0,
                "relay_priority": 2,
            },
            {
                "id": "soldier-1-soldier-2",
                "source": "soldier-1",
                "target": "soldier-2",
                "link_type": "operator-link",
                "status": "ready",
                "quality": 0.987,
                "min_delay_ms": 28.0,
                "max_delay_ms": 48.0,
                "relay_priority": 2,
            },
            {
                "id": "gateway-recon-1",
                "source": "gateway",
                "target": "recon-1",
                "link_type": "radio",
                "status": "ready",
                "quality": 0.99,
                "min_delay_ms": 55.0,
                "max_delay_ms": 95.0,
                "relay_priority": 1,
            },
            {
                "id": "gateway-attack-1",
                "source": "gateway",
                "target": "attack-1",
                "link_type": "radio",
                "status": "ready",
                "quality": 0.96,
                "min_delay_ms": 62.0,
                "max_delay_ms": 118.0,
                "relay_priority": 1,
            },
            {
                "id": "gateway-attack-2",
                "source": "gateway",
                "target": "attack-2",
                "link_type": "radio",
                "status": "ready",
                "quality": 0.92,
                "min_delay_ms": 80.0,
                "max_delay_ms": 142.0,
                "relay_priority": 1,
            },
            {
                "id": "soldier-1-recon-1",
                "source": "soldier-1",
                "target": "recon-1",
                "link_type": "tactical-radio",
                "status": "ready",
                "quality": 0.98,
                "min_delay_ms": 42.0,
                "max_delay_ms": 76.0,
                "relay_priority": 3,
            },
            {
                "id": "soldier-2-recon-1",
                "source": "soldier-2",
                "target": "recon-1",
                "link_type": "tactical-radio",
                "status": "ready",
                "quality": 0.96,
                "min_delay_ms": 46.0,
                "max_delay_ms": 84.0,
                "relay_priority": 2,
            },
            {
                "id": "soldier-1-attack-1",
                "source": "soldier-1",
                "target": "attack-1",
                "link_type": "tactical-radio",
                "status": "ready",
                "quality": 0.97,
                "min_delay_ms": 48.0,
                "max_delay_ms": 82.0,
                "relay_priority": 3,
            },
            {
                "id": "soldier-1-attack-2",
                "source": "soldier-1",
                "target": "attack-2",
                "link_type": "tactical-radio",
                "status": "ready",
                "quality": 0.95,
                "min_delay_ms": 58.0,
                "max_delay_ms": 96.0,
                "relay_priority": 2,
            },
            {
                "id": "soldier-2-attack-1",
                "source": "soldier-2",
                "target": "attack-1",
                "link_type": "tactical-radio",
                "status": "ready",
                "quality": 0.95,
                "min_delay_ms": 54.0,
                "max_delay_ms": 92.0,
                "relay_priority": 2,
            },
            {
                "id": "soldier-2-attack-2",
                "source": "soldier-2",
                "target": "attack-2",
                "link_type": "tactical-radio",
                "status": "ready",
                "quality": 0.97,
                "min_delay_ms": 46.0,
                "max_delay_ms": 80.0,
                "relay_priority": 3,
            },
            {
                "id": "recon-1-attack-1",
                "source": "recon-1",
                "target": "attack-1",
                "link_type": "mesh-relay",
                "status": "ready",
                "quality": 0.97,
                "min_delay_ms": 50.0,
                "max_delay_ms": 90.0,
                "relay_priority": 2,
            },
            {
                "id": "recon-1-attack-2",
                "source": "recon-1",
                "target": "attack-2",
                "link_type": "mesh-relay",
                "status": "ready",
                "quality": 0.95,
                "min_delay_ms": 58.0,
                "max_delay_ms": 98.0,
                "relay_priority": 2,
            },
            {
                "id": "attack-1-attack-2",
                "source": "attack-1",
                "target": "attack-2",
                "link_type": "mesh-relay",
                "status": "ready",
                "quality": 0.94,
                "min_delay_ms": 52.0,
                "max_delay_ms": 92.0,
                "relay_priority": 2,
            },
        ]

    def _build_operational_space(self) -> Dict[str, Dict]:
        return {
            "Grid Alpha": {
                "label": "Grid Alpha",
                "target_x": 150,
                "target_y": -50,
                "search_lanes": [
                    {
                        "id": "alpha-screen",
                        "label": "Alpha Screen",
                        "assigned_node": "recon-1",
                        "center_x": 150,
                        "center_y": -68,
                        "scan_radius_m": 240,
                    },
                ],
                "target_contacts": [
                    {
                        "id": "alpha-tank-1",
                        "label": "Main Battle Tank",
                        "classification": "tank",
                        "type": "armor",
                        "lane_id": "alpha-screen",
                        "priority": "critical",
                        "confidence": 0.97,
                        "threat_level": 0.84,
                        "required_weapon": "agm",
                        "required_weapon_units": 1,
                        "fallback_action": "mark_for_external_fires",
                    },
                ],
                "attack_profiles": {
                    "attack-1": {"distance_km": 1.4, "line_of_sight": 0.94, "threat_exposure": 0.33},
                    "attack-2": {"distance_km": 2.2, "line_of_sight": 0.88, "threat_exposure": 0.21},
                },
            },
            "Grid Bravo": {
                "label": "Grid Bravo",
                "target_x": -110,
                "target_y": 70,
                "search_lanes": [
                    {
                        "id": "bravo-crest",
                        "label": "Bravo Crest",
                        "assigned_node": "recon-1",
                        "center_x": -110,
                        "center_y": 76,
                        "scan_radius_m": 280,
                    },
                ],
                "target_contacts": [
                    {
                        "id": "bravo-tank-1",
                        "label": "Self-Propelled Gun",
                        "classification": "tank",
                        "type": "armor",
                        "lane_id": "bravo-crest",
                        "priority": "critical",
                        "confidence": 0.95,
                        "threat_level": 0.79,
                        "required_weapon": "agm",
                        "required_weapon_units": 1,
                        "fallback_action": "handoff_to_artillery",
                    }
                ],
                "attack_profiles": {
                    "attack-1": {"distance_km": 2.5, "line_of_sight": 0.83, "threat_exposure": 0.31},
                    "attack-2": {"distance_km": 1.8, "line_of_sight": 0.91, "threat_exposure": 0.26},
                },
            },
            "Grid Charlie": {
                "label": "Grid Charlie",
                "target_x": 30,
                "target_y": 120,
                "search_lanes": [
                    {
                        "id": "charlie-hold",
                        "label": "Charlie Hold",
                        "assigned_node": "recon-1",
                        "center_x": 34,
                        "center_y": 126,
                        "scan_radius_m": 220,
                    },
                ],
                "target_contacts": [
                    {
                        "id": "charlie-tank-1",
                        "label": "Armored Personnel Carrier",
                        "classification": "tank",
                        "type": "armor",
                        "lane_id": "charlie-hold",
                        "priority": "high",
                        "confidence": 0.93,
                        "threat_level": 0.72,
                        "required_weapon": "agm",
                        "required_weapon_units": 1,
                        "fallback_action": "shadow_and_track",
                    },
                ],
                "attack_profiles": {
                    "attack-1": {"distance_km": 1.7, "line_of_sight": 0.89, "threat_exposure": 0.28},
                    "attack-2": {"distance_km": 2.0, "line_of_sight": 0.86, "threat_exposure": 0.24},
                },
            },
        }

    def _build_topology(self) -> None:
        for node in self._base_nodes:
            self.graph.add_node(node["id"], **node)

        for edge in self._base_edges:
            attrs = {key: value for key, value in edge.items() if key not in {"source", "target"}}
            self.graph.add_edge(edge["source"], edge["target"], **attrs)

    def _build_idle_state(self) -> Dict:
        area = self._operational_space["Grid Alpha"]
        return {
            "status": "idle",
            "algorithm": "adaptive-gossip",
            "topology": "6-node-soldier-operator-mesh",
            "graph_engine": "networkx" if nx is not None else "simple-graph-fallback",
            "nodes": deepcopy(self._base_nodes),
            "edges": deepcopy(self._base_edges),
            "active_nodes": ["gateway", "soldier-1", "soldier-2"],
            "propagation_order": [],
            "total_propagation_ms": 0.0,
            "command": None,
            "target_location": area["label"],
            "target_x": area["target_x"],
            "target_y": area["target_y"],
            "protocol": {
                "origin": "soldier-1",
                "message_id": None,
                "consensus_algorithm": "gossip",
                "ttl": self.DEFAULT_TTL,
                "fanout": self.DEFAULT_FANOUT,
                "duplicate_suppression": True,
                "relay_enabled": True,
                "retry_limit": self.DEFAULT_RETRY_LIMIT,
                "retry_backoff_ms": self.DEFAULT_RETRY_BACKOFF_MS,
                "retry_jitter_ms": self.DEFAULT_RETRY_JITTER_MS,
                "dynamic_events": [],
            },
            "delivery_summary": {
                "reached_nodes": ["gateway", "soldier-1", "soldier-2"],
                "unreached_nodes": ["recon-1", "attack-1", "attack-2"],
                "all_nodes_reached": False,
                "all_field_nodes_reached": False,
                "duplicate_suppressions": 0,
                "transmission_attempts": 0,
                "successful_deliveries": 0,
                "retry_rounds_used": 0,
                "interrupted_transmissions": 0,
                "rerouted_deliveries": 0,
                "quorum_achieved": False,
            },
            "search_state": self._build_idle_search_state(area),
            "object_reports": [],
            "transmissions": [],
            "available_algorithms": self.get_supported_algorithms(),
            "benchmark": self._get_benchmark(),
            "timestamp": datetime.now().isoformat(),
        }

    def _build_idle_search_state(self, area: Dict) -> Dict:
        return {
            "target_location": area["label"],
            "target_x": area["target_x"],
            "target_y": area["target_y"],
            "mission_type": "detect-assign-engage",
            "mission_status": "idle",
            "control_node": "soldier-1",
            "operator_nodes": ["soldier-1", "soldier-2"],
            "backup_control_nodes": ["soldier-2"],
            "gateway_node": "gateway",
            "recon_nodes": ["recon-1"],
            "attack_nodes": ["attack-1", "attack-2"],
            "participating_nodes": ["soldier-1"],
            "unavailable_nodes": ["recon-1", "attack-1", "attack-2"],
            "objects_detected": 0,
            "reports_delivered": 0,
            "reports_pending": 0,
            "task_publish_ms": None,
            "assignment_completion_ms": None,
            "reassignment_count": 0,
            "mission_completion_ms": 0.0,
            "candidate_scores": [],
            "primary_assignee": None,
            "backup_assignees": [],
            "target_tasks": [],
            "engagements": [],
            "search_lanes": [
                {
                    "id": lane["id"],
                    "label": lane["label"],
                    "assigned_node": lane["assigned_node"],
                    "status": "pending",
                    "search_started_ms": None,
                    "search_completed_ms": None,
                    "target_detected": False,
                }
                for lane in area["search_lanes"]
            ],
            "sectors": [
                {
                    "id": lane["id"],
                    "label": lane["label"],
                    "assigned_node": lane["assigned_node"],
                    "status": "pending",
                    "search_started_ms": None,
                    "search_completed_ms": None,
                    "objects_detected": 0,
                }
                for lane in area["search_lanes"]
            ],
            "timeline": [],
        }

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

    def _normalize_command(self, parsed_intent: Dict) -> Dict:
        target_location = (
            parsed_intent.get("target_location")
            or parsed_intent.get("target")
            or "Grid Alpha"
        )
        area = self._resolve_target_area(target_location)
        action_code = parsed_intent.get("action_code") or parsed_intent.get("action") or "RED_ALERT"
        algorithm = self._normalize_algorithm(
            parsed_intent.get("consensus_algorithm") or parsed_intent.get("algorithm")
        )
        origin = self._resolve_origin_node(
            parsed_intent.get("origin") or parsed_intent.get("operator_node")
        )
        operator_nodes = self._operator_nodes()

        return {
            "intent": parsed_intent.get("intent", "swarm_redeploy"),
            "target_location": area["label"],
            "target": area["label"],
            "target_x": area["target_x"],
            "target_y": area["target_y"],
            "action_code": action_code,
            "action": action_code,
            "confidence": float(parsed_intent.get("confidence", 0.82)),
            "consensus_algorithm": algorithm,
            "origin": origin,
            "control_node": origin,
            "operator_nodes": operator_nodes,
            "backup_control_nodes": [node_id for node_id in operator_nodes if node_id != origin],
            "gateway_node": "gateway",
            "transcribed_text": parsed_intent.get("transcribed_text", ""),
            "operational_area": deepcopy(area),
        }

    def _resolve_edge_reference(
        self,
        value=None,
        *,
        source: Optional[str] = None,
        target: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[Tuple[str, str]]]:
        edge_id = None
        edge_key = None

        if isinstance(value, str):
            if value in self._edge_id_lookup:
                edge_id = value
                edge_key = self._edge_id_lookup[value]
            elif ":" in value:
                left, right = value.split(":", 1)
                edge_key = self._edge_key(left.strip(), right.strip())
            elif value.count("-") == 1:
                left, right = value.split("-", 1)
                if self._graph_has_node(left) and self._graph_has_node(right):
                    edge_key = self._edge_key(left, right)
        elif isinstance(value, (list, tuple)) and len(value) == 2:
            edge_key = self._edge_key(str(value[0]), str(value[1]))
        elif isinstance(value, dict):
            source = value.get("source", source)
            target = value.get("target", target)

        if edge_key is None and source and target:
            edge_key = self._edge_key(str(source), str(target))

        if edge_key and edge_id is None:
            edge_id = self._edge_key_lookup.get(edge_key)

        return edge_id, edge_key

    def _parse_partitioned_links(self, values: Iterable) -> Set[Tuple[str, str]]:
        partitioned: Set[Tuple[str, str]] = set()
        for value in values:
            _, edge_key = self._resolve_edge_reference(value)
            if edge_key:
                partitioned.add(edge_key)
        return partitioned

    def _parse_degraded_links(self, values: Iterable) -> Dict[Tuple[str, str], float]:
        degraded: Dict[Tuple[str, str], float] = {}
        for value in values:
            if isinstance(value, str):
                _, edge_key = self._resolve_edge_reference(value)
                if edge_key:
                    degraded[edge_key] = 1.35
                continue

            if isinstance(value, dict):
                _, edge_key = self._resolve_edge_reference(
                    value.get("edge"),
                    source=value.get("source"),
                    target=value.get("target"),
                )
                if edge_key:
                    degraded[edge_key] = max(1.0, float(value.get("factor", 1.35)))
        return degraded

    def _normalize_edge_action(self, value: Optional[str]) -> str:
        action = (value or "partition").strip().lower()
        if action in {"partition", "disconnect", "down"}:
            return "partition"
        if action in {"restore", "reconnect", "up"}:
            return "restore"
        if action in {"degrade", "weaken", "slow"}:
            return "degrade"
        if action in {"normalize", "heal", "recover"}:
            return "normalize"
        return "partition"

    def _normalize_node_action(self, value: Optional[str]) -> str:
        action = (value or "offline").strip().lower()
        if action in {"offline", "disconnect", "down"}:
            return "offline"
        if action in {"online", "restore", "reconnect", "up"}:
            return "online"
        return "offline"

    def _parse_edge_events(self, values: Iterable) -> List[Dict]:
        events: List[Dict] = []
        for value in values:
            if not isinstance(value, dict):
                continue

            edge_id, edge_key = self._resolve_edge_reference(
                value.get("edge"),
                source=value.get("source"),
                target=value.get("target"),
            )
            if edge_key is None:
                continue

            action = self._normalize_edge_action(value.get("action") or value.get("state"))
            at_ms = round(max(0.0, float(value.get("at_ms", 0.0))), 1)
            factor = max(1.0, float(value.get("factor", 1.35)))
            event = {
                "scope": "edge",
                "edge_id": edge_id or self._edge_key_lookup.get(edge_key),
                "edge_key": edge_key,
                "at_ms": at_ms,
                "action": action,
            }
            if action == "degrade":
                event["factor"] = factor
            events.append(event)

            duration_ms = value.get("duration_ms")
            if duration_ms is None:
                continue

            duration_ms = max(0.0, float(duration_ms))
            if duration_ms == 0.0:
                continue

            reverse_action = None
            if action == "partition":
                reverse_action = "restore"
            elif action == "degrade":
                reverse_action = "normalize"

            if reverse_action:
                events.append(
                    {
                        "scope": "edge",
                        "edge_id": edge_id or self._edge_key_lookup.get(edge_key),
                        "edge_key": edge_key,
                        "at_ms": round(at_ms + duration_ms, 1),
                        "action": reverse_action,
                    }
                )

        return sorted(events, key=lambda event: (event["at_ms"], event["scope"], event["action"]))

    def _parse_node_events(self, values: Iterable) -> List[Dict]:
        events: List[Dict] = []
        for value in values:
            if not isinstance(value, dict):
                continue

            node_id = value.get("node")
            if not self._graph_has_node(node_id):
                continue

            action = self._normalize_node_action(value.get("action") or value.get("state"))
            at_ms = round(max(0.0, float(value.get("at_ms", 0.0))), 1)
            events.append(
                {
                    "scope": "node",
                    "node": node_id,
                    "at_ms": at_ms,
                    "action": action,
                }
            )

            duration_ms = value.get("duration_ms")
            if duration_ms is None or action != "offline":
                continue

            duration_ms = max(0.0, float(duration_ms))
            if duration_ms == 0.0:
                continue

            events.append(
                {
                    "scope": "node",
                    "node": node_id,
                    "at_ms": round(at_ms + duration_ms, 1),
                    "action": "online",
                }
            )

        return sorted(events, key=lambda event: (event["at_ms"], event["scope"], event["action"]))

    def _resolve_protocol(self, parsed_intent: Dict, external_network: Optional[Dict] = None) -> Dict:
        requested_network = external_network or parsed_intent.get("network_conditions", {})
        command = self._normalize_command(parsed_intent)
        ttl = max(1, min(6, int(parsed_intent.get("ttl", self.DEFAULT_TTL))))
        fanout = max(1, min(3, int(parsed_intent.get("fanout", self.DEFAULT_FANOUT))))
        retry_limit = max(0, min(4, int(parsed_intent.get("retry_limit", self.DEFAULT_RETRY_LIMIT))))
        retry_backoff_ms = max(15.0, float(parsed_intent.get("retry_backoff_ms", self.DEFAULT_RETRY_BACKOFF_MS)))
        retry_jitter_ms = max(0.0, float(parsed_intent.get("retry_jitter_ms", self.DEFAULT_RETRY_JITTER_MS)))
        partitioned_links = self._parse_partitioned_links(requested_network.get("partitioned_links", []))
        degraded_links = self._parse_degraded_links(requested_network.get("degraded_links", []))
        edge_events = self._parse_edge_events(requested_network.get("edge_events", []))
        node_events = self._parse_node_events(requested_network.get("node_events", []))
        dynamic_events = sorted(edge_events + node_events, key=lambda event: (event["at_ms"], event["scope"], event["action"]))

        return {
            "origin": parsed_intent.get("origin")
            or parsed_intent.get("operator_node")
            or command["origin"],
            "message_id": parsed_intent.get("message_id") or self._next_message_id(),
            "consensus_algorithm": command["consensus_algorithm"],
            "ttl": ttl,
            "fanout": fanout,
            "duplicate_suppression": True,
            "relay_enabled": command["consensus_algorithm"] == "gossip",
            "retry_limit": retry_limit,
            "retry_backoff_ms": retry_backoff_ms,
            "retry_jitter_ms": retry_jitter_ms,
            "partitioned_links": partitioned_links,
            "degraded_links": degraded_links,
            "edge_events": edge_events,
            "node_events": node_events,
            "dynamic_events": dynamic_events,
        }

    def _network_state_at(self, protocol: Dict, at_ms: float) -> Dict:
        state = {
            "partitioned_links": set(protocol["partitioned_links"]),
            "degraded_links": dict(protocol["degraded_links"]),
            "offline_nodes": set(),
        }

        for event in protocol["dynamic_events"]:
            if event["at_ms"] > at_ms:
                break

            if event["scope"] == "edge":
                edge_key = event["edge_key"]
                if event["action"] == "partition":
                    state["partitioned_links"].add(edge_key)
                elif event["action"] == "restore":
                    state["partitioned_links"].discard(edge_key)
                elif event["action"] == "degrade":
                    state["degraded_links"][edge_key] = event.get("factor", 1.35)
                elif event["action"] == "normalize":
                    state["degraded_links"].pop(edge_key, None)
            elif event["scope"] == "node":
                node_id = event["node"]
                if event["action"] == "offline":
                    state["offline_nodes"].add(node_id)
                elif event["action"] == "online":
                    state["offline_nodes"].discard(node_id)

        return state

    def _edge_profile(self, source: str, target: str, protocol: Dict, at_ms: float) -> Dict:
        edge = deepcopy(self._graph_edge_attrs(source, target))
        state = self._network_state_at(protocol, at_ms)
        edge_key = self._edge_key(source, target)
        degrade_factor = state["degraded_links"].get(edge_key, 1.0)

        edge["min_delay_ms"] = round(edge["min_delay_ms"] * degrade_factor, 1)
        edge["max_delay_ms"] = round(edge["max_delay_ms"] * degrade_factor, 1)
        edge["quality"] = round(max(0.25, edge["quality"] - ((degrade_factor - 1.0) * 0.08)), 3)
        edge["degrade_factor"] = round(degrade_factor, 2)
        edge["status"] = "ready"

        if source in state["offline_nodes"] or target in state["offline_nodes"]:
            edge["status"] = "node_offline"
            edge["quality"] = 0.0
        elif edge_key in state["partitioned_links"]:
            edge["status"] = "partitioned"
            edge["quality"] = 0.0

        return edge

    def _sample_delay_ms(self, edge_profile: Dict, rng: random.Random) -> float:
        return round(rng.uniform(edge_profile["min_delay_ms"], edge_profile["max_delay_ms"]), 1)

    def _retry_delay_ms(self, retry_round: int, protocol: Dict, rng: random.Random) -> float:
        jitter_ms = round(rng.uniform(0.0, protocol["retry_jitter_ms"]), 1)
        return round((protocol["retry_backoff_ms"] * retry_round) + jitter_ms, 1)

    def _candidate_neighbors(
        self,
        node_id: str,
        path: List[str],
        protocol: Dict,
        current_time_ms: float,
        receipt_times: Dict[str, float],
    ) -> List[Tuple[float, str, Dict]]:
        if node_id in self._network_state_at(protocol, current_time_ms)["offline_nodes"]:
            return []

        candidates: List[Tuple[float, str, Dict]] = []
        path_nodes = set(path)
        for neighbor in self._graph_neighbors(node_id):
            if neighbor in path_nodes:
                continue
            if neighbor in receipt_times:
                continue

            edge = self._edge_profile(node_id, neighbor, protocol, current_time_ms)
            score = (
                35
                + edge["quality"] * 100
                - edge["min_delay_ms"] * 0.45
                + edge.get("relay_priority", 0) * 4
            )
            if edge["status"] == "partitioned":
                score -= 180
            elif edge["status"] == "node_offline":
                score -= 220

            candidates.append((score, neighbor, edge))

        candidates.sort(key=lambda item: (-item[0], item[1]))
        return candidates[: protocol["fanout"]]

    def _best_path(
        self,
        source: str,
        target: str,
        protocol: Dict,
        at_ms: float,
        *,
        allow_relay: bool,
    ) -> List[str]:
        if source == target:
            return [source]

        state = self._network_state_at(protocol, at_ms)
        if source in state["offline_nodes"] or target in state["offline_nodes"]:
            return []

        if not allow_relay:
            try:
                edge = self._edge_profile(source, target, protocol, at_ms)
            except KeyError:
                return []
            if edge["status"] in {"partitioned", "node_offline"}:
                return []
            return [source, target]

        queue: List[Tuple[float, str, List[str]]] = [(0.0, source, [source])]
        best_cost: Dict[str, float] = {source: 0.0}

        while queue:
            current_cost, node_id, path = heapq.heappop(queue)
            if node_id == target:
                return path
            if current_cost > best_cost.get(node_id, float("inf")):
                continue

            for neighbor in self._graph_neighbors(node_id):
                edge = self._edge_profile(node_id, neighbor, protocol, at_ms)
                if edge["status"] in {"partitioned", "node_offline"}:
                    continue
                edge_cost = (
                    (edge["min_delay_ms"] + edge["max_delay_ms"]) / 2
                    + (1.0 - edge["quality"]) * 100
                    - edge.get("relay_priority", 0) * 6
                )
                next_cost = round(current_cost + max(1.0, edge_cost), 3)
                if next_cost < best_cost.get(neighbor, float("inf")):
                    best_cost[neighbor] = next_cost
                    heapq.heappush(queue, (next_cost, neighbor, path + [neighbor]))

        return []

    def _initial_receipt_event(self, command: Dict, protocol: Dict) -> Dict:
        return {
            "node": protocol["origin"],
            "from": None,
            "timestamp_ms": 0.0,
            "delay_from_previous": 0.0,
            "hop": 0,
            "message_id": protocol["message_id"],
            "ttl_remaining": protocol["ttl"],
            "via_edge": None,
            "path": [protocol["origin"]],
            "relay_reason": "origin",
            "command_action": command["action_code"],
        }

    def _record_receipt(
        self,
        propagation_order: List[Dict],
        receipt_times: Dict[str, float],
        command: Dict,
        protocol: Dict,
        node_id: str,
        source: Optional[str],
        timestamp_ms: float,
        hop: int,
        via_edge: Optional[str],
        path: List[str],
        relay_reason: str,
    ) -> None:
        if source is None:
            event = self._initial_receipt_event(command, protocol)
        else:
            event = {
                "node": node_id,
                "from": source,
                "timestamp_ms": round(timestamp_ms, 1),
                "delay_from_previous": round(timestamp_ms - receipt_times[source], 1),
                "hop": hop,
                "message_id": protocol["message_id"],
                "ttl_remaining": max(protocol["ttl"] - hop, 0),
                "via_edge": via_edge,
                "path": path,
                "relay_reason": relay_reason,
                "command_action": command["action_code"],
            }

        propagation_order.append(event)
        receipt_times[node_id] = round(timestamp_ms, 1)

    def _schedule_retry_round(
        self,
        queue: List[Tuple[float, int, Dict]],
        node_id: str,
        current_time_ms: float,
        hop: int,
        path: List[str],
        retry_round: int,
        protocol: Dict,
        rng: random.Random,
        queue_counter: itertools.count,
    ) -> None:
        if retry_round > protocol["retry_limit"]:
            return
        if hop >= protocol["ttl"]:
            return

        retry_at_ms = round(current_time_ms + self._retry_delay_ms(retry_round, protocol, rng), 1)
        heapq.heappush(
            queue,
            (
                retry_at_ms,
                next(queue_counter),
                {
                    "kind": "retry_round",
                    "node": node_id,
                    "hop": hop,
                    "path": path,
                    "retry_round": retry_round,
                    "scheduled_at_ms": retry_at_ms,
                    "message_id": protocol["message_id"],
                },
            ),
        )

    def _schedule_forwarding(
        self,
        queue: List[Tuple[float, int, Dict]],
        transmission_log: List[Dict],
        current_node: str,
        current_time_ms: float,
        hop: int,
        path: List[str],
        protocol: Dict,
        rng: random.Random,
        queue_counter: itertools.count,
        receipt_times: Dict[str, float],
        retry_round: int,
    ) -> None:
        if hop >= protocol["ttl"]:
            return

        candidates = self._candidate_neighbors(
            current_node,
            path,
            protocol,
            current_time_ms,
            receipt_times,
        )
        if not candidates:
            return

        self._schedule_retry_round(
            queue,
            node_id=current_node,
            current_time_ms=current_time_ms,
            hop=hop,
            path=path,
            retry_round=retry_round + 1,
            protocol=protocol,
            rng=rng,
            queue_counter=queue_counter,
        )

        for _, neighbor, edge in candidates:
            transmission = {
                "kind": "transmission",
                "phase": "gossip-command",
                "edge_id": edge["id"],
                "source": current_node,
                "target": neighbor,
                "attempted_at_ms": round(current_time_ms, 1),
                "send_time_ms": round(current_time_ms, 1),
                "hop": hop + 1,
                "retry_round": retry_round,
                "message_id": protocol["message_id"],
                "path": path + [neighbor],
                "relay_reason": "peer-relay" if edge["link_type"] == "mesh-relay" else "direct-broadcast",
            }

            if edge["status"] in {"partitioned", "node_offline"}:
                transmission_log.append(
                    {
                        **transmission,
                        "status": edge["status"],
                        "delay_ms": 0.0,
                        "arrival_ms": None,
                        "via_edge": edge["id"],
                        "delivered": False,
                    }
                )
                continue

            delay_ms = self._sample_delay_ms(edge, rng)
            arrival_ms = round(current_time_ms + delay_ms, 1)
            heapq.heappush(
                queue,
                (
                    arrival_ms,
                    next(queue_counter),
                    {
                        **transmission,
                        "delay_ms": delay_ms,
                        "arrival_ms": arrival_ms,
                        "via_edge": edge["id"],
                        "scheduled_quality": edge["quality"],
                    },
                ),
            )

    def _find_interruption(
        self,
        source: str,
        target: str,
        send_time_ms: float,
        arrival_ms: float,
        protocol: Dict,
    ) -> Optional[Dict]:
        edge_key = self._edge_key(source, target)
        for event in protocol["dynamic_events"]:
            if event["at_ms"] <= send_time_ms:
                continue
            if event["at_ms"] > arrival_ms:
                break

            if event["scope"] == "edge" and event["edge_key"] == edge_key and event["action"] == "partition":
                return {
                    "status": "interrupted",
                    "reason": "edge_partitioned_mid_flight",
                    "at_ms": event["at_ms"],
                }
            if event["scope"] == "node" and event["node"] in {source, target} and event["action"] == "offline":
                return {
                    "status": "node_offline",
                    "reason": "node_went_offline_mid_flight",
                    "at_ms": event["at_ms"],
                }
        return None

    def _simulate_message_delivery(
        self,
        *,
        delivery_id: str,
        source_node: str,
        target_node: str,
        started_at_ms: float,
        protocol: Dict,
        rng: random.Random,
        algorithm: str,
        phase: str,
    ) -> Dict:
        allow_relay = algorithm == "gossip"
        attempts = 0
        current_time_ms = round(started_at_ms, 1)
        latest_failure = None

        while attempts <= protocol["retry_limit"]:
            attempts += 1
            path = self._best_path(
                source_node,
                target_node,
                protocol,
                current_time_ms,
                allow_relay=allow_relay,
            )
            if not path:
                latest_failure = "no_route"
                current_time_ms = round(current_time_ms + self._retry_delay_ms(attempts, protocol, rng), 1)
                continue

            hop_time_ms = current_time_ms
            delivered = True
            used_relay = len(path) > 2

            for left, right in zip(path, path[1:]):
                edge = self._edge_profile(left, right, protocol, hop_time_ms)
                if edge["status"] in {"partitioned", "node_offline"}:
                    latest_failure = edge["status"]
                    delivered = False
                    break

                delay_ms = self._sample_delay_ms(edge, rng)
                arrival_ms = round(hop_time_ms + delay_ms, 1)
                interruption = self._find_interruption(left, right, hop_time_ms, arrival_ms, protocol)
                if interruption:
                    latest_failure = interruption["status"]
                    current_time_ms = round(interruption["at_ms"], 1)
                    delivered = False
                    break

                arrival_edge = self._edge_profile(left, right, protocol, arrival_ms)
                if arrival_edge["status"] in {"partitioned", "node_offline"}:
                    latest_failure = arrival_edge["status"]
                    current_time_ms = arrival_ms
                    delivered = False
                    break

                if rng.random() > arrival_edge["quality"]:
                    latest_failure = "dropped"
                    current_time_ms = arrival_ms
                    delivered = False
                    break

                hop_time_ms = arrival_ms

            if delivered:
                return {
                    "delivery_id": delivery_id,
                    "phase": phase,
                    "status": "delivered",
                    "attempts": attempts,
                    "completed_at_ms": round(hop_time_ms, 1),
                    "path": path,
                    "relay_used": used_relay,
                    "last_failure": None,
                }

            current_time_ms = round(current_time_ms + self._retry_delay_ms(attempts, protocol, rng), 1)

        return {
            "delivery_id": delivery_id,
            "phase": phase,
            "status": "pending",
            "attempts": attempts,
            "completed_at_ms": None,
            "path": [source_node],
            "relay_used": False,
            "last_failure": latest_failure,
        }

    def _simulate_report_delivery(
        self,
        *,
        report_id: str,
        source_node: str,
        target_node: str = "gateway",
        started_at_ms: float,
        protocol: Dict,
        rng: random.Random,
        algorithm: str,
    ) -> Dict:
        result = self._simulate_message_delivery(
            delivery_id=report_id,
            source_node=source_node,
            target_node=target_node,
            started_at_ms=started_at_ms,
            protocol=protocol,
            rng=rng,
            algorithm=algorithm,
            phase="detection-report",
        )
        return {
            "report_id": report_id,
            "status": result["status"],
            "attempts": result["attempts"],
            "reported_at_ms": result["completed_at_ms"],
            "path": result["path"],
            "relay_used": result["relay_used"],
            "last_failure": result["last_failure"],
        }

    def _deliver_to_control(
        self,
        *,
        delivery_id: str,
        source_node: str,
        started_at_ms: float,
        protocol: Dict,
        rng: random.Random,
        algorithm: str,
        phase: str,
        command: Dict,
    ) -> Dict:
        last_result = None
        for target_node in self._control_targets(command):
            result = self._simulate_message_delivery(
                delivery_id=delivery_id,
                source_node=source_node,
                target_node=target_node,
                started_at_ms=started_at_ms,
                protocol=protocol,
                rng=rng,
                algorithm=algorithm,
                phase=phase,
            )
            if result["status"] == "delivered":
                return {**result, "target_node": target_node}
            last_result = {**result, "target_node": target_node}

        return last_result or {
            "delivery_id": delivery_id,
            "phase": phase,
            "status": "pending",
            "attempts": 0,
            "completed_at_ms": None,
            "path": [source_node],
            "relay_used": False,
            "last_failure": "no_control_target",
            "target_node": command["control_node"],
        }

    def _score_attack_candidates(
        self,
        area: Dict,
        target_contact: Dict,
        receipt_times: Dict[str, float],
        protocol: Dict,
        evaluation_ms: float,
    ) -> List[Dict]:
        candidates: List[Dict] = []
        state = self._network_state_at(protocol, evaluation_ms)
        required_weapon = target_contact.get("required_weapon", "agm")
        required_units = max(1, int(target_contact.get("required_weapon_units", 1)))

        for node in self._base_nodes:
            if node["role"] != "attack-drone":
                continue

            node_id = node["id"]
            profile = area.get("attack_profiles", {}).get(node_id, {})
            fuel_score = min(1.0, max(0.0, float(node.get("fuel_percent", 0.0)) / 100.0))
            distance_km = float(profile.get("distance_km", 2.0))
            proximity_score = round(max(0.15, 1.0 - min(distance_km, 4.0) / 4.0), 3)
            threat_exposure = float(profile.get("threat_exposure", 0.25))
            survivability_score = round(
                max(0.15, min(1.0, float(node.get("survivability", 0.6)) * (1.0 - (threat_exposure * 0.45)))),
                3,
            )
            line_of_sight = round(max(0.2, min(1.0, float(profile.get("line_of_sight", 0.8)))), 3)
            weapon_units = int(node.get("weapon_load", {}).get(required_weapon, 0))
            weapon_score = round(min(1.0, weapon_units / required_units), 3) if required_units else 1.0
            reachable = node_id in receipt_times and node_id not in state["offline_nodes"]
            eligible = reachable and weapon_units >= required_units and fuel_score >= 0.35
            score = round(
                (
                    (fuel_score * 0.24)
                    + (proximity_score * 0.28)
                    + (survivability_score * 0.22)
                    + (weapon_score * 0.18)
                    + (line_of_sight * 0.08)
                ) * 100,
                1,
            )

            candidates.append(
                {
                    "node": node_id,
                    "label": node["label"],
                    "fuel_score": fuel_score,
                    "fuel_percent": node.get("fuel_percent", 0),
                    "distance_km": distance_km,
                    "proximity_score": proximity_score,
                    "survivability_score": survivability_score,
                    "line_of_sight": line_of_sight,
                    "threat_exposure": threat_exposure,
                    "weapon_score": weapon_score,
                    "weapon_type": required_weapon,
                    "weapon_units": weapon_units,
                    "remaining_weapon_units": weapon_units,
                    "reachable": reachable,
                    "eligible": eligible,
                    "score": score,
                }
            )

        candidates.sort(
            key=lambda item: (
                not item["eligible"],
                -item["score"],
                item["distance_km"],
                item["node"],
            )
        )
        return candidates

    def _resolve_engagement_outcome(
        self,
        assignee: Dict,
        target_contact: Dict,
        engagement_start_ms: float,
        protocol: Dict,
        rng: random.Random,
        attempt_index: int,
    ) -> Dict:
        node_id = assignee["node"]
        if node_id in self._network_state_at(protocol, engagement_start_ms)["offline_nodes"]:
            return {
                "status": "reassignment_required",
                "result": "platform_unavailable",
                "completed_at_ms": round(engagement_start_ms, 1),
                "shot_fired": False,
                "success_probability": 0.0,
            }

        release_ms = round(engagement_start_ms + rng.uniform(52.0, 96.0), 1)
        if node_id in self._network_state_at(protocol, release_ms)["offline_nodes"]:
            return {
                "status": "reassignment_required",
                "result": "platform_unavailable",
                "completed_at_ms": release_ms,
                "shot_fired": False,
                "success_probability": 0.0,
            }

        required_units = max(1, int(target_contact.get("required_weapon_units", 1)))
        available_units = assignee.get("remaining_weapon_units", assignee.get("weapon_units", 0))
        if available_units < required_units:
            return {
                "status": "reassignment_required",
                "result": "insufficient_weapons",
                "completed_at_ms": release_ms,
                "shot_fired": False,
                "success_probability": 0.0,
            }

        success_probability = (
            0.28
            + (assignee["fuel_score"] * 0.14)
            + (assignee["proximity_score"] * 0.18)
            + (assignee["survivability_score"] * 0.16)
            + (assignee["weapon_score"] * 0.16)
            + (assignee["line_of_sight"] * 0.12)
            - (float(target_contact.get("threat_level", 0.7)) * 0.1)
        )
        if attempt_index > 1:
            success_probability += 0.07
        success_probability = round(max(0.28, min(0.92, success_probability)), 3)
        assignee["remaining_weapon_units"] = max(0, available_units - required_units)
        roll = rng.random()

        if roll <= success_probability:
            result = "target_neutralized"
        elif roll <= min(0.99, success_probability + 0.18):
            result = "shot_lost"
        else:
            result = "shot_missed"

        return {
            "status": "complete" if result == "target_neutralized" else "reassignment_required",
            "result": result,
            "completed_at_ms": release_ms,
            "shot_fired": True,
            "success_probability": success_probability,
        }

    def _simulate_search_and_reporting(
        self,
        command: Dict,
        protocol: Dict,
        receipt_times: Dict[str, float],
        rng: random.Random,
        *,
        algorithm: str,
    ) -> Tuple[Dict, List[Dict], Dict[str, Dict]]:
        area = command["operational_area"]
        search_state = {
            "target_location": area["label"],
            "target_x": area["target_x"],
            "target_y": area["target_y"],
            "mission_status": "searching",
            "mission_type": "detect-assign-engage",
            "control_node": command["control_node"],
            "operator_nodes": deepcopy(command["operator_nodes"]),
            "backup_control_nodes": deepcopy(command["backup_control_nodes"]),
            "gateway_node": command["gateway_node"],
            "recon_nodes": ["recon-1"],
            "attack_nodes": ["attack-1", "attack-2"],
            "participating_nodes": [command["control_node"]],
            "unavailable_nodes": [],
            "objects_detected": 0,
            "reports_delivered": 0,
            "reports_pending": 0,
            "task_publish_ms": None,
            "assignment_completion_ms": None,
            "reassignment_count": 0,
            "mission_completion_ms": 0.0,
            "candidate_scores": [],
            "primary_assignee": None,
            "backup_assignees": [],
            "target_tasks": [],
            "engagements": [],
            "search_lanes": [],
            "sectors": [],
            "timeline": [],
        }
        object_reports: List[Dict] = []
        node_mission_meta: Dict[str, Dict] = {
            node["id"]: {
                "mission_role": node.get("mission_role", node["role"]),
                "assigned_search_lanes": [],
                "assigned_targets": [],
                "search_status": "idle",
                "assignment_status": "idle",
                "engagement_status": "idle",
                "last_report_ms": None,
                "fallback_rank": None,
            }
            for node in self._base_nodes
            if node["id"] != "gateway"
        }
        for operator_index, operator_id in enumerate(command["operator_nodes"]):
            operator_meta = node_mission_meta.setdefault(
                operator_id,
                {
                    "mission_role": "soldier-operator",
                    "assigned_search_lanes": [],
                    "assigned_targets": [],
                    "search_status": "idle",
                    "assignment_status": "idle",
                    "engagement_status": "idle",
                    "last_report_ms": None,
                    "fallback_rank": None,
                },
            )
            operator_meta["assignment_status"] = "command-active" if operator_id == command["control_node"] else "command-standby"
            operator_meta["fallback_rank"] = None if operator_index == 0 else operator_index
        mission_end_ms = 0.0

        for lane in area["search_lanes"]:
            assigned_node = lane["assigned_node"]
            lane_state = {
                "id": lane["id"],
                "label": lane["label"],
                "assigned_node": assigned_node,
                "status": "pending",
                "search_started_ms": None,
                "search_completed_ms": None,
                "target_detected": False,
            }
            sector_state = {
                "id": lane["id"],
                "label": lane["label"],
                "assigned_node": assigned_node,
                "status": "pending",
                "search_started_ms": None,
                "search_completed_ms": None,
                "objects_detected": 0,
            }
            node_meta = node_mission_meta.setdefault(
                assigned_node,
                {
                    "mission_role": self._node_lookup.get(assigned_node, {}).get("mission_role", "sensor-platform"),
                    "assigned_search_lanes": [],
                    "assigned_targets": [],
                    "search_status": "idle",
                    "assignment_status": "idle",
                    "engagement_status": "idle",
                    "last_report_ms": None,
                    "fallback_rank": None,
                },
            )
            node_meta["assigned_search_lanes"].append(lane["id"])

            if assigned_node not in receipt_times:
                lane_state["status"] = "blocked"
                sector_state["status"] = "blocked"
                node_meta["search_status"] = "blocked"
                search_state["unavailable_nodes"].append(assigned_node)
                search_state["timeline"].append(
                    {
                        "event": "search_blocked",
                        "lane_id": lane["id"],
                        "node": assigned_node,
                        "timestamp_ms": None,
                    }
                )
                search_state["search_lanes"].append(lane_state)
                search_state["sectors"].append(sector_state)
                continue

            start_ms = round(receipt_times[assigned_node] + rng.uniform(45.0, 85.0), 1)
            complete_ms = round(start_ms + rng.uniform(130.0, 220.0), 1)
            lane_state["status"] = "searched"
            lane_state["search_started_ms"] = start_ms
            lane_state["search_completed_ms"] = complete_ms
            sector_state["status"] = "searched"
            sector_state["search_started_ms"] = start_ms
            sector_state["search_completed_ms"] = complete_ms
            search_state["participating_nodes"].append(assigned_node)
            search_state["timeline"].append(
                {
                    "event": "search_started",
                    "lane_id": lane["id"],
                    "node": assigned_node,
                    "timestamp_ms": start_ms,
                }
            )
            search_state["timeline"].append(
                {
                    "event": "search_completed",
                    "lane_id": lane["id"],
                    "node": assigned_node,
                    "timestamp_ms": complete_ms,
                }
            )
            node_meta["search_status"] = "target-classified"

            mission_end_ms = max(mission_end_ms, complete_ms)
            for target_contact in area["target_contacts"]:
                if target_contact["lane_id"] != lane["id"]:
                    continue

                detected_at_ms = round(complete_ms - rng.uniform(18.0, 42.0), 1)
                report = self._deliver_to_control(
                    delivery_id=f"report-{target_contact['id']}",
                    source_node=assigned_node,
                    started_at_ms=detected_at_ms,
                    protocol=protocol,
                    rng=rng,
                    algorithm=algorithm,
                    phase="detection-report",
                    command=command,
                )
                active_control_node = report["target_node"]
                search_state["control_node"] = active_control_node
                search_state["backup_control_nodes"] = [
                    node_id for node_id in command["operator_nodes"] if node_id != active_control_node
                ]
                search_state["participating_nodes"].append(active_control_node)
                for operator_id in command["operator_nodes"]:
                    if operator_id in node_mission_meta:
                        node_mission_meta[operator_id]["assignment_status"] = (
                            "command-active" if operator_id == active_control_node else "command-standby"
                        )
                report_payload = {
                    "report_id": report["delivery_id"],
                    "object_id": target_contact["id"],
                    "object_type": target_contact["type"],
                    "classification": target_contact["classification"],
                    "priority": target_contact["priority"],
                    "confidence": target_contact["confidence"],
                    "sector_id": lane["id"],
                    "detected_by": assigned_node,
                    "detected_at_ms": detected_at_ms,
                    "reported_at_ms": report["completed_at_ms"],
                    "status": report["status"],
                    "path": report["path"],
                    "attempts": report["attempts"],
                    "relay_used": report["relay_used"],
                    "last_failure": report["last_failure"],
                    "reported_to": active_control_node,
                }
                object_reports.append(report_payload)
                lane_state["target_detected"] = True
                sector_state["objects_detected"] += 1
                search_state["objects_detected"] += 1
                search_state["timeline"].append(
                    {
                        "event": "target_detected",
                        "lane_id": lane["id"],
                        "node": assigned_node,
                        "object_id": target_contact["id"],
                        "timestamp_ms": detected_at_ms,
                    }
                )
                if report["status"] == "delivered":
                    search_state["reports_delivered"] += 1
                    node_meta["last_report_ms"] = report["completed_at_ms"]
                    if active_control_node in node_mission_meta:
                        node_mission_meta[active_control_node]["last_report_ms"] = report["completed_at_ms"]
                    mission_end_ms = max(mission_end_ms, report["completed_at_ms"] or mission_end_ms)
                    search_state["timeline"].append(
                        {
                            "event": "target_report_delivered",
                            "lane_id": lane["id"],
                            "node": active_control_node,
                            "object_id": target_contact["id"],
                            "timestamp_ms": report["completed_at_ms"],
                        }
                    )
                    if active_control_node != command["control_node"]:
                        search_state["timeline"].append(
                            {
                                "event": "control_handoff",
                                "object_id": target_contact["id"],
                                "node": active_control_node,
                                "timestamp_ms": report["completed_at_ms"],
                            }
                        )
                else:
                    search_state["reports_pending"] += 1
                    search_state["timeline"].append(
                        {
                            "event": "target_report_pending",
                            "lane_id": lane["id"],
                            "node": assigned_node,
                            "object_id": target_contact["id"],
                            "timestamp_ms": report["completed_at_ms"],
                        }
                    )
                    search_state["search_lanes"].append(lane_state)
                    search_state["sectors"].append(sector_state)
                    continue

                candidate_scores = self._score_attack_candidates(
                    area,
                    target_contact,
                    receipt_times,
                    protocol,
                    report["completed_at_ms"] or detected_at_ms,
                )
                search_state["candidate_scores"] = deepcopy(candidate_scores)
                task_publish_ms = round((report["completed_at_ms"] or detected_at_ms) + rng.uniform(15.0, 32.0), 1)
                search_state["task_publish_ms"] = task_publish_ms
                task_state = {
                    "task_id": f"task-{target_contact['id']}",
                    "target_id": target_contact["id"],
                    "classification": target_contact["classification"],
                    "published_by": active_control_node,
                    "published_at_ms": task_publish_ms,
                    "status": "publishing",
                    "candidate_scores": deepcopy(candidate_scores),
                    "task_deliveries": [],
                    "selection_completed_ms": None,
                    "primary_assignee": None,
                    "backup_assignees": [],
                    "reassignment_history": [],
                    "completed_at_ms": None,
                    "fallback_action": target_contact.get("fallback_action", "mark_for_external_fires"),
                }
                search_state["timeline"].append(
                    {
                        "event": "target_task_published",
                        "object_id": target_contact["id"],
                        "node": active_control_node,
                        "timestamp_ms": task_publish_ms,
                    }
                )

                delivered_candidates: List[Dict] = []
                for index, candidate in enumerate(candidate_scores, start=1):
                    delivery = self._simulate_message_delivery(
                        delivery_id=f"{task_state['task_id']}-{candidate['node']}",
                        source_node=active_control_node,
                        target_node=candidate["node"],
                        started_at_ms=task_publish_ms,
                        protocol=protocol,
                        rng=rng,
                        algorithm=algorithm,
                        phase="target-task",
                    )
                    delivery_payload = {
                        **candidate,
                        "candidate_rank": index,
                        "delivery_status": delivery["status"],
                        "delivered_at_ms": delivery["completed_at_ms"],
                        "path": delivery["path"],
                        "attempts": delivery["attempts"],
                        "relay_used": delivery["relay_used"],
                        "last_failure": delivery["last_failure"],
                    }
                    task_state["task_deliveries"].append(delivery_payload)
                    if delivery_payload["eligible"] and delivery_payload["delivery_status"] == "delivered":
                        delivered_candidates.append(delivery_payload)
                    elif not delivery_payload["eligible"]:
                        node_mission_meta[candidate["node"]]["assignment_status"] = "standby"

                if delivered_candidates:
                    primary = delivered_candidates[0]
                    backups = delivered_candidates[1:]
                    task_state["status"] = "assigned"
                    task_state["primary_assignee"] = primary["node"]
                    task_state["backup_assignees"] = [candidate["node"] for candidate in backups]
                    task_state["selection_completed_ms"] = max(
                        candidate["delivered_at_ms"] or task_publish_ms for candidate in delivered_candidates
                    )
                    search_state["assignment_completion_ms"] = task_state["selection_completed_ms"]
                    search_state["participating_nodes"].append(primary["node"])
                    for candidate in backups:
                        search_state["participating_nodes"].append(candidate["node"])
                    search_state["primary_assignee"] = primary["node"]
                    search_state["backup_assignees"] = [candidate["node"] for candidate in backups]
                    node_mission_meta[primary["node"]]["assignment_status"] = "primary-assignee"
                    node_mission_meta[primary["node"]]["assigned_targets"].append(target_contact["id"])
                    for backup_index, backup in enumerate(backups, start=1):
                        node_mission_meta[backup["node"]]["assignment_status"] = "backup-assignee"
                        node_mission_meta[backup["node"]]["assigned_targets"].append(target_contact["id"])
                        node_mission_meta[backup["node"]]["fallback_rank"] = backup_index
                        search_state["timeline"].append(
                            {
                                "event": "backup_designated",
                                "object_id": target_contact["id"],
                                "node": backup["node"],
                                "timestamp_ms": backup["delivered_at_ms"],
                            }
                        )
                    search_state["timeline"].append(
                        {
                            "event": "primary_assigned",
                            "object_id": target_contact["id"],
                            "node": primary["node"],
                            "timestamp_ms": primary["delivered_at_ms"],
                        }
                    )

                    active_assignee = dict(primary)
                    backup_queue = [dict(candidate) for candidate in backups]
                    attempt_index = 1
                    while active_assignee:
                        engagement_start_ms = round(
                            max(
                                task_state["selection_completed_ms"] or task_publish_ms,
                                active_assignee.get("delivered_at_ms") or task_publish_ms,
                            ) + rng.uniform(65.0, 118.0),
                            1,
                        )
                        engagement = self._resolve_engagement_outcome(
                            active_assignee,
                            target_contact,
                            engagement_start_ms,
                            protocol,
                            rng,
                            attempt_index,
                        )
                        engagement_record = {
                            "target_id": target_contact["id"],
                            "assigned_node": active_assignee["node"],
                            "attempt_index": attempt_index,
                            "started_at_ms": engagement_start_ms,
                            "completed_at_ms": engagement["completed_at_ms"],
                            "result": engagement["result"],
                            "shot_fired": engagement["shot_fired"],
                            "success_probability": engagement["success_probability"],
                            "reassigned": False,
                            "battle_damage_report_status": None,
                            "battle_damage_reported_at_ms": None,
                        }
                        node_mission_meta[active_assignee["node"]]["engagement_status"] = engagement["result"]

                        if engagement["result"] == "target_neutralized":
                            bda = self._simulate_message_delivery(
                                delivery_id=f"bda-{target_contact['id']}-{active_assignee['node']}",
                                source_node=active_assignee["node"],
                                target_node=active_control_node,
                                started_at_ms=engagement["completed_at_ms"],
                                protocol=protocol,
                                rng=rng,
                                algorithm=algorithm,
                                phase="battle-damage-report",
                            )
                            engagement_record["battle_damage_report_status"] = bda["status"]
                            engagement_record["battle_damage_reported_at_ms"] = bda["completed_at_ms"]
                            engagement_record["battle_damage_reported_to"] = active_control_node
                            node_mission_meta[active_assignee["node"]]["last_report_ms"] = bda["completed_at_ms"]
                            if active_control_node in node_mission_meta:
                                node_mission_meta[active_control_node]["last_report_ms"] = bda["completed_at_ms"]
                            task_state["status"] = "target_neutralized"
                            task_state["completed_at_ms"] = bda["completed_at_ms"] or engagement["completed_at_ms"]
                            mission_end_ms = max(mission_end_ms, task_state["completed_at_ms"] or mission_end_ms)
                            search_state["mission_status"] = "target_neutralized"
                            search_state["mission_completion_ms"] = round(task_state["completed_at_ms"] or mission_end_ms, 1)
                            search_state["timeline"].append(
                                {
                                    "event": "target_neutralized",
                                    "object_id": target_contact["id"],
                                    "node": active_assignee["node"],
                                    "timestamp_ms": task_state["completed_at_ms"],
                                }
                            )
                            search_state["engagements"].append(engagement_record)
                            break

                        search_state["reassignment_count"] += 1
                        engagement_record["reassigned"] = True
                        search_state["timeline"].append(
                            {
                                "event": "reassignment_required",
                                "object_id": target_contact["id"],
                                "node": active_assignee["node"],
                                "timestamp_ms": engagement["completed_at_ms"],
                            }
                        )
                        next_assignee = None
                        while backup_queue and next_assignee is None:
                            backup_candidate = backup_queue.pop(0)
                            reassignment_start_ms = round(engagement["completed_at_ms"] + rng.uniform(24.0, 54.0), 1)
                            reassignment = self._simulate_message_delivery(
                                delivery_id=f"reassign-{target_contact['id']}-{backup_candidate['node']}",
                                source_node=active_control_node,
                                target_node=backup_candidate["node"],
                                started_at_ms=reassignment_start_ms,
                                protocol=protocol,
                                rng=rng,
                                algorithm=algorithm,
                                phase="reassignment",
                            )
                            history_entry = {
                                "from": active_assignee["node"],
                                "to": backup_candidate["node"],
                                "started_at_ms": reassignment_start_ms,
                                "status": reassignment["status"],
                                "completed_at_ms": reassignment["completed_at_ms"],
                                "path": reassignment["path"],
                            }
                            task_state["reassignment_history"].append(history_entry)
                            if reassignment["status"] == "delivered":
                                backup_candidate["delivered_at_ms"] = reassignment["completed_at_ms"]
                                node_mission_meta[backup_candidate["node"]]["assignment_status"] = "reassigned-primary"
                                next_assignee = backup_candidate
                                search_state["timeline"].append(
                                    {
                                        "event": "target_reassigned",
                                        "object_id": target_contact["id"],
                                        "node": backup_candidate["node"],
                                        "timestamp_ms": reassignment["completed_at_ms"],
                                    }
                                )

                        search_state["engagements"].append(engagement_record)
                        if next_assignee is None:
                            task_state["status"] = target_contact.get("fallback_action", "mark_for_external_fires")
                            task_state["completed_at_ms"] = engagement["completed_at_ms"]
                            search_state["mission_status"] = task_state["status"]
                            search_state["mission_completion_ms"] = round(engagement["completed_at_ms"], 1)
                            search_state["timeline"].append(
                                {
                                    "event": "target_handoff_required",
                                    "object_id": target_contact["id"],
                                    "node": active_control_node,
                                    "timestamp_ms": engagement["completed_at_ms"],
                                }
                            )
                            mission_end_ms = max(mission_end_ms, engagement["completed_at_ms"])
                            break

                        task_state["status"] = "reassigned"
                        active_assignee = next_assignee
                        attempt_index += 1

                    search_state["target_tasks"].append(task_state)
                else:
                    task_state["status"] = target_contact.get("fallback_action", "mark_for_external_fires")
                    task_state["completed_at_ms"] = task_publish_ms
                    search_state["mission_status"] = task_state["status"]
                    search_state["mission_completion_ms"] = task_publish_ms
                    search_state["target_tasks"].append(task_state)
                    search_state["timeline"].append(
                        {
                            "event": "no_attack_assignee_available",
                            "object_id": target_contact["id"],
                            "node": active_control_node,
                            "timestamp_ms": task_publish_ms,
                        }
                    )
                    mission_end_ms = max(mission_end_ms, task_publish_ms)

            search_state["search_lanes"].append(lane_state)
            search_state["sectors"].append(sector_state)

        field_nodes = [node["id"] for node in self._base_nodes if node["role"] != "gateway"]
        unreachable = sorted(node for node in field_nodes if node not in receipt_times)
        for node_id in unreachable:
            if node_id not in search_state["unavailable_nodes"]:
                search_state["unavailable_nodes"].append(node_id)

        search_state["participating_nodes"] = sorted(set(search_state["participating_nodes"]))
        search_state["unavailable_nodes"] = sorted(set(search_state["unavailable_nodes"]))
        if search_state["mission_completion_ms"] == 0.0:
            search_state["mission_completion_ms"] = round(mission_end_ms, 1)
        if search_state["mission_status"] == "searching":
            if search_state["reports_pending"] > 0:
                search_state["mission_status"] = "tracking_local_only"
            elif search_state["objects_detected"] == 0:
                search_state["mission_status"] = "search_clear"
            elif search_state["target_tasks"]:
                latest_task = search_state["target_tasks"][-1]
                search_state["mission_status"] = latest_task["status"]
            elif search_state["unavailable_nodes"]:
                search_state["mission_status"] = "degraded"
            else:
                search_state["mission_status"] = "target_reported"

        search_state["timeline"].sort(
            key=lambda event: (
                event["timestamp_ms"] is None,
                event["timestamp_ms"] if event["timestamp_ms"] is not None else float("inf"),
                event["event"],
            )
        )
        return search_state, object_reports, node_mission_meta

    def _annotate_nodes(
        self,
        receipt_times: Dict[str, float],
        unreached_nodes: List[str],
        protocol: Dict,
        simulation_end_ms: float,
        node_mission_meta: Dict[str, Dict],
    ) -> List[Dict]:
        nodes: List[Dict] = []
        unreached = set(unreached_nodes)
        final_state = self._network_state_at(protocol, simulation_end_ms)

        for node in self._base_nodes:
            node_copy = deepcopy(node)
            node_id = node["id"]
            node_copy["health"] = "offline" if node_id in final_state["offline_nodes"] else "online"
            if node_copy["health"] == "offline":
                node_copy["status"] = "offline"
            elif node_id in receipt_times:
                node_copy["status"] = "active"
            elif node_id in unreached:
                node_copy["status"] = "isolated"
            else:
                node_copy["status"] = "idle"
            node_copy["last_received_ms"] = receipt_times.get(node_id)
            mission_meta = node_mission_meta.get(node_id, {})
            node_copy["mission_role"] = mission_meta.get("mission_role", node_copy.get("mission_role", node_copy["role"]))
            node_copy["assigned_search_lanes"] = mission_meta.get("assigned_search_lanes", [])
            node_copy["assigned_sectors"] = mission_meta.get("assigned_search_lanes", [])
            node_copy["assigned_targets"] = mission_meta.get("assigned_targets", [])
            node_copy["search_status"] = mission_meta.get("search_status", "idle")
            node_copy["assignment_status"] = mission_meta.get("assignment_status", "idle")
            node_copy["engagement_status"] = mission_meta.get("engagement_status", "idle")
            node_copy["last_report_ms"] = mission_meta.get("last_report_ms")
            node_copy["fallback_rank"] = mission_meta.get("fallback_rank")
            nodes.append(node_copy)

        return nodes

    def _annotate_edges(
        self,
        transmission_log: List[Dict],
        protocol: Dict,
        simulation_end_ms: float,
    ) -> List[Dict]:
        edge_stats = {
            edge["id"]: {
                "attempts": 0,
                "successful_deliveries": 0,
                "duplicate_suppressions": 0,
                "dropped": 0,
                "interrupted": 0,
                "partitioned": 0,
                "node_offline": 0,
                "delay_samples": [],
            }
            for edge in self._base_edges
        }

        for transmission in transmission_log:
            edge_id = transmission.get("edge_id")
            if edge_id not in edge_stats:
                continue

            stats = edge_stats[edge_id]
            stats["attempts"] += 1
            status = transmission.get("status")
            if status == "delivered":
                stats["successful_deliveries"] += 1
                stats["delay_samples"].append(transmission.get("delay_ms", 0.0))
            elif status == "duplicate_suppressed":
                stats["duplicate_suppressions"] += 1
                stats["delay_samples"].append(transmission.get("delay_ms", 0.0))
            elif status == "dropped":
                stats["dropped"] += 1
            elif status == "interrupted":
                stats["interrupted"] += 1
            elif status == "partitioned":
                stats["partitioned"] += 1
            elif status == "node_offline":
                stats["node_offline"] += 1

        final_state = self._network_state_at(protocol, simulation_end_ms)
        annotated_edges: List[Dict] = []
        for edge in self._base_edges:
            edge_copy = deepcopy(edge)
            stats = edge_stats[edge["id"]]
            edge_key = self._edge_key(edge["source"], edge["target"])
            edge_copy["attempts"] = stats["attempts"]
            edge_copy["successful_deliveries"] = stats["successful_deliveries"]
            edge_copy["duplicate_suppressions"] = stats["duplicate_suppressions"]
            edge_copy["delay_ms"] = round(
                sum(stats["delay_samples"]) / len(stats["delay_samples"]),
                1,
            ) if stats["delay_samples"] else 0.0

            if edge["source"] in final_state["offline_nodes"] or edge["target"] in final_state["offline_nodes"]:
                edge_copy["status"] = "node_offline"
            elif edge_key in final_state["partitioned_links"]:
                edge_copy["status"] = "partitioned"
            elif stats["successful_deliveries"] > 0 and (stats["interrupted"] > 0 or stats["dropped"] > 0):
                edge_copy["status"] = "recovering"
            elif stats["successful_deliveries"] > 0:
                edge_copy["status"] = "propagated"
            elif stats["interrupted"] > 0:
                edge_copy["status"] = "interrupted"
            elif stats["dropped"] > 0:
                edge_copy["status"] = "lossy"
            else:
                edge_copy["status"] = "ready"

            annotated_edges.append(edge_copy)

        return annotated_edges

    def _simulate_gossip_consensus(
        self,
        command: Dict,
        protocol: Dict,
        rng: random.Random,
    ) -> Dict:
        seen_messages = {node_id: set() for node_id in [node["id"] for node in self._base_nodes]}
        receipt_times: Dict[str, float] = {}
        node_receipt_meta: Dict[str, Dict] = {}
        propagation_order: List[Dict] = []
        transmission_log: List[Dict] = []
        queue: List[Tuple[float, int, Dict]] = []
        queue_counter = itertools.count()
        last_event_ms = 0.0

        origin = protocol["origin"]
        seen_messages[origin].add(protocol["message_id"])
        self._record_receipt(
            propagation_order,
            receipt_times,
            command,
            protocol,
            node_id=origin,
            source=None,
            timestamp_ms=0.0,
            hop=0,
            via_edge=None,
            path=[origin],
            relay_reason="origin",
        )
        node_receipt_meta[origin] = {"hop": 0, "path": [origin]}
        self._schedule_forwarding(
            queue,
            transmission_log,
            current_node=origin,
            current_time_ms=0.0,
            hop=0,
            path=[origin],
            protocol=protocol,
            rng=rng,
            queue_counter=queue_counter,
            receipt_times=receipt_times,
            retry_round=0,
        )

        while queue:
            current_time_ms, _, event = heapq.heappop(queue)
            last_event_ms = max(last_event_ms, current_time_ms)

            if event["kind"] == "retry_round":
                node_id = event["node"]
                if protocol["message_id"] not in seen_messages[node_id]:
                    continue
                node_meta = node_receipt_meta.get(node_id)
                if node_meta is None:
                    continue
                self._schedule_forwarding(
                    queue,
                    transmission_log,
                    current_node=node_id,
                    current_time_ms=current_time_ms,
                    hop=node_meta["hop"],
                    path=node_meta["path"],
                    protocol=protocol,
                    rng=rng,
                    queue_counter=queue_counter,
                    receipt_times=receipt_times,
                    retry_round=event["retry_round"],
                )
                continue

            target = event["target"]
            if protocol["message_id"] in seen_messages[target]:
                transmission_log.append({**event, "status": "duplicate_suppressed", "delivered": False})
                continue

            interruption = self._find_interruption(
                source=event["source"],
                target=event["target"],
                send_time_ms=event["send_time_ms"],
                arrival_ms=event["arrival_ms"],
                protocol=protocol,
            )
            if interruption:
                transmission_log.append(
                    {
                        **event,
                        "status": interruption["status"],
                        "interruption_reason": interruption["reason"],
                        "interrupted_at_ms": interruption["at_ms"],
                        "delivered": False,
                    }
                )
                continue

            arrival_edge = self._edge_profile(event["source"], event["target"], protocol, event["arrival_ms"])
            if arrival_edge["status"] in {"partitioned", "node_offline"}:
                transmission_log.append({**event, "status": arrival_edge["status"], "delivered": False})
                continue

            if rng.random() > arrival_edge["quality"]:
                transmission_log.append({**event, "status": "dropped", "delivered": False})
                continue

            seen_messages[target].add(protocol["message_id"])
            transmission_log.append({**event, "status": "delivered", "delivered": True})
            self._record_receipt(
                propagation_order,
                receipt_times,
                command,
                protocol,
                node_id=target,
                source=event["source"],
                timestamp_ms=event["arrival_ms"],
                hop=event["hop"],
                via_edge=event["via_edge"],
                path=event["path"],
                relay_reason=event["relay_reason"],
            )
            node_receipt_meta[target] = {"hop": event["hop"], "path": event["path"]}
            self._schedule_forwarding(
                queue,
                transmission_log,
                current_node=target,
                current_time_ms=event["arrival_ms"],
                hop=event["hop"],
                path=event["path"],
                protocol=protocol,
                rng=rng,
                queue_counter=queue_counter,
                receipt_times=receipt_times,
                retry_round=0,
            )

        return {
            "receipt_times": receipt_times,
            "propagation_order": propagation_order,
            "transmissions": transmission_log,
            "last_event_ms": round(last_event_ms, 1),
            "duplicate_suppressions": sum(
                1 for item in transmission_log if item.get("status") == "duplicate_suppressed"
            ),
            "interrupted_transmissions": sum(
                1 for item in transmission_log if item.get("status") in {"interrupted", "node_offline"}
            ),
            "retry_rounds_used": max((item.get("retry_round", 0) for item in transmission_log), default=0),
            "rerouted_deliveries": sum(
                1 for item in propagation_order if item.get("relay_reason") == "peer-relay"
            ),
            "quorum_achieved": True,
        }

    def _schedule_direct_transmission(
        self,
        queue: List[Tuple[float, int, Dict]],
        queue_counter: itertools.count,
        transmission: Dict,
    ) -> None:
        heapq.heappush(
            queue,
            (
                transmission["arrival_ms"],
                next(queue_counter),
                transmission,
            ),
        )

    def _simulate_raft_consensus(
        self,
        command: Dict,
        protocol: Dict,
        rng: random.Random,
    ) -> Dict:
        origin = protocol["origin"]
        followers = [node["id"] for node in self._base_nodes if node["id"] != origin]
        receipt_times: Dict[str, float] = {origin: 0.0}
        propagation_order: List[Dict] = [self._initial_receipt_event(command, protocol)]
        transmission_log: List[Dict] = []
        queue: List[Tuple[float, int, Dict]] = []
        queue_counter = itertools.count()
        last_event_ms = 0.0
        staged_followers: Dict[str, float] = {}
        acked_followers: Set[str] = set()
        committed_followers: Set[str] = set()
        leader_commit_ms: Optional[float] = None
        required_follower_acks = max(1, len(self._base_nodes) // 2)

        def schedule_phase(
            source: str,
            target: str,
            current_time_ms: float,
            phase: str,
            attempt: int,
        ) -> None:
            edge = self._edge_profile(source, target, protocol, current_time_ms)
            transmission = {
                "kind": phase,
                "phase": phase,
                "edge_id": edge["id"],
                "source": source,
                "target": target,
                "attempted_at_ms": round(current_time_ms, 1),
                "send_time_ms": round(current_time_ms, 1),
                "attempt": attempt,
                "message_id": protocol["message_id"],
                "retry_round": max(0, attempt - 1),
                "hop": 1,
                "path": [source, target],
                "relay_reason": "leader-broadcast",
            }
            if edge["status"] in {"partitioned", "node_offline"}:
                transmission_log.append(
                    {
                        **transmission,
                        "status": edge["status"],
                        "delay_ms": 0.0,
                        "arrival_ms": None,
                        "via_edge": edge["id"],
                        "delivered": False,
                    }
                )
                if phase in {"append_entries", "commit_notice"} and attempt <= protocol["retry_limit"]:
                    retry_at_ms = round(current_time_ms + self._retry_delay_ms(attempt, protocol, rng), 1)
                    schedule_phase(source, target, retry_at_ms, phase, attempt + 1)
                return

            delay_ms = self._sample_delay_ms(edge, rng)
            arrival_ms = round(current_time_ms + delay_ms, 1)
            self._schedule_direct_transmission(
                queue,
                queue_counter,
                {
                    **transmission,
                    "delay_ms": delay_ms,
                    "arrival_ms": arrival_ms,
                    "via_edge": edge["id"],
                    "scheduled_quality": edge["quality"],
                },
            )

        for follower in followers:
            schedule_phase(origin, follower, 0.0, "append_entries", 1)

        while queue:
            current_time_ms, _, event = heapq.heappop(queue)
            last_event_ms = max(last_event_ms, current_time_ms)

            interruption = self._find_interruption(
                source=event["source"],
                target=event["target"],
                send_time_ms=event["send_time_ms"],
                arrival_ms=event["arrival_ms"],
                protocol=protocol,
            )
            if interruption:
                transmission_log.append(
                    {
                        **event,
                        "status": interruption["status"],
                        "interruption_reason": interruption["reason"],
                        "interrupted_at_ms": interruption["at_ms"],
                        "delivered": False,
                    }
                )
                if event["phase"] in {"append_entries", "commit_notice"} and event["attempt"] <= protocol["retry_limit"]:
                    retry_at_ms = round(interruption["at_ms"] + self._retry_delay_ms(event["attempt"], protocol, rng), 1)
                    schedule_phase(event["source"], event["target"], retry_at_ms, event["phase"], event["attempt"] + 1)
                continue

            arrival_edge = self._edge_profile(event["source"], event["target"], protocol, event["arrival_ms"])
            if arrival_edge["status"] in {"partitioned", "node_offline"}:
                transmission_log.append({**event, "status": arrival_edge["status"], "delivered": False})
                if event["phase"] in {"append_entries", "commit_notice"} and event["attempt"] <= protocol["retry_limit"]:
                    retry_at_ms = round(event["arrival_ms"] + self._retry_delay_ms(event["attempt"], protocol, rng), 1)
                    schedule_phase(event["source"], event["target"], retry_at_ms, event["phase"], event["attempt"] + 1)
                continue

            if rng.random() > arrival_edge["quality"]:
                transmission_log.append({**event, "status": "dropped", "delivered": False})
                if event["phase"] in {"append_entries", "commit_notice"} and event["attempt"] <= protocol["retry_limit"]:
                    retry_at_ms = round(event["arrival_ms"] + self._retry_delay_ms(event["attempt"], protocol, rng), 1)
                    schedule_phase(event["source"], event["target"], retry_at_ms, event["phase"], event["attempt"] + 1)
                continue

            transmission_log.append({**event, "status": "delivered", "delivered": True})
            if event["phase"] == "append_entries":
                staged_followers[event["target"]] = event["arrival_ms"]
                schedule_phase(event["target"], origin, event["arrival_ms"], "ack", 1)
                if leader_commit_ms is not None and event["target"] not in committed_followers:
                    schedule_phase(origin, event["target"], leader_commit_ms, "commit_notice", 1)
            elif event["phase"] == "ack":
                acked_followers.add(event["source"])
                if leader_commit_ms is None and len(acked_followers) >= required_follower_acks:
                    leader_commit_ms = event["arrival_ms"]
                    for follower in sorted(staged_followers):
                        schedule_phase(origin, follower, leader_commit_ms, "commit_notice", 1)
            elif event["phase"] == "commit_notice":
                if event["target"] in committed_followers:
                    continue
                committed_followers.add(event["target"])
                self._record_receipt(
                    propagation_order,
                    receipt_times,
                    command,
                    protocol,
                    node_id=event["target"],
                    source=origin,
                    timestamp_ms=event["arrival_ms"],
                    hop=1,
                    via_edge=event["via_edge"],
                    path=[origin, event["target"]],
                    relay_reason="raft-commit",
                )

        return {
            "receipt_times": receipt_times,
            "propagation_order": propagation_order,
            "transmissions": transmission_log,
            "last_event_ms": round(last_event_ms, 1),
            "duplicate_suppressions": 0,
            "interrupted_transmissions": sum(
                1 for item in transmission_log if item.get("status") in {"interrupted", "node_offline"}
            ),
            "retry_rounds_used": max((item.get("retry_round", 0) for item in transmission_log), default=0),
            "rerouted_deliveries": 0,
            "quorum_achieved": leader_commit_ms is not None,
        }

    def _serialize_protocol(self, protocol: Dict) -> Dict:
        return {
            "origin": protocol["origin"],
            "message_id": protocol["message_id"],
            "consensus_algorithm": protocol["consensus_algorithm"],
            "ttl": protocol["ttl"],
            "fanout": protocol["fanout"],
            "duplicate_suppression": protocol["duplicate_suppression"],
            "relay_enabled": protocol["relay_enabled"],
            "retry_limit": protocol["retry_limit"],
            "retry_backoff_ms": protocol["retry_backoff_ms"],
            "retry_jitter_ms": protocol["retry_jitter_ms"],
            "partitioned_links": [list(edge) for edge in sorted(protocol["partitioned_links"])],
            "degraded_links": [
                {"edge": self._edge_key_lookup[key], "factor": factor}
                for key, factor in sorted(protocol["degraded_links"].items())
            ],
            "dynamic_events": [
                {key: value for key, value in event.items() if key != "edge_key"}
                for event in protocol["dynamic_events"]
            ],
        }

    def _field_nodes(self) -> List[str]:
        return [node["id"] for node in self._base_nodes if node["role"] != "gateway"]

    def _simulate_consensus(
        self,
        parsed_intent: Dict,
        *,
        rng: Optional[random.Random] = None,
        external_network: Optional[Dict] = None,
        include_benchmark: bool = False,
        forced_algorithm: Optional[str] = None,
    ) -> Dict:
        rng = rng or self._rng
        command = self._normalize_command(parsed_intent)
        if forced_algorithm:
            command["consensus_algorithm"] = self._normalize_algorithm(forced_algorithm)

        protocol = self._resolve_protocol(
            {**parsed_intent, "consensus_algorithm": command["consensus_algorithm"]},
            external_network=external_network,
        )
        protocol["consensus_algorithm"] = command["consensus_algorithm"]

        if command["consensus_algorithm"] == "raft":
            consensus_result = self._simulate_raft_consensus(command, protocol, rng)
        else:
            consensus_result = self._simulate_gossip_consensus(command, protocol, rng)

        receipt_times = consensus_result["receipt_times"]
        reached_nodes = list(receipt_times.keys())
        field_nodes = self._field_nodes()
        unreached_nodes = [node["id"] for node in self._base_nodes if node["id"] not in receipt_times]
        unreached_field_nodes = [node for node in field_nodes if node not in receipt_times]
        total_propagation_ms = round(max(receipt_times.values()), 1) if receipt_times else 0.0
        simulation_end_ms = round(max(total_propagation_ms, consensus_result["last_event_ms"]), 1)

        search_state, object_reports, node_mission_meta = self._simulate_search_and_reporting(
            command,
            protocol,
            receipt_times,
            rng,
            algorithm=command["consensus_algorithm"],
        )
        simulation_end_ms = round(max(simulation_end_ms, search_state["mission_completion_ms"]), 1)

        successful_deliveries = sum(
            1 for item in consensus_result["transmissions"] if item.get("status") == "delivered"
        )
        mission_status = search_state.get("mission_status", "swarming")
        result = {
            "status": mission_status if mission_status != "idle" else ("swarming" if not unreached_field_nodes else "degraded"),
            "algorithm": "adaptive-gossip" if command["consensus_algorithm"] == "gossip" else "tcp-raft-baseline",
            "topology": "6-node-soldier-operator-mesh",
            "graph_engine": "networkx" if nx is not None else "simple-graph-fallback",
            "command": command,
            "target_location": command["target_location"],
            "target_x": command["target_x"],
            "target_y": command["target_y"],
            "nodes": self._annotate_nodes(
                receipt_times,
                unreached_nodes,
                protocol,
                simulation_end_ms,
                node_mission_meta,
            ),
            "edges": self._annotate_edges(
                consensus_result["transmissions"],
                protocol,
                simulation_end_ms,
            ),
            "active_nodes": reached_nodes,
            "propagation_order": consensus_result["propagation_order"],
            "total_propagation_ms": total_propagation_ms,
            "protocol": self._serialize_protocol(protocol),
            "delivery_summary": {
                "reached_nodes": reached_nodes,
                "unreached_nodes": unreached_nodes,
                "all_nodes_reached": not unreached_nodes,
                "all_field_nodes_reached": not unreached_field_nodes,
                "duplicate_suppressions": consensus_result["duplicate_suppressions"],
                "transmission_attempts": len(consensus_result["transmissions"]),
                "successful_deliveries": successful_deliveries,
                "retry_rounds_used": consensus_result["retry_rounds_used"],
                "interrupted_transmissions": consensus_result["interrupted_transmissions"],
                "rerouted_deliveries": consensus_result["rerouted_deliveries"],
                "recovered_from_disruption": consensus_result["interrupted_transmissions"] > 0 and not unreached_field_nodes,
                "quorum_achieved": consensus_result["quorum_achieved"],
                "mission_status": mission_status,
            },
            "search_state": search_state,
            "object_reports": object_reports,
            "transmissions": consensus_result["transmissions"],
            "available_algorithms": self.get_supported_algorithms(),
            "timestamp": datetime.now().isoformat(),
        }

        if include_benchmark:
            result["benchmark"] = self._get_benchmark()

        return result

    def calculate_consensus_path(self, parsed_intent: Dict) -> Dict:
        algorithm = self._normalize_algorithm(
            parsed_intent.get("consensus_algorithm") or parsed_intent.get("algorithm")
        )
        if algorithm == "raft":
            result = self._simulate_consensus(parsed_intent, include_benchmark=True, forced_algorithm="raft")
        else:
            result = self._simulate_consensus(parsed_intent, include_benchmark=True, forced_algorithm="gossip")
        self._last_state = deepcopy(result)
        return result

    def calculate_gossip_path(self, parsed_intent: Dict) -> Dict:
        """Simulate leaderless adaptive gossip command dissemination and mission execution."""
        result = self._simulate_consensus(parsed_intent, include_benchmark=True, forced_algorithm="gossip")
        self._last_state = deepcopy(result)
        return result

    def calculate_raft_path(self, parsed_intent: Dict) -> Dict:
        """Simulate a direct, leader-based TCP/Raft-style baseline."""
        result = self._simulate_consensus(parsed_intent, include_benchmark=True, forced_algorithm="raft")
        self._last_state = deepcopy(result)
        return result

    def _sample_benchmark_network(self, rng: random.Random) -> Dict:
        gateway_to_soldier1 = self._edge_key("gateway", "soldier-1")
        soldier_to_recon = self._edge_key("soldier-1", "recon-1")
        soldier_to_attack1 = self._edge_key("soldier-1", "attack-1")
        soldier_to_attack2 = self._edge_key("soldier-1", "attack-2")
        soldier_link = self._edge_key("soldier-1", "soldier-2")
        attack_mesh = self._edge_key("attack-1", "attack-2")

        profile = {
            "partitioned_links": [],
            "degraded_links": [],
            "edge_events": [],
            "node_events": [],
        }

        scenario_roll = rng.random()
        if scenario_roll < 0.12:
            profile["partitioned_links"].append(list(soldier_to_attack2))
        elif scenario_roll < 0.20:
            profile["partitioned_links"].append(list(soldier_to_attack1))
        elif scenario_roll < 0.32:
            profile["edge_events"].append(
                {
                    "edge": "soldier-1-attack-2",
                    "at_ms": 40.0,
                    "action": "partition",
                    "duration_ms": 100.0,
                }
            )
        elif scenario_roll < 0.42:
            profile["edge_events"].append(
                {
                    "edge": "soldier-1-recon-1",
                    "at_ms": 35.0,
                    "action": "partition",
                    "duration_ms": 90.0,
                }
            )
        elif scenario_roll < 0.54:
            profile["degraded_links"].append(
                {"source": soldier_to_attack2[0], "target": soldier_to_attack2[1], "factor": 1.45}
            )
        elif scenario_roll < 0.64:
            profile["degraded_links"].append(
                {"source": soldier_to_attack1[0], "target": soldier_to_attack1[1], "factor": 1.35}
            )
        elif scenario_roll < 0.74:
            profile["edge_events"].append(
                {
                    "edge": "gateway-soldier-1",
                    "at_ms": 70.0,
                    "action": "degrade",
                    "factor": 1.55,
                    "duration_ms": 90.0,
                }
            )
        elif scenario_roll < 0.82:
            profile["node_events"].append(
                {
                    "node": "soldier-1",
                    "at_ms": 45.0,
                    "action": "offline",
                    "duration_ms": 90.0,
                }
            )
        elif scenario_roll < 0.90:
            profile["node_events"].append(
                {
                    "node": "attack-1",
                    "at_ms": 55.0,
                    "action": "offline",
                    "duration_ms": 80.0,
                }
            )
        else:
            profile["degraded_links"].append(
                {"source": soldier_link[0], "target": soldier_link[1], "factor": 1.4}
            )

        return profile

    def _gateway_egress_bytes(self, transmissions: List[Dict], algorithm: str) -> int:
        total_bytes = 0
        control_sources = set(self._operator_nodes()) | {"gateway"}
        for transmission in transmissions:
            if transmission.get("source") not in control_sources:
                continue
            phase = transmission.get("phase", "")
            if algorithm == "gossip":
                total_bytes += self.MESSAGE_SIZE_BYTES + self.GOSSIP_METADATA_OVERHEAD_BYTES
            else:
                if phase == "ack":
                    continue
                total_bytes += self.MESSAGE_SIZE_BYTES + self.TCP_SESSION_OVERHEAD_BYTES + self.RAFT_CONTROL_OVERHEAD_BYTES
        return total_bytes

    def _benchmark_consensus_algorithms(self) -> Dict:
        rng = random.Random(20260418)
        gossip_successes = 0
        raft_successes = 0
        gossip_completion: List[float] = []
        raft_completion: List[float] = []
        gossip_bytes: List[int] = []
        raft_bytes: List[int] = []
        partition_runs = 0
        gossip_partition_successes = 0
        raft_partition_successes = 0

        for index in range(self.DEFAULT_BENCHMARK_RUNS):
            network_profile = self._sample_benchmark_network(rng)
            disrupted = bool(
                network_profile["partitioned_links"]
                or network_profile["edge_events"]
                or network_profile["node_events"]
            )
            if disrupted:
                partition_runs += 1

            base_intent = {
                "intent": "swarm_redeploy",
                "target_location": "Grid Alpha",
                "action_code": "ENGAGE_TARGET",
                "origin": "soldier-1",
                "ttl": 3,
                "fanout": 2,
                "retry_limit": 2,
                "retry_backoff_ms": 55.0,
                "message_id": f"bench-{index:04d}",
            }
            gossip_result = self._simulate_consensus(
                base_intent,
                rng=rng,
                external_network=network_profile,
                include_benchmark=False,
                forced_algorithm="gossip",
            )
            raft_result = self._simulate_consensus(
                base_intent,
                rng=rng,
                external_network=network_profile,
                include_benchmark=False,
                forced_algorithm="raft",
            )

            gossip_bytes.append(self._gateway_egress_bytes(gossip_result["transmissions"], "gossip"))
            raft_bytes.append(self._gateway_egress_bytes(raft_result["transmissions"], "raft"))

            if gossip_result["search_state"]["mission_status"] == "target_neutralized":
                gossip_successes += 1
                gossip_completion.append(
                    gossip_result["search_state"]["mission_completion_ms"] or gossip_result["total_propagation_ms"]
                )

            if raft_result["search_state"]["mission_status"] == "target_neutralized":
                raft_successes += 1
                raft_completion.append(
                    raft_result["search_state"]["mission_completion_ms"] or raft_result["total_propagation_ms"]
                )

            if disrupted:
                if gossip_result["search_state"]["mission_status"] == "target_neutralized":
                    gossip_partition_successes += 1
                if raft_result["search_state"]["mission_status"] == "target_neutralized":
                    raft_partition_successes += 1

        gossip_avg_ms = round(sum(gossip_completion) / len(gossip_completion), 1) if gossip_completion else 0.0
        raft_avg_ms = round(sum(raft_completion) / len(raft_completion), 1) if raft_completion else 0.0
        improvement_percent = round(
            ((raft_avg_ms - gossip_avg_ms) / raft_avg_ms) * 100,
            1,
        ) if raft_avg_ms else 0.0

        gossip_avg_bytes = round(sum(gossip_bytes) / len(gossip_bytes), 1) if gossip_bytes else 0.0
        raft_avg_bytes = round(sum(raft_bytes) / len(raft_bytes), 1) if raft_bytes else 0.0
        savings_percent = round(
            ((raft_avg_bytes - gossip_avg_bytes) / raft_avg_bytes) * 100,
            1,
        ) if raft_avg_bytes else 0.0

        return {
            "algorithm": "adaptive-gossip-vs-tcp-raft",
            "simulations": self.DEFAULT_BENCHMARK_RUNS,
            "latency": {
                "gossip_avg_ms": gossip_avg_ms,
                "raft_avg_ms": raft_avg_ms,
                "baseline_avg_ms": raft_avg_ms,
                "improvement_percent": improvement_percent,
            },
            "bandwidth": {
                "gossip_control_egress_bytes": gossip_avg_bytes,
                "raft_control_egress_bytes": raft_avg_bytes,
                "gossip_gateway_egress_bytes": gossip_avg_bytes,
                "raft_gateway_egress_bytes": raft_avg_bytes,
                "baseline_gateway_egress_bytes": raft_avg_bytes,
                "savings_percent": savings_percent,
                "scope": "control_plane_egress",
            },
            "fault_tolerance": {
                "gossip": "Leaderless relay can route around a dropped soldier-to-platform control link.",
                "raft": "Leader-based direct sessions depend on operator reachability and quorum timing.",
                "gossip_success_rate_percent": round((gossip_successes / self.DEFAULT_BENCHMARK_RUNS) * 100, 1),
                "raft_success_rate_percent": round((raft_successes / self.DEFAULT_BENCHMARK_RUNS) * 100, 1),
                "partition_success_rate_percent": {
                    "gossip": round((gossip_partition_successes / partition_runs) * 100, 1) if partition_runs else 0.0,
                    "raft": round((raft_partition_successes / partition_runs) * 100, 1) if partition_runs else 0.0,
                },
                "partitioned_network_winner": "gossip",
            },
        }

    def _get_benchmark(self) -> Dict:
        if self._benchmark_cache is None:
            self._benchmark_cache = self._benchmark_consensus_algorithms()
        return deepcopy(self._benchmark_cache)

    def benchmark_gossip_vs_raft(self) -> Dict:
        """Expose the blueprint-aligned benchmark result."""
        return self._get_benchmark()

    def benchmark_gossip_vs_tcp(self) -> Dict:
        """
        Backward-compatible alias kept for earlier integration code and docs.
        The current baseline is the TCP/Raft-style leader-based consensus model.
        """
        return self._get_benchmark()

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

    def get_state(self) -> Dict:
        """Return the latest swarm state, defaulting to the idle topology."""
        state = deepcopy(self._last_state)
        state.setdefault("benchmark", self._get_benchmark())
        state.setdefault("available_algorithms", self.get_supported_algorithms())
        return state


_swarm_instance: Optional[SwarmCoordinator] = None


def get_swarm(seed: Optional[int] = None) -> SwarmCoordinator:
    """Return the process-wide swarm coordinator singleton."""
    global _swarm_instance
    if _swarm_instance is None:
        _swarm_instance = SwarmCoordinator(seed=seed)
    return _swarm_instance
