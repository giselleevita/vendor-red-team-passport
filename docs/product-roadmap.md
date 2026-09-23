# Product roadmap

Vendor Red-Team Passport is becoming an open-core, local-first assurance product for teams that evaluate AI vendors before procurement or production approval. The evaluation engine remains the evidence source; the product layer turns that evidence into reviewable decisions.

## v0.4 — Vendor assurance workflow

- Vendor and AI-system assessment records with tenant isolation.
- Risk tier, data classification, owner, and review due date.
- Links to completed Passport runs without copying raw model output.
- Submit/review/decision lifecycle with explicit conditions and audit events.
- Sanitized evidence-package export for a procurement or security review.

## v0.5 — Application and agent testing

- Multi-turn conversations and stateful attack scenarios.
- Tool-call assertions, authorization-boundary checks, and indirect prompt-injection cases.
- Target adapters for deployed applications, retrieval pipelines, and agents.
- Reproduction bundles and remediation guidance tied to findings.

## v0.6 — Continuous assurance

- Versioned baselines, drift detection, scheduled re-evaluation, and expiring approvals.
- Policy-as-code gates by risk tier and data classification.
- Webhooks and issue-tracker integrations for findings and review deadlines.
- Portfolio views across vendors, systems, models, and unresolved conditions.

## v1.0 — Enterprise collaboration

- Durable SQL assessment storage and object storage for evidence packages.
- SSO/OIDC, organization roles, approval separation, and configurable retention.
- Signed exports, control-owner attestations, and integration APIs.
- A hosted control plane may be offered, while the evaluation runner remains deployable locally.

## Product boundary

The project does not claim certification, universal vulnerability coverage, or runtime enforcement. Its primary value is reproducible evidence and an explicit decision trail for vendor assurance. Runtime policy enforcement remains a separate control.
