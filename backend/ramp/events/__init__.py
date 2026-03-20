# RAMP Event System
# Phase 0.3: Event Flow - LOCKED

"""
Event Backbone (LOCKED for MVP)
===============================

All inter-service communication flows through events.
Events are immutable audit records stored in the events collection.

Event Flow:
    1. Service performs action
    2. Service emits event via EventBus
    3. Event stored in database (audit trail)
    4. Event added to processing queue
    5. Subscribed workers pick up event
    6. Workers process and may emit new events

Event Types (MVP Catalogue):
    - signal_ingested
    - metric_calculated
    - baseline_updated
    - baseline_frozen
    - state_started
    - state_updated
    - state_ended
    - priority_created
    - priority_updated
    - intervention_created
    - intervention_completed
    - outcome_verified
    - learning_updated

Rules:
    - Events are immutable once created
    - Events must reflect actual state changes (not hopes)
    - Event payload contains minimum data needed for processing
    - Correlation IDs link related events
"""

from .bus import EventBus
from .handlers import EventHandlers

__all__ = ["EventBus", "EventHandlers"]
