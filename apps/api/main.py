from __future__ import annotations

import time
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from apps.api.routes.health import router as health_router
from apps.api.routes.metrics import router as metrics_router
from apps.api.routes.passport import router as passport_router
from apps.api.routes.profiles import router as profiles_router
from apps.api.routes.run import router as run_router
from apps.api.routes.ui import router as ui_router
from apps.api.services.errors import error_body
from apps.api.services.observability import log_request_event, record_request_metric
from apps.api.services.run_store import reports_dir

app = FastAPI(title="AI Vendor Red-Team Passport API", version="0.1.0")

app.mount("/reports", StaticFiles(directory=str(reports_dir())), name="reports")

app.include_router(health_router)
app.include_router(run_router)
app.include_router(passport_router)
app.include_router(profiles_router)
app.include_router(ui_router)
app.include_router(metrics_router)


def _correlation_id(request: Request) -> str:
    value = str(getattr(request.state, "correlation_id", "") or "").strip()
    return value or str(uuid.uuid4())


def _route_label(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", "")
    return path if isinstance(path, str) and path else request.url.path


def _tenant_actor(request: Request) -> tuple[str, str]:
    ctx = getattr(request.state, "request_context", None)
    tenant_id = str(getattr(ctx, "tenant_id", "") or "")
    actor = str(getattr(ctx, "subject", "") or "")
    return tenant_id, actor


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    cid = (request.headers.get("x-correlation-id") or "").strip() or str(uuid.uuid4())
    request.state.correlation_id = cid

    started = time.perf_counter()
    try:
        response = await call_next(request)
        status_code = int(response.status_code)
    except Exception:
        duration_ms = (time.perf_counter() - started) * 1000.0
        route = _route_label(request)
        tenant_id, actor = _tenant_actor(request)
        record_request_metric(method=request.method, route=route, status_code=500, duration_ms=duration_ms)
        log_request_event(
            correlation_id=cid,
            method=request.method,
            route=route,
            status_code=500,
            duration_ms=duration_ms,
            tenant_id=tenant_id,
            actor=actor,
        )
        raise

    duration_ms = (time.perf_counter() - started) * 1000.0
    route = _route_label(request)
    tenant_id, actor = _tenant_actor(request)
    record_request_metric(method=request.method, route=route, status_code=status_code, duration_ms=duration_ms)
    log_request_event(
        correlation_id=cid,
        method=request.method,
        route=route,
        status_code=status_code,
        duration_ms=duration_ms,
        tenant_id=tenant_id,
        actor=actor,
    )
    response.headers["X-Correlation-ID"] = cid
    return response


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError):
    cid = _correlation_id(request)
    body = error_body(
        status_code=422,
        message="request validation failed",
        correlation_id=cid,
        detail=exc.errors(),
    )
    response = JSONResponse(status_code=422, content=body)
    response.headers["X-Correlation-ID"] = cid
    return response


@app.exception_handler(HTTPException)
@app.exception_handler(StarletteHTTPException)
async def handle_http_error(request: Request, exc: HTTPException):
    cid = _correlation_id(request)
    detail = exc.detail
    if isinstance(detail, str):
        message = detail
    else:
        message = "request failed"
    body = error_body(
        status_code=int(exc.status_code),
        message=message,
        correlation_id=cid,
        detail=detail,
    )
    response = JSONResponse(status_code=int(exc.status_code), content=body)
    response.headers["X-Correlation-ID"] = cid
    return response


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception):  # noqa: ARG001
    cid = _correlation_id(request)
    body = error_body(
        status_code=500,
        message="internal server error",
        correlation_id=cid,
    )
    response = JSONResponse(status_code=500, content=body)
    response.headers["X-Correlation-ID"] = cid
    return response
