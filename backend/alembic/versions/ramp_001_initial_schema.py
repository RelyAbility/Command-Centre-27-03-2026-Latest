"""RAMP Initial Schema

Creates all RAMP Command Centre tables.
Does NOT drop any existing tables.

Revision ID: ramp_001
Revises: 
Create Date: 2026-03-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'ramp_001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create RAMP tables in dependency order."""
    
    # =================================================================
    # PHASE 1: Foundation
    # =================================================================
    
    # organisations
    op.create_table('ramp_organisations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    
    # sites
    op.create_table('ramp_sites',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organisation_id', sa.String(36), sa.ForeignKey('ramp_organisations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('timezone', sa.String(50), nullable=False),
        sa.Column('currency', sa.String(3), default='USD'),
        sa.Column('energy_tariff', sa.Float(), nullable=True),
        sa.Column('hourly_production_value', sa.Float(), nullable=True),
        sa.Column('production_margin_per_unit', sa.Float(), nullable=True),
        sa.Column('operating_hours_per_day', sa.Float(), default=24.0),
        sa.Column('site_category', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_ramp_sites_organisation_id', 'ramp_sites', ['organisation_id'])
    
    # systems
    op.create_table('ramp_systems',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('site_id', sa.String(36), sa.ForeignKey('ramp_sites.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_ramp_systems_site_id', 'ramp_systems', ['site_id'])
    
    # assets
    op.create_table('ramp_assets',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('system_id', sa.String(36), sa.ForeignKey('ramp_systems.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('asset_class', sa.String(50), default='GENERIC'),
        sa.Column('criticality_score', sa.Float(), default=50.0),
        sa.Column('estimated_repair_cost', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_ramp_assets_system_id', 'ramp_assets', ['system_id'])
    
    # =================================================================
    # PHASE 2: Configuration
    # =================================================================
    
    # rules
    op.create_table('ramp_rules',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('state_family', sa.String(50), nullable=False),
        sa.Column('state_type', sa.String(50), nullable=False),
        sa.Column('metric_type', sa.String(100), nullable=False),
        sa.Column('operator', sa.String(10), nullable=False),
        sa.Column('threshold_multiplier', sa.Float(), nullable=False),
        sa.Column('duration_threshold_minutes', sa.Integer(), nullable=False),
        sa.Column('severity_base', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_ramp_rules_state_family', 'ramp_rules', ['state_family'])
    op.create_index('ix_ramp_rules_is_active', 'ramp_rules', ['is_active'])
    
    # =================================================================
    # PHASE 3: Ingestion
    # =================================================================
    
    # signals
    op.create_table('ramp_signals',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('asset_id', sa.String(36), sa.ForeignKey('ramp_assets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('signal_type', sa.String(100), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(50), default=''),
        sa.Column('quality', sa.String(20), default='GOOD'),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ingested_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_ramp_signals_asset_id', 'ramp_signals', ['asset_id'])
    op.create_index('ix_ramp_signals_asset_timestamp', 'ramp_signals', ['asset_id', 'timestamp'])
    
    # metrics
    op.create_table('ramp_metrics',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('asset_id', sa.String(36), sa.ForeignKey('ramp_assets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('metric_type', sa.String(100), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(50), default=''),
        sa.Column('context_signature', postgresql.JSONB(), default={}),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('calculated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_ramp_metrics_asset_id', 'ramp_metrics', ['asset_id'])
    op.create_index('ix_ramp_metrics_asset_type_ts', 'ramp_metrics', ['asset_id', 'metric_type', 'timestamp'])
    
    # =================================================================
    # PHASE 4: Core Loop
    # =================================================================
    
    # baselines
    op.create_table('ramp_baselines',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('asset_id', sa.String(36), sa.ForeignKey('ramp_assets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('metric_type', sa.String(100), nullable=False),
        sa.Column('context_signature', postgresql.JSONB(), default={}),
        sa.Column('baseline_value', sa.Float(), nullable=False),
        sa.Column('baseline_min', sa.Float(), nullable=False),
        sa.Column('baseline_max', sa.Float(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('confidence_band', sa.String(20), default='MEDIUM'),
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=False),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sample_count', sa.Integer(), default=0),
        sa.Column('data_window_days', sa.Integer(), default=14),
        sa.Column('frozen_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('frozen_for_intervention_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_ramp_baselines_asset_id', 'ramp_baselines', ['asset_id'])
    op.create_index('ix_ramp_baselines_asset_metric', 'ramp_baselines', ['asset_id', 'metric_type'])
    op.create_index('ix_ramp_baselines_frozen', 'ramp_baselines', ['frozen_for_intervention_id'])
    
    # states
    op.create_table('ramp_states',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('asset_id', sa.String(36), sa.ForeignKey('ramp_assets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('rule_id', sa.String(36), sa.ForeignKey('ramp_rules.id', ondelete='SET NULL'), nullable=True),
        sa.Column('baseline_id', sa.String(36), sa.ForeignKey('ramp_baselines.id', ondelete='SET NULL'), nullable=True),
        sa.Column('state_family', sa.String(50), nullable=False),
        sa.Column('state_type', sa.String(50), nullable=False),
        sa.Column('severity_score', sa.Integer(), nullable=False),
        sa.Column('severity_band', sa.String(20), nullable=False),
        sa.Column('severity_components', postgresql.JSONB(), default={}),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('confidence_band', sa.String(20), nullable=False),
        sa.Column('confidence_components', postgresql.JSONB(), default={}),
        sa.Column('deviation_percent', sa.Float(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), default=0),
        sa.Column('resolution_type', sa.String(50), nullable=True),
        sa.Column('transitioned_to_state_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_ramp_states_asset_id', 'ramp_states', ['asset_id'])
    op.create_index('ix_ramp_states_asset_active', 'ramp_states', ['asset_id', 'ended_at'])
    op.create_index('ix_ramp_states_baseline_id', 'ramp_states', ['baseline_id'])
    
    # priorities
    op.create_table('ramp_priorities',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('state_id', sa.String(36), sa.ForeignKey('ramp_states.id', ondelete='CASCADE'), nullable=False),
        sa.Column('asset_id', sa.String(36), sa.ForeignKey('ramp_assets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('priority_score', sa.Float(), nullable=False),
        sa.Column('priority_band', sa.String(20), nullable=False),
        sa.Column('priority_type', sa.String(20), nullable=False),
        sa.Column('drivers', postgresql.JSONB(), default=[]),
        sa.Column('economic_impact', postgresql.JSONB(), default={}),
        sa.Column('score_components', postgresql.JSONB(), default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_ramp_priorities_state_id', 'ramp_priorities', ['state_id'])
    op.create_index('ix_ramp_priorities_active', 'ramp_priorities', ['expires_at', 'priority_band'])
    
    # interventions
    op.create_table('ramp_interventions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('state_id', sa.String(36), sa.ForeignKey('ramp_states.id', ondelete='CASCADE'), nullable=False),
        sa.Column('priority_id', sa.String(36), sa.ForeignKey('ramp_priorities.id', ondelete='SET NULL'), nullable=True),
        sa.Column('asset_id', sa.String(36), sa.ForeignKey('ramp_assets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('frozen_baseline_id', sa.String(36), sa.ForeignKey('ramp_baselines.id', ondelete='SET NULL'), nullable=True),
        sa.Column('intervention_type', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('created_by', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_ramp_interventions_state_id', 'ramp_interventions', ['state_id'])
    op.create_index('ix_ramp_interventions_asset_id', 'ramp_interventions', ['asset_id'])
    
    # outcomes
    op.create_table('ramp_outcomes',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('intervention_id', sa.String(36), sa.ForeignKey('ramp_interventions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('frozen_baseline_id', sa.String(36), sa.ForeignKey('ramp_baselines.id', ondelete='SET NULL'), nullable=True),
        sa.Column('verification_window_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('verification_window_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('frozen_baseline_value', sa.Float(), nullable=False),
        sa.Column('actual_value', sa.Float(), nullable=True),
        sa.Column('savings_value', sa.Float(), nullable=True),
        sa.Column('savings_unit', sa.String(50), nullable=True),
        sa.Column('savings_type', sa.String(50), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('confidence_band', sa.String(20), nullable=True),
        sa.Column('status', sa.String(20), default='PENDING'),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('verification_notes', sa.Text(), nullable=True),
    )
    op.create_index('ix_ramp_outcomes_intervention_id', 'ramp_outcomes', ['intervention_id'])
    op.create_index('ix_ramp_outcomes_status', 'ramp_outcomes', ['status'])
    
    # =================================================================
    # PHASE 5: Audit & Learning
    # =================================================================
    
    # events (immutable audit trail)
    op.create_table('ramp_events',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', sa.String(36), nullable=False),
        sa.Column('payload', postgresql.JSONB(), default={}),
        sa.Column('correlation_id', sa.String(36), nullable=True),
        sa.Column('caused_by_event_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_ramp_events_event_type', 'ramp_events', ['event_type'])
    op.create_index('ix_ramp_events_entity', 'ramp_events', ['entity_type', 'entity_id'])
    op.create_index('ix_ramp_events_correlation', 'ramp_events', ['correlation_id', 'created_at'])
    
    # learning
    op.create_table('ramp_learning',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('asset_id', sa.String(36), sa.ForeignKey('ramp_assets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('state_type', sa.String(50), nullable=False),
        sa.Column('occurrence_count', sa.Integer(), default=0),
        sa.Column('intervention_count', sa.Integer(), default=0),
        sa.Column('total_savings', sa.Float(), default=0.0),
        sa.Column('avg_effectiveness', sa.Float(), default=0.0),
        sa.Column('first_occurred_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_occurred_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_ramp_learning_asset_state', 'ramp_learning', ['asset_id', 'state_type'], unique=True)
    
    # =================================================================
    # Event Immutability Trigger
    # =================================================================
    op.execute("""
        CREATE OR REPLACE FUNCTION ramp_prevent_event_modification()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'RAMP events are immutable. UPDATE and DELETE are not permitted.';
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    op.execute("""
        CREATE TRIGGER ramp_events_immutable
        BEFORE UPDATE OR DELETE ON ramp_events
        FOR EACH ROW
        EXECUTE FUNCTION ramp_prevent_event_modification();
    """)


def downgrade() -> None:
    """Drop all RAMP tables."""
    op.execute("DROP TRIGGER IF EXISTS ramp_events_immutable ON ramp_events")
    op.execute("DROP FUNCTION IF EXISTS ramp_prevent_event_modification()")
    
    op.drop_table('ramp_learning')
    op.drop_table('ramp_events')
    op.drop_table('ramp_outcomes')
    op.drop_table('ramp_interventions')
    op.drop_table('ramp_priorities')
    op.drop_table('ramp_states')
    op.drop_table('ramp_baselines')
    op.drop_table('ramp_metrics')
    op.drop_table('ramp_signals')
    op.drop_table('ramp_rules')
    op.drop_table('ramp_assets')
    op.drop_table('ramp_systems')
    op.drop_table('ramp_sites')
    op.drop_table('ramp_organisations')
