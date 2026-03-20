"""
RAMP SQLAlchemy Models
======================

Relational schema for RAMP Command Centre.
Migrated from MongoDB/Pydantic to PostgreSQL/SQLAlchemy.

Migration order (dependency):
1. organisations
2. sites
3. systems
4. assets
5. rules
6. signals, metrics
7. baselines
8. states
9. priorities
10. interventions
11. outcomes
12. events
13. learning
"""

from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime, Text,
    ForeignKey, Index, Enum as SQLEnum, CheckConstraint
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid
import enum

from database import Base


# =============================================================================
# ENUMS
# =============================================================================

class AssetClass(str, enum.Enum):
    COMPRESSOR = "COMPRESSOR"
    HVAC = "HVAC"
    PUMP = "PUMP"
    BOILER = "BOILER"
    MOTOR = "MOTOR"
    LIGHTING = "LIGHTING"
    GENERIC = "GENERIC"


class SiteCategory(str, enum.Enum):
    MANUFACTURING = "MANUFACTURING"
    COMMERCIAL = "COMMERCIAL"
    INDUSTRIAL = "INDUSTRIAL"
    LOGISTICS = "LOGISTICS"
    OTHER = "OTHER"


class StateFamily(str, enum.Enum):
    OPERATIONAL = "OPERATIONAL"
    ENERGY = "ENERGY"
    MAINTENANCE = "MAINTENANCE"
    PRODUCTION = "PRODUCTION"


class SeverityBand(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ConfidenceBand(str, enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INSUFFICIENT = "INSUFFICIENT"


class PriorityBand(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class PriorityType(str, enum.Enum):
    OPERATIONAL = "OPERATIONAL"
    MAINTENANCE = "MAINTENANCE"
    OPPORTUNITY = "OPPORTUNITY"
    RISK = "RISK"


class SignalQuality(str, enum.Enum):
    GOOD = "GOOD"
    DEGRADED = "DEGRADED"
    MISSING = "MISSING"


class OutcomeStatus(str, enum.Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


# =============================================================================
# HELPER
# =============================================================================

def generate_uuid():
    return str(uuid.uuid4())


# =============================================================================
# PHASE 1: FOUNDATION
# =============================================================================

class Organisation(Base):
    __tablename__ = 'ramp_organisations'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    sites = relationship('Site', back_populates='organisation', cascade='all, delete-orphan')


class Site(Base):
    __tablename__ = 'ramp_sites'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    organisation_id = Column(String(36), ForeignKey('organisations.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    timezone = Column(String(50), nullable=False)
    currency = Column(String(3), default='USD')
    
    # Economic inputs
    energy_tariff = Column(Float, nullable=True)  # Optional, default 0.12
    hourly_production_value = Column(Float, nullable=True)  # Optional, default 500
    production_margin_per_unit = Column(Float, nullable=True)
    
    # Operating context
    operating_hours_per_day = Column(Float, default=24.0)
    site_category = Column(String(50), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    organisation = relationship('Organisation', back_populates='sites')
    systems = relationship('System', back_populates='site', cascade='all, delete-orphan')


class System(Base):
    __tablename__ = 'ramp_systems'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    site_id = Column(String(36), ForeignKey('sites.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    site = relationship('Site', back_populates='systems')
    assets = relationship('Asset', back_populates='system', cascade='all, delete-orphan')


class Asset(Base):
    __tablename__ = 'ramp_assets'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    system_id = Column(String(36), ForeignKey('systems.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    asset_class = Column(String(50), default='GENERIC')
    criticality_score = Column(Float, default=50.0)
    estimated_repair_cost = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    system = relationship('System', back_populates='assets')
    signals = relationship('Signal', back_populates='asset', cascade='all, delete-orphan')
    metrics = relationship('Metric', back_populates='asset', cascade='all, delete-orphan')
    baselines = relationship('Baseline', back_populates='asset', cascade='all, delete-orphan')
    states = relationship('State', back_populates='asset', cascade='all, delete-orphan')


# =============================================================================
# PHASE 2: CONFIGURATION
# =============================================================================

class Rule(Base):
    __tablename__ = 'ramp_rules'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    state_family = Column(String(50), nullable=False, index=True)
    state_type = Column(String(50), nullable=False, index=True)
    
    metric_type = Column(String(100), nullable=False)
    operator = Column(String(10), nullable=False)  # gt, lt, gte, lte
    threshold_multiplier = Column(Float, nullable=False)
    duration_threshold_minutes = Column(Integer, nullable=False)
    
    severity_base = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    states = relationship('State', back_populates='rule')


# =============================================================================
# PHASE 3: INGESTION
# =============================================================================

class Signal(Base):
    __tablename__ = 'ramp_signals'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    asset_id = Column(String(36), ForeignKey('assets.id', ondelete='CASCADE'), nullable=False, index=True)
    signal_type = Column(String(100), nullable=False, index=True)
    value = Column(Float, nullable=False)
    unit = Column(String(50), default='')
    quality = Column(String(20), default='GOOD')
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    ingested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    asset = relationship('Asset', back_populates='signals')
    
    __table_args__ = (
        Index('ix_signals_asset_timestamp', 'asset_id', 'timestamp'),
    )


class Metric(Base):
    __tablename__ = 'ramp_metrics'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    asset_id = Column(String(36), ForeignKey('assets.id', ondelete='CASCADE'), nullable=False, index=True)
    metric_type = Column(String(100), nullable=False, index=True)
    value = Column(Float, nullable=False)
    unit = Column(String(50), default='')
    context_signature = Column(JSONB, default=dict)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    calculated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    asset = relationship('Asset', back_populates='metrics')
    
    __table_args__ = (
        Index('ix_metrics_asset_type_timestamp', 'asset_id', 'metric_type', 'timestamp'),
    )


# =============================================================================
# PHASE 4: CORE LOOP
# =============================================================================

class Baseline(Base):
    __tablename__ = 'ramp_baselines'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    asset_id = Column(String(36), ForeignKey('assets.id', ondelete='CASCADE'), nullable=False, index=True)
    metric_type = Column(String(100), nullable=False, index=True)
    context_signature = Column(JSONB, default=dict)
    
    baseline_value = Column(Float, nullable=False)
    baseline_min = Column(Float, nullable=False)
    baseline_max = Column(Float, nullable=False)
    
    confidence = Column(Float, nullable=False)
    confidence_band = Column(String(20), default='MEDIUM')
    
    valid_from = Column(DateTime(timezone=True), nullable=False)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    
    sample_count = Column(Integer, default=0)
    data_window_days = Column(Integer, default=14)
    
    # Freeze tracking
    frozen_at = Column(DateTime(timezone=True), nullable=True)
    frozen_for_intervention_id = Column(String(36), nullable=True)  # FK added after interventions table
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    asset = relationship('Asset', back_populates='baselines')
    
    __table_args__ = (
        Index('ix_baselines_asset_metric_context', 'asset_id', 'metric_type'),
        Index('ix_baselines_frozen', 'frozen_for_intervention_id'),
    )


class State(Base):
    __tablename__ = 'ramp_states'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    asset_id = Column(String(36), ForeignKey('assets.id', ondelete='CASCADE'), nullable=False, index=True)
    rule_id = Column(String(36), ForeignKey('rules.id', ondelete='SET NULL'), nullable=True, index=True)
    baseline_id = Column(String(36), ForeignKey('baselines.id', ondelete='SET NULL'), nullable=True, index=True)
    
    state_family = Column(String(50), nullable=False, index=True)
    state_type = Column(String(50), nullable=False, index=True)
    
    severity_score = Column(Integer, nullable=False)
    severity_band = Column(String(20), nullable=False)
    severity_components = Column(JSONB, default=dict)
    
    confidence = Column(Float, nullable=False)
    confidence_band = Column(String(20), nullable=False)
    confidence_components = Column(JSONB, default=dict)
    
    deviation_percent = Column(Float, nullable=True)
    
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True, index=True)
    duration_minutes = Column(Integer, default=0)
    
    resolution_type = Column(String(50), nullable=True)
    transitioned_to_state_id = Column(String(36), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    asset = relationship('Asset', back_populates='states')
    rule = relationship('Rule', back_populates='states')
    baseline = relationship('Baseline')
    priorities = relationship('Priority', back_populates='state', cascade='all, delete-orphan')
    interventions = relationship('Intervention', back_populates='state', cascade='all, delete-orphan')
    
    __table_args__ = (
        Index('ix_states_asset_active', 'asset_id', 'ended_at'),
    )


class Priority(Base):
    __tablename__ = 'ramp_priorities'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    state_id = Column(String(36), ForeignKey('states.id', ondelete='CASCADE'), nullable=False, index=True)
    asset_id = Column(String(36), ForeignKey('assets.id', ondelete='CASCADE'), nullable=False, index=True)
    
    priority_score = Column(Float, nullable=False)  # SYSTEM only
    priority_band = Column(String(20), nullable=False, index=True)
    priority_type = Column(String(20), nullable=False)
    
    drivers = Column(JSONB, default=list)  # Array of strings
    economic_impact = Column(JSONB, default=dict)
    score_components = Column(JSONB, default=dict)  # SYSTEM only
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Relationships
    state = relationship('State', back_populates='priorities')
    asset = relationship('Asset')
    
    __table_args__ = (
        Index('ix_priorities_active', 'expires_at', 'priority_band'),
    )


class Intervention(Base):
    __tablename__ = 'ramp_interventions'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    state_id = Column(String(36), ForeignKey('states.id', ondelete='CASCADE'), nullable=False, index=True)
    priority_id = Column(String(36), ForeignKey('priorities.id', ondelete='SET NULL'), nullable=True)
    asset_id = Column(String(36), ForeignKey('assets.id', ondelete='CASCADE'), nullable=False, index=True)
    frozen_baseline_id = Column(String(36), ForeignKey('baselines.id', ondelete='SET NULL'), nullable=True)
    
    intervention_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    created_by = Column(String(100), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    state = relationship('State', back_populates='interventions')
    priority = relationship('Priority')
    asset = relationship('Asset')
    frozen_baseline = relationship('Baseline')
    outcomes = relationship('Outcome', back_populates='intervention', cascade='all, delete-orphan')


class Outcome(Base):
    __tablename__ = 'ramp_outcomes'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    intervention_id = Column(String(36), ForeignKey('interventions.id', ondelete='CASCADE'), nullable=False, index=True)
    frozen_baseline_id = Column(String(36), ForeignKey('baselines.id', ondelete='SET NULL'), nullable=True)
    
    verification_window_start = Column(DateTime(timezone=True), nullable=False)
    verification_window_end = Column(DateTime(timezone=True), nullable=False)
    
    frozen_baseline_value = Column(Float, nullable=False)
    actual_value = Column(Float, nullable=True)
    
    savings_value = Column(Float, nullable=True)
    savings_unit = Column(String(50), nullable=True)
    savings_type = Column(String(50), nullable=True)
    
    confidence = Column(Float, nullable=True)
    confidence_band = Column(String(20), nullable=True)
    
    status = Column(String(20), default='PENDING', index=True)  # PENDING, VERIFIED, INSUFFICIENT_DATA
    
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verification_notes = Column(Text, nullable=True)
    
    # Relationships
    intervention = relationship('Intervention', back_populates='outcomes')
    frozen_baseline = relationship('Baseline')


# =============================================================================
# PHASE 5: AUDIT & LEARNING
# =============================================================================

class Event(Base):
    """
    Immutable audit trail.
    No UPDATE or DELETE allowed - enforced via trigger.
    """
    __tablename__ = 'ramp_events'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    event_type = Column(String(50), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(String(36), nullable=False, index=True)
    payload = Column(JSONB, default=dict)
    correlation_id = Column(String(36), nullable=True, index=True)
    caused_by_event_id = Column(String(36), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    __table_args__ = (
        Index('ix_events_entity', 'entity_type', 'entity_id'),
        Index('ix_events_correlation', 'correlation_id', 'created_at'),
    )


class Learning(Base):
    __tablename__ = 'ramp_learning'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    asset_id = Column(String(36), ForeignKey('assets.id', ondelete='CASCADE'), nullable=False, index=True)
    state_type = Column(String(50), nullable=False, index=True)
    
    occurrence_count = Column(Integer, default=0)
    intervention_count = Column(Integer, default=0)
    total_savings = Column(Float, default=0.0)
    avg_effectiveness = Column(Float, default=0.0)
    
    first_occurred_at = Column(DateTime(timezone=True), nullable=True)
    last_occurred_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    __table_args__ = (
        Index('ix_learning_asset_state', 'asset_id', 'state_type', unique=True),
    )
