import json
import math
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.swarm_logic import SwarmCoordinator


def _write_test_scenario(path: Path, *, enemies=None, drones=None):
    payload = {
        "scenario": "Command Execution Test",
        "coordinate_space_size": 1000,
        "map_overlay": {
            "asset_url": None,
            "asset_path": None,
            "opacity": 0.72,
            "visible": False,
        },
        "drones": drones or [
            {
                "id": "soldier-1",
                "type": "soldier",
                "role": "operator-node",
                "behavior": "lurk",
                "position": [100, 100],
            },
            {
                "id": "compute-1",
                "type": "compute",
                "role": "compute-drone",
                "behavior": "lurk",
                "position": [200, 200],
            },
            {
                "id": "recon-1",
                "type": "recon",
                "role": "recon-drone",
                "behavior": "lurk",
                "position": [260, 240],
                "speed": 95,
                "detection_radius": 220,
            },
            {
                "id": "attack-1",
                "type": "attack",
                "role": "attack-drone",
                "behavior": "lurk",
                "position": [320, 260],
                "speed": 120,
            },
        ],
        "enemies": enemies or [],
        "structures": [],
        "special_entities": [],
        "initial_events": [],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


class SwarmCommandExecutionTests(unittest.TestCase):
    def test_operator_nodes_default_to_expanded_transmission_range(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "command_execution.json"
            _write_test_scenario(config_path)

            swarm = SwarmCoordinator(config_path=str(config_path))
            nodes_by_id = {node["id"]: node for node in swarm.get_state()["nodes"]}

            self.assertEqual(nodes_by_id["soldier-1"]["transmission_range"], 400.0)
            self.assertEqual(nodes_by_id["compute-1"]["transmission_range"], 900.0)

    def test_move_command_updates_runtime_behaviors_and_positions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "command_execution.json"
            _write_test_scenario(config_path)

            swarm = SwarmCoordinator(config_path=str(config_path))
            result = swarm.calculate_gossip_path(
                {
                    "origin": "soldier-1",
                    "operator_node": "soldier-1",
                    "target_location": "Grid Charlie",
                    "action_code": "MOVE_TO",
                    "consensus_algorithm": "gossip",
                }
            )

            node_behaviors = {node["id"]: node.get("behavior") for node in result["nodes"]}

            self.assertEqual(result["status"], "maneuvering")
            self.assertEqual(result["search_state"]["mission_status"], "maneuvering")
            self.assertEqual(result["target_location"], "Grid Charlie")
            self.assertEqual(len(result["nodes"]), 4)
            self.assertEqual(node_behaviors["soldier-1"], "lurk")
            self.assertEqual(node_behaviors["compute-1"], "lurk")
            self.assertEqual(node_behaviors["recon-1"], "transit")
            self.assertEqual(node_behaviors["attack-1"], "transit")

            initial_compute_position = swarm.get_drone_position("compute-1")
            initial_recon_position = swarm.get_drone_position("recon-1")
            swarm.advance_simulation(now_monotonic=0.0)
            swarm.advance_simulation(now_monotonic=1.0)
            moved_compute_position = swarm.get_drone_position("compute-1")
            moved_recon_position = swarm.get_drone_position("recon-1")

            self.assertEqual(initial_compute_position, moved_compute_position)
            self.assertNotEqual(initial_recon_position, moved_recon_position)

            state = swarm.get_state()
            self.assertEqual(state["search_state"]["mission_status"], "maneuvering")
            self.assertEqual(state["target_location"], "Grid Charlie")

    def test_simulation_slowdown_factor_reduces_motion_progress(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "command_execution.json"
            _write_test_scenario(config_path)

            baseline = SwarmCoordinator(config_path=str(config_path))
            slowed = SwarmCoordinator(config_path=str(config_path))
            command = {
                "origin": "soldier-1",
                "operator_node": "soldier-1",
                "target_location": "Grid Charlie",
                "action_code": "MOVE_TO",
                "consensus_algorithm": "gossip",
            }

            baseline.calculate_gossip_path(command)
            slowed.calculate_gossip_path(command)
            slowed.set_simulation_slowdown_factor(100)

            baseline_start = baseline.get_drone_position("recon-1")
            slowed_start = slowed.get_drone_position("recon-1")

            baseline.advance_simulation(now_monotonic=0.0)
            baseline.advance_simulation(now_monotonic=1.0)
            slowed.advance_simulation(now_monotonic=0.0)
            slowed.advance_simulation(now_monotonic=1.0)

            baseline_end = baseline.get_drone_position("recon-1")
            slowed_end = slowed.get_drone_position("recon-1")

            baseline_distance = math.dist(baseline_start, baseline_end)
            slowed_distance = math.dist(slowed_start, slowed_end)
            slowed_state = slowed.get_state()

            self.assertGreater(baseline_distance, 20.0)
            self.assertGreater(baseline_distance, slowed_distance * 50)
            self.assertLess(slowed_distance, 1.0)
            self.assertEqual(slowed_state["simulation_settings"]["slowdown_factor"], 100.0)

    def test_compute_relay_links_reach_far_attack_drones(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "relay_execution.json"
            _write_test_scenario(
                config_path,
                drones=[
                    {
                        "id": "soldier-1",
                        "type": "soldier",
                        "role": "operator-node",
                        "behavior": "lurk",
                        "position": [100, 100],
                    },
                    {
                        "id": "compute-1",
                        "type": "compute",
                        "role": "compute-drone",
                        "behavior": "lurk",
                        "position": [200, 100],
                    },
                    {
                        "id": "attack-1",
                        "type": "attack",
                        "role": "attack-drone",
                        "behavior": "lurk",
                        "position": [850, 100],
                        "speed": 120,
                    },
                ],
            )

            swarm = SwarmCoordinator(config_path=str(config_path))
            result = swarm.calculate_gossip_path(
                {
                    "origin": "soldier-1",
                    "operator_node": "soldier-1",
                    "target_location": "Grid Charlie",
                    "action_code": "MOVE_TO",
                    "consensus_algorithm": "gossip",
                }
            )

            edge_pairs = {
                frozenset((edge["source"], edge["target"]))
                for edge in result["edges"]
            }

            self.assertIn(frozenset(("compute-1", "attack-1")), edge_pairs)
            self.assertIn("attack-1", result["active_nodes"])

    def test_patrol_loop_does_not_snap_recon_back_to_origin(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "patrol_loop.json"
            _write_test_scenario(
                config_path,
                drones=[
                    {
                        "id": "recon-1",
                        "type": "recon",
                        "role": "recon-drone",
                        "behavior": "lurk",
                        "position": [0, 0],
                        "speed": 10,
                        "detection_radius": 220,
                    }
                ],
            )

            swarm = SwarmCoordinator(config_path=str(config_path))
            swarm.set_drone_behavior(
                "recon-1",
                "patrol",
                [(0, 0), (10, 0), (10, 10), (10, 0)],
            )

            swarm.advance_simulation(now_monotonic=0.0)
            swarm.advance_simulation(now_monotonic=1.0)
            swarm.advance_simulation(now_monotonic=2.0)
            swarm.advance_simulation(now_monotonic=3.0)
            swarm.advance_simulation(now_monotonic=3.5)

            looping_position = swarm.get_drone_position("recon-1")

            self.assertIsNotNone(looping_position)
            self.assertAlmostEqual(looping_position[0], 10.0, places=2)
            self.assertGreater(looping_position[1], 4.0)

    def test_attack_drones_destroy_one_close_target_per_tick(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "attack_sequence.json"
            _write_test_scenario(
                config_path,
                enemies=[
                    {
                        "id": "enemy-1",
                        "label": "Enemy Infantry 1",
                        "subtype": "infantry",
                        "status": "active",
                        "position": [340, 270],
                    },
                    {
                        "id": "enemy-2",
                        "label": "Enemy Infantry 2",
                        "subtype": "infantry",
                        "status": "active",
                        "position": [350, 280],
                    },
                ],
            )

            swarm = SwarmCoordinator(seed=2, config_path=str(config_path))
            swarm.advance_simulation(now_monotonic=0.0)
            swarm.advance_simulation(now_monotonic=0.1)

            state = swarm.get_state()
            enemy_statuses = {enemy["id"]: enemy["status"] for enemy in state["enemies"]}
            attack_node = next(node for node in state["nodes"] if node["id"] == "attack-1")

            self.assertEqual(sum(status == "destroyed" for status in enemy_statuses.values()), 1)
            self.assertEqual(attack_node["status"], "active")

            swarm.advance_simulation(now_monotonic=0.2)
            state = swarm.get_state()
            enemy_statuses = {enemy["id"]: enemy["status"] for enemy in state["enemies"]}

            self.assertEqual(enemy_statuses["enemy-1"], "destroyed")
            self.assertEqual(enemy_statuses["enemy-2"], "destroyed")
            self.assertEqual(
                sum(event["event_type"] == "target_destroyed" for event in state["events"]),
                2,
            )

    def test_attack_drones_can_be_destroyed_by_counterattack(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "attack_counterattack.json"
            _write_test_scenario(
                config_path,
                enemies=[
                    {
                        "id": "enemy-1",
                        "label": "Enemy Armor 1",
                        "subtype": "armor",
                        "status": "active",
                        "position": [340, 270],
                    }
                ],
            )

            swarm = SwarmCoordinator(seed=1, config_path=str(config_path))
            swarm.advance_simulation(now_monotonic=0.0)
            swarm.advance_simulation(now_monotonic=0.1)

            state = swarm.get_state()
            enemy_statuses = {enemy["id"]: enemy["status"] for enemy in state["enemies"]}
            attack_node = next(node for node in state["nodes"] if node["id"] == "attack-1")

            self.assertEqual(enemy_statuses["enemy-1"], "destroyed")
            self.assertEqual(attack_node["status"], "destroyed")
            self.assertTrue(
                any(event["event_type"] == "drone_destroyed" for event in state["events"])
            )

    def test_search_command_assigns_patrol_and_emits_object_reports(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "search_execution.json"
            _write_test_scenario(
                config_path,
                enemies=[
                    {
                        "id": "enemy-1",
                        "label": "Enemy Infantry 1",
                        "subtype": "infantry",
                        "status": "active",
                        "position": [520, 520],
                    }
                ],
            )

            swarm = SwarmCoordinator(config_path=str(config_path))
            result = swarm.calculate_gossip_path(
                {
                    "origin": "soldier-1",
                    "operator_node": "soldier-1",
                    "target_location": "Grid Bravo",
                    "action_code": "SEARCH",
                    "consensus_algorithm": "gossip",
                }
            )

            node_behaviors = {node["id"]: node.get("behavior") for node in result["nodes"]}
            task_behaviors = {
                task["drone_id"]: task["behavior"]
                for task in result["search_state"]["target_tasks"]
            }

            self.assertEqual(result["status"], "searching")
            self.assertEqual(result["search_state"]["mission_status"], "searching")
            self.assertEqual(node_behaviors["recon-1"], "patrol")
            self.assertEqual(task_behaviors["recon-1"], "patrol")
            self.assertGreaterEqual(len(result["object_reports"]), 1)
            self.assertTrue(
                any(event["event_type"] == "target_discovered" for event in result["events"])
            )


if __name__ == "__main__":
    unittest.main()
