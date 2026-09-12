from __future__ import annotations

from datetime import datetime, timedelta
import unittest

from lmu_race_engineer.analysis import LapTracker
from lmu_race_engineer.models import TelemetrySnapshot


def snapshot(lap_number: int, lap_time: float, fuel: float, speed: float) -> TelemetrySnapshot:
    return TelemetrySnapshot(
        timestamp=datetime(2026, 1, 1, 12, 0, 0) + timedelta(seconds=lap_time + lap_number),
        lap_number=lap_number,
        lap_distance_fraction=min(0.99, lap_time / 100),
        lap_time_seconds=lap_time,
        best_lap_time_seconds=89.0,
        speed_kph=speed,
        fuel_liters=fuel,
        tire_temperatures_c={
            "front_left": 84.0,
            "front_right": 85.0,
            "rear_left": 88.0,
            "rear_right": 89.0,
        },
        tire_pressures_kpa={
            "front_left": 180.0,
            "front_right": 180.5,
            "rear_left": 183.0,
            "rear_right": 183.5,
        },
        brake_temperatures_c={"front": 620.0, "rear": 540.0},
        traction_control_level=4,
        abs_level=5,
        brake_bias_percent=53.5,
    )


class LapTrackerTest(unittest.TestCase):
    def test_completes_lap_when_number_changes(self) -> None:
        tracker = LapTracker()

        tracker.update(snapshot(1, 10.0, 90.0, 180.0))
        tracker.update(snapshot(1, 89.5, 87.5, 210.0))
        analysis = tracker.update(snapshot(2, 1.0, 87.2, 170.0))

        self.assertIsNotNone(analysis.last_lap)
        self.assertEqual(1, analysis.last_lap.lap_number)
        self.assertAlmostEqual(89.5, analysis.last_lap.lap_time_seconds)
        self.assertAlmostEqual(2.5, analysis.last_lap.fuel_used_liters)
        self.assertAlmostEqual(195.0, analysis.last_lap.average_speed_kph)
        self.assertEqual(170.0, tracker._lap_speed_samples[0])

    def test_resets_when_lap_counter_moves_backward(self) -> None:
        tracker = LapTracker()

        tracker.update(snapshot(5, 80.0, 60.0, 200.0))
        analysis = tracker.update(snapshot(1, 2.0, 59.5, 150.0))

        self.assertIsNone(analysis.last_lap)
        self.assertEqual([], tracker.completed_laps)
        self.assertIsNone(analysis.best_lap)
        self.assertEqual(1, analysis.current_lap_number)
        self.assertEqual([150.0], tracker._lap_speed_samples)


if __name__ == "__main__":
    unittest.main()
