from __future__ import annotations

from fastapi import APIRouter, HTTPException

from apps.api.services.profiles import list_profiles, load_profile

router = APIRouter()


@router.get("/profiles")
def get_profiles() -> list[dict]:
    return list_profiles()


@router.get("/profiles/{name}")
def get_profile(name: str) -> dict:
    try:
        return load_profile(name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e)) from e

