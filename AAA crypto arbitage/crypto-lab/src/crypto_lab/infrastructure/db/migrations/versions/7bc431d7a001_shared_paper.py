"""Shared paper portfolio and worker ownership.

Revision ID: 7bc431d7a001
Revises: 29ea239512cf
"""

import sqlalchemy as sa
from alembic import op

revision = "7bc431d7a001"
down_revision = "29ea239512cf"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paper_account",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("initial", sa.String(40), nullable=False),
        sa.Column("trade_limit", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "paper_position",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bot", sa.String(40), nullable=False),
        sa.Column("key", sa.String(250), nullable=False, unique=True),
        sa.Column("symbol", sa.String(160), nullable=False),
        sa.Column("venue", sa.String(40), nullable=False),
        sa.Column("quantity", sa.String(40), nullable=False),
        sa.Column("capital", sa.String(40), nullable=False),
        sa.Column("proceeds", sa.String(40)),
        sa.Column("mark", sa.String(40)),
        sa.Column("mark_at", sa.DateTime()),
        sa.Column("opened_at", sa.DateTime(), nullable=False),
        sa.Column("closed_at", sa.DateTime()),
        sa.Column("detail", sa.JSON(), nullable=False),
    )
    op.create_index("ix_paper_position_bot", "paper_position", ["bot"])
    op.create_table(
        "paper_state", sa.Column("key", sa.String(250), primary_key=True), sa.Column("value", sa.JSON(), nullable=False)
    )
    op.create_table(
        "worker_lease",
        sa.Column("slug", sa.String(40), primary_key=True),
        sa.Column("owner", sa.String(64), nullable=False),
        sa.Column("at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "paper_event",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("at", sa.DateTime(), nullable=False),
        sa.Column("bot", sa.String(40), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
    )
    op.create_index("ix_paper_event_at", "paper_event", ["at"])
    op.create_index("ix_paper_event_bot", "paper_event", ["bot"])


def downgrade() -> None:
    for name in ("paper_event", "worker_lease", "paper_state", "paper_position", "paper_account"):
        op.drop_table(name)
