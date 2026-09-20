from __future__ import annotations

import sqlite3
from datetime import datetime
import json
from pathlib import Path
from uuid import uuid4

from lmu_race_engineer.models import CompletedLap, Recommendation, TelemetrySnapshot, VoiceAlert


class SessionStore:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.session_id = uuid4().hex
        self.started_at = datetime.now().astimezone()
        self._pending_writes = 0
        self._commit_interval = 10
        self._create_tables()

    def _create_tables(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS telemetry_samples (
                session_id TEXT,
                timestamp TEXT NOT NULL,
                lap_number INTEGER NOT NULL,
                lap_time_seconds REAL NOT NULL,
                fuel_liters REAL NOT NULL,
                speed_kph REAL NOT NULL,
                throttle_input REAL NOT NULL DEFAULT 0,
                brake_input REAL NOT NULL DEFAULT 0,
                steering_input REAL NOT NULL DEFAULT 0,
                lateral_acceleration_mps2 REAL NOT NULL DEFAULT 0,
                longitudinal_acceleration_mps2 REAL NOT NULL DEFAULT 0,
                tire_loads_n TEXT NOT NULL DEFAULT '{}',
                tire_grip_fraction TEXT NOT NULL DEFAULT '{}',
                tire_wear_fraction TEXT NOT NULL DEFAULT '{}',
                tire_camber_rad TEXT NOT NULL DEFAULT '{}',
                tire_ride_height_m TEXT NOT NULL DEFAULT '{}',
                suspension_deflection_m TEXT NOT NULL DEFAULT '{}',
                suspension_force_n TEXT NOT NULL DEFAULT '{}',
                lateral_tire_force_n TEXT NOT NULL DEFAULT '{}',
                longitudinal_tire_force_n TEXT NOT NULL DEFAULT '{}',
                brake_pressure_fraction TEXT NOT NULL DEFAULT '{}',
                lateral_patch_velocity_mps TEXT NOT NULL DEFAULT '{}',
                longitudinal_patch_velocity_mps TEXT NOT NULL DEFAULT '{}',
                front_ride_height_m REAL NOT NULL DEFAULT 0,
                rear_ride_height_m REAL NOT NULL DEFAULT 0,
                front_wing_height_m REAL NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS completed_laps (
                session_id TEXT,
                lap_number INTEGER NOT NULL,
                lap_time_seconds REAL NOT NULL,
                fuel_used_liters REAL NOT NULL,
                average_speed_kph REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS recommendations (
                session_id TEXT,
                observed_at TEXT,
                lap_number INTEGER,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                reason TEXT NOT NULL,
                confidence REAL NOT NULL,
                priority TEXT NOT NULL,
                action_timing TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS alerts (
                session_id TEXT,
                created_at TEXT NOT NULL,
                lap_number INTEGER,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                priority TEXT NOT NULL
            );
            """
        )
        self._add_column_if_missing("recommendations", "observed_at", "TEXT")
        self._add_column_if_missing("recommendations", "lap_number", "INTEGER")
        for table in ("telemetry_samples", "completed_laps", "recommendations", "alerts"):
            self._add_column_if_missing(table, "session_id", "TEXT")
        for column, definition in (
            ("throttle_input", "REAL NOT NULL DEFAULT 0"),
            ("brake_input", "REAL NOT NULL DEFAULT 0"),
            ("steering_input", "REAL NOT NULL DEFAULT 0"),
            ("lateral_acceleration_mps2", "REAL NOT NULL DEFAULT 0"),
            ("longitudinal_acceleration_mps2", "REAL NOT NULL DEFAULT 0"),
            ("tire_loads_n", "TEXT NOT NULL DEFAULT '{}'"),
            ("tire_grip_fraction", "TEXT NOT NULL DEFAULT '{}'"),
            ("tire_wear_fraction", "TEXT NOT NULL DEFAULT '{}'"),
            ("tire_camber_rad", "TEXT NOT NULL DEFAULT '{}'"),
            ("tire_ride_height_m", "TEXT NOT NULL DEFAULT '{}'"),
            ("suspension_deflection_m", "TEXT NOT NULL DEFAULT '{}'"),
            ("suspension_force_n", "TEXT NOT NULL DEFAULT '{}'"),
            ("lateral_tire_force_n", "TEXT NOT NULL DEFAULT '{}'"),
            ("longitudinal_tire_force_n", "TEXT NOT NULL DEFAULT '{}'"),
            ("brake_pressure_fraction", "TEXT NOT NULL DEFAULT '{}'"),
            ("lateral_patch_velocity_mps", "TEXT NOT NULL DEFAULT '{}'"),
            ("longitudinal_patch_velocity_mps", "TEXT NOT NULL DEFAULT '{}'"),
            ("front_ride_height_m", "REAL NOT NULL DEFAULT 0"),
            ("rear_ride_height_m", "REAL NOT NULL DEFAULT 0"),
            ("front_wing_height_m", "REAL NOT NULL DEFAULT 0"),
        ):
            self._add_column_if_missing("telemetry_samples", column, definition)
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                ended_at TEXT
            )
            """
        )
        self.connection.execute(
            "INSERT INTO sessions (session_id, started_at) VALUES (?, ?)",
            (self.session_id, self.started_at.isoformat()),
        )
        self.connection.commit()

    def _add_column_if_missing(self, table: str, column: str, definition: str) -> None:
        columns = self.connection.execute(f"PRAGMA table_info({table})").fetchall()
        if column not in {row[1] for row in columns}:
            self.connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def close(self) -> None:
        self.connection.execute(
            "UPDATE sessions SET ended_at = ? WHERE session_id = ?",
            (datetime.now().astimezone().isoformat(), self.session_id),
        )
        self.connection.commit()
        self._pending_writes = 0
        self.connection.close()

    def record_snapshot(self, snapshot: TelemetrySnapshot) -> None:
        self.connection.execute(
            """
            INSERT INTO telemetry_samples (
                session_id, timestamp, lap_number, lap_time_seconds, fuel_liters, speed_kph,
                throttle_input, brake_input, steering_input,
                lateral_acceleration_mps2, longitudinal_acceleration_mps2,
                tire_loads_n, tire_grip_fraction, tire_wear_fraction, tire_camber_rad,
                tire_ride_height_m, suspension_deflection_m, suspension_force_n,
                lateral_tire_force_n, longitudinal_tire_force_n, brake_pressure_fraction,
                lateral_patch_velocity_mps, longitudinal_patch_velocity_mps,
                front_ride_height_m, rear_ride_height_m, front_wing_height_m
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self.session_id,
                snapshot.timestamp.isoformat(),
                snapshot.lap_number,
                snapshot.lap_time_seconds,
                snapshot.fuel_liters,
                snapshot.speed_kph,
                snapshot.throttle_input,
                snapshot.brake_input,
                snapshot.steering_input,
                snapshot.lateral_acceleration_mps2,
                snapshot.longitudinal_acceleration_mps2,
                json.dumps(snapshot.tire_loads_n),
                json.dumps(snapshot.tire_grip_fraction),
                json.dumps(snapshot.tire_wear_fraction),
                json.dumps(snapshot.tire_camber_rad),
                json.dumps(snapshot.tire_ride_height_m),
                json.dumps(snapshot.suspension_deflection_m),
                json.dumps(snapshot.suspension_force_n),
                json.dumps(snapshot.lateral_tire_force_n),
                json.dumps(snapshot.longitudinal_tire_force_n),
                json.dumps(snapshot.brake_pressure_fraction),
                json.dumps(snapshot.lateral_patch_velocity_mps),
                json.dumps(snapshot.longitudinal_patch_velocity_mps),
                snapshot.front_ride_height_m,
                snapshot.rear_ride_height_m,
                snapshot.front_wing_height_m,
            ),
        )
        self._mark_dirty()

    def record_completed_lap(self, lap: CompletedLap) -> None:
        self.connection.execute(
            """
            INSERT INTO completed_laps (session_id, lap_number, lap_time_seconds, fuel_used_liters, average_speed_kph)
            VALUES (?, ?, ?, ?, ?)
            """,
            (self.session_id, lap.lap_number, lap.lap_time_seconds, lap.fuel_used_liters, lap.average_speed_kph),
        )
        self._mark_dirty()

    def record_recommendations(
        self,
        recommendations: list[Recommendation],
        observed_at: datetime | None = None,
        lap_number: int | None = None,
    ) -> None:
        self.connection.executemany(
            """
            INSERT INTO recommendations (
                session_id, observed_at, lap_number, category, title, reason, confidence, priority, action_timing
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    self.session_id,
                    observed_at.isoformat() if observed_at is not None else None,
                    lap_number,
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
        self._mark_dirty()

    def record_alerts(self, alerts: list[VoiceAlert]) -> None:
        if not alerts:
            return
        self.connection.executemany(
            """
            INSERT INTO alerts (session_id, created_at, lap_number, title, message, priority)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    self.session_id,
                    alert.created_at.isoformat(),
                    alert.lap_number,
                    alert.title,
                    alert.message,
                    alert.priority,
                )
                for alert in alerts
            ],
        )
        self._mark_dirty()

    def _mark_dirty(self) -> None:
        self._pending_writes += 1
        if self._pending_writes >= self._commit_interval:
            self.connection.commit()
            self._pending_writes = 0
