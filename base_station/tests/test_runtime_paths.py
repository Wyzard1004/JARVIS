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

    def test_data_dir_seeds_bundled_scenarios_and_assets_without_overwriting_existing_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            scenario_library_dir = Path(temp_dir) / "config" / "scenarios"
            scenario_library_dir.mkdir(parents=True, exist_ok=True)
            existing_path = scenario_library_dir / "zarichne.json"
            existing_path.write_text('{"scenario":"Custom Zarichne"}\n', encoding="utf-8")

            with patch.dict(os.environ, {"JARVIS_DATA_DIR": temp_dir}, clear=False):
                paths = ensure_runtime_storage()

            bundled_scenario_names = {
                path.name for path in paths["bundled_scenario_library_dir"].glob("*.json")
            }
            seeded_scenario_names = {path.name for path in paths["scenario_library_dir"].glob("*.json")}
            bundled_asset_names = {
                path.name for path in paths["bundled_scenario_asset_dir"].iterdir() if path.is_file()
            }
            seeded_asset_names = {
                path.name for path in paths["scenario_asset_dir"].iterdir() if path.is_file()
            }

            self.assertTrue(bundled_scenario_names.issubset(seeded_scenario_names))
            self.assertTrue(bundled_asset_names.issubset(seeded_asset_names))
            self.assertEqual(existing_path.read_text(encoding="utf-8"), '{"scenario":"Custom Zarichne"}\n')


if __name__ == "__main__":
    unittest.main()
