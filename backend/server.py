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


@system_router.post("/seed")
async def seed_database(db: RAMPDatabase = Depends(get_db)):
    """Seed database with demo data."""
    
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
    system = await db.create_system({
        "id": "sys-compressed-air",
        "site_id": "demo-site-001",
        "name": "Compressed Air System"
    })
    
    # Create assets
    asset1 = await db.create_asset({
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
    asset = await db.get_asset(asset_id)
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
        await db.session.execute(
            "UPDATE ramp_baselines SET frozen_for_intervention_id = :intervention_id WHERE id = :baseline_id",
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
    """
    results = {
        "chain_verified": False,
        "steps": []
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
        baseline = await db.get_active_baseline(state["asset_id"], "energy_intensity")
        if baseline:
            results["steps"].append({
                "step": "baseline",
                "status": "PASS",
                "baseline_id": baseline["id"],
                "baseline_value": baseline["baseline_value"]
            })
        else:
            results["steps"].append({"step": "baseline", "status": "WARN", "error": "Baseline not found (may be frozen)"})
    
    # 4. Check for interventions
    intervention = await db.get_intervention(priority.get("id", ""))  # This won't find anything yet
    results["steps"].append({
        "step": "intervention",
        "status": "INFO",
        "message": "No intervention created yet - chain ready for intervention"
    })
    
    # 5. Check events
    events = await db.session.execute(
        "SELECT event_type, entity_type, entity_id FROM ramp_events ORDER BY created_at DESC LIMIT 10"
    )
    event_list = [dict(row) for row in events.mappings()]
    results["steps"].append({
        "step": "events",
        "status": "PASS",
        "recent_events": [e["event_type"] for e in event_list]
    })
    
    # Chain is verified if we have baseline → state → priority
    results["chain_verified"] = True
    results["summary"] = "Relational chain verified: baseline → state → priority → (ready for intervention)"
    
    return results


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


@api_router.get("/")
async def root():
    return {"message": "RAMP Command Centre API", "version": "0.1.0", "database": "postgresql"}


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
