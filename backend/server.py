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


@system_router.post("/demo/complete-verification-flow")
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
    
    # Build asset lookup
    assets = {}
    for p in priorities:
        asset_id = p.get("asset_id")
        if asset_id and asset_id not in assets:
            asset = await db.get_asset(asset_id)
            if asset:
                assets[asset_id] = asset
    
    # Use HOWLens to build response
    return HOWLens.priority_list_response(priorities, assets)


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
# VERIFICATION SCHEDULER ROUTES
# =============================================================================

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
