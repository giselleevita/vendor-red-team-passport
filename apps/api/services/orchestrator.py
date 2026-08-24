from __future__ import annotations

import datetime as dt
import json
import uuid
from contextlib import ExitStack
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from apps.api.config import get_settings
from apps.api.schemas.passport import Passport
from apps.api.services.compliance_mapper import map_compliance
from apps.api.services.coverage import build_coverage_report
from apps.api.services.evaluator import evaluate_case, load_case_suite
from apps.api.services.evidence import sha256_text
from apps.api.services.judge import SemanticJudge
from apps.api.services.manifest import build_and_save_manifest
from apps.api.services.policy import current_policy
from apps.api.services.providers import create_provider
from apps.api.services.run_store import (
    load_run_meta,
    save_case_evidence,
    save_json_artifact,
    save_passport,
    save_passport_html,
    save_run_meta,
)
from apps.api.services.scoring import compute_scores
from apps.api.services.taxonomy import EVALUATION_POLICY_VERSION, TAXONOMY_VERSION


def _utc_now_iso() -> str:
    return dt.datetime.now(tz=dt.timezone.utc).isoformat()


def _jinja_env() -> Environment:
    # Resolve template directory relative to this file so it works even if cwd changes.
    api_dir = Path(__file__).resolve().parents[1]  # apps/api
    templates_dir = api_dir / "templates"
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.filters["tojson"] = lambda obj, indent=2: json.dumps(obj, indent=indent)  # type: ignore[assignment]
    return env


def run_orchestrated(
    *,
    model: str,
    only_classes: list[str] | None,
    a9_mode: str,
    params: dict | None = None,
    tenant_id: str | None = None,
    run_id: str | None = None,
    suite_path: str | Path = "data/cases/cases.v1.json",
    profile: dict | None = None,
) -> str:
    """
    Executes a run and writes artifacts under reports/runs/<run_id>/.
    Sanitized-only persistence (no raw prompts, no raw responses).
    """
    run_id = run_id or str(uuid.uuid4())
    settings = get_settings()
    tenant_id = (tenant_id or "").strip() or settings.auth_default_tenant_id
    suite_path = Path(suite_path)
    suite = load_case_suite(suite_path)

    with ExitStack() as stack:
        client = stack.enter_context(create_provider(profile))
        judge = (
            stack.enter_context(SemanticJudge(target_model=model, target_base_url=client.base_url))
            if settings.judge_enabled
            else None
        )
        if a9_mode == "auto":
            strict_supported = client.supports_a9_risk_verdict_schema(model=model)
            a9_mode_used = "strict" if strict_supported else "compat"
        else:
            a9_mode_used = a9_mode
            strict_supported = client.supports_a9_risk_verdict_schema(model=model)

        enabled_cases = [c for c in suite.cases if c.enabled]
        if only_classes:
            allowed = set(only_classes)
            enabled_cases = [c for c in enabled_cases if c.attack_class in allowed]

        params = params or {"temperature": 0, "max_tokens": 256}

        created_at = _utc_now_iso()

        run_meta = {
            "run_id": run_id,
            "created_at_utc": created_at,
            "finished_at_utc": None,
            "provider": client.provider_name,
            "model": model,
            "tenant_id": tenant_id,
            "endpoint": f"{client.base_url}/chat/completions",
            "params": params,
            "suite_version": suite.suite_version,
            "enabled_case_count": len(enabled_cases),
            "only_classes": only_classes or [],
            "a9_mode_used": a9_mode_used,
            "a9_strict_supported": bool(strict_supported),
            "notes": "sanitized-only evidence",
            "taxonomy_version": TAXONOMY_VERSION,
            "evaluation_policy_version": EVALUATION_POLICY_VERSION,
            "judge": {
                "enabled": bool(judge),
                "model": judge.model if judge else None,
                "invocation_policy": "ambiguous_only",
                "data_retention": judge.data_retention if judge else "not_applicable",
                "raw_response_persisted": False,
            },
        }
        if profile:
            run_meta["profile"] = {
                "name": profile.get("name", ""),
                "source_path": profile.get("source_path", ""),
                "description": profile.get("description", ""),
            }
        save_run_meta(run_id, run_meta)

        results = []
        for case in enabled_cases:
            r = evaluate_case(case, client, a9_mode=a9_mode_used, params=params, judge=judge)
            results.append(r)

            evidence = {
                "case_id": case.id,
                "attack_class": case.attack_class,
                "expected_verdict": case.expected_verdict,
                "actual_verdict": r.actual_verdict,
                "passed": r.passed,
                "response_excerpt_sanitized": r.response_excerpt,
                "error": r.error,
                "timing": {"latency_ms": r.latency_ms},
                "evaluator": {
                    "version": r.evaluator_version,
                    "decision_source": r.decision_source,
                    "confidence": r.confidence,
                    "reason_codes": r.reason_codes,
                    "judge_model": r.judge_model,
                    "needs_human_review": r.needs_human_review,
                },
                "hashes": {
                    "prompt_sha256": sha256_text(case.prompt),
                    "response_excerpt_sha256": sha256_text(r.response_excerpt),
                },
            }
            save_case_evidence(run_id, case.id, evidence)

        scores = compute_scores(enabled_cases, results)
        judge_metadata = judge.telemetry() if judge else {
            "provider": None,
            "model": None,
            "calls": 0,
            "attempts": 0,
            "latency_ms": 0,
            "estimated_cost_usd": 0.0,
            "data_retention": "not_applicable",
            "raw_response_persisted": False,
        }
        compliance = map_compliance(scores["failed_cases"])
        policy = current_policy()
        coverage = build_coverage_report(evaluated_classes=sorted(set([c.attack_class for c in enabled_cases])))

        passport = Passport(
            run_id=run_id,
            summary={
                "overall_score": scores["overall_score"],
                "p1_pass_rate": scores["p1_pass_rate"],
                "p2_pass_rate": scores["p2_pass_rate"],
                "a9_schema_validity": scores["a9_schema_validity"],
                "a9_mode_used": a9_mode_used,
                "a9_strict_supported": bool(strict_supported),
                "critical_failures": scores["critical_failures"],
                "release_gate": scores["release_gate"],
                "taxonomy_version": TAXONOMY_VERSION,
                "evaluation_policy_version": EVALUATION_POLICY_VERSION,
                "review_required_count": scores["review_required_count"],
                "judge": {
                    "enabled": bool(judge),
                    "invocation_policy": "ambiguous_only",
                    **judge_metadata,
                },
            },
            class_scores=scores["class_scores"],
            failed_cases=scores["failed_cases"],
            executive_verdict={
                "decision": "APPROVE" if scores["release_gate"] == "PASS" else "REJECT",
                "required_remediations": [
                    "Fix all critical class failures (A4/A5/A6).",
                    "Re-run full suite with identical parameters.",
                ],
                "compliance_mapping": compliance,
            },
        )
        save_passport(run_id, passport)
        save_json_artifact(run_id, "policy.json", policy)
        save_json_artifact(run_id, "coverage.json", coverage)
        save_json_artifact(run_id, "compliance.json", compliance)

        # Update run meta with finish timestamp.
        finished = _utc_now_iso()
        run_meta["finished_at_utc"] = finished
        run_meta["judge"] = {
            "enabled": bool(judge),
            "invocation_policy": "ambiguous_only",
            **judge_metadata,
        }
        save_run_meta(run_id, run_meta)

        html = render_passport_html(run_id, passport)
        save_passport_html(run_id, html)

        build_and_save_manifest(run_id)

    return run_id


def render_passport_html(run_id: str, passport: Passport) -> str:
    env = _jinja_env()
    tmpl = env.get_template("passport.html.j2")

    meta = load_run_meta(run_id) or {}
    from apps.api.services.run_store import run_dir  # local import to avoid cycles in tooling

    def _load_json(name: str) -> dict | None:
        p = run_dir(run_id) / name
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return None

    policy = _load_json("policy.json") or current_policy()
    coverage = _load_json("coverage.json") or build_coverage_report(
        evaluated_classes=sorted({c.get("attack_class") for c in (passport.model_dump().get("class_scores") or []) if isinstance(c, dict) and c.get("attack_class")})
    )
    compliance = _load_json("compliance.json") or (passport.model_dump().get("executive_verdict", {}) or {}).get("compliance_mapping", {})

    artifacts = {
        "manifest": f"/runs/{run_id}/artifacts/manifest.json",
        "policy": f"/runs/{run_id}/artifacts/policy.json",
        "coverage": f"/runs/{run_id}/artifacts/coverage.json",
        "compliance": f"/runs/{run_id}/artifacts/compliance.json",
    }

    def evidence_link(case_id: str) -> str:
        return f"/runs/{run_id}/cases/{case_id}.json"

    return tmpl.render(
        run_id=run_id,
        meta=meta,
        passport=passport.model_dump(),
        policy=policy,
        coverage=coverage,
        compliance=compliance,
        artifacts=artifacts,
        evidence_link=evidence_link,
    )
