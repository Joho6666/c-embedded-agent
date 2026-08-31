import os
import sys
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("ADMIN_API_KEY", "test-admin")
os.environ.setdefault("GATEWAY_SECRET_KEY", "test-secret")
os.environ.setdefault("CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode())


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db = tmp_path / "t.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db.as_posix()}")
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin")
    from app.core.config import get_settings

    get_settings.cache_clear()
    import app.core.database as database
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models.database import Base

    engine = create_engine(f"sqlite:///{db.as_posix()}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    database.engine = engine
    database.SessionLocal = SessionLocal

    from app.core.state import reset_state

    reset_state()

    from app.main import app

    with TestClient(app) as c:
        yield c
    get_settings.cache_clear()
    reset_state()


@pytest.fixture()
def admin(client: TestClient):
    return {"Authorization": "Bearer test-admin"}
