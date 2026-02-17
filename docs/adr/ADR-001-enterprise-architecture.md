# ADR-001: Enterprise Architecture Baseline

Status: `accepted`  
Date: `2026-02-17`

## Context
The current system is local-first and file-backed, which is fast for pilot use but weak for enterprise requirements (IAM, tenancy, auditability, and operational scale).

## Decision
We standardize on the following target architecture:
- API: `FastAPI` (control plane and read APIs)
- Primary metadata store: `PostgreSQL`
- Async orchestration: `Redis + Celery workers`
- Artifact storage: `S3-compatible object storage` (AWS S3 / MinIO)
- Authentication: `OIDC bearer JWT validation`
- Authorization: `RBAC` + `tenant-scoped access checks`
- Observability: `OpenTelemetry` + metrics export (Prometheus-compatible)
- Security audit trail: structured audit events for all sensitive actions

## Why
- PostgreSQL gives transactional consistency for runs, tenants, and policy data.
- Redis/Celery decouples long-running evaluations from HTTP request lifecycle.
- S3 object storage supports retention, lifecycle policy, and non-local operations.
- OIDC + RBAC is the minimum viable enterprise identity and access model.
- OTel + metrics is required for SLO/SLA operation and incident response.

## Alternatives Considered
1. Keep local filesystem as system of record  
Rejected: no strong tenancy boundary, weak multi-user governance, poor operational scaling.

2. No queue (synchronous run execution)  
Rejected: API request blocking and low throughput under concurrent workloads.

3. Vendor-specific IAM only  
Rejected: reduces portability and weakens hybrid/on-prem options.

## Rollout Plan
1. Introduce AuthN/AuthZ and tenant context in current API paths.
2. Add audit events and enforce tenant checks on read/write resources.
3. Add async run execution path while preserving current sync code as fallback.
4. Migrate metadata to PostgreSQL and artifacts to object storage.

## Rollback Strategy
- Keep feature flags for auth/rbac enforcement and async execution path.
- Preserve existing file-based run artifacts until DB/object-store migration is stable.
- Revert to synchronous execution only if worker path fails.

## Consequences
- Short-term complexity increases due to dual-path compatibility.
- Long-term benefits: policy control, auditability, scalability, and easier enterprise adoption.
