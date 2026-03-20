"""
RAMP Event Handlers
===================

Phase 0.3: Event Flow - Handler Registration

This module sets up the event flow by registering handlers
for each event type with the appropriate service.

Event Chain:
    signal_ingested → Baseline (deviation check)
    metric_calculated → Baseline (update if stable), State (rule eval)
    baseline_updated → State (re-evaluate rules)
    state_started → Priority (create priority)
    state_updated → Priority (update priority)
    state_ended → Priority (expire priority), Learning (record)
    intervention_created → Baseline (freeze)
    intervention_completed → Verification (start window)
    outcome_verified → Learning (update effectiveness)
"""

from typing import TYPE_CHECKING
import logging

from ..models.schema import EventType

if TYPE_CHECKING:
    from .bus import EventBus
    from ..services import (
        IngestionService,
        BaselineEngine,
        StateEngine,
        PriorityEngine,
        InterventionService,
        VerificationEngine,
        LearningEngine,
    )

logger = logging.getLogger(__name__)


class EventHandlers:
    """
    Central handler registration for RAMP event flow.
    
    Each service registers its handlers here.
    The event bus dispatches to these handlers.
    """
    
    def __init__(
        self,
        event_bus: "EventBus",
        baseline_engine: "BaselineEngine",
        state_engine: "StateEngine",
        priority_engine: "PriorityEngine",
        verification_engine: "VerificationEngine",
        learning_engine: "LearningEngine",
    ):
        self.event_bus = event_bus
        self.baseline_engine = baseline_engine
        self.state_engine = state_engine
        self.priority_engine = priority_engine
        self.verification_engine = verification_engine
        self.learning_engine = learning_engine
    
    def register_all(self):
        """Register all event handlers."""
        
        # Signal ingested → Check for baseline deviation
        self.event_bus.subscribe(
            EventType.SIGNAL_INGESTED,
            self._on_signal_ingested
        )
        
        # Metric calculated → Update baseline if stable, evaluate rules
        self.event_bus.subscribe(
            EventType.METRIC_CALCULATED,
            self._on_metric_calculated
        )
        
        # Baseline updated → Re-evaluate state rules
        self.event_bus.subscribe(
            EventType.BASELINE_UPDATED,
            self._on_baseline_updated
        )
        
        # State started → Create priority
        self.event_bus.subscribe(
            EventType.STATE_STARTED,
            self._on_state_started
        )
        
        # State updated → Update priority
        self.event_bus.subscribe(
            EventType.STATE_UPDATED,
            self._on_state_updated
        )
        
        # State ended → Expire priority, record for learning
        self.event_bus.subscribe(
            EventType.STATE_ENDED,
            self._on_state_ended
        )
        
        # Intervention created → Freeze baseline
        self.event_bus.subscribe(
            EventType.INTERVENTION_CREATED,
            self._on_intervention_created
        )
        
        # Intervention completed → Start verification window
        self.event_bus.subscribe(
            EventType.INTERVENTION_COMPLETED,
            self._on_intervention_completed
        )
        
        # Outcome verified → Update learning
        self.event_bus.subscribe(
            EventType.OUTCOME_VERIFIED,
            self._on_outcome_verified
        )
        
        logger.info("All event handlers registered")
    
    # =========================================================================
    # HANDLER IMPLEMENTATIONS
    # =========================================================================
    
    async def _on_signal_ingested(self, event):
        """Handle signal ingestion - calculate metrics."""
        logger.debug(f"Processing signal_ingested: {event.entity_id}")
        # Baseline engine may need to recalculate deviation
        # This is handled in the ingestion flow
    
    async def _on_metric_calculated(self, event):
        """Handle metric calculation - update baseline and evaluate rules."""
        logger.debug(f"Processing metric_calculated: {event.entity_id}")
        
        payload = event.payload
        asset_id = payload.get("asset_id")
        metric_type = payload.get("metric_type")
        value = payload.get("value")
        context_signature = payload.get("context_signature", {})
        
        # 1. Baseline engine checks if baseline should update
        await self.baseline_engine.on_metric_received(
            asset_id=asset_id,
            metric_type=metric_type,
            value=value,
            context_signature=context_signature,
            correlation_id=event.correlation_id
        )
        
        # 2. State engine evaluates rules
        await self.state_engine.evaluate_rules(
            asset_id=asset_id,
            metric_type=metric_type,
            value=value,
            correlation_id=event.correlation_id
        )
    
    async def _on_baseline_updated(self, event):
        """Handle baseline update - re-evaluate active states."""
        logger.debug(f"Processing baseline_updated: {event.entity_id}")
        
        payload = event.payload
        asset_id = payload.get("asset_id")
        
        # State engine may need to re-evaluate with new baseline
        await self.state_engine.on_baseline_updated(
            asset_id=asset_id,
            baseline_id=event.entity_id,
            correlation_id=event.correlation_id
        )
    
    async def _on_state_started(self, event):
        """Handle state start - create priority."""
        logger.debug(f"Processing state_started: {event.entity_id}")
        
        payload = event.payload
        
        await self.priority_engine.create_priority(
            state_id=event.entity_id,
            asset_id=payload.get("asset_id"),
            state_family=payload.get("state_family"),
            state_type=payload.get("state_type"),
            severity_score=payload.get("severity_score"),
            confidence=payload.get("confidence"),
            correlation_id=event.correlation_id
        )
    
    async def _on_state_updated(self, event):
        """Handle state update - update priority."""
        logger.debug(f"Processing state_updated: {event.entity_id}")
        
        payload = event.payload
        
        await self.priority_engine.update_priority(
            state_id=event.entity_id,
            severity_score=payload.get("severity_score"),
            duration_minutes=payload.get("duration_minutes"),
            correlation_id=event.correlation_id
        )
    
    async def _on_state_ended(self, event):
        """Handle state end - expire priority, record for learning."""
        logger.debug(f"Processing state_ended: {event.entity_id}")
        
        payload = event.payload
        
        # Expire the priority
        await self.priority_engine.expire_priority(
            state_id=event.entity_id,
            correlation_id=event.correlation_id
        )
        
        # Record for learning
        await self.learning_engine.record_state_ended(
            state_id=event.entity_id,
            resolution_type=payload.get("resolution_type"),
            correlation_id=event.correlation_id
        )
    
    async def _on_intervention_created(self, event):
        """Handle intervention creation - freeze baseline."""
        logger.debug(f"Processing intervention_created: {event.entity_id}")
        
        payload = event.payload
        
        await self.baseline_engine.freeze_baseline(
            asset_id=payload.get("asset_id"),
            intervention_id=event.entity_id,
            correlation_id=event.correlation_id
        )
    
    async def _on_intervention_completed(self, event):
        """Handle intervention completion - start verification window."""
        logger.debug(f"Processing intervention_completed: {event.entity_id}")
        
        await self.verification_engine.start_verification(
            intervention_id=event.entity_id,
            correlation_id=event.correlation_id
        )
    
    async def _on_outcome_verified(self, event):
        """Handle outcome verification - update learning."""
        logger.debug(f"Processing outcome_verified: {event.entity_id}")
        
        payload = event.payload
        
        await self.learning_engine.record_outcome(
            intervention_id=payload.get("intervention_id"),
            savings_value=payload.get("savings_value"),
            confidence=payload.get("confidence"),
            correlation_id=event.correlation_id
        )
