from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from apps.api.config_validation import validate_all
from apps.api.routes.health import router as health_router
from apps.api.routes.metrics import router as metrics_router
from apps.api.routes.passport import router as passport_router
from apps.api.routes.profiles import router as profiles_router
from apps.api.routes.run import limiter
from apps.api.routes.run import router as run_router
from apps.api.routes.ui import router as ui_router
from apps.api.services.errors import error_body
from apps.api.services.observability import log_request_event, record_request_metric


@asynccontextmanager
async def lifespan(_app: FastAPI):
    validate_all()
    yield


app = FastAPI(
    title="AI Vendor Red-Team Passport API",
    version="0.2.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)
app.state.limiter = limiter

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
async def request_size_limit_middleware(request: Request, call_next):
    """Reject oversized request bodies before application processing."""
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size_bytes = int(content_length)
            except ValueError:
                size_bytes = 0
            max_size_bytes = 10 * 1024 * 1024
            if size_bytes > max_size_bytes:
                cid = (request.headers.get("x-correlation-id") or "").strip() or str(uuid.uuid4())
                response = JSONResponse(
                    status_code=413,
                    content=error_body(
                        status_code=413,
                        message="request payload too large",
                        correlation_id=cid,
                        detail=f"maximum request size is {max_size_bytes} bytes",
                    ),
                )
                response.headers["X-Correlation-ID"] = cid
                return response
    return await call_next(request)


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
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    )
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


@app.exception_handler(RateLimitExceeded)
async def handle_rate_limit_error(request: Request, exc: RateLimitExceeded):  # noqa: ARG001
    cid = _correlation_id(request)
    response = JSONResponse(
        status_code=429,
        content=error_body(
            status_code=429,
            message="rate limit exceeded",
            correlation_id=cid,
            detail="too many requests",
        ),
    )
    response.headers["X-Correlation-ID"] = cid
    response.headers["Retry-After"] = "60"
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

