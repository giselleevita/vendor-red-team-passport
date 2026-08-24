#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import time

import jwt


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
    parser.add_argument("--issuer", default=os.environ.get("AUTH_JWT_ISSUER", "vendor-rtp-local"))
    parser.add_argument("--audience", default=os.environ.get("AUTH_JWT_AUDIENCE", "vendor-rtp-api"))
    args = parser.parse_args()
    secret = str(args.secret or "").strip()
    if len(secret) < 32:
        parser.error("--secret or AUTH_JWT_HS256_SECRET must contain at least 32 characters")
    now = int(time.time())
    payload = {
        "sub": args.subject,
        "tenant_id": args.tenant_id,
        "roles": _roles(args.roles),
        "iat": now,
        "exp": now + max(60, int(args.ttl_seconds)),
        "iss": args.issuer,
        "aud": args.audience,
    }
    print(jwt.encode(payload, secret, algorithm="HS256"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
