from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.api.v1 import router as v1_router
from app.core.config import get_settings
from app.core.database import Base, engine

settings = get_settings()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Universal AI Gateway", version="0.1.0")
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
    return {"status": "ok", "gateway": True, "database": True}
