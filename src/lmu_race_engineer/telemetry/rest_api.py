from __future__ import annotations


class RestApiClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def get_session_summary(self) -> dict[str, str]:
        raise NotImplementedError(
            "REST API integration is not implemented yet. Add LMU telemetry endpoints here."
        )
