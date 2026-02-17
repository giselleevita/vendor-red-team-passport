from __future__ import annotations

import json
import logging
from threading import Lock


_log = logging.getLogger("vendor_rtp.http")


class _MetricsStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._request_count: dict[tuple[str, str, int], int] = {}
        self._duration_total_ms: dict[tuple[str, str, int], float] = {}

    def record(self, *, method: str, route: str, status_code: int, duration_ms: float) -> None:
        key = (method.upper(), route, int(status_code))
        with self._lock:
            self._request_count[key] = self._request_count.get(key, 0) + 1
            self._duration_total_ms[key] = self._duration_total_ms.get(key, 0.0) + float(duration_ms)

    def snapshot(self) -> dict:
        with self._lock:
            items = sorted(self._request_count.items(), key=lambda kv: kv[0])
            counts = [
                {"method": m, "route": r, "status_code": s, "value": v}
                for (m, r, s), v in items
            ]
            durations = [
                {
                    "method": m,
                    "route": r,
                    "status_code": s,
                    "sum_ms": round(self._duration_total_ms.get((m, r, s), 0.0), 3),
                }
                for (m, r, s), _ in items
            ]
        return {"http_requests_total": counts, "http_request_duration_ms": durations}

    def to_prometheus(self) -> str:
        s = self.snapshot()
        lines = [
            "# HELP http_requests_total Total HTTP requests by method, route and status.",
            "# TYPE http_requests_total counter",
        ]
        for row in s["http_requests_total"]:
            lines.append(
                'http_requests_total{method="%s",route="%s",status="%s"} %s'
                % (row["method"], row["route"], row["status_code"], row["value"])
            )
        lines.extend(
            [
                "# HELP http_request_duration_ms Total request duration in milliseconds by method, route and status.",
                "# TYPE http_request_duration_ms counter",
            ]
        )
        for row in s["http_request_duration_ms"]:
            lines.append(
                'http_request_duration_ms{method="%s",route="%s",status="%s"} %s'
                % (row["method"], row["route"], row["status_code"], row["sum_ms"])
            )
        return "\n".join(lines) + "\n"

    def reset(self) -> None:
        with self._lock:
            self._request_count.clear()
            self._duration_total_ms.clear()


_STORE = _MetricsStore()


def record_request_metric(*, method: str, route: str, status_code: int, duration_ms: float) -> None:
    _STORE.record(method=method, route=route, status_code=status_code, duration_ms=duration_ms)


def metrics_snapshot() -> dict:
    return _STORE.snapshot()


def metrics_prometheus_text() -> str:
    return _STORE.to_prometheus()


def reset_metrics() -> None:
    _STORE.reset()


def log_request_event(
    *,
    correlation_id: str,
    method: str,
    route: str,
    status_code: int,
    duration_ms: float,
    tenant_id: str,
    actor: str,
) -> None:
    payload = {
        "event": "http_request",
        "correlation_id": correlation_id,
        "method": method,
        "route": route,
        "status_code": status_code,
        "duration_ms": round(duration_ms, 3),
        "tenant_id": tenant_id,
        "actor": actor,
    }
    _log.info(json.dumps(payload, ensure_ascii=True))

