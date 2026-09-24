# 90-Second v0.6 Walkthrough

This script is designed for a screen recording or a live networking demonstration. It uses only the public, synthetic demo and makes no claim that a real vendor was assessed.

## Recording setup

- Open the [public demo](https://giselleevita.github.io/vendor-red-team-passport/) at 100% zoom.
- Use a 16:9 recording at 1080p or higher.
- Keep credentials, terminals, notifications, and private browser tabs off screen.
- Speak naturally; the timings are guides, not a requirement to rush.

## Script and shot list

### 0:00–0:12 — The problem

**On screen:** Demo title and summary.

**Say:** “AI security reviews often end as a spreadsheet of prompts. Vendor Red-Team Passport turns a versioned test run into reviewable evidence, a fail-closed release decision, and an assurance record that can be reassessed over time.”

### 0:12–0:32 — Evidence, not a score alone

**On screen:** Passport summary and class results.

**Say:** “Each case records the evaluator version, confidence, reason codes, and whether human review is needed. Raw model output is not published. Ambiguous results become uncertain and cannot silently pass.”

### 0:32–0:50 — Honest standards mapping

**On screen:** OWASP and NIST coverage section.

**Say:** “The mapping is deliberately narrow. It describes which risks the fixed suite probes; it does not claim certification or complete OWASP coverage. Policy-safety tests are labelled separately.”

### 0:50–1:10 — Continuous assurance

**On screen:** Continuous-assurance lifecycle and operational queue.

**Say:** “Version 0.6 pins an approved run as a baseline. Scheduled reassessments detect drift, apply a versioned policy, expire old approvals, and raise signed webhook events. Missing or incompatible evidence returns unknown and fails closed.”

### 1:10–1:25 — Reproducibility

**On screen:** Release page, wheel, SBOM, and provenance section.

**Say:** “A reviewer can reproduce the offline demo without an API key. The public release includes a wheel, CycloneDX SBOM, locked dependencies, and signed build provenance.”

### 1:25–1:30 — Close

**On screen:** Repository link.

**Say:** “It is an evidence-first assurance tool—not a runtime firewall and not a certification product.”

## Publication checklist

- Keep the finished recording between 60 and 90 seconds.
- Add captions and verify technical terms manually.
- Put the repository and public-demo links in the description.
- Do not show real prompts, responses, API keys, tokens, tenant names, or vendor identities.
- Do not describe the external ChatGPT panel as independent human validation.

