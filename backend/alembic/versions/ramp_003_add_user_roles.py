"""Add user roles table for auth

Revision ID: ramp_003
Revises: ramp_002
Create Date: 2026-03-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers
revision = 'ramp_003'
down_revision = 'ramp_002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create user_roles table for RAMP authentication.
    
    Role types:
    - operator: HOW lens access, can log interventions, scoped to assigned sites
    - portfolio: WHERE lens access, cross-site analytics, no intervention capability
    - admin: Full access to both lenses, user management, system configuration
    
    Scope:
    - organisation_id: Required for all roles, limits data visibility
    - site_ids: Array of site IDs for operator/portfolio (optional for admin = all sites)
    """
    op.create_table(
        'ramp_user_roles',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False, unique=True, comment='References Supabase auth.users.id'),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('role', sa.String(50), nullable=False, comment='operator | portfolio | admin'),
        sa.Column('organisation_id', sa.String(36), nullable=False, comment='Scope: organisation'),
        sa.Column('site_ids', sa.JSON, nullable=True, comment='Scope: array of site IDs (null = all sites for admin)'),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', sa.String(36), nullable=True, comment='Admin who created this role assignment'),
    )
    
    # Indexes for common queries
    op.create_index('idx_user_roles_user_id', 'ramp_user_roles', ['user_id'])
    op.create_index('idx_user_roles_role', 'ramp_user_roles', ['role'])
    op.create_index('idx_user_roles_organisation', 'ramp_user_roles', ['organisation_id'])
    op.create_index('idx_user_roles_email', 'ramp_user_roles', ['email'])


def downgrade() -> None:
    op.drop_index('idx_user_roles_email')
    op.drop_index('idx_user_roles_organisation')
    op.drop_index('idx_user_roles_role')
    op.drop_index('idx_user_roles_user_id')
    op.drop_table('ramp_user_roles')
