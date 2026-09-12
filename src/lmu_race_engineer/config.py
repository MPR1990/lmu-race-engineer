from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass(slots=True)
class VoiceAlertSettings:
    enabled: bool = True
    rate: int = 185
    volume: float = 0.9
    cooldown_seconds: int = 45


@dataclass(slots=True)
class MonitoringTargets:
    tire_temp_min_c: float = 78.0
    tire_temp_max_c: float = 98.0
    brake_temp_max_c: float = 720.0
    fuel_reserve_laps: float = 2.0
    pace_drop_threshold_seconds: float = 1.0
    repeated_event_threshold: int = 3


@dataclass(slots=True)
class TelemetrySourceSettings:
    mode: str = "demo"
    shared_memory_name: str = "LMUSharedMemory"
    rest_api_base_url: str = "http://localhost:6397/api"
    poll_interval_seconds: float = 0.5
    request_timeout_seconds: float = 2.0


@dataclass(slots=True)
class AppConfig:
    telemetry: TelemetrySourceSettings = field(default_factory=TelemetrySourceSettings)
    voice: VoiceAlertSettings = field(default_factory=VoiceAlertSettings)
    monitoring: MonitoringTargets = field(default_factory=MonitoringTargets)
    storage_path: str = "data/session_history.sqlite3"

    @classmethod
    def load(cls, path: str | Path | None = None) -> "AppConfig":
        config = cls()
        if path is None:
            return config
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        telemetry = raw.get("telemetry", {})
        voice = raw.get("voice", {})
        monitoring = raw.get("monitoring", {})
        return cls(
            telemetry=TelemetrySourceSettings(**{**asdict(config.telemetry), **telemetry}),
            voice=VoiceAlertSettings(**{**asdict(config.voice), **voice}),
            monitoring=MonitoringTargets(**{**asdict(config.monitoring), **monitoring}),
            storage_path=raw.get("storage_path", config.storage_path),
        )
