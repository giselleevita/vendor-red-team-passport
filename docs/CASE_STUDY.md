# Case Study: Treating LLM Evaluation as a Measurement System

## Problem

Security and procurement teams need more than a collection of jailbreak prompts. They need to know what was tested, how outputs were judged, which uncertainty remains, and whether the evidence can be reviewed without exposing raw model content.

The first implementation produced deterministic scores but used one global keyword heuristic. That created a concrete validity failure: safe refusals such as “I can’t reveal my system prompt” were classified as unsafe merely because they mentioned the sensitive concept.

## Engineering response

Version 0.2 treats the evaluator itself as security-sensitive:

- Ten internal classes now match the actual 100 prompts instead of imitating a one-to-one OWASP list.
- A versioned many-to-many crosswalk references OWASP GenAI 2025 and NIST AI RMF 1.0 without claiming certification.
- Class-specific rules distinguish clear refusal, unsafe compliance, and `UNCERTAIN`.
- An optional, separately configured judge receives only ambiguous cases.
- Judge failure and deterministic ambiguity fail closed and require human review.
- Every result records evaluator version, source, confidence, reason codes, judge model, and review status.

## Calibration evidence

The public calibration corpus contains 80 human-labelled synthetic responses across A1–A10:

- balanced safe refusals and unsafe compliance for A1–A8/A10;
- refusal-then-answer attacks;
- English, Spanish, French, and German refusal patterns;
- strict and non-compliant JSON for A9;
- no real secrets or operational payloads.

CI requires macro F1 ≥ 0.90 and zero unsafe false-safe decisions in the critical A4–A7 fixtures. The corpus is intentionally small enough to review manually and is a regression baseline, not a claim of universal language understanding.

## Security decisions

- PyJWT replaces handwritten token parsing and requires expiration, issuance, subject, issuer, audience, tenant, and roles claims.
- Object-level tenant checks remain on report, job, and artifact access.
- Raw prompts and responses are not persisted; sanitized excerpts and hashes support review.
- The semantic judge is an explicit external trust boundary because it receives the target prompt and response ephemerally.
- Audit HMAC language is deliberately narrow: v0.2 detects modification of signed entries, not deletion or reordering.

## Outcome

The Passport now communicates three different things separately:

1. What the target model returned.
2. How confidently the evaluator interpreted it.
3. Whether policy permits release or requires review.

That separation prevents deterministic scoring from being presented as automatic truth. The synthetic demo intentionally fails its vendor so reviewers can see remediation and uncertainty rather than a marketing-perfect result.

## Remaining work

Version 0.3 expands multilingual calibration, adds adversarial judge-injection testing, chains audit entries, enforces streaming request limits, introduces provider adapters and a packaged CLI, and raises coverage to 85%.
