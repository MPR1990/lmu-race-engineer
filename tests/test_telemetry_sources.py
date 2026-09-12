from __future__ import annotations

from datetime import datetime
import unittest

from lmu_race_engineer.telemetry import DemoTelemetrySource, RestApiClient, RestApiTelemetrySource


class FakeRestApiClient(RestApiClient):
    def __init__(self) -> None:
        super().__init__("http://example.test")
        self.calls = 0

    def get_live_telemetry(self) -> dict[str, object]:
        self.calls += 1
        return {
            "timestamp": datetime(2026, 1, 1, 12, 0, self.calls).isoformat(),
            "lap_number": 1,
            "lap_distance_fraction": 0.1 * self.calls,
            "lap_time_seconds": 10.0 * self.calls,
            "best_lap_time_seconds": 89.0,
            "speed_kph": 180.0,
            "fuel_liters": 90.0,
            "tire_temperatures_c": {
                "front_left": 84.0,
                "front_right": 85.0,
                "rear_left": 88.0,
                "rear_right": 89.0,
            },
            "tire_pressures_kpa": {
                "front_left": 180.0,
                "front_right": 180.5,
                "rear_left": 183.0,
                "rear_right": 183.5,
            },
            "brake_temperatures_c": {"front": 620.0, "rear": 540.0},
            "traction_control_level": 4,
            "abs_level": 5,
            "brake_bias_percent": 53.0,
            "wheelspin_events": 0,
            "lockup_events": 0,
        }


class TelemetrySourceTest(unittest.TestCase):
    def test_demo_source_sleeps_between_samples(self) -> None:
        sleeps: list[float] = []
        source = DemoTelemetrySource(samples=3, poll_interval_seconds=0.25, sleep_func=sleeps.append)

        samples = list(source.stream())

        self.assertEqual(3, len(samples))
        self.assertEqual([0.25, 0.25], sleeps)
        self.assertEqual(0.25, (samples[1].timestamp - samples[0].timestamp).total_seconds())

    def test_rest_source_sleeps_between_polls(self) -> None:
        client = FakeRestApiClient()
        sleeps: list[float] = []
        source = RestApiTelemetrySource(client, poll_interval_seconds=0.4, sleep_func=sleeps.append)

        stream = source.stream()
        first = next(stream)
        second = next(stream)

        self.assertEqual(1, first.lap_number)
        self.assertEqual(1, second.lap_number)
        self.assertEqual(2, client.calls)
        self.assertEqual([0.4], sleeps)


if __name__ == "__main__":
    unittest.main()
