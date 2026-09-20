from __future__ import annotations

from lmu_race_engineer.analysis import AnalysisSnapshot, HandlingAssessment
from lmu_race_engineer.config import MonitoringTargets
from lmu_race_engineer.models import Recommendation, TelemetrySnapshot


class SetupRecommendationEngine:
    def __init__(self, targets: MonitoringTargets) -> None:
        self.targets = targets

    def evaluate(
        self,
        snapshot: TelemetrySnapshot,
        analysis: AnalysisSnapshot,
        handling: HandlingAssessment | None = None,
    ) -> list[Recommendation]:
        recommendations: list[Recommendation] = []
        confirmed_exit_oversteer = (
            handling is None
            or (
                handling.condition == "oversteer"
                and handling.phase == "exit"
                and handling.evidence_count >= 3
            )
        )
        if analysis.rear_tire_temp_avg_c > self.targets.tire_temp_max_c and confirmed_exit_oversteer:
            recommendations.append(
                Recommendation(
                    category="live",
                    title="Rear tires overheating",
                    reason="Rear tire temperatures are above target, suggesting excess slip on throttle exit.",
                    confidence=0.82,
                    priority="high",
                    action_timing="change_now",
                )
            )
            recommendations.append(
                Recommendation(
                    category="pit",
                    title="Review rear pressures or camber",
                    reason="Persistent rear heat points to pressure or camber changes for the next stop.",
                    confidence=0.69,
                    priority="medium",
                    action_timing="next_stop",
                )
            )
        if handling is not None and handling.evidence_count >= 3:
            if handling.condition == "understeer" and handling.phase in ("entry", "mid_corner"):
                recommendations.append(
                    Recommendation(
                        category="pit",
                        title="Reduce front-end understeer",
                        reason=(
                            f"Repeated {handling.phase.replace('_', ' ')} understeer: "
                            + "; ".join(handling.evidence)
                            + ". Review front anti-roll stiffness, front pressure, and front camber."
                        ),
                        confidence=handling.confidence,
                        priority="medium",
                        action_timing="next_stop",
                    )
                )
            elif handling.condition == "oversteer" and handling.phase == "exit":
                recommendations.append(
                    Recommendation(
                        category="pit",
                        title="Stabilize corner exit oversteer",
                        reason=(
                            "Repeated exit oversteer under throttle: "
                            + "; ".join(handling.evidence)
                            + ". Review rear anti-roll stiffness, rear pressure, and rear aero."
                        ),
                        confidence=handling.confidence,
                        priority="medium",
                        action_timing="next_stop",
                    )
                )
            elif handling.condition == "braking_instability":
                recommendations.append(
                    Recommendation(
                        category="live",
                        title="Braking instability detected",
                        reason=(
                            "; ".join(handling.evidence)
                            + ". Review brake release technique and brake bias before changing the rear setup."
                        ),
                        confidence=handling.confidence,
                        priority="medium",
                        action_timing="observe_more",
                    )
                )
        if analysis.front_brake_temp_c > self.targets.brake_temp_max_c:
            recommendations.append(
                Recommendation(
                    category="live",
                    title="Front brakes overheating",
                    reason="Front brake temperature is above the target range. Use less trail braking or move brake bias rearward.",
                    confidence=0.8,
                    priority="high",
                    action_timing="change_now",
                )
            )
        if analysis.traction_event_count >= self.targets.repeated_event_threshold:
            recommendations.append(
                Recommendation(
                    category="live",
                    title="Increase traction control",
                    reason=(
                        f"Repeated wheelspin events suggest raising traction control one step from "
                        f"the current level {snapshot.traction_control_level}."
                    ),
                    confidence=0.76,
                    priority="high",
                    action_timing="change_now",
                )
            )
        if analysis.lockup_event_count >= self.targets.repeated_event_threshold:
            recommendations.append(
                Recommendation(
                    category="live",
                    title="Increase ABS or reduce brake bias",
                    reason=(
                        f"Repeated lockups point to a braking stability issue with ABS {snapshot.abs_level} "
                        f"and brake bias at {snapshot.brake_bias_percent:.1f}%."
                    ),
                    confidence=0.72,
                    priority="medium",
                    action_timing="change_now",
                )
            )
        if (
            analysis.estimated_laps_remaining is not None
            and analysis.estimated_laps_remaining < self.targets.fuel_reserve_laps
        ):
            recommendations.append(
                Recommendation(
                    category="pit",
                    title="Fuel target risk",
                    reason="Projected fuel remaining is below the reserve target.",
                    confidence=0.88,
                    priority="high",
                    action_timing="next_stop",
                )
            )
        if (
            analysis.last_lap is not None
            and analysis.best_lap is not None
            and analysis.last_lap.lap_time_seconds - analysis.best_lap.lap_time_seconds
            > self.targets.pace_drop_threshold_seconds
        ):
            recommendations.append(
                Recommendation(
                    category="live",
                    title="Pace has dropped",
                    reason="Recent lap time is off the best by more than the pace-drop threshold.",
                    confidence=0.67,
                    priority="medium",
                    action_timing="observe_more",
                )
            )
        return recommendations
