from __future__ import annotations

import argparse
import time
from pathlib import Path

from lmu_race_engineer.alerts import AlertManager, VoiceAlertEngine
from lmu_race_engineer.analysis import LapTracker
from lmu_race_engineer.config import AppConfig
from lmu_race_engineer.recommendations import SetupRecommendationEngine
from lmu_race_engineer.storage import SessionStore
from lmu_race_engineer.telemetry import DemoTelemetrySource, SharedMemoryTelemetrySource
from lmu_race_engineer.ui import DashboardState


def build_dashboard_state(snapshot, analysis, recommendations, alerts) -> DashboardState:
    delta_text = "-"
    if analysis.current_delta_to_best_seconds is not None:
        delta_text = f"{analysis.current_delta_to_best_seconds:+.2f}s"
    laps_remaining = "-"
    if analysis.estimated_laps_remaining is not None:
        laps_remaining = f"{analysis.estimated_laps_remaining:.1f} laps left"
    return DashboardState(
        current_lap_text=f"Lap {analysis.current_lap_number}\n{analysis.current_lap_time_seconds:.1f}s",
        delta_text=delta_text,
        fuel_text=f"{snapshot.fuel_liters:.1f} L\n{laps_remaining}",
        tire_text=f"Front {analysis.front_tire_temp_avg_c:.0f}C\nRear {analysis.rear_tire_temp_avg_c:.0f}C",
        brake_text=f"Front {analysis.front_brake_temp_c:.0f}C\nRear {analysis.rear_brake_temp_c:.0f}C",
        recommendations=recommendations,
        alerts=alerts,
    )


def create_source(config: AppConfig):
    if config.telemetry.mode == "shared_memory":
        return SharedMemoryTelemetrySource(config.telemetry.shared_memory_name)
    if config.telemetry.mode == "rest":
        raise NotImplementedError("REST telemetry streaming is not implemented yet.")
    if config.telemetry.mode == "demo":
        return DemoTelemetrySource()
    raise ValueError(f"Unsupported telemetry mode: {config.telemetry.mode}")


def run_app(config: AppConfig) -> None:
    from lmu_race_engineer.ui import RaceEngineerDashboard

    source = create_source(config)
    tracker = LapTracker()
    engine = SetupRecommendationEngine(config.monitoring)
    alerts = AlertManager(config.voice.cooldown_seconds)
    voice = VoiceAlertEngine(config.voice)
    store = SessionStore(config.storage_path)
    dashboard = RaceEngineerDashboard()
    last_recorded_lap = 0

    for snapshot in source.stream():
        analysis = tracker.update(snapshot)
        recommendations = engine.evaluate(snapshot, analysis)
        fresh_alerts = alerts.build_alerts(recommendations, snapshot.timestamp)
        for alert in fresh_alerts:
            voice.announce(alert)
        store.record_snapshot(snapshot)
        if analysis.last_lap is not None and analysis.last_lap.lap_number > last_recorded_lap:
            store.record_completed_lap(analysis.last_lap)
            last_recorded_lap = analysis.last_lap.lap_number
        if recommendations:
            store.record_recommendations(recommendations)
        dashboard.render(build_dashboard_state(snapshot, analysis, recommendations, alerts.history))
        time.sleep(config.telemetry.poll_interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=None)
    args = parser.parse_args()
    config = AppConfig.load(args.config)
    run_app(config)


if __name__ == "__main__":
    main()
