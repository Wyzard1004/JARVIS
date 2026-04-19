import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api import main as api_main


class OperatorContextRoutingTests(unittest.TestCase):
    def setUp(self):
        api_main.operator_context["active_operator"] = "soldier-1"
        api_main.operator_context["updated_at"] = None

    def test_set_active_operator_updates_shared_context(self):
        state = {
            "nodes": [
                {"id": "soldier-1", "type": "soldier", "role": "operator-node"},
                {"id": "soldier-2", "type": "soldier", "role": "operator-node"},
            ]
        }

        context = api_main._set_active_operator("soldier-2", state)

        self.assertEqual(context["active_operator"], "soldier-2")
        self.assertEqual(api_main.operator_context["active_operator"], "soldier-2")
        self.assertIn("soldier-2", context["available_operators"])

    def test_mock_parse_intent_uses_selected_operator_for_direct_commands(self):
        api_main.operator_context["active_operator"] = "soldier-2"

        intent = api_main.mock_parse_intent(
            {
                "transcribed_text": "Move to Grid Bravo",
                "target_location": "Grid Bravo",
                "action_code": "MOVE_TO",
            }
        )

        self.assertEqual(intent["origin"], "soldier-2")
        self.assertEqual(intent["operator_node"], "soldier-2")

    def test_to_swarm_intent_inherits_selected_operator_for_audio_pipeline(self):
        api_main.operator_context["active_operator"] = "soldier-2"

        parsed_command = {
            "intent": "swarm_command",
            "goal": "MOVE_TO",
            "target_location": "GRID_BRAVO",
            "avoid_location": None,
            "confidence": 0.91,
            "confirmation_required": False,
            "execution_state": "NONE",
        }

        intent = api_main._to_swarm_intent(
            parsed_command,
            "JARVIS move to Grid Bravo over",
            {},
        )

        self.assertEqual(intent["origin"], "soldier-2")
        self.assertEqual(intent["operator_node"], "soldier-2")
        self.assertEqual(intent["target_location"], "Grid Bravo")


if __name__ == "__main__":
    unittest.main()
