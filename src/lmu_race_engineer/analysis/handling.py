from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from lmu_race_engineer.models import TelemetrySnapshot


HandlingPhase = Literal["braking", "entry", "mid_corner", "exit", "straight"]
HandlingCondition = Literal["understeer", "oversteer", "braking_instability", "none"]


@dataclass(slots=True)
class HandlingAssessment:
    phase: HandlingPhase
    condition: HandlingCondition
    confidence: float
    evidence: tuple[str, ...]
    evidence_count: int
    grip_data_available: bool


class HandlingAnalyzer:
    def __init__(self, confirmation_samples: int = 3) -> None:
        self.confirmation_samples = confirmation_samples
        self._evidence_counts: dict[tuple[HandlingPhase, HandlingCondition], int] = {}

    def update(self, snapshot: TelemetrySnapshot) -> HandlingAssessment:
        phase = self._phase(snapshot)
        grip_data_available = self._has_grip_data(snapshot)
        condition, confidence, evidence = self._classify(snapshot, phase, grip_data_available)

        if condition == "none":
            return HandlingAssessment(phase, condition, 0.0, (), 0, grip_data_available)

        key = (phase, condition)
        self._evidence_counts[key] = self._evidence_counts.get(key, 0) + 1
        evidence_count = self._evidence_counts[key]
        return HandlingAssessment(
            phase=phase,
            condition=condition,
            confidence=confidence,
            evidence=evidence,
            evidence_count=evidence_count,
            grip_data_available=grip_data_available,
        )

    def _phase(self, snapshot: TelemetrySnapshot) -> HandlingPhase:
        steering = abs(snapshot.steering_input)
        if snapshot.brake_input >= 0.25 and snapshot.throttle_input <= 0.25:
            return "braking"
        if snapshot.brake_input >= 0.1 and steering >= 0.1:
            return "entry"
        if snapshot.throttle_input >= 0.35 and snapshot.brake_input <= 0.1 and steering >= 0.1:
            return "exit"
        if steering >= 0.1 and snapshot.brake_input < 0.1:
            return "mid_corner"
        return "straight"

    def _classify(
        self,
        snapshot: TelemetrySnapshot,
        phase: HandlingPhase,
        grip_data_available: bool,
    ) -> tuple[HandlingCondition, float, tuple[str, ...]]:
        if phase == "straight":
            return "none", 0.0, ()

        front_temps = self._average(snapshot.tire_temperatures_c, ("front_left", "front_right"))
        rear_temps = self._average(snapshot.tire_temperatures_c, ("rear_left", "rear_right"))
        evidence: list[str] = []

        front_slip = self._average(snapshot.tire_grip_fraction, ("front_left", "front_right"))
        rear_slip = self._average(snapshot.tire_grip_fraction, ("rear_left", "rear_right"))
        if grip_data_available:
            if phase in ("entry", "mid_corner") and front_slip >= 0.25 and front_slip > rear_slip + 0.05:
                evidence.append(f"front tire sliding fraction {front_slip:.2f} exceeds rear {rear_slip:.2f}")
                return "understeer", 0.78, tuple(evidence)
            if phase == "exit" and rear_slip >= 0.25 and rear_slip > front_slip + 0.05:
                evidence.append(f"rear tire sliding fraction {rear_slip:.2f} exceeds front {front_slip:.2f}")
                return "oversteer", 0.8, tuple(evidence)

        front_force = self._average_abs(snapshot.lateral_tire_force_n, ("front_left", "front_right"))
        rear_force = self._average_abs(snapshot.lateral_tire_force_n, ("rear_left", "rear_right"))
        if front_force > 0 and rear_force > 0:
            if (
                phase in ("entry", "mid_corner")
                and front_force < rear_force * 0.7
                and abs(snapshot.steering_input) >= 0.2
            ):
                evidence.append(f"front lateral force {front_force:.0f}N is low for steering demand")
                return "understeer", 0.6, tuple(evidence)
            if phase == "exit" and rear_force < front_force * 0.7 and snapshot.throttle_input >= 0.5:
                evidence.append(f"rear lateral force {rear_force:.0f}N falls during throttle application")
                return "oversteer", 0.62, tuple(evidence)

        temperature_delta = rear_temps - front_temps
        if phase == "braking" and temperature_delta > 8.0:
            evidence.append(f"rear tires are {temperature_delta:.1f}C hotter during braking")
            if snapshot.lockup_events or snapshot.brake_input >= 0.6:
                evidence.append("brake input or lockup activity is present")
                return "braking_instability", 0.58, tuple(evidence)
        if phase in ("entry", "mid_corner") and temperature_delta < -8.0 and abs(snapshot.steering_input) >= 0.2:
            evidence.append(f"front tires are {abs(temperature_delta):.1f}C hotter than rear")
            return "understeer", 0.48, tuple(evidence)
        if phase == "exit" and temperature_delta > 10.0 and snapshot.throttle_input >= 0.5:
            evidence.append(f"rear tires are {temperature_delta:.1f}C hotter under throttle")
            return "oversteer", 0.5, tuple(evidence)

        return "none", 0.0, ()

    def is_confirmed(self, assessment: HandlingAssessment) -> bool:
        return assessment.evidence_count >= self.confirmation_samples

    @staticmethod
    def _has_grip_data(snapshot: TelemetrySnapshot) -> bool:
        return any(value > 0.01 for value in snapshot.tire_grip_fraction.values())

    @staticmethod
    def _average(values: dict[str, float], keys: tuple[str, str]) -> float:
        return sum(values.get(key, 0.0) for key in keys) / len(keys)

    @staticmethod
    def _average_abs(values: dict[str, float], keys: tuple[str, str]) -> float:
        return sum(abs(values.get(key, 0.0)) for key in keys) / len(keys)
