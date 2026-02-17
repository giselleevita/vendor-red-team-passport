# Transparency Notes

## What This Is
- A defensive evaluation harness for LLM vendor APIs, producing:
  - reproducible test outcomes
  - sanitized evidence artifacts
  - a decision-ready “passport” report

## What This Is Not
- Not legal certification, not a compliance attestation, not a substitute for a full security review.

## Evidence Handling (Sanitized-Only)
- The system persists only:
  - `response_excerpt_sanitized` (redacted + length-capped)
  - hashes of prompt and excerpt (`sha256`)
  - verdicts, errors, timing metrics
- It does not persist raw responses, raw prompts, or secrets.
- Each run also writes a `manifest.json` (sha256 list; optional HMAC) to support tamper-evident evidence handling.

## Reproducibility
- Run artifacts are stored under `reports/runs/<run_id>/`.
- Run metadata records model name, parameters, suite version, and timestamps.
- Run profiles under `profiles/` provide stable, named execution policies (e.g. quick gates vs full suite).
- Results depend on:
  - model/provider runtime changes
  - rate limiting/pacing behavior
  - the chosen case suite version

## Safety and Authorization
- Offensive scenarios are simulated strictly for authorized lab testing and defensive vendor due diligence.
- Do not use this tool to generate or deploy offensive malware, exploit payloads, or operational intrusion guidance.

## Known Limitations
- “Strict JSON” enforcement can be provider/model dependent; if strict structured output is not enforceable, A9 is run in a compat mode with server-side validation.
- Pass/fail gates reflect this tool’s scoring policy, not a universal standard.
