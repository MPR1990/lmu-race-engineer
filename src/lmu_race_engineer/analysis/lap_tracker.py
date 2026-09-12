from __future__ import annotations

from dataclasses import dataclass

from lmu_race_engineer.models import CompletedLap, TelemetrySnapshot


@dataclass(slots=True)
class AnalysisSnapshot:
    current_lap_number: int
    current_lap_time_seconds: float
    current_delta_to_best_seconds: float | None
    last_lap: CompletedLap | None
    best_lap: CompletedLap | None
    rolling_average_lap_seconds: float | None
    estimated_laps_remaining: float | None
    rear_tire_temp_avg_c: float
    front_tire_temp_avg_c: float
    front_brake_temp_c: float
    rear_brake_temp_c: float
    traction_event_count: int
    lockup_event_count: int


class LapTracker:
    def __init__(self) -> None:
        self.completed_laps: list[CompletedLap] = []
        self._last_snapshot: TelemetrySnapshot | None = None
        self._lap_speed_samples: list[float] = []
        self._lap_start_fuel: float | None = None
        self._last_lap_number: int | None = None

    def update(self, snapshot: TelemetrySnapshot) -> AnalysisSnapshot:
        if self._last_lap_number is None:
            self._last_lap_number = snapshot.lap_number
            self._lap_start_fuel = snapshot.fuel_liters
            self._lap_speed_samples.append(snapshot.speed_kph)
        elif snapshot.lap_number < self._last_lap_number:
            self.completed_laps = []
            self._last_lap_number = snapshot.lap_number
            self._lap_start_fuel = snapshot.fuel_liters
            self._lap_speed_samples = [snapshot.speed_kph]
            self._last_snapshot = snapshot
            return self._build_analysis(snapshot)
        elif snapshot.lap_number != self._last_lap_number and self._last_snapshot is not None:
            self.completed_laps.append(
                CompletedLap(
                    lap_number=self._last_lap_number,
                    lap_time_seconds=self._last_snapshot.lap_time_seconds,
                    fuel_used_liters=max(
                        0.0, (self._lap_start_fuel or snapshot.fuel_liters) - self._last_snapshot.fuel_liters
                    ),
                    average_speed_kph=sum(self._lap_speed_samples) / max(1, len(self._lap_speed_samples)),
                )
            )
            self._lap_speed_samples = [snapshot.speed_kph]
            self._lap_start_fuel = snapshot.fuel_liters
            self._last_lap_number = snapshot.lap_number
        else:
            self._lap_speed_samples.append(snapshot.speed_kph)
        self._last_snapshot = snapshot

        return self._build_analysis(snapshot)

    def _build_analysis(self, snapshot: TelemetrySnapshot) -> AnalysisSnapshot:
        best_lap = min(self.completed_laps, key=lambda lap: lap.lap_time_seconds, default=None)
        last_lap = self.completed_laps[-1] if self.completed_laps else None
        rolling = None
        if self.completed_laps:
            relevant = self.completed_laps[-3:]
            rolling = sum(lap.lap_time_seconds for lap in relevant) / len(relevant)
        estimated_laps_remaining = None
        if self.completed_laps:
            avg_fuel = sum(lap.fuel_used_liters for lap in self.completed_laps[-3:]) / min(3, len(self.completed_laps))
            if avg_fuel > 0:
                estimated_laps_remaining = snapshot.fuel_liters / avg_fuel
        delta = None
        best_time = best_lap.lap_time_seconds if best_lap else snapshot.best_lap_time_seconds
        if best_time is not None:
            delta = snapshot.lap_time_seconds - best_time

        return AnalysisSnapshot(
            current_lap_number=snapshot.lap_number,
            current_lap_time_seconds=snapshot.lap_time_seconds,
            current_delta_to_best_seconds=delta,
            last_lap=last_lap,
            best_lap=best_lap,
            rolling_average_lap_seconds=rolling,
            estimated_laps_remaining=estimated_laps_remaining,
            rear_tire_temp_avg_c=(snapshot.tire_temperatures_c["rear_left"] + snapshot.tire_temperatures_c["rear_right"]) / 2,
            front_tire_temp_avg_c=(snapshot.tire_temperatures_c["front_left"] + snapshot.tire_temperatures_c["front_right"]) / 2,
            front_brake_temp_c=snapshot.brake_temperatures_c["front"],
            rear_brake_temp_c=snapshot.brake_temperatures_c["rear"],
            traction_event_count=snapshot.wheelspin_events,
            lockup_event_count=snapshot.lockup_events,
        )
