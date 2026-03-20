"""
RAMP Intervention Service
=========================

Responsibility:
- Capture user actions in response to states
- Link intervention to state and priority
- Trigger baseline freeze
- Emit: intervention_created, intervention_completed

Interventions are the user's response to what the system detected.
When an intervention is created, the baseline freezes for comparison.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
import logging

from ..models.schema import (
    Intervention, EventType,
    generate_id, now_utc
)
from ..events.bus import EventBus

logger = logging.getLogger(__name__)


class InterventionService:
    """
    Manages interventions (user actions).
    
    Flow:
        User sees priority in Command Centre
        User creates intervention linked to state
        Baseline freezes for verification
        User marks intervention complete
        Verification engine starts verification window
    """
    
    def __init__(self, db, event_bus: EventBus):
        self.db = db
        self.event_bus = event_bus
    
    async def create_intervention(
        self,
        state_id: str,
        intervention_type: str,
        description: str,
        created_by: str,
        priority_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> Intervention:
        """
        Create a new intervention.
        
        Args:
            state_id: ID of the state being addressed
            intervention_type: Type of action (e.g., "adjustment", "repair")
            description: Description of the action taken
            created_by: User ID who created the intervention
            priority_id: Optional linked priority ID
            correlation_id: Event chain correlation
            
        Returns:
            Created intervention
        """
        # Get state to get asset_id
        state = await self.db.states.find_one(
            {"id": state_id},
            {"_id": 0}
        )
        
        if not state:
            raise ValueError(f"State not found: {state_id}")
        
        asset_id = state.get("asset_id")
        
        # If no priority_id provided, find the active priority for this state
        if not priority_id:
            priority = await self.db.priorities.find_one(
                {"state_id": state_id, "expires_at": None},
                {"_id": 0}
            )
            if priority:
                priority_id = priority.get("id")
        
        # Create intervention
        intervention = Intervention(
            id=generate_id(),
            state_id=state_id,
            priority_id=priority_id,
            asset_id=asset_id,
            intervention_type=intervention_type,
            description=description,
            created_by=created_by,
            created_at=now_utc()
        )
        
        # Store intervention
        intervention_doc = intervention.model_dump()
        intervention_doc["created_at"] = intervention_doc["created_at"].isoformat()
        await self.db.interventions.insert_one(intervention_doc)
        
        # Emit event (triggers baseline freeze)
        await self.event_bus.emit(
            event_type=EventType.INTERVENTION_CREATED,
            entity_type="intervention",
            entity_id=intervention.id,
            payload={
                "intervention_id": intervention.id,
                "state_id": state_id,
                "asset_id": asset_id,
                "intervention_type": intervention_type,
                "created_by": created_by
            },
            correlation_id=correlation_id
        )
        
        logger.info(
            f"Intervention created: {intervention.id} "
            f"for state {state_id} by {created_by}"
        )
        
        return intervention
    
    async def complete_intervention(
        self,
        intervention_id: str,
        correlation_id: Optional[str] = None
    ):
        """
        Mark an intervention as complete.
        
        This triggers the verification window to start.
        """
        completed_at = now_utc()
        
        # Update intervention
        result = await self.db.interventions.update_one(
            {"id": intervention_id},
            {
                "$set": {
                    "completed_at": completed_at.isoformat()
                }
            }
        )
        
        if result.modified_count == 0:
            raise ValueError(f"Intervention not found: {intervention_id}")
        
        # Emit event (triggers verification)
        await self.event_bus.emit(
            event_type=EventType.INTERVENTION_COMPLETED,
            entity_type="intervention",
            entity_id=intervention_id,
            payload={
                "intervention_id": intervention_id,
                "completed_at": completed_at.isoformat()
            },
            correlation_id=correlation_id
        )
        
        logger.info(f"Intervention completed: {intervention_id}")
    
    async def get_intervention(
        self,
        intervention_id: str
    ) -> Optional[Dict]:
        """Get intervention by ID."""
        return await self.db.interventions.find_one(
            {"id": intervention_id},
            {"_id": 0}
        )
    
    async def get_interventions_for_state(
        self,
        state_id: str
    ) -> list:
        """Get all interventions for a state."""
        return await self.db.interventions.find(
            {"state_id": state_id},
            {"_id": 0}
        ).sort("created_at", -1).to_list(100)
    
    async def get_interventions_for_asset(
        self,
        asset_id: str,
        limit: int = 50
    ) -> list:
        """Get recent interventions for an asset."""
        return await self.db.interventions.find(
            {"asset_id": asset_id},
            {"_id": 0}
        ).sort("created_at", -1).to_list(limit)
