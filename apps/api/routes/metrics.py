from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse

from apps.api.services.auth import RequestContext, require_roles
from apps.api.services.observability import metrics_prometheus_text, metrics_snapshot

router = APIRouter()


@router.get("/metrics")
def get_metrics(
    fmt: str = Query(default="prom", pattern="^(prom|json)$"),
    ctx: RequestContext = Depends(require_roles("admin", "auditor")),
):
    _ = ctx
    if fmt == "json":
        return metrics_snapshot()
    return PlainTextResponse(metrics_prometheus_text(), media_type="text/plain; version=0.0.4")

