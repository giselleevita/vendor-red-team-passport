from __future__ import annotations

import datetime as dt
import uuid
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from apps.api.config import get_settings
from apps.api.services.agent_evaluator import evaluate_scenario, load_scenario_suite, summarize_agent_results
from apps.api.services.agent_targets import create_agent_target
from apps.api.services.evidence import sha256_text
from apps.api.services.manifest import build_and_save_manifest
from apps.api.services.run_store import run_dir, save_case_evidence, save_json_artifact, save_run_meta


def _now() -> str:
    return dt.datetime.now(tz=dt.UTC).isoformat()


def _render_report(run_id: str, report: dict) -> str:
    template_dir = Path(__file__).resolve().parents[1] / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=select_autoescape(["html", "xml"]))
    return env.get_template("agent_report.html.j2").render(run_id=run_id, report=report)


def run_agent_scenarios(
    *,
    profile: dict,
    model: str,
    suite_path: str | Path,
    tenant_id: str = "",
    run_id: str | None = None,
) -> str:
    run_id = run_id or str(uuid.uuid4())
    suite = load_scenario_suite(suite_path)
    settings = get_settings()
    tenant_id = tenant_id.strip() or settings.auth_default_tenant_id
    expanded_count = sum(len(item.mutations) for item in suite.scenarios if item.enabled)
    total_turns = sum(len(item.turns) * len(item.mutations) for item in suite.scenarios if item.enabled)
    if total_turns > settings.agent_max_total_turns:
        raise ValueError("expanded scenario suite exceeds configured turn budget")
    if expanded_count > 200:
        raise ValueError("expanded scenario suite exceeds 200 evaluations")

    created_at = _now()
    meta = {
        "run_id": run_id,
        "run_type": "agent_scenarios",
        "tenant_id": tenant_id,
        "created_at_utc": created_at,
        "finished_at_utc": None,
        "model": model,
        "profile": profile.get("name", ""),
        "suite_version": suite.suite_version,
        "scenario_schema_version": suite.schema_version,
        "simulation_only": True,
        "raw_transcripts_persisted": False,
    }
    save_run_meta(run_id, meta)
    results = []
    total_tool_calls = 0
    with create_agent_target(profile) as target:
        meta["target"] = target.target_name
        for scenario in suite.scenarios:
            if not scenario.enabled:
                continue
            for mutation in scenario.mutations:
                result = evaluate_scenario(scenario, target, model=model, mutation=mutation)
                results.append(result)
                total_tool_calls += len(result.tool_calls)
                if total_tool_calls > settings.agent_max_total_tool_calls:
                    raise ValueError("agent run exceeded configured total tool-call budget")
                evidence_id = f"{scenario.id}-{mutation}"
                save_case_evidence(
                    run_id,
                    evidence_id,
                    {
                        "scenario_id": scenario.id,
                        "category": scenario.category,
                        "mutation": mutation,
                        "expected_outcome": scenario.expected_outcome,
                        "status": result.status,
                        "passed": result.passed,
                        "violations": result.violations,
                        "remediation": result.remediation,
                        "response_excerpt_sanitized": result.response_excerpt,
                        "tool_calls": [item.model_dump(mode="json") for item in result.tool_calls],
                        "needs_human_review": result.needs_human_review,
                        "error": result.error,
                        "hashes": {
                            "scenario_sha256": sha256_text(scenario.model_dump_json()),
                            "response_excerpt_sha256": sha256_text(result.response_excerpt),
                        },
                    },
                )

    report = {
        "schema_version": "agent-report.v1",
        "run_id": run_id,
        "summary": summarize_agent_results(results),
        "target": {
            "name": meta.get("target", ""),
            "model": model,
            "simulation_only": True,
            "live_tools_executed": False,
        },
        "results": [result.model_dump(mode="json") for result in results],
        "evidence_policy": {
            "raw_transcripts_persisted": False,
            "tool_arguments_persisted": False,
            "sanitized_excerpts_only": True,
        },
    }
    save_json_artifact(run_id, "agent-report.json", report)
    (run_dir(run_id) / "agent-report.html").write_text(_render_report(run_id, report), encoding="utf-8")
    meta["finished_at_utc"] = _now()
    save_run_meta(run_id, meta)
    build_and_save_manifest(run_id)
    return run_id
