# Legacy: Universal AI Gateway

Moved out of the live C-Embedded Agent FastAPI app.

This tree is **not imported** by `backend/app/main.py`. It required SQLAlchemy / cryptography / extra deps that are not in `backend/requirements.txt`.

Do not mount `/v1` or `/admin` on the Embedded Agent.

Still in the live tree (pytest-ignored / unused, not imported by `main.py`):

- `backend/tests/test_gateway.py`
- `backend/tests/test_v090.py`
- `backend/scripts/backup.py`, `mock_openai.py`, `smoke_gateway.py`

`unigateway/` at repo root is a separate leftover Next console and was not moved in this pass.
