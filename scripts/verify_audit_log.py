#!/usr/bin/env python3
"""Verify audit.v2 authentication, sequence, chain links, and tail checkpoint."""

from __future__ import annotations

import argparse
from pathlib import Path

from apps.api.services.audit_verify import verify_audit_log

__all__ = ["verify_audit_log"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("secret")
    parser.add_argument("path", nargs="?", type=Path, default=Path("reports/audit/events.log"))
    args = parser.parse_args()
    valid = verify_audit_log(args.path, args.secret)
    print("audit chain valid" if valid else "audit chain invalid")
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
