"""
RAMP Baseline Engine
====================

Responsibility:
- Establish baselines from metric history
- Maintain baselines (rolling updates when stable)
- Calculate deviation from baseline
- Freeze baseline on intervention
- Emit: baseline_updated, baseline_frozen

Baseline is a FIRST CLASS PRIMITIVE.
It sits between metrics and rules, making state assignment meaningful.
Without baseline, states cannot be assigned.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
import logging
import statistics

from ..models.schema import (
    Baseline, Metric, EventType, ConfidenceBand,
    generate_id, now_utc
)
from ..events.bus import EventBus

logger = logging.getLogger(__name__)


# V1 Defaults
DEFAULT_BASELINE_WINDOW_DAYS = 14
MIN_SAMPLES_FOR_BASELINE = 24  # At least 24 data points
BASELINE_UPDATE_THRESHOLD = 0.05  # Only update if change > 5%


class BaselineEngine:
    """
    Manages baselines - the reference for normal behavior.
    
    Baselines make deviation, drift, savings, and verification meaningful.
    
    Key rules:
    - Baselines are context-aware (segmented by runtime state, etc.)
    - Baselines only update during stable operation (not drift/spike)
    - Baselines freeze when intervention starts
    - Confidence reflects data quality and stability
    """
    
    def __init__(self, db, event_bus: EventBus):
        self.db = db
        self.event_bus = event_bus
    
    async def get_baseline(
        self,
        asset_id: str,
        metric_type: str,
        context_signature: Dict[str, Any]
    ) -> Optional[Baseline]:
        """
        Get the active baseline for an asset/metric/context.
        
        Args:
            asset_id: ID of the asset
            metric_type: Type of metric
            context_signature: Operating context
            
        Returns:
            Active baseline or None if not established
        """
        baseline_doc = await self.db.baselines.find_one(
            {
                "asset_id": asset_id,
                "metric_type": metric_type,
                "context_signature": context_signature,
                "valid_until": None,
                "frozen_at": None  # Not frozen
            },
            {"_id": 0}
        )
        
        if baseline_doc:
            return Baseline(**baseline_doc)
        return None
    
    async def get_frozen_baseline(
        self,
        asset_id: str,
        intervention_id: str
    ) -> Optional[Baseline]:
        """
        Get the frozen baseline for an intervention.
        
        Args:
            asset_id: ID of the asset
            intervention_id: ID of the intervention
            
        Returns:
            Frozen baseline or None
        """
        baseline_doc = await self.db.baselines.find_one(
            {
                "asset_id": asset_id,
                "frozen_for_intervention_id": intervention_id
            },
            {"_id": 0}
        )
        
        if baseline_doc:
            return Baseline(**baseline_doc)
        return None
    
    async def calculate_deviation(
        self,
        asset_id: str,
        metric_type: str,
        current_value: float,
        context_signature: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate deviation from baseline.
        
        Args:
            asset_id: ID of the asset
            metric_type: Type of metric
            current_value: Current metric value
            context_signature: Operating context
            
        Returns:
            Deviation info or None if no baseline
        """
        baseline = await self.get_baseline(
            asset_id, metric_type, context_signature
        )
        
        if not baseline:
            return None
        
        deviation_percent = (
            (current_value - baseline.baseline_value) / baseline.baseline_value
        ) * 100
        
        # Determine deviation type
        if abs(deviation_percent) <= 10:
            deviation_type = "NORMAL"
        elif deviation_percent > 40:
            deviation_type = "SPIKE"
        elif deviation_percent > 15:
            deviation_type = "DRIFT"
        elif deviation_percent < -40:
            deviation_type = "UNDERUTILISATION"
        else:
            deviation_type = "VARIANCE"
        
        return {
            "baseline_id": baseline.id,
            "baseline_value": baseline.baseline_value,
            "current_value": current_value,
            "deviation_percent": deviation_percent,
            "deviation_type": deviation_type,
            "within_range": (
                baseline.baseline_min <= current_value <= baseline.baseline_max
            ),
            "baseline_confidence": baseline.confidence
        }
    
    async def on_metric_received(
        self,
        asset_id: str,
        metric_type: str,
        value: float,
        context_signature: Dict[str, Any],
        correlation_id: Optional[str] = None
    ):
        """
        Handle new metric - update baseline if stable.
        
        Called by event handler when metric_calculated is received.
        
        Rules:
        - Only update baseline during stable operation
        - Do not update during drift, spike, or degraded states
        - Baseline must have sufficient history
        """
        # Check if asset is in a state that should prevent baseline update
        active_state = await self.db.states.find_one(
            {
                "asset_id": asset_id,
                "ended_at": None,
                "state_family": "ENERGY",
                "state_type": {"$in": ["DRIFT", "SPIKE", "OVERCONSUMPTION"]}
            },
            {"_id": 0}
        )
        
        if active_state:
            # Do not update baseline during abnormal states
            logger.debug(
                f"Skipping baseline update for {asset_id} - "
                f"active {active_state.get('state_type')} state"
            )
            return
        
        # Check if we have an existing baseline
        existing = await self.get_baseline(
            asset_id, metric_type, context_signature
        )
        
        if existing:
            # Baseline exists - check if update is warranted
            # (significant change in rolling average)
            await self._maybe_update_baseline(
                existing, value, correlation_id
            )
        else:
            # No baseline - try to establish one
            await self._try_establish_baseline(
                asset_id, metric_type, context_signature, correlation_id
            )
    
    async def _try_establish_baseline(
        self,
        asset_id: str,
        metric_type: str,
        context_signature: Dict[str, Any],
        correlation_id: Optional[str] = None
    ):
        """
        Try to establish a new baseline from historical metrics.
        """
        # Get metric history
        window_start = now_utc() - timedelta(days=DEFAULT_BASELINE_WINDOW_DAYS)
        
        metrics = await self.db.metrics.find(
            {
                "asset_id": asset_id,
                "metric_type": metric_type,
                "context_signature": context_signature,
                "timestamp": {"$gte": window_start.isoformat()}
            },
            {"_id": 0}
        ).to_list(1000)
        
        if len(metrics) < MIN_SAMPLES_FOR_BASELINE:
            logger.debug(
                f"Insufficient data for baseline: {len(metrics)} samples "
                f"(need {MIN_SAMPLES_FOR_BASELINE})"
            )
            return
        
        # Calculate baseline using trimmed mean (robust to outliers)
        values = [m["value"] for m in metrics]
        
        # Remove top and bottom 10%
        sorted_values = sorted(values)
        trim_count = len(sorted_values) // 10
        if trim_count > 0:
            trimmed = sorted_values[trim_count:-trim_count]
        else:
            trimmed = sorted_values
        
        baseline_value = statistics.mean(trimmed)
        std_dev = statistics.stdev(trimmed) if len(trimmed) > 1 else 0
        
        # Calculate range (baseline ± 10% or 2 std devs, whichever is larger)
        range_by_percent = baseline_value * 0.10
        range_by_std = 2 * std_dev
        range_val = max(range_by_percent, range_by_std)
        
        # Calculate confidence
        confidence = self._calculate_baseline_confidence(
            sample_count=len(metrics),
            window_days=DEFAULT_BASELINE_WINDOW_DAYS,
            std_dev=std_dev,
            baseline_value=baseline_value
        )
        
        # Create baseline
        baseline = Baseline(
            id=generate_id(),
            asset_id=asset_id,
            metric_type=metric_type,
            context_signature=context_signature,
            baseline_value=baseline_value,
            baseline_min=baseline_value - range_val,
            baseline_max=baseline_value + range_val,
            confidence=confidence,
            confidence_band=self._confidence_to_band(confidence),
            valid_from=now_utc(),
            sample_count=len(metrics),
            data_window_days=DEFAULT_BASELINE_WINDOW_DAYS,
            created_at=now_utc(),
            updated_at=now_utc()
        )
        
        # Store baseline
        baseline_doc = baseline.model_dump()
        baseline_doc["valid_from"] = baseline_doc["valid_from"].isoformat()
        baseline_doc["created_at"] = baseline_doc["created_at"].isoformat()
        baseline_doc["updated_at"] = baseline_doc["updated_at"].isoformat()
        await self.db.baselines.insert_one(baseline_doc)
        
        # Emit event
        await self.event_bus.emit(
            event_type=EventType.BASELINE_UPDATED,
            entity_type="baseline",
            entity_id=baseline.id,
            payload={
                "baseline_id": baseline.id,
                "asset_id": asset_id,
                "metric_type": metric_type,
                "baseline_value": baseline_value,
                "confidence": confidence,
                "is_new": True
            },
            correlation_id=correlation_id
        )
        
        logger.info(
            f"Baseline established for {asset_id}/{metric_type}: "
            f"{baseline_value:.2f} (confidence: {confidence:.2f})"
        )
    
    async def _maybe_update_baseline(
        self,
        existing: Baseline,
        new_value: float,
        correlation_id: Optional[str] = None
    ):
        """
        Check if baseline should be updated based on new value.
        
        Only update if there's sustained improvement (not drift).
        """
        # For MVP, we use a simple rolling update check
        # In full implementation, this would be more sophisticated
        
        # Get recent metrics
        recent_metrics = await self.db.metrics.find(
            {
                "asset_id": existing.asset_id,
                "metric_type": existing.metric_type,
                "context_signature": existing.context_signature
            },
            {"_id": 0}
        ).sort("timestamp", -1).limit(24).to_list(24)
        
        if len(recent_metrics) < 24:
            return
        
        # Calculate recent average
        recent_avg = statistics.mean([m["value"] for m in recent_metrics])
        
        # Check if change exceeds threshold
        change_percent = abs(
            (recent_avg - existing.baseline_value) / existing.baseline_value
        )
        
        if change_percent < BASELINE_UPDATE_THRESHOLD:
            return
        
        # Check if this is improvement (lower is better for energy)
        # For MVP, assume lower is better
        if recent_avg >= existing.baseline_value:
            # Not an improvement - don't update
            return
        
        # Update baseline
        await self.db.baselines.update_one(
            {"id": existing.id},
            {
                "$set": {
                    "baseline_value": recent_avg,
                    "baseline_min": recent_avg * 0.90,
                    "baseline_max": recent_avg * 1.10,
                    "updated_at": now_utc().isoformat()
                }
            }
        )
        
        logger.info(
            f"Baseline updated for {existing.asset_id}/{existing.metric_type}: "
            f"{existing.baseline_value:.2f} → {recent_avg:.2f}"
        )
    
    async def freeze_baseline(
        self,
        asset_id: str,
        intervention_id: str,
        correlation_id: Optional[str] = None
    ):
        """
        Freeze baseline when intervention starts.
        
        This is CRITICAL for accurate savings calculation.
        The frozen baseline is used for post-intervention comparison.
        """
        # Find active baselines for this asset
        baselines = await self.db.baselines.find(
            {
                "asset_id": asset_id,
                "valid_until": None,
                "frozen_at": None
            },
            {"_id": 0}
        ).to_list(100)
        
        frozen_at = now_utc()
        
        for baseline_doc in baselines:
            # Update to frozen
            await self.db.baselines.update_one(
                {"id": baseline_doc["id"]},
                {
                    "$set": {
                        "frozen_at": frozen_at.isoformat(),
                        "frozen_for_intervention_id": intervention_id
                    }
                }
            )
            
            # Emit freeze event
            await self.event_bus.emit(
                event_type=EventType.BASELINE_FROZEN,
                entity_type="baseline",
                entity_id=baseline_doc["id"],
                payload={
                    "baseline_id": baseline_doc["id"],
                    "intervention_id": intervention_id,
                    "frozen_at": frozen_at.isoformat(),
                    "baseline_value": baseline_doc["baseline_value"]
                },
                correlation_id=correlation_id
            )
            
            logger.info(
                f"Baseline frozen for intervention {intervention_id}: "
                f"{baseline_doc['id']}"
            )
    
    async def on_baseline_updated(
        self,
        asset_id: str,
        baseline_id: str,
        correlation_id: Optional[str] = None
    ):
        """
        Handle baseline update notification.
        
        Called by event handler. State engine may need to re-evaluate.
        """
        # This is a hook for any baseline-update-triggered logic
        pass
    
    def _calculate_baseline_confidence(
        self,
        sample_count: int,
        window_days: int,
        std_dev: float,
        baseline_value: float
    ) -> float:
        """
        Calculate confidence score for a baseline.
        
        Based on:
        - Sample count (more samples = higher confidence)
        - Window length (longer window = higher confidence)
        - Stability (lower std dev = higher confidence)
        """
        # Sample count factor (max at 168 = 1 week hourly)
        sample_factor = min(sample_count / 168, 1.0)
        
        # Window factor (max at 14 days)
        window_factor = min(window_days / 14, 1.0)
        
        # Stability factor (coefficient of variation)
        if baseline_value > 0:
            cv = std_dev / baseline_value
            stability_factor = max(0, 1 - cv)
        else:
            stability_factor = 0.5
        
        # Combined confidence
        confidence = (
            sample_factor * 0.40 +
            window_factor * 0.30 +
            stability_factor * 0.30
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
