from __future__ import annotations

import argparse
from queue import Empty, Queue
import threading
from pathlib import Path

from lmu_race_engineer.alerts import AlertManager, VoiceAlertEngine
from lmu_race_engineer.analysis import LapTracker
from lmu_race_engineer.config import AppConfig
from lmu_race_engineer.recommendations import SetupRecommendationEngine
from lmu_race_engineer.storage import SessionStore
from lmu_race_engineer.telemetry import (
    DemoTelemetrySource,
    RestApiClient,
    RestApiTelemetrySource,
    SharedMemoryTelemetrySource,
)
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
        recommendations=list(recommendations),
        alerts=list(alerts),
    )


def create_source(config: AppConfig):
    if config.telemetry.mode == "shared_memory":
        return SharedMemoryTelemetrySource(config.telemetry.shared_memory_name)
    if config.telemetry.mode == "rest":
        return RestApiTelemetrySource(
            RestApiClient(config.telemetry.rest_api_base_url),
            poll_interval_seconds=config.telemetry.poll_interval_seconds,
        )
    if config.telemetry.mode == "demo":
        return DemoTelemetrySource(poll_interval_seconds=config.telemetry.poll_interval_seconds)
    raise ValueError(f"Unsupported telemetry mode: {config.telemetry.mode}")


def run_app(config: AppConfig) -> None:
    from lmu_race_engineer.ui import RaceEngineerDashboard

    source = create_source(config)
    tracker = LapTracker()
    engine = SetupRecommendationEngine(config.monitoring)
    alerts = AlertManager(config.voice.cooldown_seconds)
    voice = VoiceAlertEngine(config.voice)
    dashboard = RaceEngineerDashboard()
    store = SessionStore(config.storage_path)
    last_recorded_lap = 0
    last_saved_recommendations: tuple[tuple[str, str, str, float, str, str], ...] = ()
    state_queue: Queue[DashboardState] = Queue()
    stop_event = threading.Event()

    def worker() -> None:
        nonlocal last_recorded_lap, last_saved_recommendations
        try:
            for snapshot in source.stream():
                if stop_event.is_set():
                    break
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
                    current_recommendations = tuple(
                        (
                            item.category,
                            item.title,
                            item.reason,
                            item.confidence,
                            item.priority,
                            item.action_timing,
                        )
                        for item in recommendations
                    )
                    if current_recommendations != last_saved_recommendations:
                        store.record_recommendations(recommendations)
                        last_saved_recommendations = current_recommendations
                else:
                    last_saved_recommendations = ()
                state_queue.put(build_dashboard_state(snapshot, analysis, recommendations, alerts.history))
        finally:
            stop_event.set()

    def render_pending() -> None:
        try:
            while True:
                dashboard.render(state_queue.get_nowait())
        except Empty:
            pass
        if stop_event.is_set():
            dashboard.root.quit()
        else:
            dashboard.root.after(100, render_pending)

    def close_dashboard() -> None:
        stop_event.set()
        dashboard.root.quit()

    worker_thread = threading.Thread(target=worker, name="telemetry-worker", daemon=True)
    dashboard.root.protocol("WM_DELETE_WINDOW", close_dashboard)
    worker_thread.start()
    dashboard.root.after(0, render_pending)

    try:
        dashboard.root.mainloop()
    finally:
        stop_event.set()
        worker_thread.join(timeout=max(1.0, config.telemetry.poll_interval_seconds * 2))
        store.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=None)
    args = parser.parse_args()
    config = AppConfig.load(args.config)
    run_app(config)


if __name__ == "__main__":
    main()
