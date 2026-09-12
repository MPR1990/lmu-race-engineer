from __future__ import annotations

try:
    import pyttsx3
except ImportError:  # pragma: no cover
    pyttsx3 = None

from lmu_race_engineer.config import VoiceAlertSettings
from lmu_race_engineer.models import VoiceAlert


class VoiceAlertEngine:
    def __init__(self, settings: VoiceAlertSettings) -> None:
        self.settings = settings
        self._engine = None
        if self.settings.enabled and pyttsx3 is not None:
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", settings.rate)
            self._engine.setProperty("volume", settings.volume)

    def announce(self, alert: VoiceAlert) -> None:
        if self._engine is None:
            return
        self._engine.say(alert.message)
        self._engine.runAndWait()
