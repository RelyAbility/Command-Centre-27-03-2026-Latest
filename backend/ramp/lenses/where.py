"""
WHERE Lens Payload Builder
==========================

Governs what portfolio users see.
Enforces the Lens Contract for WHERE-scoped data.

INCLUDES:
- Aggregated distributions (priority bands, state families)
- Site-level summaries
- Total value at risk / recoverable (aggregated)
- Evidence export (outcomes with confidence)

EXCLUDES:
- Individual asset operational details
- Raw intervention data
- Operator-specific actions
- Individual priority items (only aggregates)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime


class WHERELens:
    """
    WHERE Lens payload builder.
    
    All WHERE endpoints MUST use these methods to construct responses.
    This ensures lens discipline is enforced at payload level.
    """
    
    @staticmethod
    def portfolio_summary(priorities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build WHERE-compliant portfolio summary.
        
        Aggregates priorities across portfolio - no individual details.
        
        Args:
            priorities: List of active priorities
            
        Returns:
            WHERE-compliant portfolio summary
        """
        distribution = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        total_var = 0.0
        total_vr = 0.0
        
        for p in priorities:
            band = p.get("priority_band", "LOW")
            if band in distribution:
                distribution[band] += 1
            
            economic = p.get("economic_impact", {})
            total_var += economic.get("value_at_risk_per_day", 0)
            total_vr += economic.get("value_recoverable_per_day", 0)
        
        return {
            "distribution": distribution,
            "total_active": len(priorities),
            "total_value_at_risk_per_day": round(total_var, 2),
            "total_value_recoverable_per_day": round(total_vr, 2),
            "currency": "USD"
            # NOT included: individual priority details, asset-level data
        }
    
    @staticmethod
    def site_states_summary(
        site_id: str,
        states: List[Dict[str, Any]],
        asset_count: int
    ) -> Dict[str, Any]:
        """
        Build WHERE-compliant site state summary.
        
        Aggregates states by family:type - no individual state details.
        
        Args:
            site_id: Site identifier
            states: Active states for site assets
            asset_count: Number of assets in site
            
        Returns:
            WHERE-compliant site state summary
        """
        state_distribution = {}
        
        for state in states:
            family = state.get("state_family", "UNKNOWN")
            state_type = state.get("state_type", "UNKNOWN")
            key = f"{family}:{state_type}"
            state_distribution[key] = state_distribution.get(key, 0) + 1
        
        return {
            "site_id": site_id,
            "total_active_states": len(states),
            "state_distribution": state_distribution,
            "asset_count": asset_count
            # NOT included: individual state details, asset names, severities
        }
    
    @staticmethod
    def outcomes_export(
        outcomes: List[Dict[str, Any]],
        period_days: int
    ) -> Dict[str, Any]:
        """
        Build WHERE-compliant outcomes export.
        
        Provides evidence of verified savings for portfolio view.
        
        Args:
            outcomes: Verified outcomes
            period_days: Days in export period
            
        Returns:
            WHERE-compliant outcomes export
        """
        total_savings = sum(o.get("savings_value", 0) or 0 for o in outcomes)
        high_confidence = [
            o for o in outcomes 
            if o.get("confidence_band") == "HIGH"
        ]
        
        # Build exportable outcome records
        export_outcomes = []
        for o in outcomes:
            export_outcomes.append({
                "outcome_id": o.get("id"),
                "intervention_id": o.get("intervention_id"),
                "savings_value": o.get("savings_value"),
                "savings_unit": o.get("savings_unit"),
                "savings_type": o.get("savings_type"),
                "confidence_band": o.get("confidence_band"),
                "status": o.get("status"),
                "verified_at": _format_datetime(o.get("verified_at")),
                "verification_window_start": _format_datetime(o.get("verification_window_start")),
                "verification_window_end": _format_datetime(o.get("verification_window_end"))
                # NOT included: frozen_baseline_value, actual_value, raw confidence
            })
        
        return {
            "period_days": period_days,
            "outcomes_count": len(outcomes),
            "total_verified_savings": round(total_savings, 2),
            "high_confidence_count": len(high_confidence),
            "outcomes": export_outcomes
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
