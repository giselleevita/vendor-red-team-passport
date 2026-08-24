# Threat Model

## Scope and assets

The model covers the FastAPI service, configured report/job storage, target-model requests, optional semantic-judge requests, case suites, API/JWT secrets, and generated Passport evidence.

Primary assets are provider credentials, tenant-scoped artifacts, evaluation integrity, audit records, case intellectual property, and the confidentiality of prompts/responses.

## Attacker capabilities

- An unauthenticated or low-privilege API caller.
- An authenticated user attempting cross-tenant access.
- A malicious target model returning prompt injection, deceptive refusal, secrets, or oversized content.
- A compromised or manipulated semantic judge.
- A local attacker who can modify filesystem artifacts but does not possess signing keys.
- An operator who accidentally publishes real vendor evidence.

## Trust boundaries and mitigations

| Boundary | Main threats | Controls |
|---|---|---|
| Caller → API | forged tokens, privilege escalation, IDOR | PyJWT algorithm allowlist and required claims; RBAC; tenant ownership; opaque IDs |
| API → target provider | prompt disclosure, provider drift, malformed output | explicit provider boundary; timeouts/retries; versioned inputs; conservative evaluation |
| Target output → evaluator | refusal-then-answer, obfuscation, evaluator evasion | class-specific rules; `UNCERTAIN`; calibration regression; optional separate judge |
| API → judge | data disclosure, judge injection, correlated failure | disabled by default; separate model; data-as-data prompt; strict output schema; low confidence fails closed |
| Evaluator → storage | raw secret/offensive content persistence | sanitization, excerpt caps, hashes, no raw prompt/response persistence |
| Tenant → artifacts | cross-tenant report disclosure, traversal | per-object ownership checks; allowlisted artifact names; validated IDs |
| Filesystem evidence | artifact modification | SHA-256 manifest and optional HMAC |
| Repository/Pages | accidental real output publication | synthetic-only fixture, secret scan, static-demo tests |

## Known residual risks

- Text rules and semantic judges can both be wrong; v0.3 calibration is a bounded synthetic regression corpus, not proof of universal accuracy.
- The judge receives raw target prompt/response data ephemerally; its provider retention policy must be reviewed separately.
- Audit-chain completeness depends on preserving the signed checkpoint separately from the append-only log.
- `Content-Length` request limits do not cover every streaming/chunked deployment path; enforce edge limits until v0.3 streaming middleware lands.
- File/in-memory stores and rate limiting are not multi-instance production controls.
- Framework crosswalks can be misread as attestation; every report carries a non-certification disclaimer.
