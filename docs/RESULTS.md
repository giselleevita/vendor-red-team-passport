# Live evaluation results — 2026-09-03

Every other example in this repo (`site/passport.json`, the demo page) is
synthetic — safe fixtures used to verify the pipeline without needing model
access. This page is the first *live* run: real model calls, real responses,
graded by the actual evaluator against the real suite. It documents exactly
how it was produced so it's reproducible, not just asserted.

## Setup

- **Target models:** `mistral:latest` (7B) and `qwen3.5:9b`, served locally via
  [Ollama](https://ollama.com)'s OpenAI-compatible API (`http://localhost:11434/v1`)
  using the [`profiles/ollama_local.yaml`](../profiles/ollama_local.yaml) profile.
- **No API keys, no cost.** Both models run entirely on local hardware. This
  was a deliberate choice to make the first published result reproducible by
  anyone with a laptop, not gated behind a paid provider account.
- **Suite:** the full 100-case bundled suite (`data/cases/cases.v1.json`),
  all ten attack classes, default params (`temperature: 0`, `max_tokens: 256`).
- **Grading:** deterministic rules only for the model comparison below
  (no judge — see the judged run for what changes with one). Evaluator
  `detector.v3`, taxonomy `taxonomy.v2-owasp-2025`, `evaluation.v2`.
- **A caveat that matters:** these are the raw base/instruct models with no
  system prompt, safety harness, or application-level guardrails in front of
  them — not how anyone would ship them. The numbers say what the suite
  measures (raw model behavior against these 100 adversarial cases), not
  "is Mistral safe." Treat this as a demonstration of the measurement, not a
  vendor verdict.

## A real bug this run found and fixed

The first attempt at this benchmark failed every single case with HTTP 404s.
Tracing it down: `evaluate_case()` never passed the `--model` argument through
to the HTTP client — every evaluation silently used `settings.default_model`
(Featherless's default) regardless of what `--model`/`--models` was given on
the CLI. Fixed in [`apps/api/services/evaluator.py`](../apps/api/services/evaluator.py)
and [`orchestrator.py`](../apps/api/services/orchestrator.py) — model now
threads through correctly, and the fix is covered by the existing 130-test
suite (all passing) plus this run itself, which is a direct regression test:
the benchmark below could not distinguish the two models at all under the
old code.

## Model comparison (rules-only grading)

| | `mistral:latest` (7B) | `qwen3.5:9b` |
|---|---|---|
| Overall score | 9.33 | 22.67 |
| P1 (critical class) pass rate | 10.0% | 27.1% |
| P2 pass rate | 6.7% | 3.3% |
| Critical failures | 27 / 100 | 21 / 100 |
| Structured-output (A9) support | not supported (`compat` mode) | not supported (`compat` mode) |
| Cases needing human review (`UNCERTAIN`) | 80 | 69 |
| Release gate | **FAIL** | **FAIL** |

Full per-class breakdowns and per-case evidence:
[`mistral_passport.json`](results/2026-09-03-local-ollama/mistral_passport.json) ·
[`qwen3.5-9b_passport.json`](results/2026-09-03-local-ollama/qwen3.5-9b_passport.json) ·
[`benchmark_mistral_vs_qwen.json`](results/2026-09-03-local-ollama/benchmark_mistral_vs_qwen.json)
(raw output of `vendor-rtp benchmark --models mistral:latest qwen3.5:9b`).

Both models fail the release gate outright. qwen3.5:9b is measurably better —
roughly 2.4x the overall score and 6 fewer critical failures — which is
exactly the kind of differentiation a benchmark suite needs to be useful; a
suite that scores everything identically isn't measuring anything.

Neither model reliably enforces the strict-JSON response format used for the
A9 class, so both ran in `compat` mode there rather than `strict`.

## What a local judge changes

Rules-only grading leaves a large fraction of responses `UNCERTAIN` — the
deterministic detector can't confidently classify free-form refusals or
partial compliance from small models that don't follow the expected refusal
phrasing patterns. Enabling the optional judge (also run locally and free,
`qwen3.5:9b` on a second Ollama instance so it's a genuinely separate
provider boundary from the target, per the judge isolation check in
[`judge.py`](../apps/api/services/judge.py)) on `mistral:latest`:

| | Rules only | + local judge |
|---|---|---|
| Overall score | 14.67 | 11.0 |
| Cases needing human review | 80 | 85 |
| Judge calls / attempts | — | 22 / 42 |

The judge resolved some ambiguous cases but not most — a 9B local judge often
can't produce the strict verdict schema reliably either, so several judge
attempts themselves fell back to `UNCERTAIN`. That's a real, useful finding
about judge reliability at this model scale, not a run to hide: full evidence
in [`mistral_judged_passport.json`](results/2026-09-03-local-ollama/mistral_judged_passport.json).

## Reproducing this

```bash
# Terminal 1: target model
ollama serve
ollama pull mistral:latest
ollama pull qwen3.5:9b

# Terminal 2: second instance for the judge (must be a different host:port)
OLLAMA_HOST=127.0.0.1:11435 ollama serve

# Run
export TARGET_API_KEY=local-ollama-no-key-needed
vendor-rtp benchmark --profile ollama_local --models mistral:latest qwen3.5:9b --out results.json

# With the judge
export JUDGE_ENABLED=true JUDGE_BASE_URL=http://127.0.0.1:11435/v1 \
       JUDGE_API_KEY=local-ollama-no-key-needed JUDGE_MODEL=qwen3.5:9b
vendor-rtp run --profile ollama_local --model mistral:latest
```
