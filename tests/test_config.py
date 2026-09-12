from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lmu_race_engineer.config import AppConfig


class AppConfigTest(unittest.TestCase):
    def test_load_overrides_selected_values(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "telemetry": {"mode": "shared_memory"},
                        "voice": {"enabled": False},
                        "monitoring": {"fuel_reserve_laps": 3.5},
                        "storage_path": "custom.sqlite3",
                    }
                ),
                encoding="utf-8",
            )

            config = AppConfig.load(config_path)

            self.assertEqual("shared_memory", config.telemetry.mode)
            self.assertFalse(config.voice.enabled)
            self.assertEqual(3.5, config.monitoring.fuel_reserve_laps)
            self.assertEqual("custom.sqlite3", config.storage_path)


if __name__ == "__main__":
    unittest.main()
