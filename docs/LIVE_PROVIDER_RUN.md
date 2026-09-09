# Live provider evaluation protocol

This protocol turns a permitted evaluation of an OpenAI-compatible endpoint into a
reviewable public result. It is deliberately separate from the synthetic demo: do
not describe a run as live until the provider calls completed and the generated
artifacts have been verified.

## Before running

1. Obtain written authorization for the target endpoint, model, test volume, and
   expected cost. Use only an endpoint the evaluator is allowed to test.
2. Copy `profiles/openai_compatible_example.yaml` to an untracked local profile,
   set its `base_url`, and select the agreed model. Never put a key in a profile,
   command history, issue, or commit.
3. Export `TARGET_API_KEY` from a secret manager or an interactive shell. Keep
   `JUDGE_ENABLED=false` unless the target and the separate judge boundary are
   both approved.
4. Start with `quick_gates`; use the full suite only after the small run is
   accepted and its cost is understood.

## Run and verify

```bash
# The copied profile remains local and is intentionally not committed.
export TARGET_API_KEY='...'
vendor-rtp run --profile profiles/my-approved-provider.yaml --model '<approved-model>' \
  --run-id 'provider-YYYY-MM-DD'

# Verify the exact emitted evidence before drawing a conclusion.
vendor-rtp verify-manifest --run-id 'provider-YYYY-MM-DD'
vendor-rtp verify-audit --run-id 'provider-YYYY-MM-DD'
```

Record the provider, model identifier, date, suite hash/version, profile settings,
case count, evaluator version, release-gate outcome, and every limitation. Do not
publish API URLs that reveal a private deployment, request headers, raw prompts,
raw responses, keys, user data, or unredacted logs.

## Publish a bounded result

Create a dated Markdown report under `docs/results/` that links only to the
sanitized `passport.json`, `coverage.json`, `policy.json`, and verified manifest.
State whether the result is a model measurement, a vendor assessment, or a
production-system assessment; those are different claims. Include a statement
that the suite is a bounded sample and not a certification or complete OWASP/NIST
coverage assessment.

Open a pull request containing the report and sanitized artifacts. The reviewer
should be able to repeat the manifest and audit verification commands without
receiving a credential. If that cannot be done, keep the result private rather
than weakening the evidence standard.
