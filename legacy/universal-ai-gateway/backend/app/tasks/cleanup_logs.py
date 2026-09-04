from __future__ import annotations

from datetime import datetime, timedelta

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.database import RequestLogRow


def cleanup_old_logs(days: int | None = None) -> int:
    retain = days if days is not None else get_settings().log_retention_days
    if retain <= 0:
        return 0
    cutoff = datetime.utcnow() - timedelta(days=retain)
    db = SessionLocal()
    try:
        q = db.query(RequestLogRow).filter(RequestLogRow.timestamp < cutoff)
        count = q.count()
        q.delete(synchronize_session=False)
        db.commit()
        return count
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    deleted = cleanup_old_logs()
    print(f"deleted {deleted} request logs")


if __name__ == "__main__":
    main()
