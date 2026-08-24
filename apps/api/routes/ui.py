from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from apps.api.config import get_settings
from apps.api.services.auth import RequestContext, require_roles
from apps.api.services.claims import build_claim_matrix
from apps.api.services.orchestrator import render_passport_html
from apps.api.services.profiles import list_profiles
from apps.api.services.run_store import (
    iter_case_evidence,
    list_run_ids_for_tenant,
    load_case_evidence,
    load_json_artifact,
    load_passport,
    load_run_meta,
    run_accessible_by_tenant,
    run_dir,
    save_passport_html,
    validate_artifact_filename,
    validate_case_id,
    validate_run_id,
)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))
_ALLOWED_RUN_ARTIFACTS = {
    "run.json",
    "passport.json",
    "policy.json",
    "coverage.json",
    "compliance.json",
    "manifest.json",
}


def _bad_run_id(e: ValueError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(e))


def _require_run_access(run_id: str, ctx: RequestContext) -> None:
    try:
        validate_run_id(run_id)
    except ValueError as e:
        raise _bad_run_id(e) from e
    if not run_accessible_by_tenant(run_id, ctx.tenant_id):
        raise HTTPException(status_code=404, detail="run_id not found")


@router.get("/", response_class=HTMLResponse)
def landing(
    request: Request,
    ctx: RequestContext = Depends(require_roles("viewer", "auditor", "operator", "admin")),
) -> HTMLResponse:
    _ = ctx
    settings = get_settings()
    return templates.TemplateResponse(
        request,
        "index.html.j2",
        {
            "request": request,
            "default_model": settings.default_model,
            "profiles": list_profiles(),
        },
    )


@router.get("/runs", response_class=HTMLResponse)
def runs_list(
    request: Request,
    ctx: RequestContext = Depends(require_roles("viewer", "auditor", "operator", "admin")),
) -> HTMLResponse:
    runs = []
    for run_id in list_run_ids_for_tenant(ctx.tenant_id)[::-1]:
        meta = load_run_meta(run_id) or {}
        passport = load_passport(run_id)
        summary = passport.summary.model_dump() if passport else {}
        prof = (meta.get("profile") or {}) if isinstance(meta.get("profile"), dict) else {}
        runs.append(
            {
                "run_id": run_id,
                "created_at_utc": meta.get("created_at_utc", ""),
                "model": meta.get("model", ""),
                "profile": prof.get("name", ""),
                "enabled_case_count": meta.get("enabled_case_count", ""),
                "only_classes": meta.get("only_classes", []),
                "gate": summary.get("release_gate", ""),
                "overall_score": summary.get("overall_score", ""),
                "critical_failures": summary.get("critical_failures", ""),
            }
        )

    # Sort by created time if present; otherwise keep filesystem order.
    runs.sort(key=lambda r: r.get("created_at_utc", ""), reverse=True)

    return templates.TemplateResponse(
        request,
        "runs.html.j2",
        {
            "request": request,
            "runs": runs,
        },
    )


@router.get("/runs/{run_id}", response_class=HTMLResponse)
def run_detail(
    run_id: str,
    ctx: RequestContext = Depends(require_roles("viewer", "auditor", "operator", "admin")),
) -> FileResponse:
    _require_run_access(run_id, ctx)
    try:
        html_path = run_dir(run_id) / "passport.html"
    except ValueError as e:
        raise _bad_run_id(e) from e
    if html_path.exists():
        try:
            cached = html_path.read_text(encoding="utf-8")
        except OSError:
            cached = ""
        if "/reports/" not in cached:
            return FileResponse(html_path, media_type="text/html")

    try:
        passport = load_passport(run_id)
    except ValueError as e:
        raise _bad_run_id(e) from e
    if passport is None:
        raise HTTPException(status_code=404, detail="run_id not found")

    html = render_passport_html(run_id, passport)
    save_passport_html(run_id, html)
    return FileResponse(html_path, media_type="text/html")


@router.get("/runs/{run_id}/artifacts/{artifact_name}")
def run_artifact(
    run_id: str,
    artifact_name: str,
    ctx: RequestContext = Depends(require_roles("viewer", "auditor", "operator", "admin")),
) -> dict:
    _require_run_access(run_id, ctx)
    try:
        name = validate_artifact_filename(artifact_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if name not in _ALLOWED_RUN_ARTIFACTS:
        raise HTTPException(status_code=404, detail="artifact not found")
    try:
        payload = load_json_artifact(run_id, name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if payload is None:
        raise HTTPException(status_code=404, detail="artifact not found")
    return payload


@router.get("/runs/{run_id}/cases/{case_id}.json")
def run_case_evidence(
    run_id: str,
    case_id: str,
    ctx: RequestContext = Depends(require_roles("viewer", "auditor", "operator", "admin")),
) -> dict:
    _require_run_access(run_id, ctx)
    try:
        cid = validate_case_id(case_id)
        evidence = load_case_evidence(run_id, cid)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if evidence is None:
        raise HTTPException(status_code=404, detail="case evidence not found")
    return evidence


@router.get("/runs/{run_id}/claims", response_class=HTMLResponse)
def run_claims(
    request: Request,
    run_id: str,
    ctx: RequestContext = Depends(require_roles("viewer", "auditor", "operator", "admin")),
) -> HTMLResponse:
    _require_run_access(run_id, ctx)
    try:
        meta = load_run_meta(run_id) or {}
        passport = load_passport(run_id)
    except ValueError as e:
        raise _bad_run_id(e) from e
    if passport is None:
        raise HTTPException(status_code=404, detail="run_id not found")

    evidences = iter_case_evidence(run_id)
    matrix = build_claim_matrix(
        run_id=run_id,
        meta=meta,
        passport=passport.model_dump(),
        evidences=evidences,
    )

    return templates.TemplateResponse(
        request,
        "claims.html.j2",
        {
            "request": request,
            "matrix": matrix,
        },
    )


@router.get("/compare", response_class=HTMLResponse)
def compare_runs(
    request: Request,
    run_id: list[str] = Query(default=[]),
    ctx: RequestContext = Depends(require_roles("viewer", "auditor", "operator", "admin")),
) -> HTMLResponse:
    available = list_run_ids_for_tenant(ctx.tenant_id)[::-1]
    selected = run_id[:2] if run_id else []

    if len(selected) == 0:
        return templates.TemplateResponse(
            request,
            "compare.html.j2",
            {"request": request, "available": available, "error": "", "comparison": None},
        )

    if len(selected) != 2:
        return templates.TemplateResponse(
            request,
            "compare.html.j2",
            {
                "request": request,
                "available": available,
                "error": "Please provide exactly two run_id query params, e.g. /compare?run_id=a&run_id=b",
                "comparison": None,
            },
        )

    a, b = selected
    if not run_accessible_by_tenant(a, ctx.tenant_id) or not run_accessible_by_tenant(b, ctx.tenant_id):
        return templates.TemplateResponse(
            request,
            "compare.html.j2",
            {
                "request": request,
                "available": available,
                "error": "One or both run_id values were not found on disk.",
                "comparison": None,
            },
        )
    try:
        pa = load_passport(a)
        pb = load_passport(b)
    except ValueError:
        return templates.TemplateResponse(
            request,
            "compare.html.j2",
            {
                "request": request,
                "available": available,
                "error": "One or both run_id values are invalid.",
                "comparison": None,
            },
        )
    if pa is None or pb is None:
        return templates.TemplateResponse(
            request,
            "compare.html.j2",
            {
                "request": request,
                "available": available,
                "error": "One or both run_id values were not found on disk.",
                "comparison": None,
            },
        )

    ma = load_run_meta(a) or {}
    mb = load_run_meta(b) or {}

    sa = pa.summary.model_dump()
    sb = pb.summary.model_dump()

    def _delta(k: str) -> dict:
        va = sa.get(k)
        vb = sb.get(k)
        try:
            d = None if va is None or vb is None else round(float(vb) - float(va), 2)
        except Exception:  # noqa: BLE001
            d = None
        return {"key": k, "a": va, "b": vb, "delta": d}

    gating = ["A4", "A5", "A6", "A9"]
    ca = {c.get("attack_class"): c for c in (pa.class_scores or []) if isinstance(c, dict) and c.get("attack_class")}
    cb = {c.get("attack_class"): c for c in (pb.class_scores or []) if isinstance(c, dict) and c.get("attack_class")}
    all_classes = sorted(set(ca.keys()) | set(cb.keys()), key=lambda x: (0, x) if x in gating else (1, x))

    class_deltas = []
    for cls in all_classes:
        a_score = ca.get(cls)
        b_score = cb.get(cls)
        ap = a_score.get("pass_rate") if isinstance(a_score, dict) else None
        bp = b_score.get("pass_rate") if isinstance(b_score, dict) else None
        d = None
        if ap is not None and bp is not None:
            d = round(float(bp) - float(ap), 2)
        class_deltas.append(
            {
                "attack_class": cls,
                "a_pass_rate": ap,
                "b_pass_rate": bp,
                "delta": d,
                "a_status": (a_score.get("status", "") if isinstance(a_score, dict) else ""),
                "b_status": (b_score.get("status", "") if isinstance(b_score, dict) else ""),
            }
        )

    comparison = {
        "a": {"run_id": a, "model": ma.get("model", ""), "created_at_utc": ma.get("created_at_utc", ""), "summary": sa},
        "b": {"run_id": b, "model": mb.get("model", ""), "created_at_utc": mb.get("created_at_utc", ""), "summary": sb},
        "summary_deltas": [
            _delta("overall_score"),
            _delta("p1_pass_rate"),
            _delta("p2_pass_rate"),
            _delta("critical_failures"),
            _delta("a9_schema_validity"),
        ],
        "class_deltas": class_deltas,
    }

    return templates.TemplateResponse(
        request,
        "compare.html.j2",
        {
            "request": request,
            "available": available,
            "error": "",
            "comparison": comparison,
        },
    )
