from __future__ import annotations

from dataclasses import dataclass, field

try:
    import tkinter as tk
except ImportError:  # pragma: no cover
    tk = None

from lmu_race_engineer.models import Recommendation, VoiceAlert


@dataclass(slots=True)
class DashboardState:
    current_lap_text: str = "-"
    delta_text: str = "-"
    fuel_text: str = "-"
    tire_text: str = "-"
    brake_text: str = "-"
    recommendations: list[Recommendation] = field(default_factory=list)
    alerts: list[VoiceAlert] = field(default_factory=list)


class RaceEngineerDashboard:
    def __init__(self) -> None:
        if tk is None:
            raise RuntimeError("Tkinter is required for the desktop dashboard.")
        self.root = tk.Tk()
        self.root.title("LMU Race Engineer")
        self.root.geometry("920x560")

        self.current_lap_var = tk.StringVar(value="-")
        self.delta_var = tk.StringVar(value="-")
        self.fuel_var = tk.StringVar(value="-")
        self.tire_var = tk.StringVar(value="-")
        self.brake_var = tk.StringVar(value="-")
        self._build()

    def _build(self) -> None:
        metrics = tk.Frame(self.root, padx=16, pady=16)
        metrics.pack(fill=tk.X)
        for idx, (label, variable) in enumerate(
            [
                ("Lap", self.current_lap_var),
                ("Delta", self.delta_var),
                ("Fuel", self.fuel_var),
                ("Tires", self.tire_var),
                ("Brakes", self.brake_var),
            ]
        ):
            block = tk.LabelFrame(metrics, text=label, padx=12, pady=12)
            block.grid(row=0, column=idx, padx=6, sticky="nsew")
            tk.Label(block, textvariable=variable, font=("Arial", 16, "bold"), wraplength=150).pack()
            metrics.grid_columnconfigure(idx, weight=1)

        body = tk.Frame(self.root, padx=16, pady=12)
        body.pack(fill=tk.BOTH, expand=True)

        recommendations = tk.LabelFrame(body, text="Recommendations", padx=12, pady=12)
        recommendations.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        recommendations_scrollbar = tk.Scrollbar(recommendations)
        recommendations_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.recommendations_text = tk.Text(
            recommendations,
            font=("Arial", 12),
            wrap=tk.WORD,
            yscrollcommand=recommendations_scrollbar.set,
            state=tk.DISABLED,
        )
        self.recommendations_text.pack(fill=tk.BOTH, expand=True)
        recommendations_scrollbar.config(command=self.recommendations_text.yview)

        alerts = tk.LabelFrame(body, text="Alert History", padx=12, pady=12)
        alerts.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))
        alerts_scrollbar = tk.Scrollbar(alerts)
        alerts_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.alerts_text = tk.Text(
            alerts,
            font=("Arial", 12),
            wrap=tk.WORD,
            yscrollcommand=alerts_scrollbar.set,
            state=tk.DISABLED,
        )
        self.alerts_text.pack(fill=tk.BOTH, expand=True)
        alerts_scrollbar.config(command=self.alerts_text.yview)

    def render(self, state: DashboardState) -> None:
        self.current_lap_var.set(state.current_lap_text)
        self.delta_var.set(state.delta_text)
        self.fuel_var.set(state.fuel_text)
        self.tire_var.set(state.tire_text)
        self.brake_var.set(state.brake_text)
        recommendations = (
            "\n\n".join(
                f"[{item.priority.upper()}] {item.title}\n{item.reason}\nConfidence: {item.confidence:.0%}"
                for item in state.recommendations[:5]
            )
            or "No recommendations yet."
        )
        alerts = (
            "\n\n".join(
                f"{alert.created_at.strftime('%H:%M:%S')} - {alert.title}\n{alert.message}"
                for alert in state.alerts[:5]
            )
            or "No alerts triggered."
        )
        self._set_text(self.recommendations_text, recommendations)
        self._set_text(self.alerts_text, alerts)

    def _set_text(self, widget, value: str) -> None:
        widget.config(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, value)
        widget.config(state=tk.DISABLED)
