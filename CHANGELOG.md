# Changelog

## Unreleased

### Adoption evidence

- Add a v0.6 screen-recording script with a safe publication checklist.
- Add a prospective external-user pilot protocol with measurable completion and comprehension targets.
- Add structured GitHub feedback intake and a sanitized case-study template.
- Keep adoption results explicitly pending until real external sessions are completed.

## v0.6.0 - 2026-09-23

### Continuous assurance

- Add explicitly pinned and historically traceable assessment baselines.
- Add versioned drift and policy evaluations with stable `PASS`, `FAIL`, and fail-closed `UNKNOWN` outcomes.
- Add packaged, validated policy-as-code selected by risk tier and data classification.
- Add tenant-scoped recurring schedules processed by the existing run worker with deterministic job identities.
- Expire approvals at their review deadline and prevent expired evidence from satisfying a gate.
- Add generic HMAC-signed webhook events with bounded retry and dead-letter records.
- Add an urgency-sorted operational portfolio API and browser queue.

### Limitations

- Assessment, schedule, and delivery records remain file-backed and single-instance in v0.6.
- Webhook signing secrets are environment-resolved and never returned by the API.
- The published ChatGPT panel is external AI review evidence, not independent human validation.

## v0.5.1 - 2026-09-23

### Added

- Finding-specific control, implementation, and retest guidance for defensive agent results.
- A CSP-compatible browser launcher for model and agent runs with bounded status polling.
- Side-by-side comparison for two to six model runs.
- A reproducible blinded independent-review kit with strict two-reviewer ingestion.
- A pinned full-history secret scan required by branch protection.

### Security

- Reject unknown and over-budget generation parameters through strict typed request models.
- Keep browser behavior in packaged same-origin JavaScript instead of weakening the content security policy.
- Keep independent accuracy explicitly pending until complete human reviews and adjudication exist.

## v0.5.0 - 2026-09-23

### Application and agent testing

- Add bounded multi-turn scenarios for indirect prompt injection, tool authorization, argument validation, synthetic canary disclosure, and resource control.
- Add OpenAI-compatible agent, fixed-contract HTTP application, and offline scripted target adapters.
- Simulate authorized tool results without executing live tools or external side effects.
- Add `vendor-rtp agent-test`, `POST /agent-runs`, sanitized reports, evidence hashes, and manifest verification.
- Reject nested credentials, remote JSON Schema references, unknown request fields, unsafe target paths, oversized responses, and over-budget runs.

### Vendor assurance workflow

#### Added

- Tenant-isolated vendor and AI-system assessment records.
- A review lifecycle linking Passport runs to auditor decisions and conditions.
- Sanitized assurance evidence packages that exclude raw prompts and responses.
- A four-release product roadmap focused on vendor-assurance teams.

#### Fixed

- Keep the orchestrator artifact test offline after the provider-factory refactor.
- Encode validator context safely so invalid API input returns the documented 422 response.

#### Known limitations

- The initial assessment store is file-backed and intended for local or single-instance use.
- The assessment workflow does not yet include a browser UI, expiring approvals, or notifications.

## v0.3.0 - 2026-09-01

### Added

- Installable Python package and `vendor-rtp` command-line interface.
- A 260-response calibration corpus with multilingual, ambiguity, and
  judge-injection regression cases.
- Versioned evaluation profiles, coverage metadata, release gates, and
  manifest and audit-verification commands.

### Changed

- Ambiguous responses now remain `UNCERTAIN` unless the separately configured
  judge returns a valid, sufficiently confident decision.
- Taxonomy mappings and public claims were narrowed to distinguish direct
  OWASP coverage from related policy-safety evidence.
- Static demo and package resources are included in the distributable wheel.

### Known limitations

- Calibration data is synthetic and does not establish production prevalence.
- The OpenAI-compatible provider path is not a claim of universal vendor
  support.
- Reports are evaluation evidence, not certification.

## v0.2.0 - 2026-08-24

- Introduced class-specific deterministic evaluators and conservative
  `UNCERTAIN` decisions.
- Added the initial 80-response calibration fixture, optional separate judge,
  locked CI, CodeQL, dependency auditing, and the public static demo.

## v0.1.1 - 2026-06-11

### Security

- Prevent profile-name traversal from resolving files outside the configured `profiles/` directory.
- Add regression tests for explicit and fallback external-path attempts.

## v0.1.0 - 2026-06-11

Initial demonstration release.

### Features

- Deterministic A1-A10 LLM security test classes.
- Sanitized JSON and HTML passport reports.
- OWASP LLM and NIST AI RMF mappings.
- Authenticated API, run comparison UI, regression gates, and CI validation.

### Known Limitations

- Filesystem report storage requires persistent storage for deployed environments.
- The comparison UI currently compares exactly two runs.
