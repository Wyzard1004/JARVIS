from __future__ import annotations

import json
import os
import shutil
from pathlib import Path


BASE_STATION_DIR = Path(__file__).resolve().parents[1]
BUNDLED_CONFIG_DIR = BASE_STATION_DIR / "config"
BUNDLED_DEFAULT_SCENARIO_FILE = BUNDLED_CONFIG_DIR / "swarm_initial_state.json"
BUNDLED_SCENARIO_LIBRARY_DIR = BUNDLED_CONFIG_DIR / "scenarios"
BUNDLED_SCENARIO_ASSET_DIR = BASE_STATION_DIR / "scenario_assets"


def _env_path(name: str) -> Path | None:
    raw = os.getenv(name, "").strip()
    if not raw:
        return None
    return Path(raw).expanduser().resolve()


def get_runtime_paths() -> dict[str, Path]:
    data_dir = _env_path("JARVIS_DATA_DIR")
    config_dir = _env_path("JARVIS_CONFIG_DIR")
    scenario_asset_dir = _env_path("JARVIS_SCENARIO_ASSET_DIR")

    if config_dir is None:
        config_dir = (data_dir / "config").resolve() if data_dir else BUNDLED_CONFIG_DIR

    if scenario_asset_dir is None:
        scenario_asset_dir = (data_dir / "scenario_assets").resolve() if data_dir else BUNDLED_SCENARIO_ASSET_DIR

    default_scenario_file = config_dir / BUNDLED_DEFAULT_SCENARIO_FILE.name
    scenario_library_dir = config_dir / "scenarios"

    return {
        "base_station_dir": BASE_STATION_DIR,
        "bundled_config_dir": BUNDLED_CONFIG_DIR,
        "bundled_default_scenario_file": BUNDLED_DEFAULT_SCENARIO_FILE,
        "bundled_scenario_library_dir": BUNDLED_SCENARIO_LIBRARY_DIR,
        "config_dir": config_dir,
        "default_scenario_file": default_scenario_file,
        "scenario_library_dir": scenario_library_dir,
        "bundled_scenario_asset_dir": BUNDLED_SCENARIO_ASSET_DIR,
        "scenario_asset_dir": scenario_asset_dir,
    }


def _seed_directory_if_missing(source_dir: Path, destination_dir: Path) -> list[str]:
    seeded_names: list[str] = []
    if not source_dir.exists():
        return seeded_names

    for source_path in source_dir.iterdir():
        if not source_path.is_file():
            continue

        destination_path = destination_dir / source_path.name
        if destination_path.exists():
            continue

        shutil.copy2(source_path, destination_path)
        seeded_names.append(source_path.name)

    return seeded_names


def ensure_runtime_storage() -> dict[str, Path]:
    paths = get_runtime_paths()
    paths["config_dir"].mkdir(parents=True, exist_ok=True)
    paths["scenario_library_dir"].mkdir(parents=True, exist_ok=True)
    paths["scenario_asset_dir"].mkdir(parents=True, exist_ok=True)

    default_scenario_file = paths["default_scenario_file"]
    bundled_default_scenario_file = paths["bundled_default_scenario_file"]

    if not default_scenario_file.exists():
        if bundled_default_scenario_file.exists():
            shutil.copy2(bundled_default_scenario_file, default_scenario_file)
        else:
            default_scenario_file.write_text(
                json.dumps(
                    {
                        "scenario": "Default Continuous Scenario",
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
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

    seeded_scenarios = _seed_directory_if_missing(
        paths["bundled_scenario_library_dir"], paths["scenario_library_dir"]
    )
    seeded_assets = _seed_directory_if_missing(
        paths["bundled_scenario_asset_dir"], paths["scenario_asset_dir"]
    )

    paths["seeded_scenario_names"] = seeded_scenarios
    paths["seeded_asset_names"] = seeded_assets
    paths["seeded_scenario_count"] = len(seeded_scenarios)
    paths["seeded_asset_count"] = len(seeded_assets)

    return paths
