"""
RAMP State Engine
=================

Responsibility:
- Evaluate rules against baselines
- Create states when rules trigger
- Manage state transitions
- Assign severity and confidence
- Emit: state_started, state_updated, state_ended

State is THE BEHAVIORAL TRUTH of the system.
States are time-bound operational facts derived from rules
acting on baseline-relative behavior.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
import logging

from ..models.schema import (
    State, Rule, Baseline, EventType,
    StateFamily, SeverityBand, ConfidenceBand,
    generate_id, now_utc
)
from ..events.bus import EventBus

logger = logging.getLogger(__name__)


# V1 Severity Defaults
SEVERITY_BASE = {
    # Energy states
    "DRIFT": 4,
    "SPIKE": 5,
    "OVERCONSUMPTION": 5,
    "UNDERUTILISATION": 3,
    # Operational states
    "IDLE": 2,
    "FAULT": 7,
    "STARTUP": 1,
    "CHANGEOVER": 1,
    # Maintenance states
    "DEGRADING": 5,
    "ALERT": 6,
    "FAILURE": 9,
    # Production states
    "BOTTLENECKED": 5,
    "PAUSED": 3,
    "IMBALANCED": 4,
}

# Duration modifier tiers (minutes)
DURATION_TIERS = [
    (30, 0),      # < 30 min: +0
    (240, 1),     # 30 min - 4 hr: +1
    (1440, 2),    # 4 hr - 24 hr: +2
    (float('inf'), 3),  # > 24 hr: +3
]

# Deviation modifier tiers (percent)
DEVIATION_TIERS = [
    (15, 0),      # < 15%: +0
    (30, 1),      # 15-30%: +1
    (50, 2),      # 30-50%: +2
    (float('inf'), 3),  # > 50%: +3
]


class StateEngine:
    """
    Evaluates rules and manages states.
    
    States are the primary behavioral truth of RAMP.
    They are created by rules acting on baseline-relative behavior.
    
    Key principles:
    - A rule does NOT equal a state - rules create/update states
    - States must transition (not just stop/start)
    - Severity = base + duration_modifier + deviation_modifier
    - Confidence = data_quality + baseline_confidence + context_validity
    """
    
    def __init__(self, db, event_bus: EventBus, baseline_engine):
        self.db = db
        self.event_bus = event_bus
        self.baseline_engine = baseline_engine
    
    async def evaluate_rules(
        self,
        asset_id: str,
        metric_type: str,
        value: float,
        correlation_id: Optional[str] = None
    ):
        """
        Evaluate all applicable rules for a metric update.
        
        Called by event handler when metric_calculated is received.
        
        Args:
            asset_id: ID of the asset
            metric_type: Type of metric
            value: Current metric value
            correlation_id: Event chain correlation
        """
        # Get applicable rules
        rules = await self.db.rules.find(
            {
                "metric_type": metric_type,
                "is_active": True
            },
            {"_id": 0}
        ).to_list(100)
        
        if not rules:
            return
        
        # Get deviation from baseline
        context = await self._get_context(asset_id)
        deviation = await self.baseline_engine.calculate_deviation(
            asset_id, metric_type, value, context
        )
        
        if not deviation:
            # No baseline - can't evaluate rules
            logger.debug(f"No baseline for {asset_id}/{metric_type}")
            return
        
        # Evaluate each rule
        for rule_doc in rules:
            rule = Rule(**rule_doc)
            await self._evaluate_rule(
                rule, asset_id, value, deviation, correlation_id
            )
    
    async def _evaluate_rule(
        self,
        rule: Rule,
        asset_id: str,
        value: float,
        deviation: Dict[str, Any],
        correlation_id: Optional[str]
    ):
        """
        Evaluate a single rule against current deviation.
        """
        baseline_value = deviation["baseline_value"]
        threshold_value = baseline_value * rule.threshold_multiplier
        
        # Check if condition is met
        condition_met = False
        if rule.operator == "gt":
            condition_met = value > threshold_value
        elif rule.operator == "lt":
            condition_met = value < threshold_value
        elif rule.operator == "gte":
            condition_met = value >= threshold_value
        elif rule.operator == "lte":
            condition_met = value <= threshold_value
        
        # Get existing active state for this rule
        existing_state = await self.db.states.find_one(
            {
                "asset_id": asset_id,
                "rule_id": rule.id,
                "ended_at": None
            },
            {"_id": 0}
        )
        
        if condition_met:
            if existing_state:
                # Update existing state
                await self._update_state(
                    existing_state, deviation, correlation_id
                )
            else:
                # Check duration threshold (simplified for MVP)
                # In full implementation, would track condition start time
                await self._start_state(
                    rule, asset_id, deviation, correlation_id
                )
        else:
            if existing_state:
                # Condition no longer met - end state
                await self._end_state(
                    existing_state, "returned_to_baseline", correlation_id
                )
    
    async def _start_state(
        self,
        rule: Rule,
        asset_id: str,
        deviation: Dict[str, Any],
        correlation_id: Optional[str]
    ):
        """
        Start a new state.
        """
        # Calculate severity
        severity_components = self._calculate_severity(
            rule.state_type,
            0,  # duration = 0 (just started)
            abs(deviation["deviation_percent"])
        )
        severity_score = sum(severity_components.values())
        severity_score = min(max(severity_score, 1), 10)  # Clamp 1-10
        
        # Calculate confidence
        confidence_components = await self._calculate_confidence(
            asset_id, deviation
        )
        confidence = (
            confidence_components["data_quality"] * 0.40 +
            confidence_components["baseline_confidence"] * 0.35 +
            confidence_components["context_validity"] * 0.25
        )
        
        # Create state
        state = State(
            id=generate_id(),
            asset_id=asset_id,
            rule_id=rule.id,
            state_family=rule.state_family,
            state_type=rule.state_type,
            severity_score=severity_score,
            severity_band=self._severity_to_band(severity_score),
            severity_components=severity_components,
            confidence=confidence,
            confidence_band=self._confidence_to_band(confidence),
            confidence_components=confidence_components,
            deviation_percent=deviation["deviation_percent"],
            baseline_id=deviation["baseline_id"],
            started_at=now_utc(),
            duration_minutes=0,
            created_at=now_utc(),
            updated_at=now_utc()
        )
        
        # Store state
        state_doc = state.model_dump()
        state_doc["started_at"] = state_doc["started_at"].isoformat()
        state_doc["created_at"] = state_doc["created_at"].isoformat()
        state_doc["updated_at"] = state_doc["updated_at"].isoformat()
        await self.db.states.insert_one(state_doc)
        
        # Emit event
        state_family_str = rule.state_family.value if hasattr(rule.state_family, 'value') else str(rule.state_family)
        await self.event_bus.emit(
            event_type=EventType.STATE_STARTED,
            entity_type="state",
            entity_id=state.id,
            payload={
                "state_id": state.id,
                "asset_id": asset_id,
                "state_family": state_family_str,
                "state_type": rule.state_type,
                "severity_score": severity_score,
                "confidence": confidence,
                "baseline_id": deviation["baseline_id"],
                "deviation_percent": deviation["deviation_percent"]
            },
            correlation_id=correlation_id
        )
        
        logger.info(
            f"State started: {rule.state_type} for {asset_id} "
            f"(severity: {severity_score}, confidence: {confidence:.2f})"
        )
    
    async def _update_state(
        self,
        state_doc: Dict,
        deviation: Dict[str, Any],
        correlation_id: Optional[str]
    ):
        """
        Update an existing state (severity may increase with duration).
        """
        # Calculate duration
        started_at = datetime.fromisoformat(state_doc["started_at"])
        duration = now_utc() - started_at
        duration_minutes = int(duration.total_seconds() / 60)
        
        # Recalculate severity with updated duration
        severity_components = self._calculate_severity(
            state_doc["state_type"],
            duration_minutes,
            abs(deviation["deviation_percent"])
        )
        severity_score = sum(severity_components.values())
        severity_score = min(max(severity_score, 1), 10)
        
        # Check if severity changed
        if severity_score == state_doc["severity_score"]:
            return  # No update needed
        
        # Update state
        await self.db.states.update_one(
            {"id": state_doc["id"]},
            {
                "$set": {
                    "severity_score": severity_score,
                    "severity_band": self._severity_to_band(severity_score).value,
                    "severity_components": severity_components,
                    "duration_minutes": duration_minutes,
                    "deviation_percent": deviation["deviation_percent"],
                    "updated_at": now_utc().isoformat()
                }
            }
        )
        
        # Emit event
        await self.event_bus.emit(
            event_type=EventType.STATE_UPDATED,
            entity_type="state",
            entity_id=state_doc["id"],
            payload={
                "state_id": state_doc["id"],
                "severity_score": severity_score,
                "duration_minutes": duration_minutes,
                "deviation_percent": deviation["deviation_percent"]
            },
            correlation_id=correlation_id
        )
        
        logger.debug(
            f"State updated: {state_doc['id']} "
            f"severity: {state_doc['severity_score']} → {severity_score}"
        )
    
    async def _end_state(
        self,
        state_doc: Dict,
        resolution_type: str,
        correlation_id: Optional[str],
        transitioned_to: Optional[str] = None
    ):
        """
        End a state.
        """
        ended_at = now_utc()
        
        # Update state
        await self.db.states.update_one(
            {"id": state_doc["id"]},
            {
                "$set": {
                    "ended_at": ended_at.isoformat(),
                    "resolution_type": resolution_type,
                    "transitioned_to_state_id": transitioned_to,
                    "updated_at": ended_at.isoformat()
                }
            }
        )
        
        # Emit event
        await self.event_bus.emit(
            event_type=EventType.STATE_ENDED,
            entity_type="state",
            entity_id=state_doc["id"],
            payload={
                "state_id": state_doc["id"],
                "ended_at": ended_at.isoformat(),
                "resolution_type": resolution_type,
                "transitioned_to_state_id": transitioned_to
            },
            correlation_id=correlation_id
        )
        
        logger.info(
            f"State ended: {state_doc['id']} ({resolution_type})"
        )
    
    async def on_baseline_updated(
        self,
        asset_id: str,
        baseline_id: str,
        correlation_id: Optional[str] = None
    ):
        """
        Handle baseline update - may need to re-evaluate active states.
        """
        # For MVP, this is a placeholder
        # Full implementation would re-evaluate states against new baseline
        pass
    
    def _calculate_severity(
        self,
        state_type: str,
        duration_minutes: int,
        deviation_percent: float
    ) -> Dict[str, int]:
        """
        Calculate severity components.
        
        Severity = base + duration_modifier + deviation_modifier
        """
        # Base severity
        base = SEVERITY_BASE.get(state_type, 3)
        
        # Duration modifier
        duration_mod = 0
        for threshold, modifier in DURATION_TIERS:
            if duration_minutes < threshold:
                duration_mod = modifier
                break
        
        # Deviation modifier
        deviation_mod = 0
        for threshold, modifier in DEVIATION_TIERS:
            if deviation_percent < threshold:
                deviation_mod = modifier
                break
        
        return {
            "base": base,
            "duration_modifier": duration_mod,
            "deviation_modifier": deviation_mod
        }
    
    async def _calculate_confidence(
        self,
        asset_id: str,
        deviation: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Calculate confidence components.
        
        Confidence = data_quality + baseline_confidence + context_validity
        """
        # Data quality - based on recent signal quality
        # For MVP, assume good quality
        data_quality = 0.90
        
        # Baseline confidence - from deviation info
        baseline_confidence = deviation.get("baseline_confidence", 0.70)
        
        # Context validity - check if we're in a valid operating context
        # For MVP, assume valid
        context_validity = 0.85
        
        return {
            "data_quality": data_quality,
            "baseline_confidence": baseline_confidence,
            "context_validity": context_validity
        }
    
    async def _get_context(self, asset_id: str) -> Dict[str, Any]:
        """Get current operating context for an asset."""
        # Check for active operational state
        active_state = await self.db.states.find_one(
            {
                "asset_id": asset_id,
                "state_family": "OPERATIONAL",
                "ended_at": None
            },
            {"_id": 0}
        )
        
        runtime_state = "RUNNING"
        if active_state:
            runtime_state = active_state.get("state_type", "RUNNING")
        
        return {
            "runtime_state": runtime_state,
            "production_band": "NORMAL"
        }
    
    def _severity_to_band(self, score: int) -> SeverityBand:
        """Convert severity score to band."""
        if score >= 9:
            return SeverityBand.CRITICAL
        elif score >= 7:
            return SeverityBand.HIGH
        elif score >= 4:
            return SeverityBand.MEDIUM
        return SeverityBand.LOW
    
    def _confidence_to_band(self, confidence: float) -> ConfidenceBand:
        """Convert confidence score to band."""
        if confidence >= 0.80:
            return ConfidenceBand.HIGH
        elif confidence >= 0.60:
            return ConfidenceBand.MEDIUM
        elif confidence >= 0.40:
            return ConfidenceBand.LOW
        return ConfidenceBand.INSUFFICIENT
