"""
RAMP Event Bus
==============

Phase 0.3: Event Flow Implementation

The event bus handles:
1. Event creation and persistence
2. Event queue management
3. Event subscription and dispatch

This is NOT Supabase Realtime - it's a proper application event layer.
"""

from typing import Dict, List, Callable, Any, Optional
from datetime import datetime, timezone
import asyncio
import logging

from ..models.schema import Event, EventType, generate_id, now_utc

logger = logging.getLogger(__name__)


class EventBus:
    """
    Central event management for RAMP.
    
    Responsibilities:
    - Store events (audit trail)
    - Queue events for processing
    - Dispatch to registered handlers
    """
    
    def __init__(self, db):
        """
        Initialize event bus with database connection.
        
        Args:
            db: MongoDB database instance
        """
        self.db = db
        self._handlers: Dict[EventType, List[Callable]] = {}
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False
    
    def subscribe(self, event_type: EventType, handler: Callable):
        """
        Register a handler for an event type.
        
        Args:
            event_type: Type of event to handle
            handler: Async function to call when event occurs
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.info(f"Handler registered for {event_type.value}")
    
    async def emit(
        self,
        event_type: EventType,
        entity_type: str,
        entity_id: str,
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None,
        caused_by_event_id: Optional[str] = None
    ) -> Event:
        """
        Emit an event.
        
        1. Create event record
        2. Store in database (audit trail)
        3. Dispatch to handlers immediately (synchronous for MVP)
        
        Args:
            event_type: Type of event
            entity_type: What entity this relates to
            entity_id: ID of the entity
            payload: Event-specific data
            correlation_id: ID linking related events
            caused_by_event_id: Event that triggered this one
            
        Returns:
            Created event
        """
        # Create event
        event = Event(
            id=generate_id(),
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload,
            correlation_id=correlation_id or generate_id(),
            caused_by_event_id=caused_by_event_id,
            created_at=now_utc()
        )
        
        # Store in database (audit trail - this is permanent)
        event_doc = event.model_dump()
        event_doc["created_at"] = event_doc["created_at"].isoformat()
        await self.db.events.insert_one(event_doc)
        
        logger.info(f"Event emitted: {event_type.value} for {entity_type}/{entity_id}")
        
        # Dispatch immediately (synchronous for MVP)
        # This ensures the full loop executes within a single request
        await self._dispatch(event)
        
        return event
        return event
    
    async def start_processing(self):
        """Start the event processing loop."""
        self._running = True
        logger.info("Event bus processing started")
        
        while self._running:
            try:
                # Wait for event with timeout to allow graceful shutdown
                try:
                    event = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Dispatch to handlers
                await self._dispatch(event)
                
            except Exception as e:
                logger.error(f"Error processing event: {e}")
    
    async def stop_processing(self):
        """Stop the event processing loop."""
        self._running = False
        logger.info("Event bus processing stopped")
    
    async def _dispatch(self, event: Event):
        """
        Dispatch event to registered handlers.
        
        Args:
            event: Event to dispatch
        """
        # Get event type (may be string or enum)
        event_type = event.event_type
        if isinstance(event_type, str):
            try:
                event_type = EventType(event_type)
            except ValueError:
                logger.warning(f"Unknown event type: {event_type}")
                return
        
        handlers = self._handlers.get(event_type, [])
        
        if not handlers:
            event_type_str = event_type.value if hasattr(event_type, 'value') else str(event_type)
            logger.debug(f"No handlers for {event_type_str}")
            return
        
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                event_type_str = event_type.value if hasattr(event_type, 'value') else str(event_type)
                logger.error(f"Handler error for {event_type_str}: {e}", exc_info=True)
    
    async def get_events(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        correlation_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Query events from audit trail.
        
        Args:
            entity_type: Filter by entity type
            entity_id: Filter by entity ID
            event_type: Filter by event type
            correlation_id: Filter by correlation ID
            limit: Max events to return
            
        Returns:
            List of events matching criteria
        """
        query = {}
        
        if entity_type:
            query["entity_type"] = entity_type
        if entity_id:
            query["entity_id"] = entity_id
        if event_type:
            query["event_type"] = event_type.value
        if correlation_id:
            query["correlation_id"] = correlation_id
        
        events = await self.db.events.find(
            query,
            {"_id": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)
        
        return events


# =============================================================================
# EVENT PAYLOADS - Type definitions for each event
# =============================================================================

"""
Event Payload Contracts (LOCKED for MVP)
========================================

Each event type has a defined payload structure.
These are the minimum fields required for downstream processing.

signal_ingested:
    - signal_id: str
    - asset_id: str
    - signal_type: str
    - value: float
    - timestamp: str (ISO)

metric_calculated:
    - metric_id: str
    - asset_id: str
    - metric_type: str
    - value: float
    - context_signature: dict

baseline_updated:
    - baseline_id: str
    - asset_id: str
    - metric_type: str
    - baseline_value: float
    - confidence: float

baseline_frozen:
    - baseline_id: str
    - intervention_id: str
    - frozen_at: str (ISO)

state_started:
    - state_id: str
    - asset_id: str
    - state_family: str
    - state_type: str
    - severity_score: int
    - confidence: float
    - baseline_id: str

state_updated:
    - state_id: str
    - severity_score: int
    - duration_minutes: int

state_ended:
    - state_id: str
    - ended_at: str (ISO)
    - resolution_type: str

priority_created:
    - priority_id: str
    - state_id: str
    - asset_id: str
    - priority_band: str
    - drivers: list[str]
    - value_at_risk_per_day: float

priority_updated:
    - priority_id: str
    - priority_band: str
    - drivers: list[str]

intervention_created:
    - intervention_id: str
    - state_id: str
    - asset_id: str
    - intervention_type: str
    - created_by: str

intervention_completed:
    - intervention_id: str
    - completed_at: str (ISO)

outcome_verified:
    - outcome_id: str
    - intervention_id: str
    - savings_value: float
    - savings_type: str
    - confidence: float

learning_updated:
    - asset_id: str
    - state_type: str
    - recurrence_count: int
    - avg_intervention_effectiveness: float
"""
