from __future__ import annotations

from datetime import datetime, timedelta

from lmu_race_engineer.models import Recommendation, VoiceAlert


class AlertManager:
    def __init__(self, cooldown_seconds: int) -> None:
        self.cooldown_seconds = cooldown_seconds
        self.history: list[VoiceAlert] = []
        self._last_sent_at: dict[str, datetime] = {}

    def build_alerts(
        self,
        recommendations: list[Recommendation],
        now: datetime,
        lap_number: int | None = None,
    ) -> list[VoiceAlert]:
        alerts: list[VoiceAlert] = []
        for recommendation in recommendations:
            if recommendation.priority != "high" or recommendation.category != "live":
                continue
            previous = self._last_sent_at.get(recommendation.title)
            if previous and now - previous < timedelta(seconds=self.cooldown_seconds):
                continue
            alert = VoiceAlert(
                title=recommendation.title,
                message=recommendation.reason,
                priority="high",
                created_at=now,
                lap_number=lap_number,
            )
            self._last_sent_at[recommendation.title] = now
            self.history.insert(0, alert)
            alerts.append(alert)
        return alerts
