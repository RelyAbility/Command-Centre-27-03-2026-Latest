"""
RAMP Priority Engine
====================

Responsibility:
- Calculate priority from state + context
- Assign priority band and explainable drivers
- Calculate economic impact (VaR and VR separately)
- Emit: priority_created, priority_updated

Priority answers: "What matters most right now?"
It combines severity, economic impact, criticality, and confidence.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging

from ..models.schema import (
    Priority, EconomicImpact, State, EventType,
    PriorityBand, PriorityType, ConfidenceBand,
    generate_id, now_utc
)
from ..events.bus import EventBus

logger = logging.getLogger(__name__)


# V1 Priority Weights
PRIORITY_WEIGHTS = {
    "severity": 0.30,
    "economic": 0.25,
    "risk": 0.15,
    "criticality": 0.15,
    "confidence": 0.10,
    "friction": -0.05,  # Subtracted
}

# V1 Default Friction (action difficulty)
DEFAULT_FRICTION = 20  # Low - assumes most MVP actions are operational adjustments

# Asset class repair cost defaults
ASSET_CLASS_REPAIR_COSTS = {
    "COMPRESSOR": 5000,
    "HVAC": 2000,
    "PUMP": 1500,
    "BOILER": 8000,
    "MOTOR": 3000,
    "LIGHTING": 500,
    "GENERIC": 2500,
}


class PriorityEngine:
    """
    Calculates priority and economic impact.
    
    Priority = (severity × w1) + (economic × w2) + (risk × w3) 
             + (criticality × w4) + (confidence × w5) - (friction × w6)
    
    Key principles:
    - Priority score is SYSTEM-only, not exposed raw
    - Priority band, drivers, and economic impact are exposed
    - VaR and VR are kept separate (not collapsed)
    - Drivers must be explainable
    """
    
    def __init__(self, db, event_bus: EventBus):
        self.db = db
        self.event_bus = event_bus
    
    async def create_priority(
        self,
        state_id: str,
        asset_id: str,
        state_family: str,
        state_type: str,
        severity_score: int,
        confidence: float,
        correlation_id: Optional[str] = None
    ):
        """
        Create priority for a new state.
        
        Called by event handler when state_started is received.
        """
        # Get asset and site info for economic calculation
        asset = await self._get_asset(asset_id)
        site = await self._get_site_for_asset(asset_id)
        
        if not asset or not site:
            logger.warning(f"Asset or site not found for {asset_id}")
            return
        
        # Get state details
        state = await self.db.states.find_one(
            {"id": state_id},
            {"_id": 0}
        )
        
        if not state:
            logger.warning(f"State not found: {state_id}")
            return
        
        # Calculate economic impact
        economic_impact = await self._calculate_economic_impact(
            state, asset, site
        )
        
        # Calculate priority components
        components = await self._calculate_priority_components(
            state, asset, economic_impact
        )
        
        # Calculate final score
        priority_score = self._calculate_score(components)
        
        # Determine band and type
        priority_band = self._score_to_band(priority_score)
        priority_type = self._determine_type(state_family, state_type)
        
        # Generate explainable drivers
        drivers = self._generate_drivers(
            state, asset, economic_impact, components
        )
        
        # Create priority
        priority = Priority(
            id=generate_id(),
            state_id=state_id,
            asset_id=asset_id,
            priority_score=priority_score,
            priority_band=priority_band,
            priority_type=priority_type,
            drivers=drivers,
            economic_impact=economic_impact,
            score_components=components,
            created_at=now_utc(),
            updated_at=now_utc()
        )
        
        # Store priority
        priority_doc = priority.model_dump()
        priority_doc["created_at"] = priority_doc["created_at"].isoformat()
        priority_doc["updated_at"] = priority_doc["updated_at"].isoformat()
        await self.db.priorities.insert_one(priority_doc)
        
        # Emit event
        await self.event_bus.emit(
            event_type=EventType.PRIORITY_CREATED,
            entity_type="priority",
            entity_id=priority.id,
            payload={
                "priority_id": priority.id,
                "state_id": state_id,
                "asset_id": asset_id,
                "priority_band": priority_band.value,
                "drivers": drivers,
                "value_at_risk_per_day": economic_impact.value_at_risk_per_day
            },
            correlation_id=correlation_id
        )
        
        logger.info(
            f"Priority created: {priority.id} "
            f"({priority_band.value}) for state {state_id}"
        )
    
    async def update_priority(
        self,
        state_id: str,
        severity_score: int,
        duration_minutes: int,
        correlation_id: Optional[str] = None
    ):
        """
        Update priority when state changes.
        
        Called by event handler when state_updated is received.
        """
        # Find existing priority
        priority_doc = await self.db.priorities.find_one(
            {"state_id": state_id, "expires_at": None},
            {"_id": 0}
        )
        
        if not priority_doc:
            logger.warning(f"No active priority for state {state_id}")
            return
        
        # Get updated state
        state = await self.db.states.find_one(
            {"id": state_id},
            {"_id": 0}
        )
        
        if not state:
            return
        
        # Get asset and site
        asset = await self._get_asset(priority_doc["asset_id"])
        site = await self._get_site_for_asset(priority_doc["asset_id"])
        
        if not asset or not site:
            return
        
        # Recalculate economic impact (may change with duration)
        economic_impact = await self._calculate_economic_impact(
            state, asset, site
        )
        
        # Recalculate priority
        components = await self._calculate_priority_components(
            state, asset, economic_impact
        )
        priority_score = self._calculate_score(components)
        priority_band = self._score_to_band(priority_score)
        
        # Regenerate drivers
        drivers = self._generate_drivers(
            state, asset, economic_impact, components
        )
        
        # Update priority
        await self.db.priorities.update_one(
            {"id": priority_doc["id"]},
            {
                "$set": {
                    "priority_score": priority_score,
                    "priority_band": priority_band.value,
                    "drivers": drivers,
                    "economic_impact": economic_impact.model_dump(),
                    "score_components": components,
                    "updated_at": now_utc().isoformat()
                }
            }
        )
        
        # Emit event if band changed
        if priority_band.value != priority_doc["priority_band"]:
            await self.event_bus.emit(
                event_type=EventType.PRIORITY_UPDATED,
                entity_type="priority",
                entity_id=priority_doc["id"],
                payload={
                    "priority_id": priority_doc["id"],
                    "priority_band": priority_band.value,
                    "drivers": drivers,
                    "value_at_risk_per_day": economic_impact.value_at_risk_per_day
                },
                correlation_id=correlation_id
            )
    
    async def expire_priority(
        self,
        state_id: str,
        correlation_id: Optional[str] = None
    ):
        """
        Expire priority when state ends.
        
        Priority decays when state resolves.
        """
        expired_at = now_utc()
        
        await self.db.priorities.update_one(
            {"state_id": state_id, "expires_at": None},
            {
                "$set": {
                    "expires_at": expired_at.isoformat(),
                    "updated_at": expired_at.isoformat()
                }
            }
        )
        
        logger.info(f"Priority expired for state {state_id}")
    
    async def _calculate_economic_impact(
        self,
        state: Dict,
        asset: Dict,
        site: Dict
    ) -> EconomicImpact:
        """
        Calculate economic impact (VaR and VR separately).
        """
        state_family = state.get("state_family")
        state_type = state.get("state_type")
        deviation_percent = state.get("deviation_percent", 0)
        
        # Get site economic inputs
        tariff = site.get("energy_tariff") or 0.12
        hourly_prod_value = site.get("hourly_production_value") or 500
        operating_hours = site.get("operating_hours_per_day", 24)
        
        var_per_day = 0.0
        vr_per_day = 0.0
        calculation_method = "UNKNOWN"
        inputs = {}
        
        if state_family == "ENERGY":
            # Energy state economic impact
            calculation_method = "ENERGY_DEVIATION"
            
            # Assume baseline consumption based on deviation
            # This is simplified - full implementation would use actual baseline
            baseline_hourly = 50  # kWh/hr (placeholder)
            excess_hourly = baseline_hourly * (abs(deviation_percent) / 100)
            
            var_per_day = excess_hourly * operating_hours * tariff
            vr_per_day = var_per_day * 0.8  # Assume 80% recoverable
            
            inputs = {
                "deviation_percent": deviation_percent,
                "tariff": tariff,
                "operating_hours": operating_hours,
                "estimated_excess_kwh_per_day": excess_hourly * operating_hours
            }
        
        elif state_family == "MAINTENANCE":
            # Maintenance state economic impact
            calculation_method = "MAINTENANCE_RISK"
            
            # Use repair cost as base
            repair_cost = (
                asset.get("estimated_repair_cost") or
                ASSET_CLASS_REPAIR_COSTS.get(asset.get("asset_class"), 2500)
            )
            
            # Progression rate based on state type
            if state_type == "DEGRADING":
                var_per_day = repair_cost * 0.10  # 10% risk per day
            elif state_type == "ALERT":
                var_per_day = repair_cost * 0.25 + (hourly_prod_value * 2)  # Higher risk + potential downtime
            elif state_type == "FAILURE":
                var_per_day = repair_cost + (hourly_prod_value * 8)  # Full repair + lost production
            
            vr_per_day = var_per_day * 0.7  # Assume 70% recoverable if addressed
            
            inputs = {
                "repair_cost": repair_cost,
                "hourly_production_value": hourly_prod_value,
                "state_type": state_type
            }
        
        elif state_family == "PRODUCTION":
            # Production state economic impact
            calculation_method = "PRODUCTION_LOSS"
            
            # Simplified: assume lost output
            if state_type == "BOTTLENECKED":
                var_per_day = hourly_prod_value * operating_hours * 0.30  # 30% loss
            elif state_type == "PAUSED":
                var_per_day = hourly_prod_value * 2  # 2 hours equivalent
            elif state_type == "IMBALANCED":
                var_per_day = hourly_prod_value * operating_hours * 0.15  # 15% inefficiency
            
            vr_per_day = var_per_day * 0.9  # Production usually recoverable
            
            inputs = {
                "hourly_production_value": hourly_prod_value,
                "operating_hours": operating_hours
            }
        
        # Determine confidence based on input availability
        confidence = ConfidenceBand.HIGH
        if not site.get("energy_tariff"):
            confidence = ConfidenceBand.MEDIUM
        if not site.get("hourly_production_value"):
            confidence = ConfidenceBand.LOW
        
        return EconomicImpact(
            value_at_risk_per_day=round(var_per_day, 2),
            value_recoverable_per_day=round(vr_per_day, 2),
            currency=site.get("currency", "USD"),
            calculation_method=calculation_method,
            confidence=confidence,
            inputs=inputs
        )
    
    async def _calculate_priority_components(
        self,
        state: Dict,
        asset: Dict,
        economic_impact: EconomicImpact
    ) -> Dict[str, float]:
        """
        Calculate normalized priority components (0-100 scale).
        """
        # Severity (state severity score * 10, capped at 100)
        severity = min(state.get("severity_score", 5) * 10, 100)
        
        # Economic (normalize VaR to 0-100, assume $1500/day = 100)
        economic = min(
            (economic_impact.value_at_risk_per_day / 1500) * 100,
            100
        )
        
        # Risk movement (simplified for MVP - based on severity)
        risk = min(severity * 0.6, 100)
        
        # Criticality (from asset)
        criticality = asset.get("criticality_score", 50)
        
        # Confidence (state confidence * 100)
        confidence = state.get("confidence", 0.7) * 100
        
        # Friction (default for MVP)
        friction = DEFAULT_FRICTION
        
        return {
            "severity": severity,
            "economic": economic,
            "risk": risk,
            "criticality": criticality,
            "confidence": confidence,
            "friction": friction
        }
    
    def _calculate_score(self, components: Dict[str, float]) -> float:
        """
        Calculate final priority score.
        
        Score = sum(component * weight) - (friction * friction_weight)
        """
        score = 0.0
        for component, value in components.items():
            weight = PRIORITY_WEIGHTS.get(component, 0)
            if component == "friction":
                score += value * weight  # Already negative in weights
            else:
                score += value * weight
        
        return round(max(0, min(100, score)), 2)
    
    def _score_to_band(self, score: float) -> PriorityBand:
        """Convert score to priority band."""
        if score >= 80:
            return PriorityBand.CRITICAL
        elif score >= 60:
            return PriorityBand.HIGH
        elif score >= 40:
            return PriorityBand.MEDIUM
        return PriorityBand.LOW
    
    def _determine_type(
        self,
        state_family: str,
        state_type: str
    ) -> PriorityType:
        """Determine priority type based on state."""
        if state_family == "ENERGY":
            if state_type in ["UNDERUTILISATION"]:
                return PriorityType.OPPORTUNITY
            return PriorityType.OPERATIONAL
        elif state_family == "MAINTENANCE":
            return PriorityType.MAINTENANCE
        elif state_family == "PRODUCTION":
            return PriorityType.OPERATIONAL
        return PriorityType.RISK
    
    def _generate_drivers(
        self,
        state: Dict,
        asset: Dict,
        economic_impact: EconomicImpact,
        components: Dict[str, float]
    ) -> List[str]:
        """
        Generate explainable driver statements.
        
        Drivers must be human-readable and justify the priority.
        """
        drivers = []
        
        # State driver
        deviation = state.get("deviation_percent", 0)
        state_type = state.get("state_type", "")
        if deviation:
            drivers.append(
                f"{abs(deviation):.0f}% {state_type.lower()} on {asset.get('name', 'asset')}"
            )
        else:
            drivers.append(f"{state_type} condition on {asset.get('name', 'asset')}")
        
        # Economic driver
        var = economic_impact.value_at_risk_per_day
        if var > 0:
            drivers.append(
                f"Estimated ${var:.0f}/day at risk"
            )
        
        # Criticality driver (if high)
        if asset.get("criticality_score", 50) >= 70:
            drivers.append(f"Critical asset ({asset.get('criticality_band', 'HIGH')})")
        
        # Duration driver (if state has been active)
        duration = state.get("duration_minutes", 0)
        if duration > 60:
            hours = duration / 60
            drivers.append(f"Active for {hours:.1f} hours")
        
        return drivers[:4]  # Limit to 4 drivers
    
    async def _get_asset(self, asset_id: str) -> Optional[Dict]:
        """Get asset by ID."""
        return await self.db.assets.find_one(
            {"id": asset_id},
            {"_id": 0}
        )
    
    async def _get_site_for_asset(self, asset_id: str) -> Optional[Dict]:
        """Get site for an asset (via system)."""
        asset = await self._get_asset(asset_id)
        if not asset:
            return None
        
        system = await self.db.systems.find_one(
            {"id": asset.get("system_id")},
            {"_id": 0}
        )
        if not system:
            return None
        
        return await self.db.sites.find_one(
            {"id": system.get("site_id")},
            {"_id": 0}
        )
