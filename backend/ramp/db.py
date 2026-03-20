"""
RAMP PostgreSQL Database Client
================================

Handles all database operations for RAMP using asyncpg.
All services use this module - no direct SQL in service code.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import uuid
import logging
import json

from sqlalchemy import select, update, delete, and_, or_, func, text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def generate_id() -> str:
    """Generate UUID for new records."""
    return str(uuid.uuid4())


def now_utc() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


class RAMPDatabase:
    """
    Database access layer for RAMP.
    
    All CRUD operations go through this class.
    Services call these methods instead of writing SQL.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # =========================================================================
    # ORGANISATIONS
    # =========================================================================
    
    async def create_organisation(self, name: str, id: Optional[str] = None) -> Dict[str, Any]:
        org_id = id or generate_id()
        await self.session.execute(
            text("""
                INSERT INTO ramp_organisations (id, name, created_at)
                VALUES (:id, :name, :created_at)
            """),
            {"id": org_id, "name": name, "created_at": now_utc()}
        )
        await self.session.commit()
        return {"id": org_id, "name": name}
    
    # =========================================================================
    # SITES
    # =========================================================================
    
    async def create_site(self, data: Dict[str, Any]) -> Dict[str, Any]:
        site_id = data.get("id") or generate_id()
        await self.session.execute(
            text("""
                INSERT INTO ramp_sites (id, organisation_id, name, timezone, currency,
                    energy_tariff, hourly_production_value, production_margin_per_unit,
                    operating_hours_per_day, site_category, created_at)
                VALUES (:id, :organisation_id, :name, :timezone, :currency,
                    :energy_tariff, :hourly_production_value, :production_margin_per_unit,
                    :operating_hours_per_day, :site_category, :created_at)
            """),
            {
                "id": site_id,
                "organisation_id": data["organisation_id"],
                "name": data["name"],
                "timezone": data["timezone"],
                "currency": data.get("currency", "USD"),
                "energy_tariff": data.get("energy_tariff"),
                "hourly_production_value": data.get("hourly_production_value"),
                "production_margin_per_unit": data.get("production_margin_per_unit"),
                "operating_hours_per_day": data.get("operating_hours_per_day", 24.0),
                "site_category": data.get("site_category"),
                "created_at": now_utc()
            }
        )
        await self.session.commit()
        return {"id": site_id, **data}
    
    async def get_site(self, site_id: str) -> Optional[Dict[str, Any]]:
        result = await self.session.execute(
            text("SELECT * FROM ramp_sites WHERE id = :id"),
            {"id": site_id}
        )
        row = result.mappings().first()
        return dict(row) if row else None
    
    # =========================================================================
    # SYSTEMS
    # =========================================================================
    
    async def create_system(self, data: Dict[str, Any]) -> Dict[str, Any]:
        system_id = data.get("id") or generate_id()
        await self.session.execute(
            text("""
                INSERT INTO ramp_systems (id, site_id, name, created_at)
                VALUES (:id, :site_id, :name, :created_at)
            """),
            {
                "id": system_id,
                "site_id": data["site_id"],
                "name": data["name"],
                "created_at": now_utc()
            }
        )
        await self.session.commit()
        return {"id": system_id, **data}
    
    async def get_systems_for_site(self, site_id: str) -> List[Dict[str, Any]]:
        result = await self.session.execute(
            text("SELECT * FROM ramp_systems WHERE site_id = :site_id"),
            {"site_id": site_id}
        )
        return [dict(row) for row in result.mappings()]
    
    # =========================================================================
    # ASSETS
    # =========================================================================
    
    async def create_asset(self, data: Dict[str, Any]) -> Dict[str, Any]:
        asset_id = data.get("id") or generate_id()
        await self.session.execute(
            text("""
                INSERT INTO ramp_assets (id, system_id, name, asset_class,
                    criticality_score, estimated_repair_cost, created_at)
                VALUES (:id, :system_id, :name, :asset_class,
                    :criticality_score, :estimated_repair_cost, :created_at)
            """),
            {
                "id": asset_id,
                "system_id": data["system_id"],
                "name": data["name"],
                "asset_class": data.get("asset_class", "GENERIC"),
                "criticality_score": data.get("criticality_score", 50.0),
                "estimated_repair_cost": data.get("estimated_repair_cost"),
                "created_at": now_utc()
            }
        )
        await self.session.commit()
        return {"id": asset_id, **data}
    
    async def get_asset(self, asset_id: str) -> Optional[Dict[str, Any]]:
        result = await self.session.execute(
            text("SELECT * FROM ramp_assets WHERE id = :id"),
            {"id": asset_id}
        )
        row = result.mappings().first()
        return dict(row) if row else None
    
    async def get_assets_for_site(self, site_id: str) -> List[Dict[str, Any]]:
        result = await self.session.execute(
            text("""
                SELECT a.* FROM ramp_assets a
                JOIN ramp_systems s ON a.system_id = s.id
                WHERE s.site_id = :site_id
            """),
            {"site_id": site_id}
        )
        return [dict(row) for row in result.mappings()]
    
    # =========================================================================
    # RULES
    # =========================================================================
    
    async def create_rule(self, data: Dict[str, Any]) -> Dict[str, Any]:
        rule_id = data.get("id") or generate_id()
        await self.session.execute(
            text("""
                INSERT INTO ramp_rules (id, name, description, state_family, state_type,
                    metric_type, operator, threshold_multiplier, duration_threshold_minutes,
                    severity_base, is_active, created_at)
                VALUES (:id, :name, :description, :state_family, :state_type,
                    :metric_type, :operator, :threshold_multiplier, :duration_threshold_minutes,
                    :severity_base, :is_active, :created_at)
            """),
            {
                "id": rule_id,
                "name": data["name"],
                "description": data.get("description"),
                "state_family": data["state_family"],
                "state_type": data["state_type"],
                "metric_type": data["metric_type"],
                "operator": data["operator"],
                "threshold_multiplier": data["threshold_multiplier"],
                "duration_threshold_minutes": data["duration_threshold_minutes"],
                "severity_base": data["severity_base"],
                "is_active": data.get("is_active", True),
                "created_at": now_utc()
            }
        )
        await self.session.commit()
        return {"id": rule_id, **data}
    
    async def get_active_rules(self, metric_type: Optional[str] = None) -> List[Dict[str, Any]]:
        if metric_type:
            result = await self.session.execute(
                text("SELECT * FROM ramp_rules WHERE is_active = true AND metric_type = :metric_type"),
                {"metric_type": metric_type}
            )
        else:
            result = await self.session.execute(
                text("SELECT * FROM ramp_rules WHERE is_active = true")
            )
        return [dict(row) for row in result.mappings()]
    
    # =========================================================================
    # SIGNALS
    # =========================================================================
    
    async def create_signal(self, data: Dict[str, Any]) -> Dict[str, Any]:
        signal_id = data.get("id") or generate_id()
        await self.session.execute(
            text("""
                INSERT INTO ramp_signals (id, asset_id, signal_type, value, unit,
                    quality, timestamp, ingested_at)
                VALUES (:id, :asset_id, :signal_type, :value, :unit,
                    :quality, :timestamp, :ingested_at)
            """),
            {
                "id": signal_id,
                "asset_id": data["asset_id"],
                "signal_type": data["signal_type"],
                "value": data["value"],
                "unit": data.get("unit", ""),
                "quality": data.get("quality", "GOOD"),
                "timestamp": data["timestamp"],
                "ingested_at": now_utc()
            }
        )
        await self.session.commit()
        return {"id": signal_id, **data}
    
    # =========================================================================
    # METRICS
    # =========================================================================
    
    async def create_metric(self, data: Dict[str, Any]) -> Dict[str, Any]:
        metric_id = data.get("id") or generate_id()
        await self.session.execute(
            text("""
                INSERT INTO ramp_metrics (id, asset_id, metric_type, value, unit,
                    context_signature, timestamp, calculated_at)
                VALUES (:id, :asset_id, :metric_type, :value, :unit,
                    :context_signature::jsonb, :timestamp, :calculated_at)
            """),
            {
                "id": metric_id,
                "asset_id": data["asset_id"],
                "metric_type": data["metric_type"],
                "value": data["value"],
                "unit": data.get("unit", ""),
                "context_signature": json.dumps(data.get("context_signature", {})),
                "timestamp": data["timestamp"],
                "calculated_at": now_utc()
            }
        )
        await self.session.commit()
        return {"id": metric_id, **data}
    
    async def get_metrics_for_baseline(
        self,
        asset_id: str,
        metric_type: str,
        since: datetime
    ) -> List[Dict[str, Any]]:
        result = await self.session.execute(
            text("""
                SELECT * FROM ramp_metrics 
                WHERE asset_id = :asset_id 
                AND metric_type = :metric_type
                AND timestamp >= :since
                ORDER BY timestamp ASC
            """),
            {"asset_id": asset_id, "metric_type": metric_type, "since": since}
        )
        return [dict(row) for row in result.mappings()]
    
    # =========================================================================
    # BASELINES
    # =========================================================================
    
    async def create_baseline(self, data: Dict[str, Any]) -> Dict[str, Any]:
        baseline_id = data.get("id") or generate_id()
        now = now_utc()
        import json
        context_sig = json.dumps(data.get("context_signature", {}))
        
        await self.session.execute(
            text("""
                INSERT INTO ramp_baselines (id, asset_id, metric_type, context_signature,
                    baseline_value, baseline_min, baseline_max, confidence, confidence_band,
                    valid_from, sample_count, data_window_days, created_at, updated_at)
                VALUES (:id, :asset_id, :metric_type, :context_signature::jsonb,
                    :baseline_value, :baseline_min, :baseline_max, :confidence, :confidence_band,
                    :valid_from, :sample_count, :data_window_days, :created_at, :updated_at)
            """),
            {
                "id": baseline_id,
                "asset_id": data["asset_id"],
                "metric_type": data["metric_type"],
                "context_signature": context_sig,
                "baseline_value": data["baseline_value"],
                "baseline_min": data["baseline_min"],
                "baseline_max": data["baseline_max"],
                "confidence": data["confidence"],
                "confidence_band": data.get("confidence_band", "MEDIUM"),
                "valid_from": data.get("valid_from", now),
                "sample_count": data.get("sample_count", 0),
                "data_window_days": data.get("data_window_days", 14),
                "created_at": now,
                "updated_at": now
            }
        )
        await self.session.commit()
        return {"id": baseline_id, **data}
    
    async def get_active_baseline(
        self,
        asset_id: str,
        metric_type: str
    ) -> Optional[Dict[str, Any]]:
        result = await self.session.execute(
            text("""
                SELECT * FROM ramp_baselines 
                WHERE asset_id = :asset_id 
                AND metric_type = :metric_type
                AND valid_until IS NULL
                AND frozen_at IS NULL
                ORDER BY created_at DESC
                LIMIT 1
            """),
            {"asset_id": asset_id, "metric_type": metric_type}
        )
        row = result.mappings().first()
        return dict(row) if row else None
    
    async def freeze_baseline(
        self,
        asset_id: str,
        intervention_id: str
    ) -> Optional[Dict[str, Any]]:
        now = now_utc()
        result = await self.session.execute(
            text("""
                UPDATE ramp_baselines 
                SET frozen_at = :frozen_at, frozen_for_intervention_id = :intervention_id
                WHERE asset_id = :asset_id
                AND valid_until IS NULL
                AND frozen_at IS NULL
                RETURNING *
            """),
            {"frozen_at": now, "intervention_id": intervention_id, "asset_id": asset_id}
        )
        await self.session.commit()
        row = result.mappings().first()
        return dict(row) if row else None
    
    async def get_frozen_baseline(self, intervention_id: str) -> Optional[Dict[str, Any]]:
        result = await self.session.execute(
            text("SELECT * FROM ramp_baselines WHERE frozen_for_intervention_id = :intervention_id"),
            {"intervention_id": intervention_id}
        )
        row = result.mappings().first()
        return dict(row) if row else None
    
    # =========================================================================
    # STATES
    # =========================================================================
    
    async def create_state(self, data: Dict[str, Any]) -> Dict[str, Any]:
        state_id = data.get("id") or generate_id()
        now = now_utc()
        await self.session.execute(
            text("""
                INSERT INTO ramp_states (id, asset_id, rule_id, baseline_id,
                    state_family, state_type, severity_score, severity_band, severity_components,
                    confidence, confidence_band, confidence_components, deviation_percent,
                    started_at, duration_minutes, created_at, updated_at)
                VALUES (:id, :asset_id, :rule_id, :baseline_id,
                    :state_family, :state_type, :severity_score, :severity_band, :severity_components::jsonb,
                    :confidence, :confidence_band, :confidence_components::jsonb, :deviation_percent,
                    :started_at, :duration_minutes, :created_at, :updated_at)
            """),
            {
                "id": state_id,
                "asset_id": data["asset_id"],
                "rule_id": data.get("rule_id"),
                "baseline_id": data.get("baseline_id"),
                "state_family": data["state_family"],
                "state_type": data["state_type"],
                "severity_score": data["severity_score"],
                "severity_band": data["severity_band"],
                "severity_components": json.dumps(data.get("severity_components", {})),
                "confidence": data["confidence"],
                "confidence_band": data["confidence_band"],
                "confidence_components": json.dumps(data.get("confidence_components", {})),
                "deviation_percent": data.get("deviation_percent"),
                "started_at": data.get("started_at", now),
                "duration_minutes": data.get("duration_minutes", 0),
                "created_at": now,
                "updated_at": now
            }
        )
        await self.session.commit()
        return {"id": state_id, **data}
    
    async def get_active_states(self, asset_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if asset_id:
            result = await self.session.execute(
                text("SELECT * FROM ramp_states WHERE asset_id = :asset_id AND ended_at IS NULL ORDER BY started_at DESC"),
                {"asset_id": asset_id}
            )
        else:
            result = await self.session.execute(
                text("SELECT * FROM ramp_states WHERE ended_at IS NULL ORDER BY started_at DESC")
            )
        return [dict(row) for row in result.mappings()]
    
    async def get_recent_states(self, asset_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        result = await self.session.execute(
            text("SELECT * FROM ramp_states WHERE asset_id = :asset_id ORDER BY started_at DESC LIMIT :limit"),
            {"asset_id": asset_id, "limit": limit}
        )
        return [dict(row) for row in result.mappings()]
    
    async def end_state(self, state_id: str, resolution_type: str) -> Optional[Dict[str, Any]]:
        now = now_utc()
        result = await self.session.execute(
            text("""
                UPDATE ramp_states 
                SET ended_at = :ended_at, resolution_type = :resolution_type, updated_at = :updated_at
                WHERE id = :id
                RETURNING *
            """),
            {"ended_at": now, "resolution_type": resolution_type, "updated_at": now, "id": state_id}
        )
        await self.session.commit()
        row = result.mappings().first()
        return dict(row) if row else None
    
    # =========================================================================
    # PRIORITIES
    # =========================================================================
    
    async def create_priority(self, data: Dict[str, Any]) -> Dict[str, Any]:
        priority_id = data.get("id") or generate_id()
        now = now_utc()
        await self.session.execute(
            text("""
                INSERT INTO ramp_priorities (id, state_id, asset_id,
                    priority_score, priority_band, priority_type,
                    drivers, economic_impact, score_components,
                    created_at, updated_at)
                VALUES (:id, :state_id, :asset_id,
                    :priority_score, :priority_band, :priority_type,
                    :drivers::jsonb, :economic_impact::jsonb, :score_components::jsonb,
                    :created_at, :updated_at)
            """),
            {
                "id": priority_id,
                "state_id": data["state_id"],
                "asset_id": data["asset_id"],
                "priority_score": data["priority_score"],
                "priority_band": data["priority_band"],
                "priority_type": data["priority_type"],
                "drivers": json.dumps(data.get("drivers", [])),
                "economic_impact": json.dumps(data.get("economic_impact", {})),
                "score_components": json.dumps(data.get("score_components", {})),
                "created_at": now,
                "updated_at": now
            }
        )
        await self.session.commit()
        return {"id": priority_id, **data}
    
    async def get_active_priorities(self) -> List[Dict[str, Any]]:
        result = await self.session.execute(
            text("""
                SELECT * FROM ramp_priorities 
                WHERE expires_at IS NULL 
                ORDER BY priority_band ASC, priority_score DESC
            """)
        )
        return [dict(row) for row in result.mappings()]
    
    async def expire_priority(self, state_id: str) -> None:
        now = now_utc()
        await self.session.execute(
            text("UPDATE ramp_priorities SET expires_at = :expires_at WHERE state_id = :state_id AND expires_at IS NULL"),
            {"expires_at": now, "state_id": state_id}
        )
        await self.session.commit()
    
    # =========================================================================
    # INTERVENTIONS
    # =========================================================================
    
    async def create_intervention(self, data: Dict[str, Any]) -> Dict[str, Any]:
        intervention_id = data.get("id") or generate_id()
        now = now_utc()
        await self.session.execute(
            text("""
                INSERT INTO ramp_interventions (id, state_id, priority_id, asset_id,
                    frozen_baseline_id, intervention_type, description, created_by, created_at)
                VALUES (:id, :state_id, :priority_id, :asset_id,
                    :frozen_baseline_id, :intervention_type, :description, :created_by, :created_at)
            """),
            {
                "id": intervention_id,
                "state_id": data["state_id"],
                "priority_id": data.get("priority_id"),
                "asset_id": data["asset_id"],
                "frozen_baseline_id": data.get("frozen_baseline_id"),
                "intervention_type": data["intervention_type"],
                "description": data["description"],
                "created_by": data["created_by"],
                "created_at": now
            }
        )
        await self.session.commit()
        return {"id": intervention_id, **data}
    
    async def get_intervention(self, intervention_id: str) -> Optional[Dict[str, Any]]:
        result = await self.session.execute(
            text("SELECT * FROM ramp_interventions WHERE id = :id"),
            {"id": intervention_id}
        )
        row = result.mappings().first()
        return dict(row) if row else None
    
    async def complete_intervention(self, intervention_id: str) -> Optional[Dict[str, Any]]:
        now = now_utc()
        result = await self.session.execute(
            text("UPDATE ramp_interventions SET completed_at = :completed_at WHERE id = :id RETURNING *"),
            {"completed_at": now, "id": intervention_id}
        )
        await self.session.commit()
        row = result.mappings().first()
        return dict(row) if row else None
    
    # =========================================================================
    # OUTCOMES
    # =========================================================================
    
    async def create_outcome(self, data: Dict[str, Any]) -> Dict[str, Any]:
        outcome_id = data.get("id") or generate_id()
        await self.session.execute(
            text("""
                INSERT INTO ramp_outcomes (id, intervention_id, frozen_baseline_id,
                    verification_window_start, verification_window_end, frozen_baseline_value,
                    actual_value, savings_value, savings_unit, savings_type,
                    confidence, confidence_band, status, verified_at, verification_notes)
                VALUES (:id, :intervention_id, :frozen_baseline_id,
                    :verification_window_start, :verification_window_end, :frozen_baseline_value,
                    :actual_value, :savings_value, :savings_unit, :savings_type,
                    :confidence, :confidence_band, :status, :verified_at, :verification_notes)
            """),
            {
                "id": outcome_id,
                "intervention_id": data["intervention_id"],
                "frozen_baseline_id": data.get("frozen_baseline_id"),
                "verification_window_start": data["verification_window_start"],
                "verification_window_end": data["verification_window_end"],
                "frozen_baseline_value": data["frozen_baseline_value"],
                "actual_value": data.get("actual_value"),
                "savings_value": data.get("savings_value"),
                "savings_unit": data.get("savings_unit"),
                "savings_type": data.get("savings_type"),
                "confidence": data.get("confidence"),
                "confidence_band": data.get("confidence_band"),
                "status": data.get("status", "PENDING"),
                "verified_at": data.get("verified_at"),
                "verification_notes": data.get("verification_notes")
            }
        )
        await self.session.commit()
        return {"id": outcome_id, **data}
    
    async def get_outcome_for_intervention(self, intervention_id: str) -> Optional[Dict[str, Any]]:
        result = await self.session.execute(
            text("SELECT * FROM ramp_outcomes WHERE intervention_id = :intervention_id"),
            {"intervention_id": intervention_id}
        )
        row = result.mappings().first()
        return dict(row) if row else None
    
    # =========================================================================
    # EVENTS
    # =========================================================================
    
    async def create_event(self, data: Dict[str, Any]) -> Dict[str, Any]:
        event_id = data.get("id") or generate_id()
        await self.session.execute(
            text("""
                INSERT INTO ramp_events (id, event_type, entity_type, entity_id,
                    payload, correlation_id, caused_by_event_id, created_at)
                VALUES (:id, :event_type, :entity_type, :entity_id,
                    :payload::jsonb, :correlation_id, :caused_by_event_id, :created_at)
            """),
            {
                "id": event_id,
                "event_type": data["event_type"],
                "entity_type": data["entity_type"],
                "entity_id": data["entity_id"],
                "payload": json.dumps(data.get("payload", {})),
                "correlation_id": data.get("correlation_id"),
                "caused_by_event_id": data.get("caused_by_event_id"),
                "created_at": now_utc()
            }
        )
        await self.session.commit()
        return {"id": event_id, **data}
    
    async def get_events_for_correlation(self, correlation_id: str) -> List[Dict[str, Any]]:
        result = await self.session.execute(
            text("SELECT * FROM ramp_events WHERE correlation_id = :correlation_id ORDER BY created_at ASC"),
            {"correlation_id": correlation_id}
        )
        return [dict(row) for row in result.mappings()]
