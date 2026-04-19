import json
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.swarm_logic import SwarmCoordinator


def _write_test_scenario(path: Path, *, enemies=None):
    payload = {
        "scenario": "Command Execution Test",
        "coordinate_space_size": 1000,
        "map_overlay": {
            "asset_url": None,
            "asset_path": None,
            "opacity": 0.72,
            "visible": False,
        },
        "drones": [
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
            self.assertEqual(node_behaviors["compute-1"], "transit")
            self.assertEqual(node_behaviors["recon-1"], "transit")
            self.assertEqual(node_behaviors["attack-1"], "transit")

            initial_recon_position = swarm.get_drone_position("recon-1")
            swarm.advance_simulation(now_monotonic=0.0)
            swarm.advance_simulation(now_monotonic=1.0)
            moved_recon_position = swarm.get_drone_position("recon-1")

            self.assertNotEqual(initial_recon_position, moved_recon_position)

            state = swarm.get_state()
            self.assertEqual(state["search_state"]["mission_status"], "maneuvering")
            self.assertEqual(state["target_location"], "Grid Charlie")

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
