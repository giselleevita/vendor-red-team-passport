from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from apps.api.routes.health import router as health_router
from apps.api.routes.passport import router as passport_router
from apps.api.routes.profiles import router as profiles_router
from apps.api.routes.run import router as run_router
from apps.api.routes.ui import router as ui_router
from apps.api.services.run_store import reports_dir

app = FastAPI(title="AI Vendor Red-Team Passport API", version="0.1.0")

app.mount("/reports", StaticFiles(directory=str(reports_dir())), name="reports")

app.include_router(health_router)
app.include_router(run_router)
app.include_router(passport_router)
app.include_router(profiles_router)
app.include_router(ui_router)
