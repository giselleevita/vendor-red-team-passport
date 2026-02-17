from fastapi import APIRouter, HTTPException

from apps.api.services.run_store import load_passport

router = APIRouter()


@router.get("/passports/{run_id}")
def get_passport(run_id: str) -> dict:
    passport = load_passport(run_id)
    if passport is None:
        raise HTTPException(status_code=404, detail="run_id not found")
    return passport.model_dump()
