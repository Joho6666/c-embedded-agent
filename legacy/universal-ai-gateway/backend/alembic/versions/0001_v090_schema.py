"""v0.9 schema baseline and additive columns

Revision ID: 0001_v090
Revises:
Create Date: 2026-09-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0001_v090"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _cols(insp, table: str) -> set[str]:
    if table not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def _add(table: str, name: str, col: sa.Column, existing: set[str]) -> None:
    if name in existing:
        return
    with op.batch_alter_table(table) as batch:
        batch.add_column(col)


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    tables = set(insp.get_table_names())
    if "providers" not in tables:
        from app.models.database import Base

        Base.metadata.create_all(bind=bind)
        return

    cred_cols = _cols(insp, "credentials")
    _add("credentials", "stats_month", sa.Column("stats_month", sa.String(7), server_default=""), cred_cols)

    key_cols = _cols(insp, "api_keys")
    _add("api_keys", "daily_request_limit", sa.Column("daily_request_limit", sa.Integer(), server_default="10000"), key_cols)
    _add("api_keys", "monthly_spend", sa.Column("monthly_spend", sa.Float(), server_default="0"), key_cols)
    _add("api_keys", "stats_month", sa.Column("stats_month", sa.String(7), server_default=""), key_cols)

    log_cols = _cols(insp, "request_logs")
    _add("request_logs", "client_disconnected", sa.Column("client_disconnected", sa.Boolean(), server_default=sa.false()), log_cols)
    _add("request_logs", "request_status", sa.Column("request_status", sa.String(24), server_default="pending"), log_cols)
    _add("request_logs", "started_at", sa.Column("started_at", sa.DateTime(), nullable=True), log_cols)
    _add("request_logs", "first_token_at", sa.Column("first_token_at", sa.DateTime(), nullable=True), log_cols)
    _add("request_logs", "completed_at", sa.Column("completed_at", sa.DateTime(), nullable=True), log_cols)
    _add("request_logs", "stream_completed", sa.Column("stream_completed", sa.Boolean(), server_default=sa.false()), log_cols)

    price_cols = _cols(insp, "model_pricing")
    if "model_pricing" not in tables:
        from app.models.database import Base

        Base.metadata.tables["model_pricing"].create(bind=bind)
    else:
        _add("model_pricing", "reasoning_per_1m", sa.Column("reasoning_per_1m", sa.Float(), server_default="0"), price_cols)
        _add("model_pricing", "effective_from", sa.Column("effective_from", sa.String(32), server_default=""), price_cols)


def downgrade() -> None:
    pass
