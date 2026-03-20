"""
RAMP HOW Lens
=============

The HOW lens serves OPERATORS who need to know:
- WHAT to do
- WHY it matters
- HOW confident we are

The HOW lens must NOT expose:
- Raw numeric scores (priority_score, severity_score, confidence)
- Baseline values or internal calculation inputs
- Score components or calculation internals

The HOW lens MUST expose:
- Bands (priority_band, severity_band)
- Confidence labels (strong, moderate, low, insufficient)
- Drivers and action-relevant context
- Economic impact (VaR, recoverable value) - these ARE action-relevant
"""

from typing import Dict, Any, List, Optional
from .helpers import (
    confidence_to_label,
    confidence_band_to_label,
    severity_to_band,
    priority_to_band
)
import json


class HOWLens:
    """
    Builds HOW-compliant API responses.
    
    All responses strip raw scores and expose only bands/labels.
    """
    
    @staticmethod
    def _parse_jsonb(value):
        """Parse JSONB field that might be string or dict."""
        if value is None:
            return {}
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return {}
        return value
    
    @staticmethod
    def priority_item(priority: Dict[str, Any], asset: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Build a single priority item for HOW lens.
        
        Exposes:
        - priority_id, state_id, asset_id, asset_name
        - priority_band (NOT priority_score)
        - priority_type
        - drivers
        - value_at_risk_per_day, value_recoverable_per_day, currency
        - confidence_label (NOT confidence raw)
        
        Suppresses:
        - priority_score
        - score_components
        - Any baseline values
        """
        economic = HOWLens._parse_jsonb(priority.get("economic_impact", {}))
        drivers = HOWLens._parse_jsonb(priority.get("drivers", []))
        if not isinstance(drivers, list):
            drivers = []
        
        # Get confidence from economic_impact (which stores it as a band/label)
        # If raw confidence exists, convert to label
        confidence_raw = economic.get("confidence")
        if isinstance(confidence_raw, (int, float)):
            confidence_label = confidence_to_label(confidence_raw)
        elif isinstance(confidence_raw, str):
            # Already a label or band
            if confidence_raw.upper() in ["HIGH", "MEDIUM", "LOW", "INSUFFICIENT"]:
                confidence_label = confidence_band_to_label(confidence_raw)
            else:
                confidence_label = confidence_raw.lower()
        else:
            confidence_label = "unknown"
        
        return {
            "priority_id": priority.get("id"),
            "asset_id": priority.get("asset_id"),
            "asset_name": asset.get("name") if asset else "Unknown",
            "state_id": priority.get("state_id"),
            "priority_band": priority.get("priority_band", "UNKNOWN"),
            "priority_type": priority.get("priority_type", "UNKNOWN"),
            "drivers": drivers,
            "value_at_risk_per_day": economic.get("value_at_risk_per_day", 0),
            "value_recoverable_per_day": economic.get("value_recoverable_per_day", 0),
            "currency": economic.get("currency", "USD"),
            "confidence_label": confidence_label,
            "created_at": priority.get("created_at")
        }
    
    @staticmethod
    def priority_list_response(priorities: List[Dict[str, Any]], assets: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build priority list response for HOW lens.
        
        Used by GET /api/how/priorities
        """
        items = []
        for p in priorities:
            asset = assets.get(p.get("asset_id"))
            items.append(HOWLens.priority_item(p, asset))
        
        return {
            "priorities": items,
            "count": len(items)
        }
    
    @staticmethod
    def state_item(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build a single state item for HOW lens.
        
        Exposes:
        - state_id, asset_id
        - state_family, state_type
        - severity_band (NOT severity_score)
        - confidence_label (NOT confidence raw)
        - duration_minutes, started_at, ended_at
        - deviation_percent (action-relevant context)
        
        Suppresses:
        - severity_score
        - confidence (raw)
        - severity_components
        - confidence_components
        - baseline_id
        - rule_id
        """
        # Get confidence label
        confidence_raw = state.get("confidence")
        confidence_band = state.get("confidence_band")
        
        if confidence_raw is not None and isinstance(confidence_raw, (int, float)):
            confidence_label = confidence_to_label(confidence_raw)
        elif confidence_band:
            confidence_label = confidence_band_to_label(confidence_band)
        else:
            confidence_label = "unknown"
        
        return {
            "state_id": state.get("id"),
            "asset_id": state.get("asset_id"),
            "state_family": state.get("state_family"),
            "state_type": state.get("state_type"),
            "severity_band": state.get("severity_band", "UNKNOWN"),
            "confidence_label": confidence_label,
            "deviation_percent": state.get("deviation_percent"),
            "duration_minutes": state.get("duration_minutes", 0),
            "started_at": state.get("started_at"),
            "ended_at": state.get("ended_at"),
            "resolution_type": state.get("resolution_type")
        }
    
    @staticmethod
    def asset_state_response(
        asset: Dict[str, Any], 
        active_states: List[Dict[str, Any]],
        recent_states: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Build asset state response for HOW lens.
        
        Used by GET /api/how/assets/{asset_id}/state
        """
        return {
            "asset_id": asset.get("id"),
            "asset_name": asset.get("name"),
            "asset_class": asset.get("asset_class"),
            "active_states": [HOWLens.state_item(s) for s in active_states],
            "recent_states": [HOWLens.state_item(s) for s in recent_states]
        }
    
    @staticmethod
    def intervention_response(
        intervention_id: str,
        frozen_baseline_id: Optional[str],
        message: str
    ) -> Dict[str, Any]:
        """
        Build intervention creation response for HOW lens.
        
        Note: Does NOT expose frozen_baseline_value - only confirms baseline was frozen.
        """
        return {
            "intervention_id": intervention_id,
            "baseline_frozen": frozen_baseline_id is not None,
            "message": message
        }
    
    @staticmethod
    def intervention_created_response(intervention_id: str, state_id: str) -> Dict[str, Any]:
        """
        Build response for intervention creation.
        
        Used by POST /api/how/interventions
        """
        return {
            "intervention_id": intervention_id,
            "state_id": state_id,
            "message": "Intervention created. Baseline frozen for verification."
        }
    
    @staticmethod
    def intervention_completed_response(intervention_id: str) -> Dict[str, Any]:
        """
        Build response for intervention completion.
        
        Used by POST /api/how/interventions/complete
        """
        return {
            "intervention_id": intervention_id,
            "message": "Intervention completed. Verification started."
        }
    
    @staticmethod
    def outcome_item(outcome: Dict[str, Any], include_details: bool = True) -> Dict[str, Any]:
        """
        Build an outcome item for HOW lens.
        
        Exposes:
        - outcome_id, intervention_id
        - status
        - savings_value, savings_unit, savings_type (action results)
        - confidence_label (NOT confidence raw)
        - time_to_verify_hours
        - verified_at
        
        Suppresses:
        - confidence (raw)
        - frozen_baseline_value
        - actual_value
        - verification_window details
        """
        # Get confidence label
        confidence_raw = outcome.get("confidence")
        confidence_band = outcome.get("confidence_band")
        
        if confidence_raw is not None and isinstance(confidence_raw, (int, float)):
            confidence_label = confidence_to_label(confidence_raw)
        elif confidence_band:
            confidence_label = confidence_band_to_label(confidence_band)
        else:
            confidence_label = "unknown"
        
        base = {
            "outcome_id": outcome.get("id") or outcome.get("outcome_id"),
            "intervention_id": outcome.get("intervention_id"),
            "status": outcome.get("status"),
            "confidence_label": confidence_label
        }
        
        if include_details and outcome.get("status") == "VERIFIED":
            base.update({
                "savings_value": outcome.get("savings_value"),
                "savings_unit": outcome.get("savings_unit"),
                "savings_type": outcome.get("savings_type"),
                "verified_at": outcome.get("verified_at")
            })
        
        return base
    
    @staticmethod
    def outcome_response(outcome: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build outcome response for HOW lens.
        
        Used by GET /api/how/interventions/{id}/outcome
        """
        return HOWLens.outcome_item(outcome, include_details=True)


# Alias for backwards compatibility during transition
def build_how_priority(priority: Dict[str, Any], asset: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Alias for HOWLens.priority_item"""
    return HOWLens.priority_item(priority, asset)


def build_how_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """Alias for HOWLens.state_item"""
    return HOWLens.state_item(state)
