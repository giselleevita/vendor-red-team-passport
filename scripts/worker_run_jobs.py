from __future__ import annotations

import argparse
import time
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.services.job_executor import execute_job
from apps.api.services.jobs import list_jobs


def run_once(limit: int) -> int:
    queued = list_jobs(status="queued", limit=limit)
    for job in queued:
        job_id = str(job.get("job_id", "")).strip()
        if not job_id:
            continue
        execute_job(job_id)
    return len(queued)


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
