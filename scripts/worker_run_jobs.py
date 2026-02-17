from __future__ import annotations

import argparse
from datetime import datetime, timezone
import time
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.services.job_executor import execute_job
from apps.api.services.jobs import list_jobs


def _is_ready(job: dict) -> bool:
    nxt = str(job.get("next_attempt_at", "")).strip()
    if not nxt:
        return True
    try:
        eta = datetime.fromisoformat(nxt)
        if eta.tzinfo is None:
            eta = eta.replace(tzinfo=timezone.utc)
        return datetime.now(tz=timezone.utc) >= eta
    except Exception:
        return True


def run_once(limit: int) -> int:
    queued = list_jobs(status="queued", limit=limit)
    processed = 0
    for job in queued:
        if not _is_ready(job):
            continue
        job_id = str(job.get("job_id", "")).strip()
        if not job_id:
            continue
        execute_job(job_id)
        processed += 1
    return processed


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="Process queued jobs once and exit")
    ap.add_argument("--limit", type=int, default=20, help="Max jobs per polling cycle")
    ap.add_argument("--sleep-seconds", type=float, default=1.5, help="Polling interval in continuous mode")
    args = ap.parse_args()

    if args.once:
        n = run_once(args.limit)
        print(f"worker_processed={n}")
        return

    while True:
        n = run_once(args.limit)
        if n == 0:
            time.sleep(max(0.2, args.sleep_seconds))


if __name__ == "__main__":
    main()
