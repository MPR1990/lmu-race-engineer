from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator

from lmu_race_engineer.models import TelemetrySnapshot


class TelemetrySource(ABC):
    @abstractmethod
    def stream(self) -> Iterator[TelemetrySnapshot]:
        raise NotImplementedError
