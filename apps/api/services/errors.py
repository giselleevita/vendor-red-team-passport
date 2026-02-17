from __future__ import annotations


def error_code_for_status(status_code: int) -> str:
    mapping = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        422: "validation_error",
        500: "internal_error",
    }
    return mapping.get(int(status_code), f"http_{int(status_code)}")


def error_body(*, status_code: int, message: str, correlation_id: str, detail=None) -> dict:
    return {
        "code": error_code_for_status(status_code),
        "message": message,
        "correlation_id": correlation_id,
        "detail": detail if detail is not None else message,
    }

