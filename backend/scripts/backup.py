"""Backup SQLite DB and non-secret metadata. Credentials stay encrypted."""

from __future__ import annotations

import json
import zipfile
from datetime import datetime
from pathlib import Path

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.database import CredentialRow, ModelPricingRow, ProviderRow, VirtualModelRow


def sqlite_path(url: str) -> Path | None:
    if url.startswith("sqlite:///"):
        return Path(url.replace("sqlite:///", "", 1))
    return None


def main() -> Path:
    settings = get_settings()
    stamp = datetime.utcnow().strftime("%Y%m%d")
    out = Path(f"gateway-backup-{stamp}.zip")
    db = SessionLocal()
    try:
        providers = [
            {"id": p.id, "name": p.name, "type": p.type, "base_url": p.base_url, "descriptor_id": p.descriptor_id}
            for p in db.query(ProviderRow).all()
        ]
        virtual = [
            {"id": v.id, "slug": v.slug, "strategy": v.strategy, "candidates_json": v.candidates_json}
            for v in db.query(VirtualModelRow).all()
        ]
        pricing = [
            {"id": r.id, "provider": r.provider, "model": r.model, "input_per_1m": r.input_per_1m, "output_per_1m": r.output_per_1m}
            for r in db.query(ModelPricingRow).all()
        ]
        creds = [
            {
                "id": c.id,
                "name": c.name,
                "provider_id": c.provider_id,
                "encrypted_secret": c.encrypted_secret,
                "base_url": c.base_url,
                "status": c.status,
            }
            for c in db.query(CredentialRow).all()
        ]
    finally:
        db.close()

    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("metadata.json", json.dumps({"providers": providers, "virtual_models": virtual, "pricing": pricing}, ensure_ascii=False, indent=2))
        zf.writestr("credentials.encrypted.json", json.dumps(creds, ensure_ascii=False, indent=2))
        path = sqlite_path(settings.database_url)
        if path and path.exists():
            zf.write(path, arcname="gateway.db")
        elif path is None:
            zf.writestr("README-RESTORE.txt", "PostgreSQL backups should use pg_dump. This archive only contains metadata.")
    print(out)
    return out


if __name__ == "__main__":
    main()
