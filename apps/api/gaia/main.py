import asyncio
import contextlib
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from . import models as m, domain as d
from .config import SessionLocal, settings

logger = logging.getLogger("gaia")


def background_step():
    with d.LOCK, SessionLocal() as db:
        sessions = list(
            db.scalars(select(m.SimulationSession).where(m.SimulationSession.status == "running"))
        )
        for sim in sessions:
            try:
                d.tick(db, sim.territory_id, sim.speed)
                db.commit()
            except Exception:
                db.rollback()
                logger.exception("Simulation tick failed")


async def background_loop():
    while True:
        await asyncio.sleep(1)
        await asyncio.to_thread(background_step)


@contextlib.asynccontextmanager
async def lifespan(_):
    # A restart never silently resumes a pump or a running simulation.
    with d.LOCK, SessionLocal() as db:
        for sim in db.scalars(select(m.SimulationSession)):
            d.stop_pump(db, sim.territory_id, "Сервер перезапущен: безопасная остановка")
            if sim.status == "running":
                sim.status = "paused"
        db.commit()
    task = asyncio.create_task(background_loop()) if settings.background_enabled and settings.legacy_simulation_enabled else None
    yield
    if task:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="GAIA API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "X-GAIA-Request"],
)


@app.middleware("http")
async def csrf(request: Request, call_next):
    if not settings.legacy_simulation_enabled and request.url.path.startswith("/api/v1/territories/") and any(
        segment in request.url.path.split("/") for segment in ("simulation", "irrigation")
    ):
        return JSONResponse({"detail": "Этот архивный модуль отключён. Используйте мониторинг по реальным устройствам."}, status_code=410)
    if (
        request.method in ("POST", "PUT", "PATCH", "DELETE")
        and request.url.path != "/api/v1/devices/telemetry"
    ):
        origin = request.headers.get("origin")
        if (origin and origin != settings.web_origin) or request.headers.get("x-gaia-request") != "1":
            return JSONResponse({"detail": "Запрос отклонён: проверка CSRF"}, status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


from .api.routes import legacy, foundation, global_workspace, earth  # noqa: E402

app.include_router(legacy.router)
app.include_router(foundation.router)
app.include_router(global_workspace.router)
app.include_router(earth.router)
