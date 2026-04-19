import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api import main as api_main
from core.ai_bridge import create_confirmation_text, process_voice_command
from core.continuous_coordinate_space import ContinuousCoordinateSpace


class VoiceCommandParsingTests(unittest.TestCase):
    def test_full_8x8_grid_location_parses(self):
        parsed = process_voice_command("JARVIS, move to Grid Hotel 8, over.")

        self.assertEqual(parsed["goal"], "MOVE_TO")
        self.assertEqual(parsed["target_location"], "GRID_HOTEL_8")
        self.assertEqual(create_confirmation_text(parsed), "JARVIS, moving to Grid Hotel 8, over.")

    def test_recon_patrol_route_parses(self):
        parsed = process_voice_command("JARVIS, recon patrol bravo 1 to bravo 3, over.")

        self.assertEqual(parsed["goal"], "SCAN_AREA")
        self.assertEqual(parsed["target_location"], "GRID_BRAVO_1")
        self.assertEqual(parsed["patrol_end_location"], "GRID_BRAVO_3")
        self.assertEqual(
            create_confirmation_text(parsed),
            "JARVIS, recon patrol from Grid Bravo 1 to Grid Bravo 3, over.",
        )

    def test_swarm_intent_humanizes_patrol_route_locations(self):
        parsed_command = {
            "intent": "swarm_command",
            "goal": "SCAN_AREA",
            "target_location": "GRID_BRAVO_1",
            "avoid_location": None,
            "patrol_end_location": "GRID_BRAVO_3",
            "confidence": 0.95,
            "confirmation_required": False,
            "execution_state": "NONE",
        }

        intent = api_main._to_swarm_intent(
            parsed_command,
            "JARVIS recon patrol bravo 1 to bravo 3 over",
            {},
        )

        self.assertEqual(intent["target_location"], "Grid Bravo 1")
        self.assertEqual(intent["patrol_end_location"], "Grid Bravo 3")

    def test_continuous_space_round_trips_display_sector_labels(self):
        space = ContinuousCoordinateSpace()

        self.assertEqual(space.display_sector_label(space.location_to_point("Grid Alpha 1")), "Alpha-1")
        self.assertEqual(space.display_sector_label(space.location_to_point("Grid Delta 6")), "Delta-6")
        self.assertEqual(space.display_sector_label(space.location_to_point("Grid Hotel 8")), "Hotel-8")

    def test_search_ui_simulation_does_not_fabricate_attack_queue(self):
        sim_data = api_main._simulate_enemies_and_attacks(
            "Grid Bravo 1",
            ["soldier-1", "recon-1", "attack-1"],
            [],
            "searching",
        )

        self.assertEqual(sim_data["attack_queue"], [])
        self.assertTrue(
            all(signal["phase"] != "operators_to_attacks" for signal in sim_data["operator_signals"])
        )


if __name__ == "__main__":
    unittest.main()
