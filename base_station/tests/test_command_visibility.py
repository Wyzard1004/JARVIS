import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api import main as api_main


class CommandVisibilityTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        api_main.operator_context["active_operator"] = "soldier-1"
        api_main.operator_context["updated_at"] = None
        api_main.pending_execute_commands.clear()
        api_main.command_trace_log.clear()

    async def test_no_op_audio_command_broadcasts_ignored_event(self):
        captured = []

        async def fake_broadcast(message):
            captured.append(message)

        original_broadcast = api_main.manager.broadcast
        api_main.manager.broadcast = fake_broadcast
        try:
            payload = await api_main._dispatch_swarm_command(
                "jarvis uh maybe do something",
                {
                    "origin": "soldier-1",
                    "operator_node": "soldier-1",
                    "action_code": "NO_OP",
                },
                {
                    "goal": "NO_OP",
                    "execution_state": "NONE",
                    "callsign": "JARVIS",
                },
                input_source="jetson-esp32-ptt",
            )
        finally:
            api_main.manager.broadcast = original_broadcast

        self.assertEqual(payload["event"], "command_ignored")
        self.assertEqual(payload["status"], "ignored")
        self.assertEqual(payload["input_source"], "jetson-esp32-ptt")
        self.assertEqual(payload["transcribed_text"], "jarvis uh maybe do something")
        self.assertTrue(payload["trace_id"])
        self.assertTrue(payload["command_id"])
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0]["command_id"], payload["command_id"])
        self.assertTrue(
            any(
                entry["trace_id"] == payload["trace_id"] and entry["stage"] == "dispatch_result"
                for entry in api_main.command_trace_log
            )
        )

    async def test_execute_without_pending_command_broadcasts_ignored_event(self):
        captured = []

        async def fake_broadcast(message):
            captured.append(message)

        original_broadcast = api_main.manager.broadcast
        api_main.manager.broadcast = fake_broadcast
        try:
            payload = await api_main._dispatch_swarm_command(
                "execute",
                {
                    "origin": "soldier-1",
                    "operator_node": "soldier-1",
                    "action_code": "EXECUTE",
                },
                {
                    "goal": "EXECUTE",
                    "execution_state": "NONE",
                    "callsign": "JARVIS",
                },
                input_source="jetson-esp32-ptt",
            )
        finally:
            api_main.manager.broadcast = original_broadcast

        self.assertEqual(payload["event"], "command_ignored")
        self.assertEqual(payload["status"], "ignored")
        self.assertEqual(payload["input_source"], "jetson-esp32-ptt")
        self.assertIn("No pending destructive command", payload["message"])
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0]["command_id"], payload["command_id"])

    async def test_review_reports_broadcasts_report_snapshot_without_dispatching_swarm(self):
        captured = []

        async def fake_broadcast(message):
            captured.append(message)

        original_broadcast = api_main.manager.broadcast
        api_main.manager.broadcast = fake_broadcast
        try:
            payload = await api_main._dispatch_swarm_command(
                "review reports",
                {
                    "origin": "soldier-1",
                    "operator_node": "soldier-1",
                    "action_code": "REVIEW_REPORTS",
                },
                {
                    "goal": "REVIEW_REPORTS",
                    "execution_state": "NONE",
                    "callsign": "JARVIS",
                },
            )
        finally:
            api_main.manager.broadcast = original_broadcast

        self.assertEqual(payload["event"], "report_review")
        self.assertEqual(payload["status"], "reporting")
        self.assertIn("Reviewing reports:", payload["message"])
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0]["command_id"], payload["command_id"])
        self.assertIn("report_summary", payload)

    def test_record_command_trace_appends_debug_entry(self):
        entry = api_main._record_command_trace(
            "trace-debug-1",
            "audio_received",
            origin="soldier-1",
            audio_bytes=4096,
        )

        self.assertEqual(entry["trace_id"], "trace-debug-1")
        self.assertEqual(entry["stage"], "audio_received")
        self.assertEqual(entry["audio_bytes"], 4096)
        self.assertEqual(api_main.command_trace_log[-1]["trace_id"], "trace-debug-1")


if __name__ == "__main__":
    unittest.main()
