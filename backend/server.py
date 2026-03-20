"""
RAMP Command Centre API
=======================

FastAPI backend with PostgreSQL persistence via Supabase.
Implements HOW and WHERE lens separation at API level.
"""

from fastapi import FastAPI, APIRouter, HTTPException, Query, Depends
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import random

# Load environment
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Database setup
from database import AsyncSessionLocal, init_db
from ramp.db import RAMPDatabase, generate_id, now_utc
from ramp.lenses import HOWLens, WHERELens

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="RAMP Command Centre API",
    description="State-based industrial intelligence platform",
    version="0.1.0"
)

# Routers with lens separation
api_router = APIRouter(prefix="/api")
how_router = APIRouter(prefix="/api/how", tags=["HOW Lens"])
where_router = APIRouter(prefix="/api/where", tags=["WHERE Lens"])
system_router = APIRouter(prefix="/api/system", tags=["System"])


# =============================================================================
# DEPENDENCIES
# =============================================================================

async def get_db():
    """Get database session."""
    async with AsyncSessionLocal() as session:
        yield RAMPDatabase(session)


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class InterventionCreate(BaseModel):
    state_id: str
    intervention_type: str
    description: str
    created_by: str


class InterventionComplete(BaseModel):
    intervention_id: str


# =============================================================================
# SYSTEM ROUTES
# =============================================================================

@system_router.get("/health")
async def health_check():
    """System health check."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "database": "postgresql"
    }


@system_router.post("/reset")
async def reset_database(db: RAMPDatabase = Depends(get_db)):
    """
    Reset all demo data for a fresh start.
    Deletes in reverse dependency order to respect foreign keys.
    """
    from sqlalchemy import text
    
    # Delete in reverse dependency order
    tables = [
        "ramp_learning",
        "ramp_outcomes",
        "ramp_interventions",
        "ramp_priorities",
        "ramp_states",
        "ramp_baselines",
        "ramp_metrics",
        "ramp_signals",
        "ramp_rules",
        "ramp_assets",
        "ramp_systems",
        "ramp_sites",
        "ramp_organisations"
    ]
    
    # Events are immutable - we can't delete them by design
    # But for demo reset, we'll disable the trigger temporarily
    await db.session.execute(text("DROP TRIGGER IF EXISTS ramp_events_immutable ON ramp_events"))
    await db.session.execute(text("DELETE FROM ramp_events"))
    await db.session.execute(text("""
        CREATE TRIGGER ramp_events_immutable
        BEFORE UPDATE OR DELETE ON ramp_events
        FOR EACH ROW
        EXECUTE FUNCTION ramp_prevent_event_modification()
    """))
    
    for table in tables:
        await db.session.execute(text(f"DELETE FROM {table}"))
    
    await db.session.commit()
    
    return {"status": "reset", "message": "All RAMP data cleared"}


@system_router.post("/seed")
async def seed_database(db: RAMPDatabase = Depends(get_db)):
    """Seed database with demo data. Idempotent - skips if data exists."""
    from sqlalchemy import text
    
    # Check if already seeded
    result = await db.session.execute(
        text("SELECT id FROM ramp_organisations WHERE id = :id"),
        {"id": "demo-org-001"}
    )
    if result.first():
        return {
            "status": "already_seeded",
            "message": "Demo data already exists. Use /api/system/reset first to clear.",
            "organisation": "demo-org-001",
            "site": "demo-site-001",
            "assets": ["asset-comp-001"]
        }
    
    # Create organisation
    org = await db.create_organisation("Demo Manufacturing Corp", id="demo-org-001")
    
    # Create site
    site = await db.create_site({
        "id": "demo-site-001",
        "organisation_id": "demo-org-001",
        "name": "Riverside Manufacturing",
        "timezone": "America/Chicago",
        "currency": "USD",
        "energy_tariff": 0.11,
        "hourly_production_value": 600,
        "operating_hours_per_day": 20,
        "site_category": "MANUFACTURING"
    })
    
    # Create system
    await db.create_system({
        "id": "sys-compressed-air",
        "site_id": "demo-site-001",
        "name": "Compressed Air System"
    })
    
    # Create assets
    await db.create_asset({
        "id": "asset-comp-001",
        "system_id": "sys-compressed-air",
        "name": "Main Compressor A",
        "asset_class": "COMPRESSOR",
        "criticality_score": 85,
        "estimated_repair_cost": 6000
    })
    
    # Create rules
    await db.create_rule({
        "id": "rule-energy-drift",
        "name": "Energy Drift Detection",
        "description": "Detect sustained energy consumption above baseline",
        "state_family": "ENERGY",
        "state_type": "DRIFT",
        "metric_type": "energy_intensity",
        "operator": "gt",
        "threshold_multiplier": 1.15,
        "duration_threshold_minutes": 30,
        "severity_base": 4,
        "is_active": True
    })
    
    return {
        "status": "seeded",
        "organisation": org["id"],
        "site": site["id"],
        "assets": ["asset-comp-001"]
    }


@system_router.post("/demo/simulate-drift")
async def simulate_drift(db: RAMPDatabase = Depends(get_db)):
    """
    Simulate an active drift condition for demonstration.
    Creates the full relational chain: baseline → state → priority
    """
    asset_id = "asset-comp-001"
    baseline_value = 45.0
    now = now_utc()
    correlation_id = generate_id()
    
    # 1. Create baseline (established from historical data)
    baseline = await db.create_baseline({
        "id": generate_id(),
        "asset_id": asset_id,
        "metric_type": "energy_intensity",
        "context_signature": {"runtime_state": "RUNNING"},
        "baseline_value": baseline_value,
        "baseline_min": baseline_value * 0.90,
        "baseline_max": baseline_value * 1.10,
        "confidence": 0.85,
        "confidence_band": "HIGH",
        "valid_from": now - timedelta(days=14),
        "sample_count": 336,
        "data_window_days": 14
    })
    logger.info(f"Baseline created: {baseline['id']}")
    
    # Create baseline event
    await db.create_event({
        "event_type": "baseline_updated",
        "entity_type": "baseline",
        "entity_id": baseline["id"],
        "payload": {
            "baseline_id": baseline["id"],
            "asset_id": asset_id,
            "baseline_value": baseline_value,
            "confidence": 0.85
        },
        "correlation_id": correlation_id
    })
    
    # 2. Create state (drift detected)
    drift_deviation = 25.5  # 25.5% above baseline
    state = await db.create_state({
        "id": generate_id(),
        "asset_id": asset_id,
        "rule_id": "rule-energy-drift",
        "baseline_id": baseline["id"],
        "state_family": "ENERGY",
        "state_type": "DRIFT",
        "severity_score": 5,
        "severity_band": "MEDIUM",
        "severity_components": {"base": 4, "duration_modifier": 0, "deviation_modifier": 1},
        "confidence": 0.82,
        "confidence_band": "HIGH",
        "confidence_components": {"data_quality": 0.90, "baseline_confidence": 0.85, "context_validity": 0.70},
        "deviation_percent": drift_deviation,
        "started_at": now - timedelta(hours=2),
        "duration_minutes": 120
    })
    logger.info(f"State created: {state['id']}")
    
    # Create state event
    await db.create_event({
        "event_type": "state_started",
        "entity_type": "state",
        "entity_id": state["id"],
        "payload": {
            "state_id": state["id"],
            "asset_id": asset_id,
            "state_family": "ENERGY",
            "state_type": "DRIFT",
            "severity_score": 5,
            "confidence": 0.82,
            "baseline_id": baseline["id"]
        },
        "correlation_id": correlation_id
    })
    
    # 3. Create priority
    site = await db.get_site("demo-site-001")
    
    # Calculate economic impact
    tariff = site.get("energy_tariff", 0.12) if site else 0.12
    excess_hourly = baseline_value * (drift_deviation / 100)
    var_per_day = excess_hourly * 20 * tariff  # 20 operating hours
    vr_per_day = var_per_day * 0.8
    
    priority = await db.create_priority({
        "id": generate_id(),
        "state_id": state["id"],
        "asset_id": asset_id,
        "priority_score": 62.5,
        "priority_band": "HIGH",
        "priority_type": "OPERATIONAL",
        "drivers": [
            f"{drift_deviation:.0f}% energy drift on Main Compressor A",
            f"Estimated ${var_per_day:.0f}/day at risk",
            "Critical asset (HIGH criticality)",
            "Active for 2.0 hours"
        ],
        "economic_impact": {
            "value_at_risk_per_day": round(var_per_day, 2),
            "value_recoverable_per_day": round(vr_per_day, 2),
            "currency": "USD",
            "calculation_method": "ENERGY_DEVIATION",
            "confidence": "HIGH"
        },
        "score_components": {
            "severity": 50,
            "economic": 20,
            "risk": 30,
            "criticality": 85,
            "confidence": 82,
            "friction": 20
        }
    })
    logger.info(f"Priority created: {priority['id']}")
    
    # Create priority event
    await db.create_event({
        "event_type": "priority_created",
        "entity_type": "priority",
        "entity_id": priority["id"],
        "payload": {
            "priority_id": priority["id"],
            "state_id": state["id"],
            "asset_id": asset_id,
            "priority_band": "HIGH",
            "drivers": priority["drivers"],
            "value_at_risk_per_day": var_per_day
        },
        "correlation_id": correlation_id
    })
    
    return {
        "status": "simulated",
        "correlation_id": correlation_id,
        "baseline_id": baseline["id"],
        "state_id": state["id"],
        "priority_id": priority["id"],
        "chain": "baseline → state → priority (complete)"
    }


@system_router.post("/demo/first-five-minutes")
async def first_five_minutes_demo(db: RAMPDatabase = Depends(get_db)):
    """
    First 5 Minutes Experience
    ==========================
    
    A guided entry that establishes credibility and demonstrates the full loop.
    Works for both new user onboarding and live demos.
    
    Creates:
    1. A realistic site with multiple assets (credibility)
    2. Established baselines showing normal operation (context)
    3. One completed verification loop (proof the system works)
    4. 2-3 current active issues (actionable priorities)
    5. Historical data showing this is continuous monitoring
    """
    from sqlalchemy import text as sql_text
    
    # Reset everything
    tables = [
        "ramp_learning", "ramp_outcomes", "ramp_interventions",
        "ramp_priorities", "ramp_states", "ramp_baselines",
        "ramp_metrics", "ramp_signals", "ramp_rules",
        "ramp_assets", "ramp_systems", "ramp_sites", "ramp_organisations"
    ]
    await db.session.execute(sql_text("DROP TRIGGER IF EXISTS ramp_events_immutable ON ramp_events"))
    await db.session.execute(sql_text("DELETE FROM ramp_events"))
    await db.session.execute(sql_text("""
        CREATE TRIGGER ramp_events_immutable
        BEFORE UPDATE OR DELETE ON ramp_events
        FOR EACH ROW
        EXECUTE FUNCTION ramp_prevent_event_modification()
    """))
    for table in tables:
        await db.session.execute(sql_text(f"DELETE FROM {table}"))
    await db.session.commit()
    
    now = now_utc()
    
    # =========================================================================
    # STEP 1: ESTABLISH CREDIBILITY - Real Site with Multiple Assets
    # =========================================================================
    
    await db.create_organisation("Riverside Manufacturing Group", id="rmg-001")
    
    await db.create_site({
        "id": "site-riverside",
        "organisation_id": "rmg-001",
        "name": "Riverside Plant - Building A",
        "timezone": "America/Chicago",
        "currency": "USD",
        "energy_tariff": 0.11,
        "hourly_production_value": 850,
        "production_margin_per_unit": 12.50,
        "operating_hours_per_day": 20,
        "site_category": "MANUFACTURING"
    })
    
    # Create realistic systems
    await db.create_system({"id": "sys-hvac", "site_id": "site-riverside", "name": "HVAC System"})
    await db.create_system({"id": "sys-compressed-air", "site_id": "site-riverside", "name": "Compressed Air"})
    await db.create_system({"id": "sys-cooling", "site_id": "site-riverside", "name": "Process Cooling"})
    
    # Create multiple realistic assets
    assets = [
        {
            "id": "asset-ahu-01",
            "system_id": "sys-hvac",
            "name": "Air Handling Unit 1",
            "asset_class": "HVAC",
            "criticality_score": 75,
            "estimated_repair_cost": 4500
        },
        {
            "id": "asset-comp-main",
            "system_id": "sys-compressed-air",
            "name": "Main Air Compressor",
            "asset_class": "COMPRESSOR",
            "criticality_score": 90,
            "estimated_repair_cost": 8500
        },
        {
            "id": "asset-chiller-01",
            "system_id": "sys-cooling",
            "name": "Process Chiller 1",
            "asset_class": "CHILLER",
            "criticality_score": 85,
            "estimated_repair_cost": 12000
        },
        {
            "id": "asset-vfd-pump",
            "system_id": "sys-cooling",
            "name": "VFD Coolant Pump",
            "asset_class": "PUMP",
            "criticality_score": 60,
            "estimated_repair_cost": 2200
        }
    ]
    
    for asset_data in assets:
        await db.create_asset(asset_data)
    
    # Create detection rules
    rules = [
        {
            "id": "rule-energy-drift",
            "name": "Energy Consumption Drift",
            "description": "Detects sustained energy consumption above baseline",
            "state_family": "ENERGY",
            "state_type": "DRIFT",
            "metric_type": "energy_intensity",
            "operator": "gt",
            "threshold_multiplier": 1.15,
            "duration_threshold_minutes": 30,
            "severity_base": 4,
            "is_active": True
        },
        {
            "id": "rule-efficiency-drop",
            "name": "Efficiency Degradation",
            "description": "Detects drop in operational efficiency",
            "state_family": "OPERATIONAL",
            "state_type": "DEGRADATION",
            "metric_type": "efficiency",
            "operator": "lt",
            "threshold_multiplier": 0.85,
            "duration_threshold_minutes": 60,
            "severity_base": 3,
            "is_active": True
        }
    ]
    
    for rule_data in rules:
        await db.create_rule(rule_data)
    
    # =========================================================================
    # STEP 2: ESTABLISH BASELINE CONTEXT - Show Normal Operation History
    # =========================================================================
    
    # Create baselines for all assets (showing 14 days of established behaviour)
    baselines = {}
    baseline_data = [
        {"asset_id": "asset-ahu-01", "metric_type": "energy_intensity", "value": 28.5, "min": 25.0, "max": 32.0, "confidence": 0.88},
        {"asset_id": "asset-comp-main", "metric_type": "energy_intensity", "value": 52.0, "min": 47.0, "max": 57.0, "confidence": 0.92},
        {"asset_id": "asset-chiller-01", "metric_type": "energy_intensity", "value": 68.0, "min": 62.0, "max": 74.0, "confidence": 0.85},
        {"asset_id": "asset-vfd-pump", "metric_type": "energy_intensity", "value": 12.5, "min": 11.0, "max": 14.0, "confidence": 0.90},
    ]
    
    for bl in baseline_data:
        baseline = await db.create_baseline({
            "asset_id": bl["asset_id"],
            "metric_type": bl["metric_type"],
            "context_signature": {"runtime_state": "RUNNING", "shift": "DAY"},
            "baseline_value": bl["value"],
            "baseline_min": bl["min"],
            "baseline_max": bl["max"],
            "confidence": bl["confidence"],
            "confidence_band": "HIGH" if bl["confidence"] >= 0.85 else "MEDIUM",
            "valid_from": now - timedelta(days=14),
            "sample_count": 336,
            "data_window_days": 14
        })
        baselines[bl["asset_id"]] = baseline
    
    # =========================================================================
    # STEP 3: ONE COMPLETED LOOP - Proof the System Works
    # =========================================================================
    
    # Create a PAST verified intervention for the VFD pump
    # This shows the system has already caught and resolved an issue
    
    # 3a. Create past state (3 days ago)
    past_state = await db.create_state({
        "asset_id": "asset-vfd-pump",
        "rule_id": "rule-energy-drift",
        "baseline_id": baselines["asset-vfd-pump"]["id"],
        "state_family": "ENERGY",
        "state_type": "DRIFT",
        "severity_score": 4,
        "severity_band": "MEDIUM",
        "severity_components": {"base": 3, "duration_modifier": 0.5, "deviation_modifier": 0.5},
        "confidence": 0.78,
        "confidence_band": "MEDIUM",
        "confidence_components": {"data_quality": 0.82, "baseline_confidence": 0.90},
        "deviation_percent": 18.5,
        "started_at": now - timedelta(days=3, hours=4),
        "duration_minutes": 180,
        "ended_at": now - timedelta(days=3, hours=1),
        "resolution_type": "INTERVENTION"
    })
    
    # 3b. Create past intervention
    past_intervention = await db.create_intervention({
        "state_id": past_state["id"],
        "asset_id": "asset-vfd-pump",
        "frozen_baseline_id": baselines["asset-vfd-pump"]["id"],
        "intervention_type": "CALIBRATION",
        "description": "Recalibrated VFD frequency setpoints. Found drift in speed controller.",
        "created_by": "mike.johnson@riverside.com"
    })
    
    # Set completed_at in the past
    await db.session.execute(
        sql_text("UPDATE ramp_interventions SET completed_at = :completed_at WHERE id = :id"),
        {"completed_at": now - timedelta(days=3, hours=1), "id": past_intervention["id"]}
    )
    await db.session.commit()
    
    # 3c. Create VERIFIED outcome (showing real savings)
    await db.create_outcome({
        "intervention_id": past_intervention["id"],
        "frozen_baseline_id": baselines["asset-vfd-pump"]["id"],
        "verification_window_start": now - timedelta(days=3, hours=1),
        "verification_window_end": now - timedelta(days=3),
        "frozen_baseline_value": 12.5,
        "actual_value": 11.2,
        "savings_value": 1.3,
        "savings_unit": "kWh",
        "savings_type": "energy",
        "confidence": 0.91,
        "confidence_band": "HIGH",
        "status": "VERIFIED",
        "verified_at": now - timedelta(days=2, hours=20),
        "verification_notes": "Verified with 18 samples over 1h window. Energy consumption returned to baseline."
    })
    
    # 3d. Update learning record
    await db.upsert_learning_record({
        "asset_id": "asset-vfd-pump",
        "state_type": "DRIFT",
        "occurrence_count": 1,
        "intervention_count": 1,
        "total_savings": 1.3,
        "avg_effectiveness": 1.3,
        "first_occurred_at": now - timedelta(days=3, hours=4),
        "last_occurred_at": now - timedelta(days=3, hours=4)
    })
    
    # 3e. Create event for audit trail
    await db.create_event({
        "event_type": "outcome_verified",
        "entity_type": "outcome",
        "entity_id": past_intervention["id"],
        "payload": {
            "savings_value": 1.3,
            "savings_unit": "kWh",
            "confidence": 0.91,
            "message": "VFD pump calibration verified - 1.3 kWh/hour savings confirmed"
        }
    })
    
    # =========================================================================
    # STEP 4: CURRENT ACTIVE ISSUES - 2-3 Actionable Priorities
    # =========================================================================
    
    current_issues = []
    
    # Issue 1: Main Compressor - HIGH priority energy drift (22% above baseline)
    comp_state = await db.create_state({
        "asset_id": "asset-comp-main",
        "rule_id": "rule-energy-drift",
        "baseline_id": baselines["asset-comp-main"]["id"],
        "state_family": "ENERGY",
        "state_type": "DRIFT",
        "severity_score": 6,
        "severity_band": "HIGH",
        "severity_components": {"base": 4, "duration_modifier": 1, "deviation_modifier": 1},
        "confidence": 0.89,
        "confidence_band": "HIGH",
        "confidence_components": {"data_quality": 0.92, "baseline_confidence": 0.92},
        "deviation_percent": 22.0,
        "started_at": now - timedelta(hours=3),
        "duration_minutes": 180
    })
    
    comp_priority = await db.create_priority({
        "state_id": comp_state["id"],
        "asset_id": "asset-comp-main",
        "priority_score": 78,
        "priority_band": "HIGH",
        "priority_type": "OPERATIONAL",
        "drivers": [
            "22% energy drift sustained for 3 hours",
            "Critical production asset (90 criticality)",
            "Estimated $12.60/hr excess energy cost"
        ],
        "economic_impact": {
            "value_at_risk_per_day": 151.20,
            "value_recoverable_per_day": 128.52,
            "estimated_annual_impact": 55188
        },
        "score_components": {"severity": 45, "economic": 25, "criticality": 30}
    })
    current_issues.append({"asset": "Main Air Compressor", "state": comp_state, "priority": comp_priority})
    
    # Issue 2: AHU - MEDIUM priority efficiency drop (12% below baseline)
    ahu_state = await db.create_state({
        "asset_id": "asset-ahu-01",
        "rule_id": "rule-efficiency-drop",
        "baseline_id": baselines["asset-ahu-01"]["id"],
        "state_family": "OPERATIONAL",
        "state_type": "DEGRADATION",
        "severity_score": 4,
        "severity_band": "MEDIUM",
        "severity_components": {"base": 3, "duration_modifier": 0.5, "deviation_modifier": 0.5},
        "confidence": 0.76,
        "confidence_band": "MEDIUM",
        "confidence_components": {"data_quality": 0.80, "baseline_confidence": 0.88},
        "deviation_percent": 12.0,
        "started_at": now - timedelta(hours=6),
        "duration_minutes": 360
    })
    
    ahu_priority = await db.create_priority({
        "state_id": ahu_state["id"],
        "asset_id": "asset-ahu-01",
        "priority_score": 52,
        "priority_band": "MEDIUM",
        "priority_type": "OPERATIONAL",
        "drivers": [
            "12% efficiency drop over 6 hours",
            "Filter differential pressure increasing",
            "May indicate clogged filters"
        ],
        "economic_impact": {
            "value_at_risk_per_day": 42.50,
            "value_recoverable_per_day": 36.12,
            "estimated_annual_impact": 15513
        },
        "score_components": {"severity": 35, "economic": 20, "criticality": 25}
    })
    current_issues.append({"asset": "Air Handling Unit 1", "state": ahu_state, "priority": ahu_priority})
    
    # Issue 3: Chiller - LOW priority slight drift (8% above baseline, recent)
    chiller_state = await db.create_state({
        "asset_id": "asset-chiller-01",
        "rule_id": "rule-energy-drift",
        "baseline_id": baselines["asset-chiller-01"]["id"],
        "state_family": "ENERGY",
        "state_type": "DRIFT",
        "severity_score": 2,
        "severity_band": "LOW",
        "severity_components": {"base": 2, "duration_modifier": 0, "deviation_modifier": 0},
        "confidence": 0.65,
        "confidence_band": "MEDIUM",
        "confidence_components": {"data_quality": 0.70, "baseline_confidence": 0.85},
        "deviation_percent": 8.0,
        "started_at": now - timedelta(minutes=45),
        "duration_minutes": 45
    })
    
    chiller_priority = await db.create_priority({
        "state_id": chiller_state["id"],
        "asset_id": "asset-chiller-01",
        "priority_score": 28,
        "priority_band": "LOW",
        "priority_type": "MONITORING",
        "drivers": [
            "8% energy drift detected 45 minutes ago",
            "Below action threshold - monitoring",
            "May self-correct with load changes"
        ],
        "economic_impact": {
            "value_at_risk_per_day": 18.90,
            "value_recoverable_per_day": 12.30,
            "estimated_annual_impact": 6899
        },
        "score_components": {"severity": 20, "economic": 15, "criticality": 20}
    })
    current_issues.append({"asset": "Process Chiller 1", "state": chiller_state, "priority": chiller_priority})
    
    # =========================================================================
    # STEP 5: CONTINUOUS MONITORING NARRATIVE
    # =========================================================================
    
    # Create events showing ongoing monitoring
    await db.create_event({
        "event_type": "baseline_updated",
        "entity_type": "baseline",
        "entity_id": baselines["asset-comp-main"]["id"],
        "payload": {"message": "Baseline recalculated with latest 14-day window", "sample_count": 336}
    })
    
    await db.create_event({
        "event_type": "state_detected",
        "entity_type": "state",
        "entity_id": comp_state["id"],
        "payload": {"asset": "Main Air Compressor", "deviation": "22%", "action": "Priority created"}
    })
    
    # Calculate totals
    total_var = sum(
        p.get("economic_impact", {}).get("value_at_risk_per_day", 0) 
        if isinstance(p.get("economic_impact"), dict) else 0
        for p in [comp_priority, ahu_priority, chiller_priority]
    )
    
    return {
        "status": "ready",
        "narrative": {
            "site": {
                "name": "Riverside Plant - Building A",
                "assets_monitored": 4,
                "systems": ["HVAC", "Compressed Air", "Process Cooling"],
                "baseline_data_days": 14,
                "context": "All assets have established baselines from 2 weeks of normal operation."
            },
            "completed_loop": {
                "asset": "VFD Coolant Pump",
                "issue": "18.5% energy drift detected 3 days ago",
                "action": "Calibration - recalibrated VFD frequency setpoints",
                "outcome": "Verified +1.3 kWh/hr savings with 91% confidence",
                "time_to_verify": "1 hour",
                "message": "This demonstrates the full RAMP loop: detection → action → verification → learning."
            },
            "current_value_at_risk": {
                "total_per_day": round(total_var, 2),
                "currency": "USD",
                "active_issues": 3,
                "breakdown": [
                    {"asset": "Main Air Compressor", "var": 151.20, "band": "HIGH"},
                    {"asset": "Air Handling Unit 1", "var": 42.50, "band": "MEDIUM"},
                    {"asset": "Process Chiller 1", "var": 18.90, "band": "LOW"}
                ]
            },
            "priority_actions": [
                {
                    "rank": 1,
                    "asset": "Main Air Compressor",
                    "issue": "22% energy drift for 3 hours",
                    "band": "HIGH",
                    "confidence_label": "strong",
                    "var_per_day": 151.20,
                    "recommended_action": "Inspect inlet filter and check for leaks in downstream piping",
                    "state_id": comp_state["id"]
                },
                {
                    "rank": 2,
                    "asset": "Air Handling Unit 1",
                    "issue": "12% efficiency drop for 6 hours",
                    "band": "MEDIUM",
                    "confidence_label": "moderate",
                    "var_per_day": 42.50,
                    "recommended_action": "Check filter differential pressure and consider filter replacement",
                    "state_id": ahu_state["id"]
                },
                {
                    "rank": 3,
                    "asset": "Process Chiller 1",
                    "issue": "8% energy drift for 45 minutes",
                    "band": "LOW",
                    "confidence_label": "moderate",
                    "var_per_day": 18.90,
                    "recommended_action": "Monitor - may self-correct with load changes",
                    "state_id": chiller_state["id"]
                }
            ],
            "continuous_monitoring": {
                "message": "RAMP continuously monitors all assets against their established baselines.",
                "assets_healthy": 1,
                "assets_in_state": 3,
                "learning_active": True,
                "next_baseline_refresh": "Daily at 00:00 UTC"
            }
        }
    }
async def complete_verification_flow(db: RAMPDatabase = Depends(get_db)):
    """
    Demonstrate the complete verification flow end-to-end.
    
    This demo:
    1. Resets data
    2. Seeds configuration
    3. Simulates drift (creates baseline → state → priority)
    4. Creates intervention (freezes baseline)
    5. Completes intervention (creates pending outcome)
    6. Generates post-action metrics (simulates improved performance)
    7. Runs verification scheduler
    8. Returns verified outcome with savings
    
    This demonstrates the full MVP loop with real data.
    """
    # 1. Reset
    from sqlalchemy import text as sql_text
    tables = [
        "ramp_learning", "ramp_outcomes", "ramp_interventions",
        "ramp_priorities", "ramp_states", "ramp_baselines",
        "ramp_metrics", "ramp_signals", "ramp_rules",
        "ramp_assets", "ramp_systems", "ramp_sites", "ramp_organisations"
    ]
    await db.session.execute(sql_text("DROP TRIGGER IF EXISTS ramp_events_immutable ON ramp_events"))
    await db.session.execute(sql_text("DELETE FROM ramp_events"))
    await db.session.execute(sql_text("""
        CREATE TRIGGER ramp_events_immutable
        BEFORE UPDATE OR DELETE ON ramp_events
        FOR EACH ROW
        EXECUTE FUNCTION ramp_prevent_event_modification()
    """))
    for table in tables:
        await db.session.execute(sql_text(f"DELETE FROM {table}"))
    await db.session.commit()
    
    # 2. Seed
    await db.create_organisation("Demo Manufacturing Corp", id="demo-org-001")
    await db.create_site({
        "id": "demo-site-001",
        "organisation_id": "demo-org-001",
        "name": "Riverside Manufacturing",
        "timezone": "America/Chicago",
        "currency": "USD",
        "energy_tariff": 0.11,
        "hourly_production_value": 600,
        "operating_hours_per_day": 20,
        "site_category": "MANUFACTURING"
    })
    await db.create_system({
        "id": "sys-compressed-air",
        "site_id": "demo-site-001",
        "name": "Compressed Air System"
    })
    await db.create_asset({
        "id": "asset-comp-001",
        "system_id": "sys-compressed-air",
        "name": "Main Compressor A",
        "asset_class": "COMPRESSOR",
        "criticality_score": 85,
        "estimated_repair_cost": 6000
    })
    await db.create_rule({
        "id": "rule-energy-drift",
        "name": "Energy Drift Detection",
        "state_family": "ENERGY",
        "state_type": "DRIFT",
        "metric_type": "energy_intensity",
        "operator": "gt",
        "threshold_multiplier": 1.15,
        "duration_threshold_minutes": 30,
        "severity_base": 4,
        "is_active": True
    })
    
    # 3. Create baseline (historical normal)
    asset_id = "asset-comp-001"
    baseline_value = 45.0  # Normal energy intensity
    now = now_utc()
    
    baseline = await db.create_baseline({
        "id": generate_id(),
        "asset_id": asset_id,
        "metric_type": "energy_intensity",
        "context_signature": {"runtime_state": "RUNNING"},
        "baseline_value": baseline_value,
        "baseline_min": baseline_value * 0.90,
        "baseline_max": baseline_value * 1.10,
        "confidence": 0.85,
        "confidence_band": "HIGH",
        "valid_from": now - timedelta(days=14),
        "sample_count": 336,
        "data_window_days": 14
    })
    
    # 4. Create state (drift detected - 25% above baseline)
    drift_deviation = 25.5
    state = await db.create_state({
        "id": generate_id(),
        "asset_id": asset_id,
        "rule_id": "rule-energy-drift",
        "baseline_id": baseline["id"],
        "state_family": "ENERGY",
        "state_type": "DRIFT",
        "severity_score": 5,
        "severity_band": "MEDIUM",
        "severity_components": {"base": 4, "duration_modifier": 0, "deviation_modifier": 1},
        "confidence": 0.82,
        "confidence_band": "HIGH",
        "confidence_components": {"data_quality": 0.90, "baseline_confidence": 0.85},
        "deviation_percent": drift_deviation,
        "started_at": now - timedelta(hours=2),
        "duration_minutes": 120
    })
    
    # 5. Create priority
    priority = await db.create_priority({
        "id": generate_id(),
        "state_id": state["id"],
        "asset_id": asset_id,
        "priority_score": 62.5,
        "priority_band": "HIGH",
        "priority_type": "OPERATIONAL",
        "drivers": [f"{drift_deviation:.0f}% energy drift", "Critical asset"],
        "economic_impact": {"value_at_risk_per_day": 25.25},
        "score_components": {"severity": 50, "economic": 20, "risk": 30}
    })
    
    # 6. Freeze baseline and create intervention
    frozen_baseline = await db.freeze_baseline(asset_id, generate_id())
    
    intervention = await db.create_intervention({
        "state_id": state["id"],
        "asset_id": asset_id,
        "frozen_baseline_id": frozen_baseline["id"] if frozen_baseline else baseline["id"],
        "intervention_type": "CALIBRATION",  # Use CALIBRATION for shorter window (1h)
        "description": "Recalibrated compressor pressure settings",
        "created_by": "demo@example.com"
    })
    
    # 7. Complete intervention (backdated to simulate window elapsed)
    # Set completed_at to 2 hours ago so verification window has passed
    completed_at = now - timedelta(hours=2)
    await db.session.execute(
        sql_text("UPDATE ramp_interventions SET completed_at = :completed_at WHERE id = :id"),
        {"completed_at": completed_at, "id": intervention["id"]}
    )
    await db.session.commit()
    
    # 8. Create pending outcome
    window_hours = 1.0  # CALIBRATION window
    outcome = await db.create_outcome({
        "id": generate_id(),
        "intervention_id": intervention["id"],
        "frozen_baseline_id": frozen_baseline["id"] if frozen_baseline else baseline["id"],
        "verification_window_start": completed_at,
        "verification_window_end": completed_at + timedelta(hours=window_hours),
        "frozen_baseline_value": baseline_value,
        "status": "PENDING"
    })
    
    # 9. Generate post-action metrics (showing improvement)
    # New value is ~15% lower than baseline (improvement)
    improved_value = baseline_value * 0.85
    
    for i in range(10):
        # Add some realistic variance
        metric_value = improved_value + random.uniform(-2, 2)
        metric_time = completed_at + timedelta(minutes=i * 6)  # Every 6 minutes
        
        await db.create_metric({
            "id": generate_id(),
            "asset_id": asset_id,
            "metric_type": "energy_intensity",
            "value": metric_value,
            "unit": "kWh",
            "context_signature": {"runtime_state": "RUNNING"},
            "timestamp": metric_time
        })
    
    # 10. Run verification scheduler
    from ramp.services.verification_scheduler import VerificationScheduler
    scheduler = VerificationScheduler(db)
    verification_result = await scheduler.process_pending_outcomes()
    
    # 11. Get final outcome
    final_outcome = await db.get_outcome_by_id(outcome["id"])
    
    # 12. Get learning record
    learning = await db.get_learning_record(asset_id, "DRIFT")
    
    return {
        "status": "complete",
        "flow_summary": {
            "1_baseline": {"id": baseline["id"], "value": baseline_value},
            "2_state": {"id": state["id"], "deviation": f"{drift_deviation}%"},
            "3_priority": {"id": priority["id"], "band": "HIGH"},
            "4_intervention": {"id": intervention["id"], "type": "CALIBRATION"},
            "5_outcome": {
                "id": outcome["id"],
                "status": final_outcome.get("status") if final_outcome else "UNKNOWN",
                "savings_value": final_outcome.get("savings_value") if final_outcome else None,
                "savings_type": final_outcome.get("savings_type") if final_outcome else None,
                "confidence": final_outcome.get("confidence") if final_outcome else None,
                "confidence_band": final_outcome.get("confidence_band") if final_outcome else None
            },
            "6_learning": learning
        },
        "verification_result": verification_result,
        "message": "Full verification loop completed: baseline → state → priority → intervention → outcome → learning"
    }


@system_router.post("/demo/insufficient-data-scenario")
async def demo_insufficient_data(db: RAMPDatabase = Depends(get_db)):
    """
    Demonstrate the insufficient data scenario.
    
    Creates an intervention that completes but has NO post-action metrics,
    forcing the verification to fail with INSUFFICIENT_DATA after max retries.
    """
    from sqlalchemy import text as sql_text
    
    # Reset
    tables = [
        "ramp_learning", "ramp_outcomes", "ramp_interventions",
        "ramp_priorities", "ramp_states", "ramp_baselines",
        "ramp_metrics", "ramp_signals", "ramp_rules",
        "ramp_assets", "ramp_systems", "ramp_sites", "ramp_organisations"
    ]
    await db.session.execute(sql_text("DROP TRIGGER IF EXISTS ramp_events_immutable ON ramp_events"))
    await db.session.execute(sql_text("DELETE FROM ramp_events"))
    await db.session.execute(sql_text("""
        CREATE TRIGGER ramp_events_immutable
        BEFORE UPDATE OR DELETE ON ramp_events
        FOR EACH ROW
        EXECUTE FUNCTION ramp_prevent_event_modification()
    """))
    for table in tables:
        await db.session.execute(sql_text(f"DELETE FROM {table}"))
    await db.session.commit()
    
    # Minimal seed
    await db.create_organisation("Demo Corp", id="demo-org-001")
    await db.create_site({
        "id": "demo-site-001",
        "organisation_id": "demo-org-001",
        "name": "Test Site",
        "timezone": "UTC",
        "energy_tariff": 0.10
    })
    await db.create_system({
        "id": "sys-001",
        "site_id": "demo-site-001",
        "name": "Test System"
    })
    await db.create_asset({
        "id": "asset-001",
        "system_id": "sys-001",
        "name": "Test Asset"
    })
    
    # Create baseline
    asset_id = "asset-001"
    baseline_value = 50.0
    now = now_utc()
    
    baseline = await db.create_baseline({
        "asset_id": asset_id,
        "metric_type": "energy_intensity",
        "context_signature": {},
        "baseline_value": baseline_value,
        "baseline_min": 45.0,
        "baseline_max": 55.0,
        "confidence": 0.8,
        "confidence_band": "HIGH"
    })
    
    # Create state
    state = await db.create_state({
        "asset_id": asset_id,
        "baseline_id": baseline["id"],
        "state_family": "ENERGY",
        "state_type": "DRIFT",
        "severity_score": 4,
        "severity_band": "MEDIUM",
        "confidence": 0.75,
        "confidence_band": "MEDIUM"
    })
    
    # Freeze baseline
    await db.freeze_baseline(asset_id, generate_id())
    
    # Create intervention
    intervention = await db.create_intervention({
        "state_id": state["id"],
        "asset_id": asset_id,
        "frozen_baseline_id": baseline["id"],
        "intervention_type": "CALIBRATION",  # 1-hour window, 4 samples min
        "description": "Test intervention",
        "created_by": "test@test.com"
    })
    
    # Complete intervention (backdated)
    completed_at = now - timedelta(hours=3)  # Well past the 1-hour window
    await db.session.execute(
        sql_text("UPDATE ramp_interventions SET completed_at = :completed_at WHERE id = :id"),
        {"completed_at": completed_at, "id": intervention["id"]}
    )
    await db.session.commit()
    
    # Create pending outcome with max retries already hit
    # This simulates the scheduler having already tried multiple times
    outcome = await db.create_outcome({
        "intervention_id": intervention["id"],
        "frozen_baseline_id": baseline["id"],
        "verification_window_start": completed_at,
        "verification_window_end": completed_at + timedelta(hours=1),
        "frozen_baseline_value": baseline_value,
        "status": "PENDING"
    })
    
    # Set retry count to max-1 so next run will mark as insufficient
    await db.session.execute(
        sql_text("UPDATE ramp_outcomes SET retry_count = 5 WHERE id = :id"),
        {"id": outcome["id"]}
    )
    await db.session.commit()
    
    # Run verification (NO metrics exist - should fail)
    from ramp.services.verification_scheduler import VerificationScheduler
    scheduler = VerificationScheduler(db)
    result = await scheduler.process_pending_outcomes()
    
    # Get final outcome
    final_outcome = await db.get_outcome_by_id(outcome["id"])
    
    return {
        "status": "demonstrated",
        "scenario": "insufficient_data",
        "outcome": {
            "id": outcome["id"],
            "status": final_outcome.get("status") if final_outcome else "UNKNOWN",
            "verification_notes": final_outcome.get("verification_notes") if final_outcome else None
        },
        "verification_result": result,
        "message": "This demonstrates proper handling when no post-action data exists"
    }


# =============================================================================
# HOW LENS ROUTES
# =============================================================================

@how_router.get("/priorities")
async def get_priorities_how(db: RAMPDatabase = Depends(get_db)):
    """
    Get priority queue for operators.
    Uses HOWLens to enforce payload discipline.
    """
    priorities = await db.get_active_priorities()
    
    # Build asset and state lookups
    assets = {}
    states = {}
    for p in priorities:
        asset_id = p.get("asset_id")
        state_id = p.get("state_id")
        
        if asset_id and asset_id not in assets:
            asset = await db.get_asset(asset_id)
            if asset:
                assets[asset_id] = asset
        
        if state_id and state_id not in states:
            # Get active states for this asset and find the matching one
            active_states = await db.get_active_states(asset_id)
            state = next((s for s in active_states if s["id"] == state_id), None)
            if state:
                states[state_id] = state
    
    # Use HOWLens to build response with state confidence
    return HOWLens.priority_list_response(priorities, assets, states)


@how_router.get("/assets/{asset_id}/state")
async def get_asset_state_how(asset_id: str, db: RAMPDatabase = Depends(get_db)):
    """
    Get current state for an asset.
    Uses HOWLens to enforce payload discipline.
    """
    asset = await db.get_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    active_states = await db.get_active_states(asset_id)
    recent_states = await db.get_recent_states(asset_id, limit=10)
    
    # Use HOWLens to build response
    return HOWLens.asset_state_response(asset, active_states, recent_states)


@how_router.post("/interventions")
async def create_intervention_how(
    intervention: InterventionCreate,
    db: RAMPDatabase = Depends(get_db)
):
    """
    Create an intervention for a state.
    Triggers baseline freeze for verification.
    """
    # Get state to get asset_id
    active_states = await db.get_active_states()
    state = next((s for s in active_states if s["id"] == intervention.state_id), None)
    
    if not state:
        raise HTTPException(status_code=400, detail="State not found or not active")
    
    asset_id = state["asset_id"]
    correlation_id = generate_id()
    
    # Freeze baseline
    frozen_baseline = await db.freeze_baseline(asset_id, generate_id())
    
    # Create intervention
    intervention_record = await db.create_intervention({
        "state_id": intervention.state_id,
        "asset_id": asset_id,
        "frozen_baseline_id": frozen_baseline["id"] if frozen_baseline else None,
        "intervention_type": intervention.intervention_type,
        "description": intervention.description,
        "created_by": intervention.created_by
    })
    
    # Update frozen baseline with intervention ID
    if frozen_baseline:
        from sqlalchemy import text as sql_text
        await db.session.execute(
            sql_text("UPDATE ramp_baselines SET frozen_for_intervention_id = :intervention_id WHERE id = :baseline_id"),
            {"intervention_id": intervention_record["id"], "baseline_id": frozen_baseline["id"]}
        )
    
    # Create events
    await db.create_event({
        "event_type": "intervention_created",
        "entity_type": "intervention",
        "entity_id": intervention_record["id"],
        "payload": {
            "intervention_id": intervention_record["id"],
            "state_id": intervention.state_id,
            "asset_id": asset_id,
            "intervention_type": intervention.intervention_type,
            "created_by": intervention.created_by
        },
        "correlation_id": correlation_id
    })
    
    if frozen_baseline:
        await db.create_event({
            "event_type": "baseline_frozen",
            "entity_type": "baseline",
            "entity_id": frozen_baseline["id"],
            "payload": {
                "baseline_id": frozen_baseline["id"],
                "intervention_id": intervention_record["id"],
                "frozen_at": now_utc().isoformat(),
                "baseline_value": frozen_baseline["baseline_value"]
            },
            "correlation_id": correlation_id
        })
    
    # Use HOWLens to build response
    return HOWLens.intervention_created_response(
        intervention_record["id"],
        intervention.state_id
    )


@how_router.post("/interventions/complete")
async def complete_intervention_how(
    data: InterventionComplete,
    db: RAMPDatabase = Depends(get_db)
):
    """
    Mark an intervention as complete.
    Creates pending outcome for verification.
    """
    intervention = await db.get_intervention(data.intervention_id)
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention not found")
    
    # Complete intervention
    await db.complete_intervention(data.intervention_id)
    
    # Get frozen baseline
    frozen_baseline = await db.get_frozen_baseline(data.intervention_id)
    
    # Create pending outcome
    now = now_utc()
    await db.create_outcome({
        "intervention_id": data.intervention_id,
        "frozen_baseline_id": frozen_baseline["id"] if frozen_baseline else None,
        "verification_window_start": now,
        "verification_window_end": now + timedelta(hours=4),
        "frozen_baseline_value": frozen_baseline["baseline_value"] if frozen_baseline else 0,
        "status": "PENDING"
    })
    
    # Create event
    await db.create_event({
        "event_type": "intervention_completed",
        "entity_type": "intervention",
        "entity_id": data.intervention_id,
        "payload": {
            "intervention_id": data.intervention_id,
            "completed_at": now.isoformat()
        }
    })
    
    return HOWLens.intervention_completed_response(data.intervention_id)


@how_router.get("/interventions/{intervention_id}/outcome")
async def get_intervention_outcome_how(
    intervention_id: str,
    db: RAMPDatabase = Depends(get_db)
):
    """
    Get verification outcome for an intervention.
    Uses HOWLens to enforce payload discipline.
    """
    outcome = await db.get_outcome_for_intervention(intervention_id)
    return HOWLens.outcome_response(outcome, intervention_id)


# =============================================================================
# WHERE LENS ROUTES
# =============================================================================

@where_router.get("/priorities/summary")
async def get_priorities_summary_where(db: RAMPDatabase = Depends(get_db)):
    """
    Get priority summary for portfolio view.
    Uses WHERELens to enforce payload discipline.
    """
    priorities = await db.get_active_priorities()
    return WHERELens.portfolio_summary(priorities)


@where_router.get("/sites/{site_id}/states")
async def get_site_states_where(site_id: str, db: RAMPDatabase = Depends(get_db)):
    """
    Get state summary for a site.
    Uses WHERELens to enforce payload discipline.
    """
    assets = await db.get_assets_for_site(site_id)
    asset_ids = [a["id"] for a in assets]
    
    # Get active states for all assets
    all_active_states = await db.get_active_states()
    site_states = [s for s in all_active_states if s.get("asset_id") in asset_ids]
    
    return WHERELens.site_states_summary(site_id, site_states, len(assets))


# =============================================================================
# CHECKPOINT TEST ROUTE
# =============================================================================

@system_router.get("/checkpoint/relational-chain")
async def verify_relational_chain(db: RAMPDatabase = Depends(get_db)):
    """
    Verify the relational chain: baseline → state → intervention → outcome → event
    This is the checkpoint test for architectural alignment.
    
    Uses JOINs to prove the referential chain is intact.
    """
    from sqlalchemy import text as sql_text
    
    results = {
        "chain_verified": False,
        "steps": [],
        "sql_joins": []
    }
    
    # 1. Find an active priority
    priorities = await db.get_active_priorities()
    if not priorities:
        results["steps"].append({"step": "priority", "status": "FAIL", "error": "No active priorities"})
        return results
    
    priority = priorities[0]
    results["steps"].append({
        "step": "priority",
        "status": "PASS",
        "priority_id": priority["id"],
        "state_id": priority["state_id"]
    })
    
    # 2. Verify state exists and links to baseline
    active_states = await db.get_active_states()
    state = next((s for s in active_states if s["id"] == priority["state_id"]), None)
    if not state:
        results["steps"].append({"step": "state", "status": "FAIL", "error": "State not found"})
        return results
    
    results["steps"].append({
        "step": "state",
        "status": "PASS",
        "state_id": state["id"],
        "baseline_id": state.get("baseline_id")
    })
    
    # 3. Verify baseline exists
    if state.get("baseline_id"):
        # First try to get the baseline directly by ID
        baseline = await db.get_baseline_by_id(state["baseline_id"])
        if baseline:
            is_frozen = baseline.get("frozen_at") is not None
            results["steps"].append({
                "step": "baseline",
                "status": "PASS",
                "baseline_id": baseline["id"],
                "baseline_value": baseline["baseline_value"],
                "note": "Baseline is frozen for intervention" if is_frozen else "Active baseline"
            })
        else:
            results["steps"].append({"step": "baseline", "status": "WARN", "error": "Baseline not found"})
    
    # 4. Check for interventions linked to this state
    intervention_query = await db.session.execute(
        sql_text("SELECT * FROM ramp_interventions WHERE state_id = :state_id ORDER BY created_at DESC LIMIT 1"),
        {"state_id": state["id"]}
    )
    intervention_row = intervention_query.mappings().first()
    
    if intervention_row:
        intervention = dict(intervention_row)
        results["steps"].append({
            "step": "intervention",
            "status": "PASS",
            "intervention_id": intervention["id"],
            "intervention_type": intervention["intervention_type"],
            "frozen_baseline_id": intervention.get("frozen_baseline_id"),
            "completed_at": str(intervention.get("completed_at")) if intervention.get("completed_at") else None
        })
        
        # 5. Check for outcome linked to intervention
        outcome = await db.get_outcome_for_intervention(intervention["id"])
        if outcome:
            results["steps"].append({
                "step": "outcome",
                "status": "PASS",
                "outcome_id": outcome["id"],
                "status_value": outcome.get("status"),
                "frozen_baseline_value": outcome.get("frozen_baseline_value")
            })
        else:
            results["steps"].append({
                "step": "outcome",
                "status": "INFO",
                "message": "No outcome yet - intervention may not be completed"
            })
    else:
        results["steps"].append({
            "step": "intervention",
            "status": "INFO",
            "message": "No intervention created yet - chain ready for intervention"
        })
    
    # 6. Check events with correlation
    events = await db.session.execute(
        sql_text("SELECT event_type, entity_type, entity_id FROM ramp_events ORDER BY created_at DESC LIMIT 10")
    )
    event_list = [dict(row) for row in events.mappings()]
    results["steps"].append({
        "step": "events",
        "status": "PASS",
        "recent_events": [e["event_type"] for e in event_list]
    })
    
    # 7. SQL JOIN verification - prove the chain with explicit JOINs
    join_query = await db.session.execute(
        sql_text("""
            SELECT 
                b.id as baseline_id,
                b.baseline_value,
                s.id as state_id,
                s.state_type,
                s.severity_band,
                p.id as priority_id,
                p.priority_band,
                i.id as intervention_id,
                i.intervention_type,
                o.id as outcome_id,
                o.status as outcome_status
            FROM ramp_baselines b
            JOIN ramp_states s ON s.baseline_id = b.id
            JOIN ramp_priorities p ON p.state_id = s.id
            LEFT JOIN ramp_interventions i ON i.state_id = s.id
            LEFT JOIN ramp_outcomes o ON o.intervention_id = i.id
            WHERE s.ended_at IS NULL
            LIMIT 5
        """)
    )
    join_results = [dict(row) for row in join_query.mappings()]
    
    if join_results:
        results["sql_joins"] = join_results
        results["chain_verified"] = True
        
        # Determine completeness
        has_intervention = any(r.get("intervention_id") for r in join_results)
        has_outcome = any(r.get("outcome_id") for r in join_results)
        
        if has_outcome:
            results["summary"] = "FULL CHAIN VERIFIED: baseline → state → priority → intervention → outcome (with SQL JOINs)"
        elif has_intervention:
            results["summary"] = "CHAIN VERIFIED: baseline → state → priority → intervention (outcome pending)"
        else:
            results["summary"] = "CHAIN VERIFIED: baseline → state → priority (ready for intervention)"
    else:
        results["chain_verified"] = False
        results["summary"] = "No complete chain found - data may need to be seeded"
    
    return results


# =============================================================================
# PROOF OF VALUE VIEW
# =============================================================================

@system_router.get("/value-summary")
async def get_value_summary(db: RAMPDatabase = Depends(get_db)):
    """
    Single aggregated view showing proof of value.
    
    Returns everything needed to answer in under a minute:
    1. Where is value being lost? → Current VaR/day
    2. What to do about it? → Top priority actions with recoverable value + confidence
    3. What has been recovered? → Recently verified outcomes with savings
    4. Is the system working? → Loop integrity
    
    This endpoint uses HOW lens discipline for confidence (labels not raw values).
    """
    from sqlalchemy import text as sql_text
    from ramp.lenses.helpers import confidence_to_label, confidence_band_to_label
    
    # 1. CURRENT VALUE AT RISK
    priorities = await db.get_active_priorities()
    
    total_var = sum(
        p.get("economic_impact", {}).get("value_at_risk_per_day", 0) 
        if isinstance(p.get("economic_impact"), dict) else 0
        for p in priorities
    )
    
    # Get site for currency
    site = await db.get_site("demo-site-001")
    currency = site.get("currency", "USD") if site else "USD"
    
    # 2. TOP PRIORITY ACTIONS (max 5)
    top_actions = []
    for p in priorities[:5]:
        # Get state for confidence
        states = await db.get_active_states(p.get("asset_id"))
        state = next((s for s in states if s["id"] == p.get("state_id")), None)
        
        # Get asset name
        asset = await db.get_asset(p.get("asset_id"))
        
        economic = p.get("economic_impact", {})
        if isinstance(economic, str):
            import json
            try:
                economic = json.loads(economic)
            except Exception:
                economic = {}
        
        drivers = p.get("drivers", [])
        if isinstance(drivers, str):
            import json
            try:
                drivers = json.loads(drivers)
            except Exception:
                drivers = []
        
        # Get confidence label (NOT raw value) - Lens Contract compliant
        if state:
            confidence_raw = state.get("confidence")
            confidence_band = state.get("confidence_band")
            if confidence_raw is not None and isinstance(confidence_raw, (int, float)):
                confidence_label = confidence_to_label(confidence_raw)
            elif confidence_band:
                confidence_label = confidence_band_to_label(confidence_band)
            else:
                confidence_label = "unknown"
        else:
            confidence_label = "unknown"
        
        top_actions.append({
            "priority_id": p["id"],
            "state_id": p.get("state_id"),
            "asset_id": p.get("asset_id"),
            "asset_name": asset.get("name") if asset else "Unknown",
            "priority_band": p.get("priority_band"),
            "state_type": state.get("state_type") if state else "Unknown",
            "state_family": state.get("state_family") if state else "Unknown",
            "severity_band": state.get("severity_band") if state else "Unknown",
            "value_at_risk_per_day": economic.get("value_at_risk_per_day", 0),
            "value_recoverable_per_day": economic.get("value_recoverable_per_day", 0),
            "confidence_label": confidence_label,  # Label not raw value
            "drivers": drivers[:2]  # Top 2 drivers only
        })
    
    # 3. RECENTLY VERIFIED OUTCOMES
    verified_outcomes_query = await db.session.execute(
        sql_text("""
            SELECT 
                o.id as outcome_id,
                o.intervention_id,
                o.savings_value,
                o.savings_type,
                o.savings_unit,
                o.confidence,
                o.confidence_band,
                o.status,
                o.verified_at,
                o.verification_window_start,
                o.verification_window_end,
                o.frozen_baseline_value,
                o.actual_value,
                i.intervention_type,
                i.completed_at as intervention_completed_at,
                a.name as asset_name
            FROM ramp_outcomes o
            JOIN ramp_interventions i ON o.intervention_id = i.id
            JOIN ramp_assets a ON i.asset_id = a.id
            WHERE o.status = 'VERIFIED'
            ORDER BY o.verified_at DESC
            LIMIT 5
        """)
    )
    
    verified_outcomes = []
    for row in verified_outcomes_query.mappings():
        row_dict = dict(row)
        
        # Calculate time to verify
        verified_at = row_dict.get("verified_at")
        completed_at = row_dict.get("intervention_completed_at")
        
        time_to_verify_hours = None
        if verified_at and completed_at:
            if isinstance(verified_at, str):
                verified_at = datetime.fromisoformat(verified_at.replace("Z", "+00:00"))
            if isinstance(completed_at, str):
                completed_at = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
            time_to_verify_hours = round((verified_at - completed_at).total_seconds() / 3600, 1)
        
        # Get confidence label (NOT raw value) - Lens Contract compliant
        confidence_raw = row_dict.get("confidence")
        confidence_band = row_dict.get("confidence_band")
        if confidence_raw is not None and isinstance(confidence_raw, (int, float)):
            outcome_confidence_label = confidence_to_label(confidence_raw)
        elif confidence_band:
            outcome_confidence_label = confidence_band_to_label(confidence_band)
        else:
            outcome_confidence_label = "unknown"
        
        verified_outcomes.append({
            "outcome_id": row_dict["outcome_id"],
            "asset_name": row_dict["asset_name"],
            "intervention_type": row_dict["intervention_type"],
            "savings_value": round(row_dict.get("savings_value") or 0, 2),
            "savings_unit": row_dict.get("savings_unit", "units"),
            "savings_type": row_dict.get("savings_type"),
            "confidence_label": outcome_confidence_label,  # Label not raw value
            "time_to_verify_hours": time_to_verify_hours,
            "verified_at": row_dict.get("verified_at").isoformat() if row_dict.get("verified_at") else None
        })
    
    # Calculate total savings recovered
    total_savings = sum(o.get("savings_value", 0) for o in verified_outcomes)
    
    # 4. LOOP INTEGRITY SIGNAL
    # Count outcomes by status
    integrity_query = await db.session.execute(
        sql_text("""
            SELECT 
                status,
                COUNT(*) as count
            FROM ramp_outcomes
            GROUP BY status
        """)
    )
    
    integrity = {
        "VERIFIED": 0,
        "PENDING": 0,
        "INSUFFICIENT_DATA": 0
    }
    for row in integrity_query.mappings():
        status = row["status"]
        if status in integrity:
            integrity[status] = row["count"]
    
    total_outcomes = sum(integrity.values())
    
    # Calculate verification rate (only for outcomes that have been processed)
    processed = integrity["VERIFIED"] + integrity["INSUFFICIENT_DATA"]
    verification_rate = round(integrity["VERIFIED"] / processed * 100, 1) if processed > 0 else None
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "currency": currency,
        
        # 1. WHERE VALUE IS BEING LOST
        "value_at_risk": {
            "total_per_day": round(total_var, 2),
            "active_priorities": len(priorities),
            "breakdown_by_band": {
                band: sum(
                    p.get("economic_impact", {}).get("value_at_risk_per_day", 0) 
                    if isinstance(p.get("economic_impact"), dict) else 0
                    for p in priorities if p.get("priority_band") == band
                )
                for band in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
            }
        },
        
        # 2. WHAT TO DO ABOUT IT
        "top_actions": top_actions,
        
        # 3. WHAT HAS BEEN RECOVERED
        "recovered_value": {
            "total_savings": round(total_savings, 2),
            "verified_outcomes_count": len(verified_outcomes),
            "recent_outcomes": verified_outcomes
        },
        
        # 4. LOOP INTEGRITY
        "loop_integrity": {
            "verified": integrity["VERIFIED"],
            "pending": integrity["PENDING"],
            "insufficient_data": integrity["INSUFFICIENT_DATA"],
            "total_outcomes": total_outcomes,
            "verification_rate_percent": verification_rate,
            "status": "HEALTHY" if verification_rate is None or verification_rate >= 70 else "DEGRADED" if verification_rate >= 40 else "POOR"
        }
    }

@system_router.post("/verification/run")
async def run_verification_scheduler(db: RAMPDatabase = Depends(get_db)):
    """
    Run the verification scheduler to process pending outcomes.
    
    This endpoint:
    1. Checks all PENDING outcomes
    2. Verifies those where the window has elapsed and data is sufficient
    3. Marks INSUFFICIENT_DATA for those that exceed retry limits
    4. Updates learning records for verified outcomes
    
    In production, this would be called by a cron job or scheduled task.
    """
    from ramp.services.verification_scheduler import VerificationScheduler
    
    scheduler = VerificationScheduler(db)
    results = await scheduler.process_pending_outcomes()
    
    return {
        "status": "completed",
        "summary": {
            "processed": results["processed"],
            "verified": results["verified"],
            "insufficient_data": results["insufficient_data"],
            "still_pending": results["still_pending"],
            "errors": results["errors"]
        },
        "details": results["details"]
    }


@system_router.get("/verification/pending")
async def get_pending_verifications(db: RAMPDatabase = Depends(get_db)):
    """
    Get all pending verification outcomes.
    
    Returns outcomes that are waiting for verification with their
    current status, retry count, and time since intervention.
    """
    pending = await db.get_pending_outcomes()
    
    now = datetime.now(timezone.utc)
    enriched = []
    
    for outcome in pending:
        completed_at = outcome.get("intervention_completed_at")
        if isinstance(completed_at, str):
            completed_at = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
        
        hours_since_completion = (now - completed_at).total_seconds() / 3600 if completed_at else 0
        
        enriched.append({
            "outcome_id": outcome["id"],
            "intervention_id": outcome["intervention_id"],
            "state_family": outcome.get("state_family"),
            "state_type": outcome.get("state_type"),
            "intervention_type": outcome.get("intervention_type"),
            "status": outcome.get("status"),
            "retry_count": outcome.get("retry_count", 0),
            "hours_since_completion": round(hours_since_completion, 2),
            "frozen_baseline_value": outcome.get("frozen_baseline_value"),
            "verification_notes": outcome.get("verification_notes")
        })
    
    return {
        "pending_count": len(enriched),
        "outcomes": enriched
    }


@system_router.get("/verification/config")
async def get_verification_configs():
    """
    Get all verification configuration settings.
    
    Shows the window hours, min samples, and retry settings
    for each state family and intervention type.
    """
    from ramp.services.verification_config import (
        DEFAULT_CONFIGS, 
        INTERVENTION_TYPE_CONFIGS
    )
    
    return {
        "by_state_family": {
            k: {
                "window_hours": v.window_hours,
                "min_samples": v.min_samples,
                "min_window_coverage": v.min_window_coverage,
                "max_retry_attempts": v.max_retry_attempts,
                "retry_interval_hours": v.retry_interval_hours
            }
            for k, v in DEFAULT_CONFIGS.items()
        },
        "by_intervention_type": {
            k: {
                "window_hours": v.window_hours,
                "min_samples": v.min_samples,
                "min_window_coverage": v.min_window_coverage,
                "max_retry_attempts": v.max_retry_attempts,
                "retry_interval_hours": v.retry_interval_hours
            }
            for k, v in INTERVENTION_TYPE_CONFIGS.items()
        },
        "note": "Intervention type config takes precedence over state family config"
    }


@system_router.get("/learning/{asset_id}")
async def get_learning_for_asset(asset_id: str, db: RAMPDatabase = Depends(get_db)):
    """
    Get learning records for an asset.
    
    Shows recurrence counts, intervention effectiveness, and savings totals.
    """
    from sqlalchemy import text as sql_text
    
    result = await db.session.execute(
        sql_text("SELECT * FROM ramp_learning WHERE asset_id = :asset_id ORDER BY updated_at DESC"),
        {"asset_id": asset_id}
    )
    records = [dict(row) for row in result.mappings()]
    
    return {
        "asset_id": asset_id,
        "learning_records": records,
        "summary": {
            "total_state_types": len(records),
            "total_interventions": sum(r.get("intervention_count", 0) for r in records),
            "total_savings": sum(r.get("total_savings", 0) for r in records)
        }
    }


# Root endpoint for API
@api_router.get("/")
async def root():
    return {"message": "RAMP Command Centre API", "version": "0.1.0", "database": "postgresql"}


# =============================================================================
# SETUP
# =============================================================================

app.include_router(api_router)
app.include_router(how_router)
app.include_router(where_router)
app.include_router(system_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup."""
    try:
        await init_db()
        logger.info("RAMP Command Centre started with PostgreSQL")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("RAMP Command Centre stopped")
