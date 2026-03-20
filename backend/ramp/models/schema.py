"""
RAMP Command Centre MVP - Locked Data Schema
=============================================

Phase 0.1: Data Model

This schema is LOCKED for MVP. Changes require explicit approval.

Hierarchy:
    Organisation → Site → System → Asset → Signal/Metric/Baseline

Behavioral Truth:
    Signal (input) → Metric (derived) → Baseline (reference) → State (truth)

Action Loop:
    State → Priority → Intervention → Outcome

Audit:
    Event (immutable record of all state changes)
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, timezone
from enum import Enum
import uuid


# =============================================================================
# ENUMS - Locked for MVP
# =============================================================================

class AssetClass(str, Enum):
    COMPRESSOR = "COMPRESSOR"
    HVAC = "HVAC"
    PUMP = "PUMP"
    BOILER = "BOILER"
    MOTOR = "MOTOR"
    LIGHTING = "LIGHTING"
    GENERIC = "GENERIC"


class SiteCategory(str, Enum):
    MANUFACTURING = "MANUFACTURING"
    COMMERCIAL = "COMMERCIAL"
    INDUSTRIAL = "INDUSTRIAL"
    LOGISTICS = "LOGISTICS"
    OTHER = "OTHER"


class StateFamily(str, Enum):
    OPERATIONAL = "OPERATIONAL"
    ENERGY = "ENERGY"
    MAINTENANCE = "MAINTENANCE"
    PRODUCTION = "PRODUCTION"


class EnergyStateType(str, Enum):
    BASELINE = "BASELINE"
    DRIFT = "DRIFT"
    SPIKE = "SPIKE"
    OVERCONSUMPTION = "OVERCONSUMPTION"
    UNDERUTILISATION = "UNDERUTILISATION"


class OperationalStateType(str, Enum):
    OFF = "OFF"
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    FAULT = "FAULT"
    STARTUP = "STARTUP"
    CHANGEOVER = "CHANGEOVER"


class MaintenanceStateType(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADING = "DEGRADING"
    ALERT = "ALERT"
    FAILURE = "FAILURE"


class ProductionStateType(str, Enum):
    NORMAL = "NORMAL"
    BOTTLENECKED = "BOTTLENECKED"
    PAUSED = "PAUSED"
    IMBALANCED = "IMBALANCED"


class SeverityBand(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ConfidenceBand(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INSUFFICIENT = "INSUFFICIENT"


class PriorityBand(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class PriorityType(str, Enum):
    OPERATIONAL = "OPERATIONAL"
    MAINTENANCE = "MAINTENANCE"
    OPPORTUNITY = "OPPORTUNITY"
    RISK = "RISK"


class EventType(str, Enum):
    # Ingestion events
    SIGNAL_INGESTED = "signal_ingested"
    METRIC_CALCULATED = "metric_calculated"
    # Baseline events
    BASELINE_UPDATED = "baseline_updated"
    BASELINE_FROZEN = "baseline_frozen"
    # State events
    STATE_STARTED = "state_started"
    STATE_UPDATED = "state_updated"
    STATE_ENDED = "state_ended"
    # Priority events
    PRIORITY_CREATED = "priority_created"
    PRIORITY_UPDATED = "priority_updated"
    # Intervention events
    INTERVENTION_CREATED = "intervention_created"
    INTERVENTION_COMPLETED = "intervention_completed"
    # Verification events
    OUTCOME_VERIFIED = "outcome_verified"
    # Learning events
    LEARNING_UPDATED = "learning_updated"


class SignalQuality(str, Enum):
    GOOD = "GOOD"
    DEGRADED = "DEGRADED"
    MISSING = "MISSING"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def generate_id() -> str:
    """Generate a unique ID for entities."""
    return str(uuid.uuid4())


def now_utc() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


# =============================================================================
# BASE MODEL
# =============================================================================

class RAMPBaseModel(BaseModel):
    """Base model for all RAMP entities."""
    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=True,
        json_encoders={datetime: lambda v: v.isoformat()}
    )


# =============================================================================
# ORGANISATION HIERARCHY
# =============================================================================

class Organisation(RAMPBaseModel):
    """Tenant root entity."""
    id: str = Field(default_factory=generate_id)
    name: str
    created_at: datetime = Field(default_factory=now_utc)


class Site(RAMPBaseModel):
    """Physical location with configuration."""
    id: str = Field(default_factory=generate_id)
    organisation_id: str
    name: str
    timezone: str  # IANA timezone
    currency: str = "USD"  # ISO 4217
    
    # Economic inputs (optional with defaults)
    energy_tariff: Optional[float] = None  # $/kWh, default 0.12 if None
    hourly_production_value: Optional[float] = None  # $/hr, default 500 if None
    production_margin_per_unit: Optional[float] = None  # Required for production states
    
    # Operating context
    operating_hours_per_day: float = 24.0  # Projection default
    site_category: Optional[SiteCategory] = None
    
    created_at: datetime = Field(default_factory=now_utc)
    
    @property
    def effective_energy_tariff(self) -> float:
        """Return configured tariff or V1 default."""
        return self.energy_tariff if self.energy_tariff is not None else 0.12
    
    @property
    def effective_hourly_production_value(self) -> float:
        """Return configured value or V1 default."""
        return self.hourly_production_value if self.hourly_production_value is not None else 500.0


class System(RAMPBaseModel):
    """Logical grouping of assets."""
    id: str = Field(default_factory=generate_id)
    site_id: str
    name: str
    created_at: datetime = Field(default_factory=now_utc)


class Asset(RAMPBaseModel):
    """Physical equipment being monitored."""
    id: str = Field(default_factory=generate_id)
    system_id: str
    name: str
    asset_class: AssetClass = AssetClass.GENERIC
    
    # Criticality (semi-static, can be overridden)
    criticality_score: float = 50.0  # 0-100, default MEDIUM
    
    # Repair cost override (optional, else use asset class default)
    estimated_repair_cost: Optional[float] = None
    
    created_at: datetime = Field(default_factory=now_utc)
    
    @property
    def criticality_band(self) -> str:
        """Derive band from score."""
        if self.criticality_score >= 80:
            return "CRITICAL"
        elif self.criticality_score >= 60:
            return "HIGH"
        elif self.criticality_score >= 40:
            return "MEDIUM"
        return "LOW"


# =============================================================================
# SIGNALS AND METRICS
# =============================================================================

class Signal(RAMPBaseModel):
    """Raw sensor reading - INPUT to the system."""
    id: str = Field(default_factory=generate_id)
    asset_id: str
    signal_type: str  # e.g., "energy_consumption", "temperature", "vibration"
    value: float
    unit: str  # e.g., "kWh", "C", "mm/s"
    quality: SignalQuality = SignalQuality.GOOD
    timestamp: datetime
    ingested_at: datetime = Field(default_factory=now_utc)


class Metric(RAMPBaseModel):
    """Derived measurement - calculated from signals."""
    id: str = Field(default_factory=generate_id)
    asset_id: str
    metric_type: str  # e.g., "energy_intensity", "load_factor"
    value: float
    unit: str
    
    # Context for baseline segmentation
    context_signature: Dict[str, Any] = Field(default_factory=dict)
    # e.g., {"runtime_state": "RUNNING", "production_band": "HIGH"}
    
    timestamp: datetime
    calculated_at: datetime = Field(default_factory=now_utc)


# =============================================================================
# BASELINE - FIRST CLASS ENGINE
# =============================================================================

class Baseline(RAMPBaseModel):
    """
    Reference for normal behavior - FIRST CLASS PRIMITIVE.
    
    Baselines make deviation, drift, savings, and verification meaningful.
    Without baseline, states cannot be assigned.
    """
    id: str = Field(default_factory=generate_id)
    asset_id: str
    metric_type: str
    
    # Context this baseline applies to
    context_signature: Dict[str, Any] = Field(default_factory=dict)
    
    # Baseline values
    baseline_value: float
    baseline_min: float  # Lower bound of acceptable range
    baseline_max: float  # Upper bound of acceptable range
    
    # Confidence in this baseline
    confidence: float  # 0-1
    confidence_band: ConfidenceBand = ConfidenceBand.MEDIUM
    
    # Validity window
    valid_from: datetime
    valid_until: Optional[datetime] = None
    
    # Data quality indicators
    sample_count: int  # Number of data points used
    data_window_days: int  # Days of history used
    
    # Freeze tracking (for intervention verification)
    frozen_at: Optional[datetime] = None
    frozen_for_intervention_id: Optional[str] = None
    
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


# =============================================================================
# RULES AND STATES
# =============================================================================

class Rule(RAMPBaseModel):
    """
    Threshold definition for state detection.
    
    Rules evaluate metrics against baselines and create states.
    A rule does NOT equal a state - a rule creates or updates a state.
    """
    id: str = Field(default_factory=generate_id)
    name: str
    description: Optional[str] = None
    
    # What this rule detects
    state_family: StateFamily
    state_type: str  # One of the state type enums
    
    # Condition expression (simplified for MVP)
    metric_type: str
    operator: Literal["gt", "lt", "gte", "lte"]  # greater than, less than, etc.
    threshold_multiplier: float  # e.g., 1.15 means baseline * 1.15
    duration_threshold_minutes: int  # How long condition must persist
    
    # Severity assignment
    severity_base: int  # 1-10
    
    # Active flag
    is_active: bool = True
    
    created_at: datetime = Field(default_factory=now_utc)


class State(RAMPBaseModel):
    """
    Detected condition - THE BEHAVIORAL TRUTH.
    
    States are time-bound operational facts derived from rules
    acting on baseline-relative behavior.
    
    States are the primary truth of the system, not metrics.
    """
    id: str = Field(default_factory=generate_id)
    asset_id: str
    rule_id: str
    
    # State classification
    state_family: StateFamily
    state_type: str
    
    # Severity (constructed from base + modifiers)
    severity_score: int  # 1-10
    severity_band: SeverityBand
    severity_components: Dict[str, int] = Field(default_factory=dict)
    # {"base": 4, "duration_modifier": 1, "deviation_modifier": 1}
    
    # Confidence (constructed from data quality + baseline + context)
    confidence: float  # 0-1
    confidence_band: ConfidenceBand
    confidence_components: Dict[str, float] = Field(default_factory=dict)
    # {"data_quality": 0.95, "baseline_confidence": 0.80, "context_validity": 0.90}
    
    # Deviation from baseline
    deviation_percent: Optional[float] = None
    baseline_id: str  # Reference to the baseline used
    
    # Lifecycle
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_minutes: int = 0
    
    # Resolution
    resolution_type: Optional[str] = None  # "returned_to_baseline", "transitioned", "manual"
    transitioned_to_state_id: Optional[str] = None
    
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


# =============================================================================
# PRIORITY
# =============================================================================

class EconomicImpact(RAMPBaseModel):
    """Economic impact calculation - VaR and VR kept separate."""
    value_at_risk_per_day: float  # Current cost
    value_recoverable_per_day: float  # Potential savings
    currency: str = "USD"
    calculation_method: str  # "ENERGY_DEVIATION", "MAINTENANCE_DOWNTIME", etc.
    confidence: ConfidenceBand = ConfidenceBand.MEDIUM
    
    inputs: Dict[str, Any] = Field(default_factory=dict)
    # Raw inputs used for calculation (SYSTEM lens only)


class Priority(RAMPBaseModel):
    """
    Ranked action item - what needs attention.
    
    Priority combines severity, economic impact, criticality,
    and confidence to answer: "What matters most right now?"
    """
    id: str = Field(default_factory=generate_id)
    state_id: str
    asset_id: str
    
    # Priority scoring (SYSTEM only - not exposed raw)
    priority_score: float  # 0-100, internal use
    priority_band: PriorityBand
    priority_type: PriorityType
    
    # Explainable drivers (exposed to users)
    drivers: List[str]  # Human-readable reasons
    
    # Economic impact (VaR and VR separate)
    economic_impact: EconomicImpact
    
    # Component scores (SYSTEM only)
    score_components: Dict[str, float] = Field(default_factory=dict)
    # {"severity": 21, "economic": 16.25, "risk": 6, "criticality": 12, "confidence": 8.5, "friction": -1}
    
    # Lifecycle
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
    expires_at: Optional[datetime] = None


# =============================================================================
# INTERVENTION AND OUTCOME
# =============================================================================

class Intervention(RAMPBaseModel):
    """
    Action taken by user in response to state/priority.
    
    When intervention is created, the baseline is frozen.
    """
    id: str = Field(default_factory=generate_id)
    state_id: str
    priority_id: Optional[str] = None
    asset_id: str
    
    # Intervention details
    intervention_type: str  # "adjustment", "repair", "replacement", etc.
    description: str
    
    # User tracking
    created_by: str  # User ID
    
    # Lifecycle
    created_at: datetime = Field(default_factory=now_utc)
    completed_at: Optional[datetime] = None
    
    # Linked frozen baseline
    frozen_baseline_id: Optional[str] = None


class Outcome(RAMPBaseModel):
    """
    Verified result of intervention.
    
    Compares post-action behavior to frozen baseline
    to calculate actual savings.
    """
    id: str = Field(default_factory=generate_id)
    intervention_id: str
    
    # Verification window
    verification_window_start: datetime
    verification_window_end: datetime
    
    # Baseline reference
    frozen_baseline_id: str
    frozen_baseline_value: float
    
    # Post-intervention performance
    actual_value: float
    
    # Calculated savings
    savings_value: float
    savings_unit: str  # "kWh", "$", etc.
    savings_type: str  # "energy", "cost", "demand"
    
    # Confidence in verification
    confidence: float  # 0-1
    confidence_band: ConfidenceBand
    
    # Verification status
    verified_at: datetime = Field(default_factory=now_utc)
    verification_notes: Optional[str] = None


# =============================================================================
# EVENTS - AUDIT TRAIL
# =============================================================================

class Event(RAMPBaseModel):
    """
    Immutable record of state change.
    
    All inter-service communication flows through events.
    Events are the audit trail of the system.
    """
    id: str = Field(default_factory=generate_id)
    event_type: EventType
    
    # What entity this event relates to
    entity_type: str  # "signal", "metric", "baseline", "state", etc.
    entity_id: str
    
    # Event payload (type-specific data)
    payload: Dict[str, Any] = Field(default_factory=dict)
    
    # Correlation for event chains
    correlation_id: Optional[str] = None
    caused_by_event_id: Optional[str] = None
    
    # Timestamp
    created_at: datetime = Field(default_factory=now_utc)


# =============================================================================
# COLLECTIONS (MongoDB)
# =============================================================================

COLLECTIONS = {
    "organisations": Organisation,
    "sites": Site,
    "systems": System,
    "assets": Asset,
    "signals": Signal,
    "metrics": Metric,
    "baselines": Baseline,
    "rules": Rule,
    "states": State,
    "priorities": Priority,
    "interventions": Intervention,
    "outcomes": Outcome,
    "events": Event,
}
