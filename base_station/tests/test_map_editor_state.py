import json
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.map_geometry import footprint_center, normalize_rect_footprint
from core.swarm_logic import SwarmCoordinator


class MapGeometryTests(unittest.TestCase):
    def test_normalize_rect_footprint_clamps_bounds(self):
        footprint = normalize_rect_footprint({
            "kind": "rect",
            "x": 990,
            "y": -20,
            "width": 100,
            "height": 40,
        })

        self.assertEqual(footprint["x"], 900.0)
        self.assertEqual(footprint["y"], 0.0)
        self.assertEqual(footprint["width"], 100.0)
        self.assertEqual(footprint["height"], 40.0)
        self.assertEqual(footprint_center(footprint), (950.0, 20.0))


class SwarmEditorStateTests(unittest.TestCase):
    def test_loading_scenario_rewrites_overlay_url_to_backend_served_asset(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "scenario.json"
            config_path.write_text(
                json.dumps(
                    {
                        "scenario": "Overlay URL Rewrite",
                        "coordinate_space_size": 1000,
                        "map_overlay": {
                            "asset_url": "http://100.71.205.85:8000/scenario-assets/overlay-test.png",
                            "asset_path": "scenario_assets/overlay-test.png",
                            "opacity": 0.72,
                            "visible": True,
                        },
                        "drones": [],
                        "enemies": [],
                        "structures": [],
                        "special_entities": [],
                        "initial_events": [],
                    }
                ),
                encoding="utf-8",
            )

            swarm = SwarmCoordinator(config_path=str(config_path))

            self.assertEqual(swarm.get_state()["map_overlay"]["asset_url"], "/scenario-assets/overlay-test.png")

    def test_apply_editor_state_and_save_persists_overlay_and_structures(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "scenario.json"
            config_path.write_text(
                json.dumps(
                    {
                        "scenario": "Test Scenario",
                        "coordinate_space_size": 1000,
                        "map_overlay": {
                            "asset_url": None,
                            "asset_path": None,
                            "opacity": 0.72,
                            "visible": False,
                        },
                        "drones": [
                            {
                                "id": "recon-1",
                                "type": "recon",
                                "behavior": "patrol",
                                "position": [100, 100],
                                "waypoints": [[100, 100], [200, 100]],
                                "detection_radius": 220,
                            }
                        ],
                        "enemies": [],
                        "structures": [],
                        "special_entities": [],
                        "initial_events": [],
                    }
                ),
                encoding="utf-8",
            )

            swarm = SwarmCoordinator(config_path=str(config_path))
            state = swarm.apply_editor_state(
                {
                    "map_overlay": {
                        "asset_url": "/scenario-assets/test.png",
                        "asset_path": "scenario_assets/test.png",
                        "opacity": 0.55,
                        "visible": True,
                    },
                    "structures": [
                        {
                            "id": "structure-building-test",
                            "label": "Test Building",
                            "type": "structure",
                            "subtype": "building",
                            "status": "intact",
                            "position": [210, 230],
                            "footprint": {
                                "kind": "rect",
                                "x": 180,
                                "y": 200,
                                "width": 60,
                                "height": 40,
                            },
                        }
                    ],
                }
            )

            self.assertEqual(state["map_overlay"]["asset_url"], "/scenario-assets/test.png")
            self.assertEqual(len(state["structures"]), 1)
            self.assertEqual(state["structures"][0]["footprint"]["width"], 60.0)
            self.assertEqual(state["structures"][0]["position"], [210.0, 220.0])

            save_path = swarm.save_scenario()
            saved_payload = json.loads(save_path.read_text(encoding="utf-8"))

            self.assertEqual(saved_payload["map_overlay"]["visible"], True)
            self.assertEqual(saved_payload["structures"][0]["footprint"]["height"], 40.0)

    def test_apply_editor_state_can_remove_drones_and_save_to_new_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "blank_workspace.json"
            save_path = Path(temp_dir) / "saved_scenarios" / "custom_scenario.json"
            config_path.write_text(
                json.dumps(
                    {
                        "scenario": "Blank Workspace",
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
                                "position": [90, 90],
                            },
                            {
                                "id": "recon-1",
                                "type": "recon",
                                "behavior": "patrol",
                                "position": [100, 100],
                                "waypoints": [[100, 100], [200, 100]],
                                "detection_radius": 220,
                            },
                        ],
                        "enemies": [],
                        "structures": [],
                        "special_entities": [],
                        "initial_events": [],
                    }
                ),
                encoding="utf-8",
            )

            swarm = SwarmCoordinator(config_path=str(config_path))
            state = swarm.apply_editor_state(
                {
                    "drones": [
                        {
                            "id": "recon-1",
                            "type": "recon",
                            "behavior": "patrol",
                            "position": [250, 260],
                            "waypoints": [[250, 260], [280, 300]],
                            "detection_radius": 220,
                        }
                    ]
                }
            )

            self.assertEqual(len(state["nodes"]), 1)
            self.assertEqual(state["nodes"][0]["id"], "recon-1")
            self.assertEqual(state["nodes"][0]["position"], [250.0, 260.0])
            self.assertFalse(state["scenario_info"]["is_blank"])

            written_path = swarm.save_scenario(target_path=save_path, scenario_name="Custom Scenario")
            saved_payload = json.loads(written_path.read_text(encoding="utf-8"))

            self.assertEqual(written_path, save_path)
            self.assertEqual(saved_payload["scenario"], "Custom Scenario")
            self.assertEqual(len(saved_payload["drones"]), 1)
            self.assertEqual(saved_payload["drones"][0]["id"], "recon-1")

    def test_suggested_commands_are_normalized_in_state_and_saved(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "scenario.json"
            config_path.write_text(
                json.dumps(
                    {
                        "scenario": "Metadata Test",
                        "suggested_commands": ["scan grid alpha"],
                        "coordinate_space_size": 1000,
                        "map_overlay": {
                            "asset_url": None,
                            "asset_path": None,
                            "opacity": 0.72,
                            "visible": False,
                        },
                        "drones": [],
                        "enemies": [],
                        "structures": [],
                        "special_entities": [],
                        "initial_events": [],
                    }
                ),
                encoding="utf-8",
            )

            swarm = SwarmCoordinator(config_path=str(config_path))
            state = swarm.apply_editor_state(
                {
                    "suggested_commands": [
                        "  scan grid alpha  ",
                        "",
                        "hold position near bridge",
                        "scan grid alpha",
                    ]
                }
            )

            self.assertEqual(
                state["scenario_info"]["suggested_commands"],
                ["scan grid alpha", "hold position near bridge"],
            )
            self.assertEqual(state["scenario_info"]["suggested_command_count"], 2)

            save_path = swarm.save_scenario()
            saved_payload = json.loads(save_path.read_text(encoding="utf-8"))

            self.assertEqual(
                saved_payload["suggested_commands"],
                ["scan grid alpha", "hold position near bridge"],
            )


if __name__ == "__main__":
    unittest.main()
