#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import time


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _token(payload: dict, secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64url(json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    payload_b64 = _b64url(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{_b64url(signature)}"


def _roles(raw: str) -> list[str]:
    roles = [item.strip() for item in raw.split(",") if item.strip()]
    return roles or ["viewer"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a local HS256 JWT for demo and test API calls.")
    parser.add_argument("--secret", default=os.environ.get("AUTH_JWT_HS256_SECRET", ""))
    parser.add_argument("--subject", default="local-reviewer")
    parser.add_argument("--tenant-id", default=os.environ.get("AUTH_DEFAULT_TENANT_ID", "default"))
    parser.add_argument("--roles", default="viewer,operator,auditor,admin")
    parser.add_argument("--ttl-seconds", type=int, default=3600)
    parser.add_argument("--issuer", default=os.environ.get("AUTH_JWT_ISSUER", ""))
    parser.add_argument("--audience", default=os.environ.get("AUTH_JWT_AUDIENCE", ""))
    args = parser.parse_args()

    secret = str(args.secret or "").strip()
    if not secret:
        parser.error("--secret or AUTH_JWT_HS256_SECRET is required")

    payload = {
        "sub": args.subject,
        "tenant_id": args.tenant_id,
        "roles": _roles(args.roles),
        "exp": int(time.time()) + max(60, int(args.ttl_seconds)),
    }
    if args.issuer:
        payload["iss"] = args.issuer
    if args.audience:
        payload["aud"] = args.audience

    print(_token(payload, secret))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
