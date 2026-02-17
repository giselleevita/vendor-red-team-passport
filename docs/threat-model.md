# Threat Model (Local-First, Defensive Evaluation Tool)

## Scope
This threat model covers the local operator workstation running the FastAPI service, local artifacts under `reports/`, and outbound calls to the external LLM provider API (Featherless OpenAI-compatible endpoint).

## Assets
- Provider API key (`FEATHERLESS_API_KEY`) and any other environment secrets
- Case suite (`data/cases/*.json`)
- Run artifacts (`reports/runs/<run_id>/...`) including sanitized evidence excerpts
- Benchmark summaries (`reports/benchmarks/*.md/*.json`)

## Trust Boundaries
- Operator workstation (trusted boundary)
- Local FastAPI process (trusted boundary, but must be hardened against accidental leakage)
- Filesystem storage for artifacts (trusted boundary; still needs safe defaults)
- External provider API (untrusted network boundary)

## Attacker Models
- Local attacker with filesystem access (steals keys/artifacts)
- Network attacker observing outbound traffic (if TLS is compromised or misconfigured)
- Malicious/compromised model provider (returns unexpected content, attempts prompt injection, or logs prompts)
- Accidental insider leakage via sharing artifacts (copy/paste of evidence excerpts)

## Top Risks and Mitigations
### 1) Secret leakage (API keys, tokens) into artifacts
- Risk: prompts/responses could contain secret-like content; logs/artifacts could leak it.
- Mitigations:
  - Persist sanitized excerpts only (`response_excerpt_sanitized`), redact secret-like patterns and code blocks.
  - Do not print `.env` contents.
  - Store only hashes for prompts (not raw prompts) in per-case evidence.
  - Use `manifest.json` (optional HMAC) to detect post-run artifact tampering if stored securely.

### 2) Raw offensive content captured and shared
- Risk: evidence packs could contain unsafe procedural guidance.
- Mitigations:
  - Excerpts are capped and sanitized (redaction rules).
  - Benchmarks/one-pagers use extra “safe snippet” logic and refuse code blocks/secret-like content.

### 3) Non-reproducible decisions due to mutable params/provider drift
- Risk: evaluation output changes over time; procurement decisions become non-auditable.
- Mitigations:
  - Record run metadata (model, params, suite_version, timestamps) in `run.json`.
  - Keep scoring deterministic given the recorded inputs.

### 4) Over-claiming compliance
- Risk: users interpret control mapping as certification.
- Mitigations:
  - Explicit transparency notes (`docs/transparency.md`).
  - Reports frame compliance mapping as “mapping hints”, not legal attestation.

### 5) Provider structured-output enforcement uncertainty (A9)
- Risk: “strict JSON” may not be enforced by some models/providers, causing false confidence.
- Mitigations:
  - Conservative mode selection: default `a9_mode=auto`, only use strict if enforceability probe passes.
  - Treat non-JSON as failure for A9 cases.
