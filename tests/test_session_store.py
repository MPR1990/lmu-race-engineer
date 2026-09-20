from __future__ import annotations

from datetime import UTC, datetime
import sqlite3
import json
import tempfile
import unittest
from pathlib import Path

from lmu_race_engineer.models import Recommendation, VoiceAlert
from lmu_race_engineer.models import TelemetrySnapshot
from lmu_race_engineer.storage import SessionStore


class SessionStoreTest(unittest.TestCase):
    def test_records_handling_telemetry_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "telemetry.sqlite3"
            store = SessionStore(str(database_path))
            snapshot = TelemetrySnapshot(
                timestamp=datetime(2026, 9, 19, tzinfo=UTC),
                lap_number=3,
                lap_distance_fraction=0.5,
                lap_time_seconds=45.0,
                best_lap_time_seconds=90.0,
                speed_kph=150.0,
                fuel_liters=40.0,
                tire_temperatures_c={"front_left": 85.0, "front_right": 85.0, "rear_left": 90.0, "rear_right": 90.0},
                tire_pressures_kpa={"front_left": 180.0, "front_right": 180.0, "rear_left": 183.0, "rear_right": 183.0},
                brake_temperatures_c={"front": 600.0, "rear": 500.0},
                traction_control_level=4,
                abs_level=5,
                brake_bias_percent=54.0,
                throttle_input=0.7,
                lateral_acceleration_mps2=2.0,
                tire_loads_n={"front_left": 1200.0},
                tire_ride_height_m={"front_left": 0.042},
            )

            store.record_snapshot(snapshot)
            store.close()

            connection = sqlite3.connect(database_path)
            row = connection.execute(
                "SELECT throttle_input, lateral_acceleration_mps2, tire_loads_n, tire_ride_height_m FROM telemetry_samples"
            ).fetchone()
            connection.close()

            self.assertEqual(0.7, row[0])
            self.assertEqual(2.0, row[1])
            self.assertEqual(1200.0, json.loads(row[2])["front_left"])
            self.assertEqual(0.042, json.loads(row[3])["front_left"])

    def test_records_recommendations_and_alerts_with_context(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "session.sqlite3"
            store = SessionStore(str(database_path))
            observed_at = datetime(2026, 9, 18, 12, 0, 5, tzinfo=UTC)
            recommendation = Recommendation(
                category="live",
                title="Rear tires overheating",
                reason="Reduce throttle on corner exit.",
                confidence=0.82,
                priority="high",
                action_timing="change_now",
            )
            alert = VoiceAlert(
                title=recommendation.title,
                message=recommendation.reason,
                priority="high",
                created_at=observed_at,
                lap_number=7,
            )

            store.record_recommendations([recommendation], observed_at=observed_at, lap_number=7)
            store.record_alerts([alert])
            session_id = store.session_id
            store.close()

            connection = sqlite3.connect(database_path)
            session_row = connection.execute(
                "SELECT session_id, started_at, ended_at FROM sessions"
            ).fetchone()
            recommendation_row = connection.execute(
                "SELECT observed_at, lap_number, title, action_timing FROM recommendations"
            ).fetchone()
            alert_row = connection.execute(
                "SELECT created_at, lap_number, title, priority FROM alerts"
            ).fetchone()
            connection.close()

            self.assertEqual(
                (observed_at.isoformat(), 7, "Rear tires overheating", "change_now"),
                recommendation_row,
            )
            self.assertEqual(
                (observed_at.isoformat(), 7, "Rear tires overheating", "high"),
                alert_row,
            )
            self.assertEqual(session_id, session_row[0])
            self.assertIsNotNone(session_row[1])
            self.assertIsNotNone(session_row[2])


if __name__ == "__main__":
    unittest.main()