"""
RAMP Escalation Service
========================

Responsibility:
- Monitor active states and priorities for duration-based escalation
- Auto-escalate priority bands based on configured thresholds
- Create escalation events for audit trail
- Support manual escalation triggers

Escalation Logic (from Priority Engine spec):
- DRIFT for 10 minutes = MEDIUM
- DRIFT for 8 hours = HIGH  
- DRIFT for 2 days = CRITICAL

- No action taken increases escalation urgency
- Repeat occurrences increase escalation urgency
- State worsening triggers immediate escalation
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)


# Escalation thresholds (duration in minutes -> target band)
# These are cumulative - if duration exceeds threshold, escalate to that band
DURATION_ESCALATION_THRESHOLDS = {
    # Format: state_type -> [(duration_minutes, target_band), ...]
    "DRIFT": [
        (10, "MEDIUM"),      # 10 minutes -> at least MEDIUM
        (480, "HIGH"),       # 8 hours (480 min) -> at least HIGH
        (2880, "CRITICAL"),  # 2 days (2880 min) -> CRITICAL
    ],
    "DEGRADATION": [
        (30, "MEDIUM"),
        (240, "HIGH"),       # 4 hours
        (1440, "CRITICAL"),  # 1 day
    ],
    "SPIKE": [
        (5, "HIGH"),         # Spikes are urgent
        (60, "CRITICAL"),    # 1 hour spike is critical
    ],
    "DEFAULT": [
        (60, "MEDIUM"),
        (480, "HIGH"),
        (2880, "CRITICAL"),
    ],
}

# Priority band ordering (for comparison)
BAND_ORDER = {
    "LOW": 0,
    "MEDIUM": 1,
    "HIGH": 2,
    "CRITICAL": 3,
}


def get_band_order(band: str) -> int:
    """Get numeric order for a priority band."""
    return BAND_ORDER.get(band.upper(), 0)


def should_escalate(current_band: str, target_band: str) -> bool:
    """Check if escalation from current to target band is needed."""
    return get_band_order(target_band) > get_band_order(current_band)


class EscalationService:
    """
    Service for handling priority escalation based on duration and other factors.
    
    Key behaviors:
    1. Duration-based escalation: States that persist escalate in priority
    2. Inaction escalation: Priorities with no intervention escalate faster
    3. Recurrence escalation: Assets with recurring issues get boosted priority
    """
    
    def __init__(self, db):
        """
        Initialize with database client.
        
        Args:
            db: RAMPDatabase instance
        """
        self.db = db
    
    async def check_and_escalate_all(self) -> Dict[str, Any]:
        """
        Check all active priorities for escalation and apply updates.
        
        Returns summary of escalation actions taken.
        """
        from sqlalchemy import text
        
        result = {
            "checked": 0,
            "escalated": 0,
            "escalations": [],
            "errors": []
        }
        
        try:
            # Get all active priorities with their states
            query = await self.db.session.execute(
                text("""
                    SELECT 
                        p.id as priority_id,
                        p.state_id,
                        p.asset_id,
                        p.priority_band,
                        p.priority_score,
                        p.created_at as priority_created_at,
                        s.state_type,
                        s.state_family,
                        s.severity_band,
                        s.started_at,
                        s.duration_minutes,
                        s.confidence
                    FROM ramp_priorities p
                    JOIN ramp_states s ON p.state_id = s.id
                    WHERE p.expires_at IS NULL
                    AND s.ended_at IS NULL
                    ORDER BY p.priority_score DESC
                """)
            )
            
            priorities = [dict(row) for row in query.mappings()]
            result["checked"] = len(priorities)
            
            for priority in priorities:
                try:
                    escalation = await self._check_priority_escalation(priority)
                    if escalation:
                        await self._apply_escalation(priority, escalation)
                        result["escalated"] += 1
                        result["escalations"].append(escalation)
                except Exception as e:
                    logger.error(f"Error checking priority {priority['priority_id']}: {e}")
                    result["errors"].append({
                        "priority_id": priority["priority_id"],
                        "error": str(e)
                    })
            
            return result
            
        except Exception as e:
            logger.error(f"Error in escalation check: {e}")
            result["errors"].append({"error": str(e)})
            return result
    
    async def _check_priority_escalation(
        self, 
        priority: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Check if a priority should be escalated.
        
        Returns escalation details if escalation is needed, None otherwise.
        """
        current_band = priority.get("priority_band", "LOW")
        state_type = priority.get("state_type", "DEFAULT")
        
        # Calculate actual duration from started_at
        started_at = priority.get("started_at")
        if started_at:
            if isinstance(started_at, str):
                started_at = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            duration_minutes = int((now - started_at).total_seconds() / 60)
        else:
            duration_minutes = priority.get("duration_minutes", 0)
        
        # Get escalation thresholds for this state type
        thresholds = DURATION_ESCALATION_THRESHOLDS.get(
            state_type.upper(),
            DURATION_ESCALATION_THRESHOLDS["DEFAULT"]
        )
        
        # Find the highest applicable target band
        target_band = None
        threshold_triggered = None
        
        for threshold_minutes, band in thresholds:
            if duration_minutes >= threshold_minutes:
                if should_escalate(current_band, band):
                    target_band = band
                    threshold_triggered = threshold_minutes
        
        if target_band:
            return {
                "priority_id": priority["priority_id"],
                "state_id": priority["state_id"],
                "asset_id": priority["asset_id"],
                "current_band": current_band,
                "target_band": target_band,
                "reason": "DURATION",
                "duration_minutes": duration_minutes,
                "threshold_minutes": threshold_triggered,
                "state_type": state_type
            }
        
        return None
    
    async def _apply_escalation(
        self, 
        priority: Dict[str, Any],
        escalation: Dict[str, Any]
    ) -> None:
        """
        Apply an escalation to a priority.
        
        Updates the priority band and creates an audit event.
        """
        from sqlalchemy import text
        from ramp.db import now_utc, generate_id, to_json
        
        target_band = escalation["target_band"]
        priority_id = escalation["priority_id"]
        
        # Calculate new score based on band
        # This is a simplified calculation - full implementation would recalculate
        band_scores = {
            "LOW": 30,
            "MEDIUM": 50,
            "HIGH": 70,
            "CRITICAL": 90,
        }
        new_score = max(
            priority.get("priority_score", 0),
            band_scores.get(target_band, 50)
        )
        
        # Update priority
        await self.db.session.execute(
            text("""
                UPDATE ramp_priorities 
                SET priority_band = :band,
                    priority_score = :score,
                    updated_at = :updated_at
                WHERE id = :id
            """),
            {
                "band": target_band,
                "score": new_score,
                "updated_at": now_utc(),
                "id": priority_id
            }
        )
        
        # Create escalation event
        event_payload = {
            "priority_id": priority_id,
            "state_id": escalation["state_id"],
            "asset_id": escalation["asset_id"],
            "from_band": escalation["current_band"],
            "to_band": target_band,
            "reason": escalation["reason"],
            "duration_minutes": escalation["duration_minutes"],
            "threshold_minutes": escalation["threshold_minutes"]
        }
        
        await self.db.session.execute(
            text("""
                INSERT INTO ramp_events (id, event_type, entity_type, entity_id,
                    payload, created_at)
                VALUES (:id, :event_type, :entity_type, :entity_id,
                    CAST(:payload AS jsonb), :created_at)
            """),
            {
                "id": generate_id(),
                "event_type": "priority_escalated",
                "entity_type": "priority",
                "entity_id": priority_id,
                "payload": to_json(event_payload),
                "created_at": now_utc()
            }
        )
        
        await self.db.session.commit()
        
        logger.info(
            f"Priority {priority_id} escalated: "
            f"{escalation['current_band']} → {target_band} "
            f"(duration: {escalation['duration_minutes']}min)"
        )
    
    async def manual_escalate(
        self,
        priority_id: str,
        target_band: str,
        reason: str,
        escalated_by: str
    ) -> Dict[str, Any]:
        """
        Manually escalate a priority.
        
        Used when an operator determines immediate escalation is needed.
        """
        from sqlalchemy import text
        from ramp.db import now_utc, generate_id, to_json
        
        # Get current priority
        query = await self.db.session.execute(
            text("SELECT * FROM ramp_priorities WHERE id = :id"),
            {"id": priority_id}
        )
        priority = query.mappings().first()
        
        if not priority:
            return {"error": "Priority not found", "priority_id": priority_id}
        
        priority = dict(priority)
        current_band = priority.get("priority_band")
        
        if not should_escalate(current_band, target_band):
            return {
                "error": "Target band is not higher than current band",
                "current_band": current_band,
                "target_band": target_band
            }
        
        # Calculate new score
        band_scores = {"LOW": 30, "MEDIUM": 50, "HIGH": 70, "CRITICAL": 90}
        new_score = max(priority.get("priority_score", 0), band_scores.get(target_band, 50))
        
        # Update priority
        await self.db.session.execute(
            text("""
                UPDATE ramp_priorities 
                SET priority_band = :band,
                    priority_score = :score,
                    updated_at = :updated_at
                WHERE id = :id
            """),
            {
                "band": target_band,
                "score": new_score,
                "updated_at": now_utc(),
                "id": priority_id
            }
        )
        
        # Create event
        event_payload = {
            "priority_id": priority_id,
            "from_band": current_band,
            "to_band": target_band,
            "reason": "MANUAL",
            "manual_reason": reason,
            "escalated_by": escalated_by
        }
        
        await self.db.session.execute(
            text("""
                INSERT INTO ramp_events (id, event_type, entity_type, entity_id,
                    payload, created_at)
                VALUES (:id, :event_type, :entity_type, :entity_id,
                    CAST(:payload AS jsonb), :created_at)
            """),
            {
                "id": generate_id(),
                "event_type": "priority_escalated",
                "entity_type": "priority",
                "entity_id": priority_id,
                "payload": to_json(event_payload),
                "created_at": now_utc()
            }
        )
        
        await self.db.session.commit()
        
        logger.info(
            f"Priority {priority_id} manually escalated: "
            f"{current_band} → {target_band} by {escalated_by}"
        )
        
        return {
            "status": "escalated",
            "priority_id": priority_id,
            "from_band": current_band,
            "to_band": target_band,
            "reason": reason,
            "escalated_by": escalated_by
        }
    
    async def get_escalation_candidates(self) -> List[Dict[str, Any]]:
        """
        Get all priorities that are candidates for escalation.
        
        Returns priorities that would escalate if check_and_escalate_all() is run.
        """
        from sqlalchemy import text
        
        query = await self.db.session.execute(
            text("""
                SELECT 
                    p.id as priority_id,
                    p.state_id,
                    p.asset_id,
                    p.priority_band,
                    p.priority_score,
                    s.state_type,
                    s.started_at,
                    s.duration_minutes,
                    a.name as asset_name
                FROM ramp_priorities p
                JOIN ramp_states s ON p.state_id = s.id
                JOIN ramp_assets a ON p.asset_id = a.id
                WHERE p.expires_at IS NULL
                AND s.ended_at IS NULL
                ORDER BY s.started_at ASC
            """)
        )
        
        candidates = []
        for row in query.mappings():
            priority = dict(row)
            escalation = await self._check_priority_escalation(priority)
            if escalation:
                candidates.append({
                    **escalation,
                    "asset_name": priority.get("asset_name")
                })
        
        return candidates
