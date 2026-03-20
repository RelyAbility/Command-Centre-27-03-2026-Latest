"""
RAMP Learning Engine (Partial MVP)
==================================

Responsibility:
- Track state recurrence
- Track intervention effectiveness
- Emit: learning_updated

This is a PARTIAL implementation for MVP.
Full learning capabilities come after MVP stability.

MVP Learning tracks:
- How often states recur for an asset
- Average intervention effectiveness
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
import logging

from ..models.schema import (
    EventType,
    generate_id, now_utc
)
from ..events.bus import EventBus

logger = logging.getLogger(__name__)


class LearningEngine:
    """
    Partial learning implementation for MVP.
    
    Tracks:
    - State recurrence (how often same state type occurs)
    - Intervention effectiveness (average savings achieved)
    
    Does NOT include (deferred to post-MVP):
    - Baseline learning from improvements
    - Rule optimization
    - Benchmark learning
    - Pattern discovery
    """
    
    def __init__(self, db, event_bus: EventBus):
        self.db = db
        self.event_bus = event_bus
    
    async def record_state_ended(
        self,
        state_id: str,
        resolution_type: str,
        correlation_id: Optional[str] = None
    ):
        """
        Record that a state ended (for recurrence tracking).
        
        Called by event handler when state_ended is received.
        """
        # Get state details
        state = await self.db.states.find_one(
            {"id": state_id},
            {"_id": 0}
        )
        
        if not state:
            return
        
        asset_id = state.get("asset_id")
        state_type = state.get("state_type")
        
        # Get or create learning record for this asset/state_type
        learning_key = f"{asset_id}:{state_type}"
        
        learning = await self.db.learning.find_one(
            {"learning_key": learning_key},
            {"_id": 0}
        )
        
        if learning:
            # Update existing record
            await self.db.learning.update_one(
                {"learning_key": learning_key},
                {
                    "$inc": {"occurrence_count": 1},
                    "$set": {
                        "last_occurred_at": now_utc().isoformat(),
                        "last_resolution_type": resolution_type
                    }
                }
            )
        else:
            # Create new record
            learning_doc = {
                "id": generate_id(),
                "learning_key": learning_key,
                "asset_id": asset_id,
                "state_type": state_type,
                "occurrence_count": 1,
                "intervention_count": 0,
                "total_savings": 0.0,
                "avg_effectiveness": 0.0,
                "first_occurred_at": now_utc().isoformat(),
                "last_occurred_at": now_utc().isoformat(),
                "last_resolution_type": resolution_type
            }
            await self.db.learning.insert_one(learning_doc)
        
        logger.debug(f"Learning updated for {learning_key}: state ended")
    
    async def record_outcome(
        self,
        intervention_id: str,
        savings_value: float,
        confidence: float,
        correlation_id: Optional[str] = None
    ):
        """
        Record intervention outcome (for effectiveness tracking).
        
        Called by event handler when outcome_verified is received.
        """
        # Get intervention to find state
        intervention = await self.db.interventions.find_one(
            {"id": intervention_id},
            {"_id": 0}
        )
        
        if not intervention:
            return
        
        state_id = intervention.get("state_id")
        
        # Get state details
        state = await self.db.states.find_one(
            {"id": state_id},
            {"_id": 0}
        )
        
        if not state:
            return
        
        asset_id = state.get("asset_id")
        state_type = state.get("state_type")
        learning_key = f"{asset_id}:{state_type}"
        
        # Update learning record
        learning = await self.db.learning.find_one(
            {"learning_key": learning_key},
            {"_id": 0}
        )
        
        if learning:
            # Calculate new average effectiveness
            old_count = learning.get("intervention_count", 0)
            old_total = learning.get("total_savings", 0.0)
            
            new_count = old_count + 1
            new_total = old_total + savings_value
            new_avg = new_total / new_count if new_count > 0 else 0.0
            
            await self.db.learning.update_one(
                {"learning_key": learning_key},
                {
                    "$set": {
                        "intervention_count": new_count,
                        "total_savings": new_total,
                        "avg_effectiveness": new_avg,
                        "last_intervention_savings": savings_value,
                        "last_intervention_confidence": confidence,
                        "updated_at": now_utc().isoformat()
                    }
                }
            )
            
            # Emit learning updated event
            await self.event_bus.emit(
                event_type=EventType.LEARNING_UPDATED,
                entity_type="learning",
                entity_id=learning.get("id"),
                payload={
                    "asset_id": asset_id,
                    "state_type": state_type,
                    "recurrence_count": learning.get("occurrence_count", 1),
                    "avg_intervention_effectiveness": new_avg
                },
                correlation_id=correlation_id
            )
            
            logger.info(
                f"Learning updated for {learning_key}: "
                f"savings={savings_value:.2f}, avg_effectiveness={new_avg:.2f}"
            )
    
    async def get_learning_for_asset(
        self,
        asset_id: str
    ) -> list:
        """Get all learning records for an asset."""
        return await self.db.learning.find(
            {"asset_id": asset_id},
            {"_id": 0}
        ).to_list(100)
    
    async def get_recurrence_rate(
        self,
        asset_id: str,
        state_type: str
    ) -> int:
        """Get recurrence count for a state type on an asset."""
        learning_key = f"{asset_id}:{state_type}"
        learning = await self.db.learning.find_one(
            {"learning_key": learning_key},
            {"_id": 0}
        )
        
        if learning:
            return learning.get("occurrence_count", 0)
        return 0
