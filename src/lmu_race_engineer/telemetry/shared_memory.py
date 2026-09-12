from __future__ import annotations

from collections.abc import Iterator

from lmu_race_engineer.models import TelemetrySnapshot
from lmu_race_engineer.telemetry.base import TelemetrySource


class SharedMemoryTelemetrySource(TelemetrySource):
    def __init__(self, memory_name: str) -> None:
        self.memory_name = memory_name

    def stream(self) -> Iterator[TelemetrySnapshot]:
        raise NotImplementedError(
            "Shared memory parsing is not implemented yet. Add the LMU shared memory layout here."
        )
