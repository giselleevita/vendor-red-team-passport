# Sprint Backlog (Woche 3-4): Async Execution + Operability

Status: `in-progress`

## Sprint-Status (laufend)
- `W2-01` done: Async job queue for runs (`POST /runs` + `GET /runs/jobs/{job_id}`)
- `W2-02` pending: DB-backed job metadata (PostgreSQL)
- `W2-03` pending: Worker separation (Celery/Redis)
- `W2-04` pending: Failure handling (retry policy + dead-letter)
- `W2-05` pending: Job cancellation API

## `W2-01` Ergebnis
- `/runs` queues jobs instead of blocking request lifecycle.
- Job state endpoint added at `/runs/jobs/{job_id}`.
- Tenant-scoped job read access enforced.
- Test coverage added in `tests/api/test_run_jobs.py`.

## Nächster geplanter Slice (`W2-02`)
- Introduce `jobs` relational schema in PostgreSQL.
- Persist and query job states via repository abstraction.
- Keep file-based backend as temporary fallback via feature flag.
