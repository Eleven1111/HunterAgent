from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any


logger = logging.getLogger("huntflow.api")


def configure_logging() -> None:
    if logger.handlers:
        return
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def log_event(event_type: str, **payload: Any) -> None:
    logger.info(json.dumps({"event_type": event_type, **payload}, ensure_ascii=False, default=str))


@dataclass
class RequestMetrics:
    total_requests: int = 0
    status_counts: dict[str, int] = field(default_factory=dict)
    route_counts: dict[str, int] = field(default_factory=dict)

    def record(self, *, method: str, path: str, status_code: int) -> None:
        self.total_requests += 1
        status_key = str(status_code)
        route_key = f"{method} {path}"
        self.status_counts[status_key] = self.status_counts.get(status_key, 0) + 1
        self.route_counts[route_key] = self.route_counts.get(route_key, 0) + 1

    def render_prometheus(self) -> str:
        lines = [
            "# HELP huntflow_requests_total Total HTTP requests handled by the API",
            "# TYPE huntflow_requests_total counter",
            f"huntflow_requests_total {self.total_requests}",
            "# HELP huntflow_requests_by_status_total HTTP requests by response status",
            "# TYPE huntflow_requests_by_status_total counter",
        ]
        for status_code, count in sorted(self.status_counts.items()):
            lines.append(f'huntflow_requests_by_status_total{{status="{status_code}"}} {count}')
        lines.extend(
            [
                "# HELP huntflow_requests_by_route_total HTTP requests by method/path",
                "# TYPE huntflow_requests_by_route_total counter",
            ]
        )
        for route_key, count in sorted(self.route_counts.items()):
            method, path = route_key.split(" ", 1)
            lines.append(
                f'huntflow_requests_by_route_total{{method="{method}",path="{path}"}} {count}'
            )
        return "\n".join(lines) + "\n"
