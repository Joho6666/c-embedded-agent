from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.api.v1 import router as v1_router
from app.core.config import get_settings
from app.core.database import Base, engine
from app.core.security_boot import assert_production_secrets
from app.core.state import init_state

logger = logging.getLogger("gateway")


def _run_migrations() -> None:
    try:
        from alembic import command
        from alembic.config import Config

        cfg = Config()
        cfg.set_main_option("script_location", "alembic")
        cfg.set_main_option("sqlalchemy.url", get_settings().database_url)
        command.upgrade(cfg, "head")
    except Exception as exc:  # noqa: BLE001
        logger.warning("alembic upgrade skipped: %s", exc)
        Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    assert_production_secrets()
    init_state(get_settings().redis_url)
    _run_migrations()
    Base.metadata.create_all(bind=engine)
    stop = asyncio.Event()

    async def _cleanup_loop() -> None:
        from app.tasks.cleanup_logs import cleanup_old_logs

        while not stop.is_set():
            try:
                cleanup_old_logs()
            except Exception as exc:  # noqa: BLE001
                logger.warning("log cleanup failed: %s", exc)
            try:
                await asyncio.wait_for(stop.wait(), timeout=3600)
            except TimeoutError:
                continue

    task = asyncio.create_task(_cleanup_loop())
    yield
    stop.set()
    task.cancel()


settings = get_settings()
app = FastAPI(title="Universal AI Gateway", version="0.9.0-rc.1", lifespan=lifespan)
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(admin_router)
app.include_router(v1_router)


@app.get("/health")
def health():
    from app.core.state import state_status

    st = state_status()
    return {
        "status": "ok",
        "gateway": True,
        "database": True,
        "stateBackend": st.get("mode"),
        "redis": st.get("redis"),
    }
