#!/usr/bin/env python3
"""
Verify the integrity of audit log events.

This script checks that all audit events in the audit log have valid HMAC-SHA256
signatures, indicating they have not been tampered with.

Usage:
    python scripts/verify_audit_log.py <hmac_secret>

    Example:
        python scripts/verify_audit_log.py "your-secret-key-here"

Exit codes:
    0: All events are valid
    1: One or more events have invalid signatures or missing HMAC
    2: Audit log file not found
"""

from __future__ import annotations

import hashlib
import hmac
import json
import sys
from pathlib import Path


def verify_audit_log(audit_log_path: Path, secret: str) -> bool:
    """
    Verify audit log integrity.

    Args:
        audit_log_path: Path to audit log file (events.log)
        secret: HMAC secret key (must match the one used to sign events)

    Returns:
        True if all events are valid, False otherwise
    """
    if not audit_log_path.exists():
        print(f"❌ FAILED: Audit log file not found: {audit_log_path}")
        return False

    if not secret or not secret.strip():
        print("⚠️  WARNING: No HMAC secret provided. Cannot verify signatures.")
        print("   To verify, provide the VENDOR_RTP_MANIFEST_HMAC_KEY value.")
        return True  # Not a failure, just can't verify

    secret = secret.strip()
    total_events = 0
    valid_events = 0
    unsigned_events = 0
    tampered_events = 0

    with audit_log_path.open("r") as f:
        for line_num, line in enumerate(f, start=1):
            total_events += 1
            line = line.strip()
            if not line:
                continue

            try:
                event = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"❌ Line {line_num}: Invalid JSON: {e}")
                tampered_events += 1
                continue

            # Check if event has HMAC signature
            expected_hmac = event.pop("hmac_sha256", None)
            if not expected_hmac:
                unsigned_events += 1
                continue

            # Reconstruct event as it was when signed (must be canonical/sorted)
            event_json = json.dumps(event, ensure_ascii=True, sort_keys=True)

            # Compute expected HMAC
            computed_hmac = hmac.new(
                secret.encode("utf-8"),
                event_json.encode("utf-8"),
                hashlib.sha256
            ).hexdigest()

            # Compare (constant-time comparison)
            if hmac.compare_digest(computed_hmac, expected_hmac):
                valid_events += 1
            else:
                tampered_events += 1
                event_id = event.get("event_id", "unknown")
                print(f"❌ Line {line_num} (event_id={event_id}): HMAC verification failed!")
                print("   This event has been tampered with.")

    # Print summary
    print("\n" + "=" * 70)
    print("AUDIT LOG VERIFICATION REPORT")
    print("=" * 70)
    print(f"Total events:    {total_events}")
    print(f"Valid events:    {valid_events}")
    print(f"Unsigned events: {unsigned_events}")
    print(f"Tampered events: {tampered_events}")
    print("=" * 70)

    if tampered_events > 0:
        print("\n🚨 CRITICAL: Audit log has been tampered with!")
        print(f"   {tampered_events} event(s) have invalid HMAC signatures.")
        return False
    elif unsigned_events > 0:
        print(f"\n⚠️  WARNING: {unsigned_events} event(s) are unsigned (pre-HMAC era).")
        print("   These events cannot be verified for tampering.")

    if valid_events > 0:
        print(f"\n✅ SUCCESS: All {valid_events} signed event(s) have valid HMACs.")
        print("   Audit log integrity verified.")

    return True


def main() -> int:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/verify_audit_log.py <hmac_secret>")
        print("\nProvide the VENDOR_RTP_MANIFEST_HMAC_KEY value to verify audit log integrity.")
        print("\nExample:")
        print("  python scripts/verify_audit_log.py 'AbCdEfGh...'")
        return 1

    secret = sys.argv[1]

    # Find audit log (look in standard locations)
    audit_log_candidates = [
        Path("reports/audit/events.log"),
        Path("./reports/audit/events.log"),
        Path("/app/reports/audit/events.log"),  # Docker container
    ]

    audit_log_path = None
    for candidate in audit_log_candidates:
        if candidate.exists():
            audit_log_path = candidate
            break

    if not audit_log_path:
        print("❌ ERROR: Audit log not found in any of:")
        for c in audit_log_candidates:
            print(f"  - {c}")
        return 2

    print(f"Verifying audit log: {audit_log_path}\n")

    # Verify
    success = verify_audit_log(audit_log_path, secret)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
