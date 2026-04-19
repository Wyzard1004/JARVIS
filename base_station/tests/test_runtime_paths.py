import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.runtime_paths import ensure_runtime_storage


class RuntimePathTests(unittest.TestCase):
    def test_data_dir_creates_writable_runtime_structure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"JARVIS_DATA_DIR": temp_dir}, clear=False):
                paths = ensure_runtime_storage()

            default_scenario_file = paths["default_scenario_file"]
            scenario_library_dir = paths["scenario_library_dir"]
            scenario_asset_dir = paths["scenario_asset_dir"]

            self.assertTrue(default_scenario_file.exists())
            self.assertTrue(scenario_library_dir.exists())
            self.assertTrue(scenario_asset_dir.exists())

            payload = json.loads(default_scenario_file.read_text(encoding="utf-8"))
            self.assertIn("scenario", payload)
            self.assertEqual(default_scenario_file.parent, Path(temp_dir) / "config")
            self.assertEqual(scenario_library_dir, Path(temp_dir) / "config" / "scenarios")
            self.assertEqual(scenario_asset_dir, Path(temp_dir) / "scenario_assets")


if __name__ == "__main__":
    unittest.main()
