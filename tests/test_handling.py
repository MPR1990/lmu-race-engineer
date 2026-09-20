from __future__ import annotations

from datetime import UTC, datetime
import unittest

from lmu_race_engineer.analysis import HandlingAnalyzer
from lmu_race_engineer.models import TelemetrySnapshot


class HandlingAnalyzerTest(unittest.TestCase):
    def make_snapshot(self, **changes: object) -> TelemetrySnapshot:
        values: dict[str, object] = {
            "timestamp": datetime(2026, 9, 19, tzinfo=UTC),
            "lap_number": 3,
            "lap_distance_fraction": 0.5,
            "lap_time_seconds": 50.0,
            "best_lap_time_seconds": 90.0,
            "speed_kph": 140.0,
            "fuel_liters": 40.0,
            "tire_temperatures_c": {
                "front_left": 85.0,
                "front_right": 85.0,
                "rear_left": 85.0,
                "rear_right": 85.0,
            },
            "tire_pressures_kpa": {},
            "brake_temperatures_c": {"front": 500.0, "rear": 500.0},
            "traction_control_level": 4,
            "abs_level": 5,
            "brake_bias_percent": 54.0,
            "wheelspin_events": 0,
            "lockup_events": 0,
            "throttle_input": 0.0,
            "brake_input": 0.0,
            "steering_input": 0.3,
            "lateral_acceleration_mps2": 5.0,
            "longitudinal_acceleration_mps2": 0.0,
        }
        values.update(changes)
        return TelemetrySnapshot(**values)

    def test_braking_heat_is_not_classified_as_exit_oversteer(self) -> None:
        analyzer = HandlingAnalyzer()
        snapshot = self.make_snapshot(
            brake_input=0.8,
            throttle_input=0.0,
            lockup_events=1,
            tire_temperatures_c={
                "front_left": 85.0,
                "front_right": 85.0,
                "rear_left": 100.0,
                "rear_right": 100.0,
            },
        )

        assessment = analyzer.update(snapshot)
        self.assertEqual("braking", assessment.phase)
        self.assertEqual("braking_instability", assessment.condition)

    def test_repeated_front_grip_loss_is_understeer(self) -> None:
        analyzer = HandlingAnalyzer()
        snapshot = self.make_snapshot(
            tire_grip_fraction={
                "front_left": 0.55,
                "front_right": 0.50,
                "rear_left": 0.10,
                "rear_right": 0.12,
            },
        )

        assessments = [analyzer.update(snapshot) for _ in range(3)]
        self.assertEqual("understeer", assessments[-1].condition)
        self.assertEqual("mid_corner", assessments[-1].phase)
        self.assertEqual(3, assessments[-1].evidence_count)

    def test_exit_rear_grip_loss_is_oversteer(self) -> None:
        analyzer = HandlingAnalyzer()
        snapshot = self.make_snapshot(
            throttle_input=0.7,
            tire_grip_fraction={
                "front_left": 0.10,
                "front_right": 0.12,
                "rear_left": 0.55,
                "rear_right": 0.50,
            },
        )

        assessment = analyzer.update(snapshot)
        self.assertEqual("exit", assessment.phase)
        self.assertEqual("oversteer", assessment.condition)


if __name__ == "__main__":
    unittest.main()
