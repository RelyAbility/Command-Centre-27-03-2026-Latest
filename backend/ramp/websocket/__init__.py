"""
RAMP WebSocket Module
=====================

Real-time updates driven from the event backbone.
All broadcasts respect lens discipline (HOW/WHERE separation).

Architecture:
- ConnectionManager handles client connections per channel
- EventBroadcaster hooks into db.create_event() to trigger broadcasts
- Payloads are transformed through lens helpers before broadcast
- Reconnect provides initial state snapshot for clean recovery
"""

from typing import Dict, Set, Any, Optional, List
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime, timezone
import json
import logging
import asyncio

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections by channel.
    
    Channels:
    - priorities: Priority queue updates (HOW lens)
    - states:{asset_id}: State changes for specific asset (HOW lens)
    - outcomes: Verified outcome notifications (HOW lens)
    """
    
    def __init__(self):
        # channel_name -> set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # websocket -> set of subscribed channels
        self.connection_channels: Dict[WebSocket, Set[str]] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, channel: str) -> None:
        """
        Accept connection and add to channel.
        """
        await websocket.accept()
        
        async with self._lock:
            if channel not in self.active_connections:
                self.active_connections[channel] = set()
            self.active_connections[channel].add(websocket)
            
            if websocket not in self.connection_channels:
                self.connection_channels[websocket] = set()
            self.connection_channels[websocket].add(channel)
        
        logger.info(f"WebSocket connected to channel: {channel}")
    
    async def disconnect(self, websocket: WebSocket) -> None:
        """
        Remove connection from all subscribed channels.
        """
        async with self._lock:
            channels = self.connection_channels.pop(websocket, set())
            for channel in channels:
                if channel in self.active_connections:
                    self.active_connections[channel].discard(websocket)
                    if not self.active_connections[channel]:
                        del self.active_connections[channel]
        
        logger.info(f"WebSocket disconnected from channels: {channels}")
    
    async def subscribe(self, websocket: WebSocket, channel: str) -> None:
        """
        Subscribe an existing connection to an additional channel.
        """
        async with self._lock:
            if channel not in self.active_connections:
                self.active_connections[channel] = set()
            self.active_connections[channel].add(websocket)
            
            if websocket in self.connection_channels:
                self.connection_channels[websocket].add(channel)
    
    async def unsubscribe(self, websocket: WebSocket, channel: str) -> None:
        """
        Unsubscribe connection from a specific channel.
        """
        async with self._lock:
            if channel in self.active_connections:
                self.active_connections[channel].discard(websocket)
            if websocket in self.connection_channels:
                self.connection_channels[websocket].discard(channel)
    
    async def broadcast(self, channel: str, message: Dict[str, Any]) -> None:
        """
        Broadcast message to all connections on a channel.
        
        Handles disconnected clients gracefully.
        """
        async with self._lock:
            connections = self.active_connections.get(channel, set()).copy()
        
        if not connections:
            return
        
        # Serialize once
        data = json.dumps(message, default=str)
        
        # Track failed connections for cleanup
        failed = []
        
        for websocket in connections:
            try:
                await websocket.send_text(data)
            except Exception as e:
                logger.warning(f"Failed to send to websocket: {e}")
                failed.append(websocket)
        
        # Clean up failed connections
        for websocket in failed:
            await self.disconnect(websocket)
    
    async def broadcast_to_multiple(
        self, 
        channels: List[str], 
        message: Dict[str, Any]
    ) -> None:
        """
        Broadcast same message to multiple channels.
        """
        for channel in channels:
            await self.broadcast(channel, message)
    
    def get_connection_count(self, channel: Optional[str] = None) -> int:
        """
        Get number of active connections, optionally filtered by channel.
        """
        if channel:
            return len(self.active_connections.get(channel, set()))
        return sum(len(conns) for conns in self.active_connections.values())
    
    def get_channels(self) -> List[str]:
        """
        Get list of active channels.
        """
        return list(self.active_connections.keys())


# Global connection manager instance
manager = ConnectionManager()


# =============================================================================
# PAYLOAD BUILDERS (Lens-compliant)
# =============================================================================

def build_priority_update_payload(
    event_type: str,
    priority_data: Dict[str, Any],
    state_data: Optional[Dict[str, Any]] = None,
    asset_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build HOW-lens-compliant priority update payload.
    
    Does NOT expose:
    - priority_score (raw numeric)
    - score_components
    - confidence (raw numeric)
    
    DOES expose:
    - priority_band
    - drivers
    - economic_impact (VaR, VR)
    - confidence_label
    """
    from ramp.lenses.helpers import confidence_to_label, confidence_band_to_label
    
    # Get confidence label from state if available
    confidence_label = "unknown"
    if state_data:
        confidence_raw = state_data.get("confidence")
        confidence_band = state_data.get("confidence_band")
        if confidence_raw is not None and isinstance(confidence_raw, (int, float)):
            confidence_label = confidence_to_label(confidence_raw)
        elif confidence_band:
            confidence_label = confidence_band_to_label(confidence_band)
    
    # Parse economic impact if it's a string
    economic = priority_data.get("economic_impact", {})
    if isinstance(economic, str):
        try:
            economic = json.loads(economic)
        except Exception:
            economic = {}
    
    # Parse drivers if it's a string
    drivers = priority_data.get("drivers", [])
    if isinstance(drivers, str):
        try:
            drivers = json.loads(drivers)
        except Exception:
            drivers = []
    
    return {
        "type": "priority_update",
        "event": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "priority_id": priority_data.get("id") or priority_data.get("priority_id"),
            "state_id": priority_data.get("state_id"),
            "asset_id": priority_data.get("asset_id"),
            "asset_name": asset_data.get("name") if asset_data else None,
            "priority_band": priority_data.get("priority_band"),
            "state_type": state_data.get("state_type") if state_data else None,
            "state_family": state_data.get("state_family") if state_data else None,
            "severity_band": state_data.get("severity_band") if state_data else None,
            "confidence_label": confidence_label,
            "value_at_risk_per_day": economic.get("value_at_risk_per_day"),
            "value_recoverable_per_day": economic.get("value_recoverable_per_day"),
            "drivers": drivers[:3] if drivers else []  # Limit to top 3
        }
    }


def build_state_update_payload(
    event_type: str,
    state_data: Dict[str, Any],
    asset_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build HOW-lens-compliant state update payload.
    
    Does NOT expose:
    - severity_score (raw numeric)
    - confidence (raw numeric)
    - severity_components
    - confidence_components
    
    DOES expose:
    - severity_band
    - confidence_band (as label)
    - state_type, state_family
    - deviation_percent
    """
    from ramp.lenses.helpers import confidence_to_label, confidence_band_to_label
    
    # Get confidence label
    confidence_raw = state_data.get("confidence")
    confidence_band = state_data.get("confidence_band")
    if confidence_raw is not None and isinstance(confidence_raw, (int, float)):
        confidence_label = confidence_to_label(confidence_raw)
    elif confidence_band:
        confidence_label = confidence_band_to_label(confidence_band)
    else:
        confidence_label = "unknown"
    
    return {
        "type": "state_update",
        "event": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "state_id": state_data.get("id"),
            "asset_id": state_data.get("asset_id"),
            "asset_name": asset_data.get("name") if asset_data else None,
            "state_family": state_data.get("state_family"),
            "state_type": state_data.get("state_type"),
            "severity_band": state_data.get("severity_band"),
            "confidence_label": confidence_label,
            "deviation_percent": state_data.get("deviation_percent"),
            "started_at": state_data.get("started_at"),
            "ended_at": state_data.get("ended_at"),
            "resolution_type": state_data.get("resolution_type"),
            "transitioned_to_state_id": state_data.get("transitioned_to_state_id")
        }
    }


def build_outcome_update_payload(
    event_type: str,
    outcome_data: Dict[str, Any],
    intervention_data: Optional[Dict[str, Any]] = None,
    asset_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build HOW-lens-compliant outcome update payload.
    
    Does NOT expose:
    - confidence (raw numeric)
    - frozen_baseline_value
    - actual_value
    
    DOES expose:
    - status
    - savings_value, savings_unit, savings_type
    - confidence_label
    """
    from ramp.lenses.helpers import confidence_to_label, confidence_band_to_label
    
    # Get confidence label
    confidence_raw = outcome_data.get("confidence")
    confidence_band = outcome_data.get("confidence_band")
    if confidence_raw is not None and isinstance(confidence_raw, (int, float)):
        confidence_label = confidence_to_label(confidence_raw)
    elif confidence_band:
        confidence_label = confidence_band_to_label(confidence_band)
    else:
        confidence_label = "unknown"
    
    return {
        "type": "outcome_update",
        "event": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "outcome_id": outcome_data.get("id"),
            "intervention_id": outcome_data.get("intervention_id"),
            "asset_id": asset_data.get("id") if asset_data else intervention_data.get("asset_id") if intervention_data else None,
            "asset_name": asset_data.get("name") if asset_data else None,
            "intervention_type": intervention_data.get("intervention_type") if intervention_data else None,
            "status": outcome_data.get("status"),
            "savings_value": outcome_data.get("savings_value"),
            "savings_unit": outcome_data.get("savings_unit"),
            "savings_type": outcome_data.get("savings_type"),
            "confidence_label": confidence_label,
            "verified_at": outcome_data.get("verified_at")
        }
    }


def build_resync_payload(
    channel: str,
    priorities: Optional[List[Dict]] = None,
    states: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """
    Build resync payload for client recovery after reconnect.
    
    Provides current state snapshot so client can reconcile.
    """
    return {
        "type": "resync",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "channel": channel,
        "data": {
            "priorities": priorities,
            "states": states,
            "message": "Full state resync - reconcile with local state"
        }
    }


def build_heartbeat_payload() -> Dict[str, Any]:
    """
    Build heartbeat payload for connection keep-alive.
    """
    return {
        "type": "heartbeat",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
