# 5-Min Demo Script (Recruiter-Ready)

## Goal
Show procurement-grade evidence artifacts (sanitized), a decision-ready HTML report, and model-to-model comparison in one flow.

## Pre-Req (30s)
```bash
source .venv/bin/activate
uvicorn apps.api.main:app --reload --port 8000
```

Open the UI:
- `http://127.0.0.1:8000/`

## Part 1: Quick Gates Run (2 min)
1. On `/`, keep profile `quick_gates` and `A9 mode=profile default`.
2. Click `Run`.
3. On the generated `/runs/<run_id>` report:
   - Point to `Gate: PASS/FAIL`.
   - Highlight `Critical Failures (A4/A5/A6)` and `A9 Schema Validity`.
   - Show “Artifacts”: `manifest.json`, `policy.json`, `coverage.json`.
4. Click one Evidence link:
   - Shows `cases/<case_id>.json` with `response_excerpt_sanitized`, `latency_ms`, and hashes.
   - Confirm: no raw responses are persisted.
5. Open `/runs/<run_id>/claims`:
   - Show “Claim vs Evidence” matrix and headline suggestions.

## Part 2: Benchmark Two Models (2 min)
```bash
python scripts/benchmark_models.py \
  --models moonshotai/Kimi-K2-Instruct meta-llama/Meta-Llama-3-8B-Instruct \
  --profile quick_gates \
  --out reports/benchmarks/benchmark.quick_gates.demo.json
```
Open:
- `reports/benchmarks/executive_summary.benchmark.quick_gates.demo.md`
- `reports/benchmarks/one_pager.benchmark.quick_gates.demo.md`

Explain (one sentence): this is a procurement-facing summary that links back to evidence artifacts.

## Part 3: Compare (30s)
Open:
- `http://127.0.0.1:8000/compare`

Select the two run IDs from the benchmark and show:
- Summary deltas (B - A)
- Per-class deltas (A4/A5/A6/A9 highlighted first)

## Close (10s)
Pitch: “This is a vendor due-diligence passport that produces reproducible, sanitized evidence packs and a decision-ready procurement one-pager.”
