from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


TireKey = Literal["front_left", "front_right", "rear_left", "rear_right"]
AxleKey = Literal["front", "rear"]


@dataclass(slots=True)
class TelemetrySnapshot:
    timestamp: datetime
    lap_number: int
    lap_distance_fraction: float
    lap_time_seconds: float
    best_lap_time_seconds: float | None
    speed_kph: float
    fuel_liters: float
    tire_temperatures_c: dict[TireKey, float]
    tire_pressures_kpa: dict[TireKey, float]
    brake_temperatures_c: dict[AxleKey, float]
    traction_control_level: int
    abs_level: int
    brake_bias_percent: float
    wheelspin_events: int = 0
    lockup_events: int = 0


@dataclass(slots=True)
class CompletedLap:
    lap_number: int
    lap_time_seconds: float
    fuel_used_liters: float
    average_speed_kph: float


@dataclass(slots=True)
class Recommendation:
    category: Literal["live", "pit"]
    title: str
    reason: str
    confidence: float
    priority: Literal["low", "medium", "high"]
    action_timing: Literal["change_now", "observe_more", "next_stop"]


@dataclass(slots=True)
class VoiceAlert:
    title: str
    message: str
    priority: Literal["medium", "high"]
    created_at: datetime = field(default_factory=datetime.utcnow)
