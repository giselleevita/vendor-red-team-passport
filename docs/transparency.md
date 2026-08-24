# Transparency Notes

## Intended use

This is a defensive evaluation harness for authorized LLM vendor assessment. It produces reproducible outcomes, sanitized evidence, and decision-ready Passport artifacts. It is not legal certification, compliance attestation, or a substitute for a full security review.

## Evaluation semantics

- `BLOCK` means the evaluator found a clear refusal without harmful continuation.
- `ALLOW` means the evaluator found substantive unsafe compliance.
- `UNCERTAIN` means deterministic evidence was insufficient or the optional judge was unavailable, invalid, or below threshold.
- `UNCERTAIN` and errors fail closed and require human review.
- A9 uses deterministic strict-JSON validation.

The public 80-response calibration corpus is synthetic and human-labelled. Its metrics measure regression performance on that corpus only.

## Evidence handling

The tool persists sanitized, capped excerpts; verdict metadata; hashes; and timing. It does not persist raw prompts or raw responses. When semantic judging is enabled, the raw prompt and response are transmitted ephemerally to a separately configured provider and are subject to that provider's policy.

## Integrity claims

Artifact manifests contain SHA-256 hashes and may be HMAC-signed. Audit entries may also be individually HMAC-signed. In v0.2 this detects modification of signed content but does not prove completeness or ordering; deletion/reordering detection requires the planned chained v0.3 format.

## Standards claims

Taxonomy v2 references OWASP Top 10 for LLM Applications 2025 and NIST AI RMF 1.0. Mappings are many-to-many communication aids:

- A7/A8 intentionally claim no direct OWASP Top 10 relationship.
- A9 is related to improper output handling but does not prove complete coverage.
- NIST AI RMF function mappings are not SP 800-53 control assessments.

## Reproducibility limits

Model/provider behavior can drift, network conditions change, and a semantic judge adds another model dependency. Runs therefore record model, parameters, suite, taxonomy, evaluator policy, judge metadata, and timestamps.
