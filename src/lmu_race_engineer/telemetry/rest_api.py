from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import datetime
import time
from urllib.request import urlopen

from lmu_race_engineer.models import TelemetrySnapshot
from lmu_race_engineer.telemetry.base import TelemetrySource


class RestApiClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def get_session_summary(self) -> dict[str, str]:
        return self._get_json("/session")

    def get_live_telemetry(self) -> dict[str, object]:
        return self._get_json("/telemetry/live")

    def _get_json(self, path: str) -> dict[str, object]:
        with urlopen(f"{self.base_url}{path}") as response:
            return json.loads(response.read().decode("utf-8"))


class RestApiTelemetrySource(TelemetrySource):
    def __init__(self, client: RestApiClient, poll_interval_seconds: float = 0.5, sleep_func=None) -> None:
        self.client = client
        self.poll_interval_seconds = poll_interval_seconds
        self.sleep_func = sleep_func or time.sleep

    def stream(self) -> Iterator[TelemetrySnapshot]:
        first_sample = True
        while True:
            if not first_sample:
                self.sleep_func(self.poll_interval_seconds)
            first_sample = False
            payload = self.client.get_live_telemetry()
            yield TelemetrySnapshot(
                timestamp=datetime.fromisoformat(str(payload["timestamp"])),
                lap_number=int(payload["lap_number"]),
                lap_distance_fraction=float(payload["lap_distance_fraction"]),
                lap_time_seconds=float(payload["lap_time_seconds"]),
                best_lap_time_seconds=_optional_float(payload.get("best_lap_time_seconds")),
                speed_kph=float(payload["speed_kph"]),
                fuel_liters=float(payload["fuel_liters"]),
                tire_temperatures_c=_tire_map(payload["tire_temperatures_c"]),
                tire_pressures_kpa=_tire_map(payload["tire_pressures_kpa"]),
                brake_temperatures_c={
                    "front": float(payload["brake_temperatures_c"]["front"]),
                    "rear": float(payload["brake_temperatures_c"]["rear"]),
                },
                traction_control_level=int(payload["traction_control_level"]),
                abs_level=int(payload["abs_level"]),
                brake_bias_percent=float(payload["brake_bias_percent"]),
                wheelspin_events=int(payload.get("wheelspin_events", 0)),
                lockup_events=int(payload.get("lockup_events", 0)),
            )


def _tire_map(raw: object) -> dict[str, float]:
    values = dict(raw or {})
    return {
        "front_left": float(values["front_left"]),
        "front_right": float(values["front_right"]),
        "rear_left": float(values["rear_left"]),
        "rear_right": float(values["rear_right"]),
    }


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    return float(value)
