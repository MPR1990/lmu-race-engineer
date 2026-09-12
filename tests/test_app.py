from __future__ import annotations

import unittest

from lmu_race_engineer.app import create_source
from lmu_race_engineer.config import AppConfig, TelemetrySourceSettings
from lmu_race_engineer.telemetry import DemoTelemetrySource, RestApiTelemetrySource, SharedMemoryTelemetrySource


class AppSourceSelectionTest(unittest.TestCase):
    def test_demo_mode_returns_demo_source(self) -> None:
        config = AppConfig(telemetry=TelemetrySourceSettings(mode="demo", poll_interval_seconds=0.25))
        source = create_source(config)

        self.assertIsInstance(source, DemoTelemetrySource)
        self.assertEqual(0.25, source.poll_interval_seconds)

    def test_shared_memory_mode_returns_shared_memory_source(self) -> None:
        config = AppConfig(
            telemetry=TelemetrySourceSettings(mode="shared_memory", shared_memory_name="CustomLMU")
        )
        source = create_source(config)

        self.assertIsInstance(source, SharedMemoryTelemetrySource)
        self.assertEqual("CustomLMU", source.memory_name)

    def test_rest_mode_returns_rest_source(self) -> None:
        config = AppConfig(
            telemetry=TelemetrySourceSettings(
                mode="rest",
                rest_api_base_url="http://localhost:5000/api",
                poll_interval_seconds=0.4,
            )
        )
        source = create_source(config)

        self.assertIsInstance(source, RestApiTelemetrySource)
        self.assertEqual("http://localhost:5000/api", source.client.base_url)
        self.assertEqual(0.4, source.poll_interval_seconds)

    def test_unknown_mode_raises_value_error(self) -> None:
        config = AppConfig(telemetry=TelemetrySourceSettings(mode="unknown"))
        with self.assertRaises(ValueError):
            create_source(config)


if __name__ == "__main__":
    unittest.main()
