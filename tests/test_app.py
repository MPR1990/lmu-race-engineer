from __future__ import annotations

import unittest

from lmu_race_engineer.app import build_dashboard_state, create_source
from lmu_race_engineer.analysis import AnalysisSnapshot
from lmu_race_engineer.config import AppConfig, TelemetrySourceSettings
from lmu_race_engineer.models import CompletedLap, Recommendation, TelemetrySnapshot, VoiceAlert
from lmu_race_engineer.telemetry import DemoTelemetrySource, RestApiTelemetrySource, SharedMemoryTelemetrySource
from datetime import datetime


class AppSourceSelectionTest(unittest.TestCase):
    def test_demo_mode_returns_demo_source(self) -> None:
        config = AppConfig(telemetry=TelemetrySourceSettings(mode="demo", poll_interval_seconds=0.25))
        source = create_source(config)

        self.assertIsInstance(source, DemoTelemetrySource)
        self.assertEqual(180, source.samples)
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
                request_timeout_seconds=3.0,
            )
        )
        source = create_source(config)

        self.assertIsInstance(source, RestApiTelemetrySource)
        self.assertEqual("http://localhost:5000/api", source.client.base_url)
        self.assertEqual(3.0, source.client.request_timeout_seconds)
        self.assertEqual(0.4, source.poll_interval_seconds)

    def test_unknown_mode_raises_value_error(self) -> None:
        config = AppConfig(telemetry=TelemetrySourceSettings(mode="unknown"))
        with self.assertRaises(ValueError):
            create_source(config)

    def test_build_dashboard_state_formats_fallbacks(self) -> None:
        snapshot = TelemetrySnapshot(
            timestamp=datetime(2026, 1, 1, 12, 0, 0),
            lap_number=3,
            lap_distance_fraction=0.5,
            lap_time_seconds=45.2,
            best_lap_time_seconds=None,
            speed_kph=200.0,
            fuel_liters=25.4,
            tire_temperatures_c={
                "front_left": 84.0,
                "front_right": 85.0,
                "rear_left": 90.0,
                "rear_right": 91.0,
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
            brake_bias_percent=53.0,
        )
        analysis = AnalysisSnapshot(
            current_lap_number=3,
            current_lap_time_seconds=45.2,
            current_delta_to_best_seconds=None,
            last_lap=None,
            best_lap=None,
            rolling_average_lap_seconds=None,
            estimated_laps_remaining=None,
            rear_tire_temp_avg_c=90.5,
            front_tire_temp_avg_c=84.5,
            front_brake_temp_c=620.0,
            rear_brake_temp_c=540.0,
            traction_event_count=0,
            lockup_event_count=0,
        )

        state = build_dashboard_state(snapshot, analysis, [], [])

        self.assertEqual("Lap 3\n45.2s", state.current_lap_text)
        self.assertEqual("-", state.delta_text)
        self.assertEqual("25.4 L\n-", state.fuel_text)

    def test_build_dashboard_state_formats_recommendations_and_alerts(self) -> None:
        snapshot = TelemetrySnapshot(
            timestamp=datetime(2026, 1, 1, 12, 0, 0),
            lap_number=4,
            lap_distance_fraction=0.5,
            lap_time_seconds=44.0,
            best_lap_time_seconds=88.0,
            speed_kph=205.0,
            fuel_liters=20.0,
            tire_temperatures_c={
                "front_left": 84.0,
                "front_right": 85.0,
                "rear_left": 90.0,
                "rear_right": 91.0,
            },
            tire_pressures_kpa={
                "front_left": 180.0,
                "front_right": 180.5,
                "rear_left": 183.0,
                "rear_right": 183.5,
            },
            brake_temperatures_c={"front": 650.0, "rear": 550.0},
            traction_control_level=4,
            abs_level=5,
            brake_bias_percent=53.0,
        )
        analysis = AnalysisSnapshot(
            current_lap_number=4,
            current_lap_time_seconds=44.0,
            current_delta_to_best_seconds=1.25,
            last_lap=CompletedLap(3, 89.2, 2.0, 190.0),
            best_lap=CompletedLap(2, 88.0, 2.0, 191.0),
            rolling_average_lap_seconds=89.5,
            estimated_laps_remaining=8.6,
            rear_tire_temp_avg_c=90.5,
            front_tire_temp_avg_c=84.5,
            front_brake_temp_c=650.0,
            rear_brake_temp_c=550.0,
            traction_event_count=0,
            lockup_event_count=0,
        )
        recommendations = [
            Recommendation(
                category="live",
                title="Increase traction control",
                reason="Repeated wheelspin events suggest raising traction control one step.",
                confidence=0.76,
                priority="high",
                action_timing="change_now",
            )
        ]
        alerts = [
            VoiceAlert(
                title="Rear tires overheating",
                message="Rear tire temperatures are above target.",
                priority="high",
                created_at=datetime(2026, 1, 1, 12, 0, 5),
            )
        ]

        state = build_dashboard_state(snapshot, analysis, recommendations, alerts)

        self.assertEqual("+1.25s", state.delta_text)
        self.assertEqual("20.0 L\n8.6 laps left", state.fuel_text)
        self.assertEqual("Increase traction control", state.recommendations[0].title)
        self.assertEqual("Rear tires overheating", state.alerts[0].title)


if __name__ == "__main__":
    unittest.main()
