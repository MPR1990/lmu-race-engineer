from __future__ import annotations

from datetime import datetime, timedelta
import unittest

from lmu_race_engineer.alerts import AlertManager
from lmu_race_engineer.models import Recommendation


class AlertManagerTest(unittest.TestCase):
    def test_high_priority_live_recommendation_creates_alert(self) -> None:
        manager = AlertManager(cooldown_seconds=30)
        recommendation = Recommendation(
            category="live",
            title="Rear tires overheating",
            reason="Rear tires are too hot.",
            confidence=0.9,
            priority="high",
            action_timing="change_now",
        )

        alerts = manager.build_alerts([recommendation], datetime(2026, 1, 1, 12, 0, 0))
        self.assertEqual(1, len(alerts))
        self.assertEqual("Rear tires overheating", alerts[0].title)

        second = manager.build_alerts([recommendation], datetime(2026, 1, 1, 12, 0, 10))
        self.assertEqual([], second)

        third = manager.build_alerts([recommendation], datetime(2026, 1, 1, 12, 0, 31))
        self.assertEqual(1, len(third))


if __name__ == "__main__":
    unittest.main()
