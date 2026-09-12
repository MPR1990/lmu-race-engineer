from __future__ import annotations

import sqlite3
from pathlib import Path

from lmu_race_engineer.models import CompletedLap, Recommendation, TelemetrySnapshot


class SessionStore:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self._create_tables()

    def _create_tables(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS telemetry_samples (
                timestamp TEXT NOT NULL,
                lap_number INTEGER NOT NULL,
                lap_time_seconds REAL NOT NULL,
                fuel_liters REAL NOT NULL,
                speed_kph REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS completed_laps (
                lap_number INTEGER NOT NULL,
                lap_time_seconds REAL NOT NULL,
                fuel_used_liters REAL NOT NULL,
                average_speed_kph REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS recommendations (
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                reason TEXT NOT NULL,
                confidence REAL NOT NULL,
                priority TEXT NOT NULL,
                action_timing TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def record_snapshot(self, snapshot: TelemetrySnapshot) -> None:
        self.connection.execute(
            """
            INSERT INTO telemetry_samples (timestamp, lap_number, lap_time_seconds, fuel_liters, speed_kph)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                snapshot.timestamp.isoformat(),
                snapshot.lap_number,
                snapshot.lap_time_seconds,
                snapshot.fuel_liters,
                snapshot.speed_kph,
            ),
        )
        self.connection.commit()

    def record_completed_lap(self, lap: CompletedLap) -> None:
        self.connection.execute(
            """
            INSERT INTO completed_laps (lap_number, lap_time_seconds, fuel_used_liters, average_speed_kph)
            VALUES (?, ?, ?, ?)
            """,
            (lap.lap_number, lap.lap_time_seconds, lap.fuel_used_liters, lap.average_speed_kph),
        )
        self.connection.commit()

    def record_recommendations(self, recommendations: list[Recommendation]) -> None:
        self.connection.executemany(
            """
            INSERT INTO recommendations (category, title, reason, confidence, priority, action_timing)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    recommendation.category,
                    recommendation.title,
                    recommendation.reason,
                    recommendation.confidence,
                    recommendation.priority,
                    recommendation.action_timing,
                )
                for recommendation in recommendations
            ],
        )
        self.connection.commit()
