# v0.5 walkthrough — 90 seconds

## 0–15 seconds: the decision problem

“This project turns model and agent security tests into evidence a vendor-risk reviewer can inspect. It separates test results from the final assurance decision.”

Show the public synthetic demo and its deliberately failed release gate. Point out that uncertainty requires review rather than being counted as safe.

## 15–35 seconds: run the defensive agent suite

Open the authenticated home page, choose `agent_defensive_demo`, and select **Run defensive scenarios**. Explain that the 16 expanded scenarios cover indirect prompt injection, denied tools, strict arguments, cross-turn escalation, synthetic canaries, and call budgets.

“Tools are simulated. The target may propose calls, but the harness never executes a live side effect.”

## 35–55 seconds: inspect a finding

Open a failed scenario. Show the stable reason code, sanitized excerpt, argument-key metadata, hashes, and the finding-specific control, action, and retest instructions.

“Raw transcripts and tool arguments are intentionally not persisted.”

## 55–70 seconds: verify evidence

Run `vendor-rtp verify-manifest --run-id <run-id>` and show `manifest valid`. Explain that the manifest hashes the evidence package and that audit verification is a separate chained control.

## 70–90 seconds: make an assurance decision

Create or open an assessment, link the Passport run, submit it for review, and export the sanitized evidence package. Finish with the honest boundary:

“This is reproducible review evidence—not certification, universal OWASP coverage, or runtime enforcement.”
