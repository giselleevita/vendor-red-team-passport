from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, HTTPException

from pydantic import BaseModel, Field

from apps.api.config import get_settings
from apps.api.services.profiles import load_profile
from apps.api.services.orchestrator import run_orchestrated

router = APIRouter()


class RunCreateRequest(BaseModel):
    profile: str | None = Field(default=None, description="Run profile name or path (e.g. quick_gates, full_suite)")
    model: str | None = Field(default=None, description="Featherless model name")
    only_classes: list[str] | None = Field(
        default=None, description="If set, run only these attack classes (e.g. ['A4','A5','A6','A9'])."
    )
    a9_mode: Literal["auto", "compat", "strict"] | None = Field(default=None)
    params: dict | None = Field(default=None, description="Optional generation params (temperature, max_tokens)")


@router.post("/runs")
def create_run(req: RunCreateRequest) -> dict[str, str]:
    settings = get_settings()
    run_id = str(uuid.uuid4())
    try:
        profile = load_profile(req.profile, allow_external_paths=False) if req.profile else None
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e)) from e

    model = (req.model or "").strip() or (profile.get("model") if profile else "") or settings.default_model
    suite_path = (profile.get("suite_path") if profile else "") or "data/cases/cases.v1.json"

    only_classes = req.only_classes if req.only_classes is not None else (profile.get("only_classes") if profile else None)
    if only_classes == []:
        only_classes = None

    a9_mode = req.a9_mode if req.a9_mode is not None else (profile.get("a9_mode") if profile else "auto")
    params = req.params if req.params is not None else (profile.get("params") if profile else None)

    if params is not None:
        allowed = {"temperature", "max_tokens"}
        extra = set(params.keys()) - allowed
        if extra:
            raise HTTPException(status_code=422, detail=f"unsupported params keys: {sorted(extra)}")
        if "temperature" in params and params["temperature"] is not None:
            try:
                params["temperature"] = float(params["temperature"])
            except Exception as e:  # noqa: BLE001
                raise HTTPException(status_code=422, detail="params.temperature must be a number") from e
        if "max_tokens" in params and params["max_tokens"] is not None:
            try:
                params["max_tokens"] = int(params["max_tokens"])
            except Exception as e:  # noqa: BLE001
                raise HTTPException(status_code=422, detail="params.max_tokens must be an integer") from e

    if only_classes is not None:
        normalized = []
        for c in only_classes:
            cc = (c or "").strip().upper()
            if not cc:
                continue
            if not (len(cc) in (2, 3) and cc.startswith("A") and cc[1:].isdigit()):
                raise HTTPException(status_code=422, detail=f"invalid attack class: {c!r}")
            normalized.append(cc)
        only_classes = normalized or None

    run_orchestrated(
        model=model,
        only_classes=only_classes,
        a9_mode=a9_mode,
        params=params,
        run_id=run_id,
        suite_path=suite_path,
        profile=profile,
    )
    return {
        "run_id": run_id,
        "passport_json_url": f"/passports/{run_id}",
        "passport_html_url": f"/runs/{run_id}",
        "files_url_prefix": f"/reports/runs/{run_id}/",
    }
