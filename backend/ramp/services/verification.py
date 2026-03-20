"""
RAMP Verification Engine
========================

Responsibility:
- Compare post-action metrics to frozen baseline
- Calculate verified savings
- Assign verification confidence
- Emit: outcome_verified

Verification is what proves the system works.
Without verification, savings are just claims.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import logging
import statistics

from ..models.schema import (
    Outcome, Baseline, EventType, ConfidenceBand,
    generate_id, now_utc
)
from ..events.bus import EventBus

logger = logging.getLogger(__name__)


# V1 Defaults
DEFAULT_VERIFICATION_WINDOW_HOURS = 4
MIN_POST_ACTION_SAMPLES = 8  # At least 8 data points for verification


class VerificationEngine:
    """
    Verifies intervention outcomes.
    
    Flow:
        Intervention completed → verification window starts
        After window passes → compare metrics to frozen baseline
        Calculate savings → emit outcome_verified
    
    Key principles:
    - Savings = (frozen_baseline - actual) × activity
    - Confidence reflects post-intervention stability
    - Never verify without sufficient post-action data
    """
    
    def __init__(self, db, event_bus: EventBus):
        self.db = db
        self.event_bus = event_bus
    
    async def start_verification(
        self,
        intervention_id: str,
        correlation_id: Optional[str] = None
    ):
        """
        Start the verification window for an intervention.
        
        Called by event handler when intervention_completed is received.
        
        For MVP, we do immediate verification with available data.
        Full implementation would schedule verification after window.
        """
        # Get intervention
        intervention = await self.db.interventions.find_one(
            {"id": intervention_id},
            {"_id": 0}
        )
        
        if not intervention:
            logger.warning(f"Intervention not found: {intervention_id}")
            return
        
        asset_id = intervention.get("asset_id")
        completed_at = datetime.fromisoformat(intervention.get("completed_at"))
        
        # Get frozen baseline
        frozen_baseline = await self.db.baselines.find_one(
            {
                "asset_id": asset_id,
                "frozen_for_intervention_id": intervention_id
            },
            {"_id": 0}
        )
        
        if not frozen_baseline:
            logger.warning(
                f"No frozen baseline for intervention {intervention_id}"
            )
            return
        
        # For MVP, verify immediately with available post-action data
        # In full implementation, would wait for verification window
        await self._verify_outcome(
            intervention, frozen_baseline, completed_at, correlation_id
        )
    
    async def _verify_outcome(
        self,
        intervention: Dict,
        frozen_baseline: Dict,
        completed_at: datetime,
        correlation_id: Optional[str]
    ):
        """
        Verify the outcome of an intervention.
        """
        asset_id = intervention.get("asset_id")
        intervention_id = intervention.get("id")
        
        # Define verification window
        window_start = completed_at
        window_end = completed_at + timedelta(hours=DEFAULT_VERIFICATION_WINDOW_HOURS)
        
        # Get post-action metrics
        post_action_metrics = await self.db.metrics.find(
            {
                "asset_id": asset_id,
                "metric_type": frozen_baseline.get("metric_type"),
                "timestamp": {
                    "$gte": window_start.isoformat(),
                    "$lte": window_end.isoformat()
                }
            },
            {"_id": 0}
        ).to_list(100)
        
        # Check if we have enough data
        if len(post_action_metrics) < MIN_POST_ACTION_SAMPLES:
            logger.info(
                f"Insufficient post-action data for {intervention_id}: "
                f"{len(post_action_metrics)} samples"
            )
            # Could schedule retry or mark as "pending verification"
            return
        
        # Calculate actual post-action average
        actual_values = [m["value"] for m in post_action_metrics]
        actual_avg = statistics.mean(actual_values)
        
        # Get frozen baseline value
        baseline_value = frozen_baseline.get("baseline_value")
        
        # Calculate savings
        savings_value = baseline_value - actual_avg
        
        # Determine savings type (based on metric type)
        metric_type = frozen_baseline.get("metric_type")
        if metric_type in ["energy_intensity", "energy_consumption"]:
            savings_type = "energy"
            savings_unit = "kWh"
        else:
            savings_type = "operational"
            savings_unit = frozen_baseline.get("unit", "units")
        
        # Calculate verification confidence
        confidence = self._calculate_verification_confidence(
            actual_values, baseline_value
        )
        
        # Create outcome
        outcome = Outcome(
            id=generate_id(),
            intervention_id=intervention_id,
            verification_window_start=window_start,
            verification_window_end=window_end,
            frozen_baseline_id=frozen_baseline.get("id"),
            frozen_baseline_value=baseline_value,
            actual_value=actual_avg,
            savings_value=round(savings_value, 2),
            savings_unit=savings_unit,
            savings_type=savings_type,
            confidence=confidence,
            confidence_band=self._confidence_to_band(confidence),
            verified_at=now_utc()
        )
        
        # Store outcome
        outcome_doc = outcome.model_dump()
        outcome_doc["verification_window_start"] = outcome_doc["verification_window_start"].isoformat()
        outcome_doc["verification_window_end"] = outcome_doc["verification_window_end"].isoformat()
        outcome_doc["verified_at"] = outcome_doc["verified_at"].isoformat()
        await self.db.outcomes.insert_one(outcome_doc)
        
        # Emit event
        await self.event_bus.emit(
            event_type=EventType.OUTCOME_VERIFIED,
            entity_type="outcome",
            entity_id=outcome.id,
            payload={
                "outcome_id": outcome.id,
                "intervention_id": intervention_id,
                "savings_value": outcome.savings_value,
                "savings_type": savings_type,
                "confidence": confidence
            },
            correlation_id=correlation_id
        )
        
        logger.info(
            f"Outcome verified for intervention {intervention_id}: "
            f"{savings_value:.2f} {savings_unit} ({savings_type}), "
            f"confidence: {confidence:.2f}"
        )
    
    def _calculate_verification_confidence(
        self,
        actual_values: list,
        baseline_value: float
    ) -> float:
        """
        Calculate confidence in verification.
        
        Based on:
        - Sample count
        - Post-action stability (low variance = higher confidence)
        - Magnitude of change
        """
        # Sample count factor
        sample_factor = min(len(actual_values) / 24, 1.0)
        
        # Stability factor (coefficient of variation)
        if len(actual_values) > 1:
            std_dev = statistics.stdev(actual_values)
            mean_val = statistics.mean(actual_values)
            if mean_val > 0:
                cv = std_dev / mean_val
                stability_factor = max(0, 1 - cv)
            else:
                stability_factor = 0.5
        else:
            stability_factor = 0.5
        
        # Change magnitude factor (larger changes are more confident)
        actual_avg = statistics.mean(actual_values)
        if baseline_value > 0:
            change_percent = abs(actual_avg - baseline_value) / baseline_value
            magnitude_factor = min(change_percent / 0.20, 1.0)  # 20%+ change = full confidence
        else:
            magnitude_factor = 0.5
        
        # Combined confidence
        confidence = (
            sample_factor * 0.40 +
            stability_factor * 0.35 +
            magnitude_factor * 0.25
        )
        
        return min(max(confidence, 0.0), 1.0)
    
    def _confidence_to_band(self, confidence: float) -> ConfidenceBand:
        """Convert confidence score to band."""
        if confidence >= 0.80:
            return ConfidenceBand.HIGH
        elif confidence >= 0.60:
            return ConfidenceBand.MEDIUM
        elif confidence >= 0.40:
            return ConfidenceBand.LOW
        return ConfidenceBand.INSUFFICIENT
    
    async def get_outcome(
        self,
        outcome_id: str
    ) -> Optional[Dict]:
        """Get outcome by ID."""
        return await self.db.outcomes.find_one(
            {"id": outcome_id},
            {"_id": 0}
        )
    
    async def get_outcome_for_intervention(
        self,
        intervention_id: str
    ) -> Optional[Dict]:
        """Get outcome for an intervention."""
        return await self.db.outcomes.find_one(
            {"intervention_id": intervention_id},
            {"_id": 0}
        )
