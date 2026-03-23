"""
RAMP Event Broadcaster
======================

Hooks into the event backbone to trigger WebSocket broadcasts.
All broadcasts respect lens discipline.

This module is imported by db.py to trigger broadcasts when events are created.
"""

from typing import Dict, Any, Optional, Callable, Awaitable
import logging
import asyncio

logger = logging.getLogger(__name__)

# Registry of event handlers
# event_type -> async handler function
_event_handlers: Dict[str, Callable[[Dict[str, Any]], Awaitable[None]]] = {}


def register_event_handler(
    event_type: str, 
    handler: Callable[[Dict[str, Any]], Awaitable[None]]
) -> None:
    """
    Register a handler to be called when an event of this type is created.
    """
    _event_handlers[event_type] = handler
    logger.info(f"Registered WebSocket handler for event type: {event_type}")


async def broadcast_event(event_data: Dict[str, Any]) -> None:
    """
    Called by db.create_event() to trigger WebSocket broadcasts.
    
    Routes to the appropriate handler based on event_type.
    """
    event_type = event_data.get("event_type")
    
    if not event_type:
        return
    
    handler = _event_handlers.get(event_type)
    if handler:
        try:
            # Run in background to not block the event creation
            asyncio.create_task(handler(event_data))
        except Exception as e:
            logger.error(f"Error in broadcast handler for {event_type}: {e}")


async def _handle_priority_created(event_data: Dict[str, Any]) -> None:
    """Handle priority_created event."""
    from ramp.websocket import manager, build_priority_update_payload
    
    payload = event_data.get("payload", {})
    
    # Build lens-compliant payload
    ws_payload = build_priority_update_payload(
        event_type="priority_created",
        priority_data=payload,
        state_data=None,  # Will be enriched by client if needed
        asset_data=None
    )
    
    # Broadcast to priorities channel
    await manager.broadcast("priorities", ws_payload)
    
    # Also broadcast to asset-specific state channel if we have asset_id
    asset_id = payload.get("asset_id")
    if asset_id:
        await manager.broadcast(f"states:{asset_id}", ws_payload)


async def _handle_priority_updated(event_data: Dict[str, Any]) -> None:
    """Handle priority_updated event."""
    from ramp.websocket import manager, build_priority_update_payload
    
    payload = event_data.get("payload", {})
    
    ws_payload = build_priority_update_payload(
        event_type="priority_updated",
        priority_data=payload
    )
    
    await manager.broadcast("priorities", ws_payload)
    
    asset_id = payload.get("asset_id")
    if asset_id:
        await manager.broadcast(f"states:{asset_id}", ws_payload)


async def _handle_priority_escalated(event_data: Dict[str, Any]) -> None:
    """Handle priority_escalated event."""
    from ramp.websocket import manager, build_priority_update_payload
    
    payload = event_data.get("payload", {})
    
    ws_payload = build_priority_update_payload(
        event_type="priority_escalated",
        priority_data=payload
    )
    
    # Escalation is high-priority - broadcast to priorities channel
    await manager.broadcast("priorities", ws_payload)
    
    asset_id = payload.get("asset_id")
    if asset_id:
        await manager.broadcast(f"states:{asset_id}", ws_payload)


async def _handle_state_started(event_data: Dict[str, Any]) -> None:
    """Handle state_started event."""
    from ramp.websocket import manager, build_state_update_payload
    
    payload = event_data.get("payload", {})
    
    ws_payload = build_state_update_payload(
        event_type="state_started",
        state_data=payload
    )
    
    asset_id = payload.get("asset_id")
    if asset_id:
        await manager.broadcast(f"states:{asset_id}", ws_payload)
    
    # Also notify priorities channel as new state may create priority
    await manager.broadcast("priorities", ws_payload)


async def _handle_state_ended(event_data: Dict[str, Any]) -> None:
    """Handle state_ended event."""
    from ramp.websocket import manager, build_state_update_payload
    
    payload = event_data.get("payload", {})
    
    ws_payload = build_state_update_payload(
        event_type="state_ended",
        state_data=payload
    )
    
    asset_id = payload.get("asset_id")
    if asset_id:
        await manager.broadcast(f"states:{asset_id}", ws_payload)
    
    # Notify priorities as state end may expire priority
    await manager.broadcast("priorities", ws_payload)


async def _handle_state_transitioned(event_data: Dict[str, Any]) -> None:
    """Handle state_transitioned event."""
    from ramp.websocket import manager, build_state_update_payload
    
    payload = event_data.get("payload", {})
    
    ws_payload = build_state_update_payload(
        event_type="state_transitioned",
        state_data=payload
    )
    
    asset_id = payload.get("asset_id")
    if asset_id:
        await manager.broadcast(f"states:{asset_id}", ws_payload)
    
    await manager.broadcast("priorities", ws_payload)


async def _handle_intervention_created(event_data: Dict[str, Any]) -> None:
    """Handle intervention_created event."""
    from ramp.websocket import manager
    
    payload = event_data.get("payload", {})
    
    ws_payload = {
        "type": "intervention_update",
        "event": "intervention_created",
        "timestamp": event_data.get("created_at"),
        "data": {
            "intervention_id": payload.get("intervention_id"),
            "state_id": payload.get("state_id"),
            "asset_id": payload.get("asset_id"),
            "intervention_type": payload.get("intervention_type"),
            "created_by": payload.get("created_by")
        }
    }
    
    asset_id = payload.get("asset_id")
    if asset_id:
        await manager.broadcast(f"states:{asset_id}", ws_payload)
    
    await manager.broadcast("priorities", ws_payload)


async def _handle_intervention_completed(event_data: Dict[str, Any]) -> None:
    """Handle intervention_completed event."""
    from ramp.websocket import manager
    
    payload = event_data.get("payload", {})
    
    ws_payload = {
        "type": "intervention_update",
        "event": "intervention_completed",
        "timestamp": event_data.get("created_at"),
        "data": {
            "intervention_id": payload.get("intervention_id"),
            "completed_at": payload.get("completed_at")
        }
    }
    
    await manager.broadcast("priorities", ws_payload)
    await manager.broadcast("outcomes", ws_payload)


async def _handle_outcome_verified(event_data: Dict[str, Any]) -> None:
    """Handle outcome_verified event."""
    from ramp.websocket import manager, build_outcome_update_payload
    
    payload = event_data.get("payload", {})
    
    ws_payload = build_outcome_update_payload(
        event_type="outcome_verified",
        outcome_data=payload
    )
    
    # Broadcast to outcomes channel
    await manager.broadcast("outcomes", ws_payload)
    
    # Also notify priorities channel for value summary updates
    await manager.broadcast("priorities", ws_payload)


def initialize_handlers() -> None:
    """
    Register all event handlers.
    
    Called during application startup.
    """
    # Priority events
    register_event_handler("priority_created", _handle_priority_created)
    register_event_handler("priority_updated", _handle_priority_updated)
    register_event_handler("priority_escalated", _handle_priority_escalated)
    
    # State events
    register_event_handler("state_started", _handle_state_started)
    register_event_handler("state_ended", _handle_state_ended)
    register_event_handler("state_transitioned", _handle_state_transitioned)
    
    # Intervention events
    register_event_handler("intervention_created", _handle_intervention_created)
    register_event_handler("intervention_completed", _handle_intervention_completed)
    
    # Outcome events
    register_event_handler("outcome_verified", _handle_outcome_verified)
    
    logger.info("WebSocket event handlers initialized")
