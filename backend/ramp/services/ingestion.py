"""
RAMP Ingestion Service
======================

Responsibility:
- Receive raw signals from external sources
- Calculate metrics from signals
- Emit: signal_ingested, metric_calculated

This service is the ENTRY POINT for data into RAMP.
Signals are inputs, not truth. Truth comes from states.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging

from ..models.schema import (
    Signal, Metric, EventType, SignalQuality,
    generate_id, now_utc
)
from ..events.bus import EventBus

logger = logging.getLogger(__name__)


class IngestionService:
    """
    Handles signal ingestion and metric calculation.
    
    Flow:
        External source → ingest_signal() → Signal stored
        Signal stored → calculate_metrics() → Metrics stored
        Each step emits events for downstream processing
    """
    
    def __init__(self, db, event_bus: EventBus):
        self.db = db
        self.event_bus = event_bus
    
    async def ingest_signal(
        self,
        asset_id: str,
        signal_type: str,
        value: float,
        unit: str,
        timestamp: datetime,
        quality: SignalQuality = SignalQuality.GOOD,
        correlation_id: Optional[str] = None
    ) -> Signal:
        """
        Ingest a raw signal reading.
        
        Args:
            asset_id: ID of the asset
            signal_type: Type of signal (e.g., "energy_consumption")
            value: Signal value
            unit: Unit of measurement
            timestamp: When the reading was taken
            quality: Signal quality indicator
            correlation_id: Optional correlation for event chain
            
        Returns:
            Created signal
        """
        # Create signal
        signal = Signal(
            id=generate_id(),
            asset_id=asset_id,
            signal_type=signal_type,
            value=value,
            unit=unit,
            quality=quality,
            timestamp=timestamp,
            ingested_at=now_utc()
        )
        
        # Store in database
        signal_doc = signal.model_dump()
        signal_doc["timestamp"] = signal_doc["timestamp"].isoformat()
        signal_doc["ingested_at"] = signal_doc["ingested_at"].isoformat()
        await self.db.signals.insert_one(signal_doc)
        
        # Emit event
        await self.event_bus.emit(
            event_type=EventType.SIGNAL_INGESTED,
            entity_type="signal",
            entity_id=signal.id,
            payload={
                "signal_id": signal.id,
                "asset_id": asset_id,
                "signal_type": signal_type,
                "value": value,
                "unit": unit,
                "quality": quality.value if isinstance(quality, SignalQuality) else quality,
                "timestamp": timestamp.isoformat()
            },
            correlation_id=correlation_id
        )
        
        logger.info(f"Signal ingested: {signal_type} = {value} for asset {asset_id}")
        
        # Calculate metrics from this signal
        await self._calculate_metrics(signal, correlation_id)
        
        return signal
    
    async def ingest_batch(
        self,
        signals: List[Dict[str, Any]],
        correlation_id: Optional[str] = None
    ) -> List[Signal]:
        """
        Ingest multiple signals in batch.
        
        Args:
            signals: List of signal data dicts
            correlation_id: Optional correlation for event chain
            
        Returns:
            List of created signals
        """
        results = []
        corr_id = correlation_id or generate_id()
        
        for signal_data in signals:
            signal = await self.ingest_signal(
                asset_id=signal_data["asset_id"],
                signal_type=signal_data["signal_type"],
                value=signal_data["value"],
                unit=signal_data.get("unit", ""),
                timestamp=signal_data["timestamp"],
                quality=signal_data.get("quality", SignalQuality.GOOD),
                correlation_id=corr_id
            )
            results.append(signal)
        
        return results
    
    async def _calculate_metrics(
        self,
        signal: Signal,
        correlation_id: Optional[str] = None
    ):
        """
        Calculate metrics from a signal.
        
        For MVP, we support simple metric derivation:
        - energy_consumption → energy_intensity (if production context available)
        - temperature → temperature (passthrough)
        - vibration → vibration (passthrough)
        
        More complex metric calculations can be added.
        """
        # Get asset context for metric calculation
        asset = await self.db.assets.find_one(
            {"id": signal.asset_id},
            {"_id": 0}
        )
        
        if not asset:
            logger.warning(f"Asset not found: {signal.asset_id}")
            return
        
        # Get current context (for baseline segmentation)
        context = await self._get_asset_context(signal.asset_id)
        
        # Calculate metrics based on signal type
        metrics = []
        
        if signal.signal_type == "energy_consumption":
            # For MVP, create energy_intensity metric
            # In full implementation, would divide by production units
            metric = Metric(
                id=generate_id(),
                asset_id=signal.asset_id,
                metric_type="energy_intensity",
                value=signal.value,  # Simplified: direct passthrough
                unit=signal.unit,
                context_signature=context,
                timestamp=signal.timestamp,
                calculated_at=now_utc()
            )
            metrics.append(metric)
        
        elif signal.signal_type in ["temperature", "vibration"]:
            # Passthrough metrics
            metric = Metric(
                id=generate_id(),
                asset_id=signal.asset_id,
                metric_type=signal.signal_type,
                value=signal.value,
                unit=signal.unit,
                context_signature=context,
                timestamp=signal.timestamp,
                calculated_at=now_utc()
            )
            metrics.append(metric)
        
        # Store metrics and emit events
        for metric in metrics:
            metric_doc = metric.model_dump()
            metric_doc["timestamp"] = metric_doc["timestamp"].isoformat()
            metric_doc["calculated_at"] = metric_doc["calculated_at"].isoformat()
            await self.db.metrics.insert_one(metric_doc)
            
            await self.event_bus.emit(
                event_type=EventType.METRIC_CALCULATED,
                entity_type="metric",
                entity_id=metric.id,
                payload={
                    "metric_id": metric.id,
                    "asset_id": metric.asset_id,
                    "metric_type": metric.metric_type,
                    "value": metric.value,
                    "unit": metric.unit,
                    "context_signature": metric.context_signature,
                    "timestamp": metric.timestamp.isoformat()
                },
                correlation_id=correlation_id
            )
            
            logger.debug(f"Metric calculated: {metric.metric_type} = {metric.value}")
    
    async def _get_asset_context(self, asset_id: str) -> Dict[str, Any]:
        """
        Get current operating context for an asset.
        
        This is used for baseline segmentation.
        
        Returns:
            Context signature dict
        """
        # For MVP, return simplified context
        # In full implementation, would query operational state, production band, etc.
        
        # Check if there's an active operational state
        active_state = await self.db.states.find_one(
            {
                "asset_id": asset_id,
                "state_family": "OPERATIONAL",
                "ended_at": None
            },
            {"_id": 0}
        )
        
        runtime_state = "RUNNING"  # Default
        if active_state:
            runtime_state = active_state.get("state_type", "RUNNING")
        
        return {
            "runtime_state": runtime_state,
            "production_band": "NORMAL"  # Simplified for MVP
        }
