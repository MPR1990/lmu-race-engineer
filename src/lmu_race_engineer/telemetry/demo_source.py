from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
import time

from lmu_race_engineer.models import TelemetrySnapshot
from lmu_race_engineer.telemetry.base import TelemetrySource


class DemoTelemetrySource(TelemetrySource):
    def __init__(
        self,
        samples: int = 180,
        lap_time_seconds: float = 90.0,
        poll_interval_seconds: float = 0.5,
        sleep_func=None,
    ) -> None:
        self.samples = samples
        self.lap_time_seconds = lap_time_seconds
        self.poll_interval_seconds = poll_interval_seconds
        self.sleep_func = sleep_func or time.sleep

    def stream(self) -> Iterator[TelemetrySnapshot]:
        start = datetime.now(UTC)
        fuel = 92.0
        for index in range(self.samples):
            if index > 0:
                self.sleep_func(self.poll_interval_seconds)
            lap_number = index // 30 + 1
            lap_progress = (index % 30) / 30
            lap_time = lap_progress * self.lap_time_seconds
            overheating = index >= 55
            yield TelemetrySnapshot(
                timestamp=start + timedelta(seconds=index),
                lap_number=lap_number,
                lap_distance_fraction=lap_progress,
                lap_time_seconds=lap_time,
                best_lap_time_seconds=89.4,
                speed_kph=205 - abs(0.5 - lap_progress) * 70,
                fuel_liters=max(0.0, fuel - index * 0.22),
                tire_temperatures_c={
                    "front_left": 84 + (3 if overheating else 0),
                    "front_right": 85 + (4 if overheating else 0),
                    "rear_left": 89 + (9 if overheating else 0),
                    "rear_right": 90 + (10 if overheating else 0),
                },
                tire_pressures_kpa={
                    "front_left": 180.0,
                    "front_right": 181.0,
                    "rear_left": 183.5,
                    "rear_right": 184.0,
                },
                brake_temperatures_c={
                    "front": 610 + (130 if overheating else 0),
                    "rear": 540 + (40 if overheating else 0),
                },
                traction_control_level=4,
                abs_level=5,
                brake_bias_percent=53.2,
                wheelspin_events=2 if overheating else 0,
                lockup_events=0 if index % 17 else 1,
            )
