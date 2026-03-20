"""Add retry_count to outcomes

Adds retry_count column for tracking verification retry attempts.

Revision ID: ramp_002
Revises: ramp_001
Create Date: 2026-03-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'ramp_002'
down_revision: Union[str, Sequence[str], None] = 'ramp_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add retry_count column to ramp_outcomes."""
    op.add_column('ramp_outcomes', 
        sa.Column('retry_count', sa.Integer(), default=0, nullable=True)
    )
    
    # Set default value for existing rows
    op.execute("UPDATE ramp_outcomes SET retry_count = 0 WHERE retry_count IS NULL")


def downgrade() -> None:
    """Remove retry_count column."""
    op.drop_column('ramp_outcomes', 'retry_count')
