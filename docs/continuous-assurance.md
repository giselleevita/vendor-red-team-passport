# Continuous assurance in v0.6

An approved assessment may pin one completed Passport run as its explicit baseline. A later run is comparable only when its evaluator, taxonomy, and suite versions are compatible. Missing or incompatible evidence produces `UNKNOWN`, which never satisfies the assurance gate.

## Operating model

1. Approve an assessment and set its baseline with an auditor or administrator identity.
2. Create a tenant-scoped schedule referencing a packaged profile and IANA timezone.
3. Run the existing worker. It claims due schedules, creates deterministic jobs, and safely advances the schedule.
4. Successful reassessments are compared with the pinned baseline and evaluated against the selected packaged policy.
5. Failures, unknown results, reassessment errors, and expired approvals enter the operational portfolio and may emit signed webhooks.

Run the worker once with `python scripts/worker_run_jobs.py --once`, or continuously without `--once`. Schedules and assessments are file-backed in v0.6 and therefore require a single application instance. The SQL job backend can still coordinate multiple execution workers.

## Webhook trust boundary

Destinations must use HTTPS without embedded credentials, query strings, fragments, local hostnames, or private/reserved literal addresses. Resolution is checked immediately before delivery and non-public results are rejected. Production deployments should also set the exact `WEBHOOK_ALLOWED_HOSTS` allowlist and enforce matching outbound network policy; application DNS checks alone cannot eliminate DNS-rebinding races. Redirect following remains disabled. The API stores only the name of an environment variable containing the secret. Each request includes event ID, Unix timestamp, key ID, and `X-Vendor-RTP-Signature: v1=<HMAC-SHA256>` over `<timestamp>.<canonical-body>`.

Consumers should reject stale timestamps, cache event IDs to prevent replay, select the verification key by key ID, and compare signatures in constant time. Deliveries retry with bounded exponential backoff and then enter a dead-letter state. Payloads contain sanitized assurance data, not raw model responses.

## Honest evidence statement

The four-reviewer ChatGPT panel is published as external AI review evidence. It does not replace independent human annotation or adjudication. Human validation remains pending until real reviewers provide labels.
