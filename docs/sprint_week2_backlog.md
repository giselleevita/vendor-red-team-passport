# Sprint Backlog (Woche 3-4): Async Execution + Operability

Status: `in-progress`

## Sprint-Status (laufend)
- `W2-01` done: Async job queue for runs (`POST /runs` + `GET /runs/jobs/{job_id}`)
- `W2-02` done: DB-backed job metadata via repository abstraction (`file|sql`)
- `W2-03` done: Worker separation via external executor mode + worker script
- `W2-04` done: Failure handling with retries, backoff, dead-letter state
- `W2-05` pending: Job cancellation API

## `W2-01` Ergebnis
- `/runs` queues jobs instead of blocking request lifecycle.
- Job state endpoint added at `/runs/jobs/{job_id}`.
- Tenant-scoped job read access enforced.
- Test coverage added in `tests/api/test_run_jobs.py`.

## Nächster geplanter Slice (`W2-02`)
- Implemented:
  - `JOB_STORE_BACKEND=file|sql`
  - `JOB_STORE_DSN=sqlite:///...` and `postgresql://...`
  - relational `jobs` schema with upsert/read paths
  - file backend retained as compatibility fallback

## Nächster geplanter Slice (`W2-03`)
- Implemented:
  - `RUN_EXECUTOR_MODE=inline|external`
  - `scripts/worker_run_jobs.py` for external job processing
  - API path remains queue-only in external mode

## Nächster geplanter Slice (`W2-04`)
- Implemented:
  - `attempt_count`, `max_attempts`, `next_attempt_at`
  - exponential backoff with configurable caps
  - terminal `dead_letter` status after final failed attempt
  - worker only executes queued jobs that are ready by `next_attempt_at`

## Nächster geplanter Slice (`W2-05`)
- Job cancellation endpoint and cancellation-safe worker behavior.
- Cancelled jobs must never transition back to running.
