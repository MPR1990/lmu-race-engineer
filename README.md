# lmu-race-engineer

Race engineer desktop application for Le Mans Ultimate. It is structured around live telemetry ingestion, lap analysis, setup recommendations, persistence, and real-time voice alerts.

## Current status

This repository now contains the first vertical slice of the app:

- Python desktop app with a Tkinter dashboard
- `pyttsx3` voice-alert integration
- telemetry source abstraction with shared-memory and REST placeholders
- demo telemetry stream for development
- lap tracking and fuel projection
- rule-based live and pit recommendation engine
- SQLite-backed session storage

## Project layout

```text
.
├── pyproject.toml
├── src/lmu_race_engineer
│   ├── alerts
│   ├── analysis
│   ├── recommendations
│   ├── storage
│   ├── telemetry
│   ├── ui
│   ├── app.py
│   ├── config.py
│   └── models.py
└── tests
```

## Run

Install dependencies:

```bash
python -m pip install -e .
```

Start the desktop app:

```bash
python -m lmu_race_engineer.app
```

The current default uses the built-in demo telemetry source so the dashboard and alert flow can be exercised without a live game connection.

## Configuration

The app accepts an optional JSON config file:

```bash
python -m lmu_race_engineer.app --config config.example.json
```

Supported config sections:

- `telemetry`: source mode, shared memory name, REST base URL, poll interval
- `voice`: enable/disable speech, voice rate, volume, alert cooldown
- `monitoring`: tire, brake, fuel, and pace thresholds
- `storage_path`: SQLite file location

Use `config.example.json` as the starting point for your own config.

## Next implementation targets

1. Replace the shared-memory placeholder with the Le Mans Ultimate memory map.
2. Implement the native telemetry REST client for session and vehicle metadata.
3. Add track/car-specific baselines and richer recommendation rules.
4. Expand the UI with stint summaries and lap-comparison views.
