from __future__ import annotations

import unittest

from lmu_race_engineer.app import create_source
from lmu_race_engineer.config import AppConfig, TelemetrySourceSettings
from lmu_race_engineer.telemetry import DemoTelemetrySource, SharedMemoryTelemetrySource


class AppSourceSelectionTest(unittest.TestCase):
    def test_demo_mode_returns_demo_source(self) -> None:
        config = AppConfig(telemetry=TelemetrySourceSettings(mode="demo"))
        self.assertIsInstance(create_source(config), DemoTelemetrySource)

    def test_shared_memory_mode_returns_shared_memory_source(self) -> None:
        config = AppConfig(telemetry=TelemetrySourceSettings(mode="shared_memory"))
        self.assertIsInstance(create_source(config), SharedMemoryTelemetrySource)

    def test_rest_mode_is_explicitly_not_implemented(self) -> None:
        config = AppConfig(telemetry=TelemetrySourceSettings(mode="rest"))
        with self.assertRaises(NotImplementedError):
            create_source(config)

    def test_unknown_mode_raises_value_error(self) -> None:
        config = AppConfig(telemetry=TelemetrySourceSettings(mode="unknown"))
        with self.assertRaises(ValueError):
            create_source(config)


if __name__ == "__main__":
    unittest.main()
