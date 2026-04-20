"""fix contractstatus enum values

Revision ID: fdae63fe7d96
Revises: b90bda1a1531
Create Date: 2026-04-20 16:12:06.314875
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'fdae63fe7d96'
down_revision: Union[str, None] = 'b90bda1a1531'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1 — convert column to TEXT first
    op.execute("""
        ALTER TABLE contracts
        ALTER COLUMN status DROP DEFAULT
    """)

    op.execute("""
        ALTER TABLE contracts
        ALTER COLUMN status TYPE TEXT
        USING status::TEXT
    """)

    # Step 2 — update existing uppercase values to lowercase
    op.execute("""
        UPDATE contracts SET status = LOWER(status)
    """)

    # Step 3 — drop old enum type
    op.execute("DROP TYPE contractstatus")

    # Step 4 — create new enum with correct lowercase values
    op.execute("""
        CREATE TYPE contractstatus AS ENUM (
            'draft',
            'pending',
            'signed',
            'deposit_received',
            'paid_in_full',
            'cancelled'
        )
    """)

    # Step 5 — restore column with new enum type and default
    op.execute("""
        ALTER TABLE contracts
        ALTER COLUMN status TYPE contractstatus
        USING status::contractstatus
    """)

    op.execute("""
        ALTER TABLE contracts
        ALTER COLUMN status SET DEFAULT 'draft'
    """)


def downgrade() -> None:
    pass