# RAMP Services
# Phase 0.2: Service Boundaries - LOCKED

"""
Service Ownership (LOCKED for MVP)
==================================

Each service has clear, non-overlapping responsibility.

Ingestion Service
    - Receives raw signals
    - Calculates metrics from signals
    - Emits: signal_ingested, metric_calculated

Baseline Engine
    - Establishes baselines from metric history
    - Calculates deviation from baseline
    - Freezes baseline on intervention
    - Emits: baseline_updated, baseline_frozen

State Engine
    - Evaluates rules against baselines
    - Creates and transitions states
    - Assigns severity and confidence
    - Emits: state_started, state_updated, state_ended

Priority Engine
    - Calculates priority from state + context
    - Assigns priority band and drivers
    - Calculates economic impact (VaR, VR)
    - Emits: priority_created, priority_updated

Intervention Service
    - Captures user actions
    - Links intervention to state/priority
    - Triggers baseline freeze
    - Emits: intervention_created, intervention_completed

Verification Engine
    - Compares post-action metrics to frozen baseline
    - Calculates verified savings
    - Assigns verification confidence
    - Emits: outcome_verified

Learning Engine (partial MVP)
    - Tracks state recurrence
    - Tracks intervention effectiveness
    - Emits: learning_updated
"""

from .ingestion import IngestionService
from .baseline import BaselineEngine
from .state import StateEngine
from .priority import PriorityEngine
from .intervention import InterventionService
from .verification import VerificationEngine
from .learning import LearningEngine

__all__ = [
    "IngestionService",
    "BaselineEngine",
    "StateEngine",
    "PriorityEngine",
    "InterventionService",
    "VerificationEngine",
    "LearningEngine",
]
