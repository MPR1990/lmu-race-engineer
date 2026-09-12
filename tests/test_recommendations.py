from __future__ import annotations

from lmu_race_engineer.analysis import AnalysisSnapshot
from lmu_race_engineer.config import MonitoringTargets
from lmu_race_engineer.models import CompletedLap, TelemetrySnapshot
from lmu_race_engineer.recommendations import SetupRecommendationEngine
from datetime import datetime
import unittest


class RecommendationEngineTest(unittest.TestCase):
    def test_generates_live_and_pit_actions_for_hot_rears_and_fuel_risk(self) -> None:
        engine = SetupRecommendationEngine(MonitoringTargets())
        snapshot = TelemetrySnapshot(
            timestamp=datetime(2026, 1, 1, 12, 0, 0),
            lap_number=5,
            lap_distance_fraction=0.5,
            lap_time_seconds=46.0,
            best_lap_time_seconds=89.0,
            speed_kph=190.0,
            fuel_liters=2.0,
            tire_temperatures_c={
                "front_left": 85.0,
                "front_right": 86.0,
                "rear_left": 102.0,
                "rear_right": 103.0,
            },
            tire_pressures_kpa={
                "front_left": 180.0,
                "front_right": 180.5,
                "rear_left": 183.0,
                "rear_right": 183.5,
            },
            brake_temperatures_c={"front": 740.0, "rear": 560.0},
            traction_control_level=4,
            abs_level=5,
            brake_bias_percent=53.0,
            wheelspin_events=3,
            lockup_events=0,
        )
        analysis = AnalysisSnapshot(
            current_lap_number=5,
            current_lap_time_seconds=46.0,
            current_delta_to_best_seconds=1.3,
            last_lap=CompletedLap(4, 91.0, 2.2, 188.0),
            best_lap=CompletedLap(2, 89.5, 2.0, 191.0),
            rolling_average_lap_seconds=90.5,
            estimated_laps_remaining=0.9,
            rear_tire_temp_avg_c=102.5,
            front_tire_temp_avg_c=85.5,
            front_brake_temp_c=740.0,
            rear_brake_temp_c=560.0,
            traction_event_count=3,
            lockup_event_count=0,
        )

        recommendations = engine.evaluate(snapshot, analysis)
        titles = {item.title for item in recommendations}

        self.assertIn("Rear tires overheating", titles)
        self.assertIn("Review rear pressures or camber", titles)
        self.assertIn("Front brakes overheating", titles)
        self.assertIn("Increase traction control", titles)
        self.assertIn("Fuel target risk", titles)


if __name__ == "__main__":
    unittest.main()
