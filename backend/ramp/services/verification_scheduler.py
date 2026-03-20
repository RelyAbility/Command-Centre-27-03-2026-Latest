"""
RAMP Verification Scheduler
============================

Processes pending outcomes and attempts verification when:
1. Verification window has elapsed
2. Sufficient post-action data is available

If insufficient data:
- Retry up to max_retry_attempts
- After max retries, mark as INSUFFICIENT_DATA

When verified:
- Calculate savings against frozen baseline
- Assign explicit confidence
- Update learning records
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
import logging
import statistics

from sqlalchemy import text
from .verification_config import (
    get_verification_config, 
    VerificationConfig, 
    OutcomeStatus
)

logger = logging.getLogger(__name__)


def confidence_to_band(confidence: float) -> str:
    """Convert confidence score to band."""
    if confidence >= 0.80:
        return "HIGH"
    elif confidence >= 0.60:
        return "MEDIUM"
    elif confidence >= 0.40:
        return "LOW"
    return "INSUFFICIENT"


class VerificationScheduler:
    """
    Processes pending verification outcomes.
    
    Called periodically to check if pending outcomes are ready
    for verification based on:
    1. Time since intervention completion
    2. Available post-action metric data
    
    Key principles:
    - Always verify against frozen baseline
    - Never force verification without sufficient data
    - Explicit confidence on all verified outcomes
    """
    
    def __init__(self, db):
        self.db = db
    
    async def process_pending_outcomes(self) -> Dict[str, Any]:
        """
        Process all pending outcomes.
        
        Returns summary of processing results.
        """
        results = {
            "processed": 0,
            "verified": 0,
            "insufficient_data": 0,
            "still_pending": 0,
            "errors": 0,
            "details": []
        }
        
        # Get all pending outcomes with intervention/state info
        pending = await self.db.get_pending_outcomes()
        
        for outcome in pending:
            try:
                result = await self._process_outcome(outcome)
                results["processed"] += 1
                results["details"].append(result)
                
                if result["status"] == "VERIFIED":
                    results["verified"] += 1
                elif result["status"] == "INSUFFICIENT_DATA":
                    results["insufficient_data"] += 1
                else:
                    results["still_pending"] += 1
                    
            except Exception as e:
                logger.error(f"Error processing outcome {outcome.get('id')}: {e}")
                results["errors"] += 1
                results["details"].append({
                    "outcome_id": outcome.get("id"),
                    "status": "ERROR",
                    "error": str(e)
                })
        
        return results
    
    async def _process_outcome(self, outcome: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single pending outcome.
        
        Decision flow:
        1. Get verification config for this state family / intervention type
        2. Check if verification window has passed
        3. If yes, attempt verification
        4. If insufficient data, either retry or mark INSUFFICIENT_DATA
        """
        outcome_id = outcome["id"]
        state_family = outcome.get("state_family", "OPERATIONAL")
        intervention_type = outcome.get("intervention_type", "ADJUSTMENT")
        
        # Get config
        config = get_verification_config(state_family, intervention_type)
        
        # Get intervention completion time
        completed_at = outcome.get("intervention_completed_at")
        if isinstance(completed_at, str):
            completed_at = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
        
        now = datetime.now(timezone.utc)
        window_end = completed_at + timedelta(hours=config.window_hours)
        
        # Check if window has passed
        if now < window_end:
            # Window not yet elapsed
            time_remaining = (window_end - now).total_seconds() / 3600
            return {
                "outcome_id": outcome_id,
                "status": "PENDING",
                "reason": f"Verification window not elapsed ({time_remaining:.1f}h remaining)"
            }
        
        # Window has passed - attempt verification
        return await self._attempt_verification(outcome, config)
    
    async def _attempt_verification(
        self, 
        outcome: Dict[str, Any],
        config: VerificationConfig
    ) -> Dict[str, Any]:
        """
        Attempt to verify an outcome.
        
        Steps:
        1. Get frozen baseline
        2. Get post-action metrics
        3. Check if sufficient data
        4. Calculate savings and confidence
        5. Update outcome status
        """
        outcome_id = outcome["id"]
        intervention_id = outcome["intervention_id"]
        frozen_baseline_id = outcome.get("frozen_baseline_id")
        retry_count = outcome.get("retry_count") or 0
        
        # Get frozen baseline
        if not frozen_baseline_id:
            return await self._mark_insufficient_data(
                outcome_id, 
                retry_count,
                config,
                "No frozen baseline found"
            )
        
        frozen_baseline = await self.db.get_baseline_by_id(frozen_baseline_id)
        if not frozen_baseline:
            return await self._mark_insufficient_data(
                outcome_id,
                retry_count,
                config,
                "Frozen baseline record not found"
            )
        
        # Get intervention to find asset_id
        intervention = await self.db.get_intervention(intervention_id)
        if not intervention:
            return await self._mark_insufficient_data(
                outcome_id,
                retry_count,
                config,
                "Intervention not found"
            )
        
        asset_id = intervention["asset_id"]
        metric_type = frozen_baseline["metric_type"]
        baseline_value = frozen_baseline["baseline_value"]
        
        # Calculate verification window
        completed_at = intervention.get("completed_at")
        if isinstance(completed_at, str):
            completed_at = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
        
        window_start = completed_at
        window_end = completed_at + timedelta(hours=config.window_hours)
        
        # Get post-action metrics
        post_metrics = await self.db.get_post_action_metrics(
            asset_id=asset_id,
            metric_type=metric_type,
            start_time=window_start,
            end_time=window_end
        )
        
        # Check if sufficient data
        if len(post_metrics) < config.min_samples:
            return await self._handle_insufficient_data(
                outcome_id,
                retry_count,
                config,
                f"Only {len(post_metrics)} samples, need {config.min_samples}"
            )
        
        # Check window coverage
        if len(post_metrics) >= 2:
            actual_coverage = self._calculate_coverage(post_metrics, window_start, window_end)
            if actual_coverage < config.min_window_coverage:
                return await self._handle_insufficient_data(
                    outcome_id,
                    retry_count,
                    config,
                    f"Coverage {actual_coverage:.1%}, need {config.min_window_coverage:.1%}"
                )
        
        # Calculate verification
        actual_values = [m["value"] for m in post_metrics]
        actual_avg = statistics.mean(actual_values)
        
        # Calculate savings (baseline - actual)
        # Positive savings = improvement (actual is lower than baseline)
        savings_value = baseline_value - actual_avg
        
        # Determine savings type
        if metric_type in ["energy_intensity", "energy_consumption", "power"]:
            savings_type = "energy"
            savings_unit = "kWh"
        elif metric_type in ["temperature", "pressure", "vibration"]:
            savings_type = "operational"
            savings_unit = frozen_baseline.get("unit", "units")
        else:
            savings_type = "operational"
            savings_unit = "units"
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            actual_values,
            baseline_value,
            len(post_metrics),
            config.min_samples
        )
        
        # Update outcome as verified
        now = datetime.now(timezone.utc)
        await self.db.update_outcome(outcome_id, {
            "actual_value": round(actual_avg, 4),
            "savings_value": round(savings_value, 4),
            "savings_unit": savings_unit,
            "savings_type": savings_type,
            "confidence": round(confidence, 4),
            "confidence_band": confidence_to_band(confidence),
            "status": OutcomeStatus.VERIFIED.value,
            "verified_at": now,
            "verification_notes": f"Verified with {len(post_metrics)} samples over {config.window_hours}h window"
        })
        
        # Update learning
        await self._update_learning(
            intervention,
            outcome.get("state_family", "OPERATIONAL"),
            outcome.get("state_type", "UNKNOWN"),
            savings_value,
            confidence
        )
        
        # Create verification event
        await self.db.create_event({
            "event_type": "outcome_verified",
            "entity_type": "outcome",
            "entity_id": outcome_id,
            "payload": {
                "outcome_id": outcome_id,
                "intervention_id": intervention_id,
                "savings_value": round(savings_value, 4),
                "savings_type": savings_type,
                "confidence": round(confidence, 4),
                "confidence_band": confidence_to_band(confidence),
                "sample_count": len(post_metrics),
                "frozen_baseline_value": baseline_value,
                "actual_value": round(actual_avg, 4)
            }
        })
        
        logger.info(
            f"Outcome verified: {outcome_id}, "
            f"savings={savings_value:.2f} {savings_unit}, "
            f"confidence={confidence:.2f}"
        )
        
        return {
            "outcome_id": outcome_id,
            "status": "VERIFIED",
            "savings_value": round(savings_value, 4),
            "savings_unit": savings_unit,
            "confidence": round(confidence, 4),
            "sample_count": len(post_metrics)
        }
    
    def _calculate_coverage(
        self,
        metrics: List[Dict],
        window_start: datetime,
        window_end: datetime
    ) -> float:
        """Calculate what % of the verification window has data coverage."""
        if not metrics:
            return 0.0
        
        # Get actual time range of data
        timestamps = []
        for m in metrics:
            ts = m.get("timestamp")
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            timestamps.append(ts)
        
        data_start = min(timestamps)
        data_end = max(timestamps)
        
        window_duration = (window_end - window_start).total_seconds()
        data_duration = (data_end - data_start).total_seconds()
        
        if window_duration <= 0:
            return 0.0
        
        return min(data_duration / window_duration, 1.0)
    
    def _calculate_confidence(
        self,
        actual_values: List[float],
        baseline_value: float,
        sample_count: int,
        min_samples: int
    ) -> float:
        """
        Calculate verification confidence.
        
        Components:
        1. Sample adequacy (40%) - how many samples vs minimum
        2. Post-action stability (35%) - low variance = higher confidence
        3. Change significance (25%) - larger changes are more confident
        """
        # Sample adequacy factor
        sample_factor = min(sample_count / (min_samples * 2), 1.0)
        
        # Stability factor (coefficient of variation)
        if len(actual_values) > 1:
            std_dev = statistics.stdev(actual_values)
            mean_val = statistics.mean(actual_values)
            if mean_val > 0:
                cv = std_dev / mean_val
                stability_factor = max(0, 1 - min(cv, 1.0))
            else:
                stability_factor = 0.5
        else:
            stability_factor = 0.3
        
        # Change significance factor
        actual_avg = statistics.mean(actual_values)
        if baseline_value > 0:
            change_percent = abs(actual_avg - baseline_value) / baseline_value
            # 15%+ change = full significance confidence
            significance_factor = min(change_percent / 0.15, 1.0)
        else:
            significance_factor = 0.5
        
        # Combined confidence
        confidence = (
            sample_factor * 0.40 +
            stability_factor * 0.35 +
            significance_factor * 0.25
        )
        
        return min(max(confidence, 0.0), 1.0)
    
    async def _handle_insufficient_data(
        self,
        outcome_id: str,
        retry_count: int,
        config: VerificationConfig,
        reason: str
    ) -> Dict[str, Any]:
        """Handle case where there's insufficient data for verification."""
        new_retry_count = retry_count + 1
        
        if new_retry_count >= config.max_retry_attempts:
            # Max retries reached - mark as insufficient data
            return await self._mark_insufficient_data(
                outcome_id,
                new_retry_count,
                config,
                f"Max retries reached ({config.max_retry_attempts}). {reason}"
            )
        
        # Increment retry count and keep pending
        await self.db.update_outcome(outcome_id, {
            "retry_count": new_retry_count,
            "verification_notes": f"Retry {new_retry_count}/{config.max_retry_attempts}: {reason}"
        })
        
        return {
            "outcome_id": outcome_id,
            "status": "PENDING",
            "reason": reason,
            "retry_count": new_retry_count,
            "max_retries": config.max_retry_attempts
        }
    
    async def _mark_insufficient_data(
        self,
        outcome_id: str,
        retry_count: int,
        config: VerificationConfig,
        reason: str
    ) -> Dict[str, Any]:
        """Mark outcome as INSUFFICIENT_DATA."""
        now = datetime.now(timezone.utc)
        
        await self.db.update_outcome(outcome_id, {
            "status": OutcomeStatus.INSUFFICIENT_DATA.value,
            "retry_count": retry_count,
            "verified_at": now,
            "verification_notes": reason
        })
        
        # Create event
        await self.db.create_event({
            "event_type": "outcome_insufficient_data",
            "entity_type": "outcome",
            "entity_id": outcome_id,
            "payload": {
                "outcome_id": outcome_id,
                "reason": reason,
                "retry_count": retry_count
            }
        })
        
        logger.warning(f"Outcome marked insufficient data: {outcome_id} - {reason}")
        
        return {
            "outcome_id": outcome_id,
            "status": "INSUFFICIENT_DATA",
            "reason": reason
        }
    
    async def _update_learning(
        self,
        intervention: Dict[str, Any],
        state_family: str,
        state_type: str,
        savings_value: float,
        confidence: float
    ):
        """Update learning records from verified outcome."""
        asset_id = intervention["asset_id"]
        
        # Get existing learning record
        existing = await self.db.get_learning_record(asset_id, state_type)
        
        if existing:
            # Update existing
            old_count = existing.get("intervention_count", 0)
            old_total = existing.get("total_savings", 0.0)
            
            new_count = old_count + 1
            new_total = old_total + savings_value
            new_avg = new_total / new_count if new_count > 0 else 0.0
            
            await self.db.upsert_learning_record({
                "asset_id": asset_id,
                "state_type": state_type,
                "occurrence_count": existing.get("occurrence_count", 1),
                "intervention_count": new_count,
                "total_savings": new_total,
                "avg_effectiveness": new_avg
            })
        else:
            # Create new
            await self.db.upsert_learning_record({
                "asset_id": asset_id,
                "state_type": state_type,
                "occurrence_count": 1,
                "intervention_count": 1,
                "total_savings": savings_value,
                "avg_effectiveness": savings_value
            })
        
        # Create learning updated event
        await self.db.create_event({
            "event_type": "learning_updated",
            "entity_type": "learning",
            "entity_id": f"{asset_id}:{state_type}",
            "payload": {
                "asset_id": asset_id,
                "state_type": state_type,
                "savings_value": savings_value,
                "confidence": confidence
            }
        })
