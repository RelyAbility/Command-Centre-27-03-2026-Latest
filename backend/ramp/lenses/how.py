"""
HOW Lens Payload Builder
========================

Governs what operators see in the Command Centre.
Enforces the Lens Contract for HOW-scoped data.

INCLUDES:
- priority_band, priority_type
- drivers (explainable reasons)
- value_at_risk_per_day, value_recoverable_per_day
- confidence_band
- state_type, severity_band, deviation_percent

EXCLUDES:
- priority_score (SYSTEM only)
- score_components (SYSTEM only)
- economic_impact.inputs (SYSTEM only)
- severity_score (raw number)
- confidence (raw number)
- calculation internals
"""

from typing import Dict, Any, List, Optional
from datetime import datetime


class HOWLens:
    """
    HOW Lens payload builder.
    
    All HOW endpoints MUST use these methods to construct responses.
    This ensures lens discipline is enforced at payload level.
    """
    
    @staticmethod
    def priority_response(priority: Dict[str, Any], asset: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build HOW-compliant priority payload.
        
        Args:
            priority: Priority record from database
            asset: Associated asset record
            
        Returns:
            HOW-compliant priority dict
        """
        economic = priority.get("economic_impact", {})
        
        return {
            "priority_id": priority.get("id"),
            "asset_id": priority.get("asset_id"),
            "asset_name": asset.get("name", "Unknown"),
            "state_id": priority.get("state_id"),
            "priority_band": priority.get("priority_band"),
            "priority_type": priority.get("priority_type"),
            "drivers": priority.get("drivers", []),
            "value_at_risk_per_day": economic.get("value_at_risk_per_day", 0),
            "value_recoverable_per_day": economic.get("value_recoverable_per_day", 0),
            "currency": economic.get("currency", "USD"),
            "confidence_band": economic.get("confidence", "MEDIUM"),
            "created_at": _format_datetime(priority.get("created_at"))
            # NOT included: priority_score, score_components, economic_impact.inputs
        }
    
    @staticmethod
    def priority_list_response(priorities: List[Dict[str, Any]], assets: Dict[str, Dict]) -> Dict[str, Any]:
        """
        Build HOW-compliant priority list response.
        
        Args:
            priorities: List of priority records
            assets: Dict of asset_id -> asset record
            
        Returns:
            HOW-compliant priority list response
        """
        items = [
            HOWLens.priority_response(p, assets.get(p.get("asset_id"), {}))
            for p in priorities
        ]
        return {
            "priorities": items,
            "count": len(items)
        }
    
    @staticmethod
    def state_response(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build HOW-compliant state payload.
        
        Args:
            state: State record from database
            
        Returns:
            HOW-compliant state dict
        """
        return {
            "state_id": state.get("id"),
            "state_family": state.get("state_family"),
            "state_type": state.get("state_type"),
            "severity_band": state.get("severity_band"),
            "confidence_band": state.get("confidence_band"),
            "deviation_percent": state.get("deviation_percent"),
            "duration_minutes": state.get("duration_minutes", 0),
            "started_at": _format_datetime(state.get("started_at")),
            "ended_at": _format_datetime(state.get("ended_at"))
            # NOT included: severity_score, severity_components, confidence, confidence_components
        }
    
    @staticmethod
    def asset_state_response(
        asset: Dict[str, Any],
        active_states: List[Dict[str, Any]],
        recent_states: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Build HOW-compliant asset state response.
        
        Args:
            asset: Asset record
            active_states: Currently active states
            recent_states: Recent state history
            
        Returns:
            HOW-compliant asset state response
        """
        criticality = asset.get("criticality_score", 50)
        if criticality >= 80:
            criticality_band = "CRITICAL"
        elif criticality >= 60:
            criticality_band = "HIGH"
        elif criticality >= 40:
            criticality_band = "MEDIUM"
        else:
            criticality_band = "LOW"
        
        return {
            "asset_id": asset.get("id"),
            "asset_name": asset.get("name"),
            "criticality_band": criticality_band,
            "active_states": [HOWLens.state_response(s) for s in active_states],
            "recent_states": [HOWLens.state_response(s) for s in recent_states]
            # NOT included: criticality_score (raw), asset internals
        }
    
    @staticmethod
    def intervention_created_response(
        intervention_id: str,
        state_id: str
    ) -> Dict[str, Any]:
        """
        Build HOW-compliant intervention created response.
        """
        return {
            "intervention_id": intervention_id,
            "state_id": state_id,
            "message": "Intervention created. Baseline frozen for verification."
        }
    
    @staticmethod
    def intervention_completed_response(intervention_id: str) -> Dict[str, Any]:
        """
        Build HOW-compliant intervention completed response.
        """
        return {
            "intervention_id": intervention_id,
            "message": "Intervention completed. Verification started."
        }
    
    @staticmethod
    def outcome_response(outcome: Optional[Dict[str, Any]], intervention_id: str) -> Dict[str, Any]:
        """
        Build HOW-compliant outcome response.
        
        Args:
            outcome: Outcome record or None if not yet verified
            intervention_id: ID of the intervention
            
        Returns:
            HOW-compliant outcome response
        """
        if not outcome:
            return {
                "intervention_id": intervention_id,
                "status": "pending",
                "message": "Verification not yet complete"
            }
        
        return {
            "intervention_id": intervention_id,
            "status": outcome.get("status", "VERIFIED").lower(),
            "savings_value": outcome.get("savings_value"),
            "savings_unit": outcome.get("savings_unit"),
            "savings_type": outcome.get("savings_type"),
            "confidence_band": outcome.get("confidence_band"),
            "verified_at": _format_datetime(outcome.get("verified_at"))
            # NOT included: confidence (raw), frozen_baseline_value, actual_value
        }


def _format_datetime(dt) -> Optional[str]:
    """Format datetime to ISO string."""
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)
