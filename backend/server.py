from fastapi import FastAPI, APIRouter, HTTPException, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone

# RAMP imports
from ramp.app import get_ramp_app, RAMPApplication
from ramp.seed import seed_demo_data, generate_demo_signals
from ramp.models.schema import SignalQuality


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Initialize RAMP application
ramp: Optional[RAMPApplication] = None

# Create the main app without a prefix
app = FastAPI(
    title="RAMP Command Centre API",
    description="State-based industrial intelligence platform",
    version="0.1.0"
)

# Create routers
api_router = APIRouter(prefix="/api")
how_router = APIRouter(prefix="/api/how", tags=["HOW Lens"])
where_router = APIRouter(prefix="/api/where", tags=["WHERE Lens"])
system_router = APIRouter(prefix="/api/system", tags=["System"])


# =============================================================================
# PYDANTIC MODELS FOR API
# =============================================================================

class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

class SignalIngest(BaseModel):
    asset_id: str
    signal_type: str
    value: float
    unit: str = ""
    timestamp: Optional[datetime] = None
    quality: str = "GOOD"

class SignalBatchIngest(BaseModel):
    signals: List[SignalIngest]

class InterventionCreate(BaseModel):
    state_id: str
    intervention_type: str
    description: str
    created_by: str

class InterventionComplete(BaseModel):
    intervention_id: str


# =============================================================================
# SYSTEM ROUTES (Internal/Admin)
# =============================================================================

@system_router.get("/health")
async def health_check():
    """System health check."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "ramp_initialized": ramp is not None
    }

@system_router.post("/seed")
async def seed_database():
    """Seed database with demo data."""
    result = await seed_demo_data(db)
    return {"status": "seeded", "data": result}

@system_router.post("/demo/simulate-drift")
async def simulate_active_drift():
    """
    Simulate an active drift condition for demonstration.
    
    This creates:
    1. Baseline from normal signals
    2. Current drift signals that haven't resolved yet
    """
    if not ramp:
        raise HTTPException(status_code=500, detail="RAMP not initialized")
    
    from datetime import timedelta
    import random
    
    asset_id = "asset-comp-001"
    baseline_value = 45.0
    
    # Clear existing data for fresh demo
    await db.signals.delete_many({"asset_id": asset_id})
    await db.metrics.delete_many({"asset_id": asset_id})
    await db.baselines.delete_many({"asset_id": asset_id})
    await db.states.delete_many({"asset_id": asset_id})
    await db.priorities.delete_many({"asset_id": asset_id})
    
    now = datetime.now(timezone.utc)
    
    # Phase 1: Historical normal signals (24 hours ago to 2 hours ago)
    for i in range(96):  # 24 hours * 4 readings/hour
        timestamp = now - timedelta(hours=24) + timedelta(minutes=i * 15)
        value = baseline_value + random.uniform(-2, 2)
        
        await ramp.ingestion.ingest_signal(
            asset_id=asset_id,
            signal_type="energy_consumption",
            value=round(value, 2),
            unit="kWh",
            timestamp=timestamp,
            quality=SignalQuality.GOOD
        )
    
    # Phase 2: Drift signals (2 hours ago to now)
    drift_value = baseline_value * 1.25  # 25% above baseline
    for i in range(8):  # 2 hours * 4 readings/hour
        timestamp = now - timedelta(hours=2) + timedelta(minutes=i * 15)
        value = drift_value + random.uniform(-1, 3)
        
        await ramp.ingestion.ingest_signal(
            asset_id=asset_id,
            signal_type="energy_consumption",
            value=round(value, 2),
            unit="kWh",
            timestamp=timestamp,
            quality=SignalQuality.GOOD
        )
    
    # Check results
    baselines = await db.baselines.count_documents({"asset_id": asset_id})
    active_states = await db.states.count_documents({"asset_id": asset_id, "ended_at": None})
    active_priorities = await db.priorities.count_documents({"asset_id": asset_id, "expires_at": None})
    
    return {
        "status": "simulated",
        "asset_id": asset_id,
        "baseline_value": baseline_value,
        "drift_value": drift_value,
        "signals_ingested": 104,
        "baselines_established": baselines,
        "active_states": active_states,
        "active_priorities": active_priorities
    }


@system_router.post("/demo/generate-signals")
async def generate_demo_signal_data(
    hours_normal: int = Query(24, ge=1, le=168),
    hours_drift: int = Query(3, ge=1, le=24),
    hours_post: int = Query(5, ge=1, le=24)
):
    """Generate and ingest demo signals for testing the loop."""
    if not ramp:
        raise HTTPException(status_code=500, detail="RAMP not initialized")
    
    signals = generate_demo_signals(
        asset_id="asset-comp-001",
        hours_normal=hours_normal,
        hours_drift=hours_drift,
        hours_post_intervention=hours_post
    )
    
    # Ingest signals
    ingested = 0
    for signal_data in signals:
        await ramp.ingestion.ingest_signal(
            asset_id=signal_data["asset_id"],
            signal_type=signal_data["signal_type"],
            value=signal_data["value"],
            unit=signal_data["unit"],
            timestamp=signal_data["timestamp"],
            quality=SignalQuality(signal_data["quality"])
        )
        ingested += 1
    
    return {"status": "generated", "signals_ingested": ingested}


# =============================================================================
# HOW LENS ROUTES (Operator View)
# =============================================================================

@how_router.get("/priorities")
async def get_priorities_how():
    """
    Get priority queue for operators.
    
    Returns active priorities ranked by band and score.
    HOW lens: sees totals, drivers, actionable info.
    Does NOT see: raw calculation inputs, portfolio aggregates.
    """
    priorities = await db.priorities.find(
        {"expires_at": None},
        {"_id": 0}
    ).sort([("priority_band", 1), ("priority_score", -1)]).to_list(100)
    
    # Transform for HOW lens (remove SYSTEM-only fields)
    how_priorities = []
    for p in priorities:
        # Get asset name
        asset = await db.assets.find_one({"id": p.get("asset_id")}, {"_id": 0})
        asset_name = asset.get("name", "Unknown") if asset else "Unknown"
        
        how_priorities.append({
            "priority_id": p.get("id"),
            "asset_id": p.get("asset_id"),
            "asset_name": asset_name,
            "state_id": p.get("state_id"),
            "priority_band": p.get("priority_band"),
            "priority_type": p.get("priority_type"),
            "drivers": p.get("drivers", []),
            "value_at_risk_per_day": p.get("economic_impact", {}).get("value_at_risk_per_day", 0),
            "value_recoverable_per_day": p.get("economic_impact", {}).get("value_recoverable_per_day", 0),
            "currency": p.get("economic_impact", {}).get("currency", "USD"),
            "created_at": p.get("created_at")
        })
    
    return {"priorities": how_priorities, "count": len(how_priorities)}

@how_router.get("/assets/{asset_id}/state")
async def get_asset_state_how(asset_id: str):
    """
    Get current state for an asset.
    
    HOW lens: sees state type, severity band, confidence band, drivers.
    Does NOT see: raw scores, calculation components.
    """
    # Get asset
    asset = await db.assets.find_one({"id": asset_id}, {"_id": 0})
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Get active states
    active_states = await db.states.find(
        {"asset_id": asset_id, "ended_at": None},
        {"_id": 0}
    ).to_list(10)
    
    # Get recent states (last 10)
    recent_states = await db.states.find(
        {"asset_id": asset_id},
        {"_id": 0}
    ).sort("started_at", -1).limit(10).to_list(10)
    
    # Transform for HOW lens
    def transform_state(s):
        return {
            "state_id": s.get("id"),
            "state_family": s.get("state_family"),
            "state_type": s.get("state_type"),
            "severity_band": s.get("severity_band"),
            "confidence_band": s.get("confidence_band"),
            "deviation_percent": s.get("deviation_percent"),
            "duration_minutes": s.get("duration_minutes", 0),
            "started_at": s.get("started_at"),
            "ended_at": s.get("ended_at")
        }
    
    return {
        "asset_id": asset_id,
        "asset_name": asset.get("name"),
        "criticality_band": asset.get("criticality_band", "MEDIUM"),
        "active_states": [transform_state(s) for s in active_states],
        "recent_states": [transform_state(s) for s in recent_states]
    }

@how_router.post("/interventions")
async def create_intervention_how(intervention: InterventionCreate):
    """
    Create an intervention for a state.
    
    This triggers baseline freeze for verification.
    """
    if not ramp:
        raise HTTPException(status_code=500, detail="RAMP not initialized")
    
    try:
        result = await ramp.intervention.create_intervention(
            state_id=intervention.state_id,
            intervention_type=intervention.intervention_type,
            description=intervention.description,
            created_by=intervention.created_by
        )
        
        return {
            "intervention_id": result.id,
            "state_id": result.state_id,
            "message": "Intervention created. Baseline frozen for verification."
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@how_router.post("/interventions/complete")
async def complete_intervention_how(data: InterventionComplete):
    """
    Mark an intervention as complete.
    
    This starts the verification window.
    """
    if not ramp:
        raise HTTPException(status_code=500, detail="RAMP not initialized")
    
    try:
        await ramp.intervention.complete_intervention(data.intervention_id)
        return {
            "intervention_id": data.intervention_id,
            "message": "Intervention completed. Verification started."
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@how_router.get("/interventions/{intervention_id}/outcome")
async def get_intervention_outcome_how(intervention_id: str):
    """
    Get verification outcome for an intervention.
    
    HOW lens: sees savings value, type, confidence band.
    """
    outcome = await db.outcomes.find_one(
        {"intervention_id": intervention_id},
        {"_id": 0}
    )
    
    if not outcome:
        return {
            "intervention_id": intervention_id,
            "status": "pending",
            "message": "Verification not yet complete"
        }
    
    return {
        "intervention_id": intervention_id,
        "status": "verified",
        "savings_value": outcome.get("savings_value"),
        "savings_unit": outcome.get("savings_unit"),
        "savings_type": outcome.get("savings_type"),
        "confidence_band": outcome.get("confidence_band"),
        "verified_at": outcome.get("verified_at")
    }


# =============================================================================
# WHERE LENS ROUTES (Portfolio View)
# =============================================================================

@where_router.get("/priorities/summary")
async def get_priorities_summary_where():
    """
    Get priority summary for portfolio view.
    
    WHERE lens: sees aggregated distribution, site-level summaries.
    Does NOT see: individual operator actions, raw asset data.
    """
    # Get all active priorities
    priorities = await db.priorities.find(
        {"expires_at": None},
        {"_id": 0}
    ).to_list(1000)
    
    # Aggregate by band
    band_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    total_var = 0
    total_vr = 0
    
    for p in priorities:
        band = p.get("priority_band", "LOW")
        if band in band_counts:
            band_counts[band] += 1
        
        ei = p.get("economic_impact", {})
        total_var += ei.get("value_at_risk_per_day", 0)
        total_vr += ei.get("value_recoverable_per_day", 0)
    
    return {
        "distribution": band_counts,
        "total_active": len(priorities),
        "total_value_at_risk_per_day": round(total_var, 2),
        "total_value_recoverable_per_day": round(total_vr, 2),
        "currency": "USD"
    }

@where_router.get("/sites/{site_id}/states")
async def get_site_states_where(site_id: str):
    """
    Get state summary for a site.
    
    WHERE lens: sees aggregated state distribution.
    """
    # Get systems for site
    systems = await db.systems.find(
        {"site_id": site_id},
        {"_id": 0}
    ).to_list(100)
    
    system_ids = [s["id"] for s in systems]
    
    # Get assets for systems
    assets = await db.assets.find(
        {"system_id": {"$in": system_ids}},
        {"_id": 0}
    ).to_list(1000)
    
    asset_ids = [a["id"] for a in assets]
    
    # Get active states for assets
    states = await db.states.find(
        {"asset_id": {"$in": asset_ids}, "ended_at": None},
        {"_id": 0}
    ).to_list(1000)
    
    # Aggregate by family and type
    state_dist = {}
    for s in states:
        family = s.get("state_family", "UNKNOWN")
        state_type = s.get("state_type", "UNKNOWN")
        key = f"{family}:{state_type}"
        state_dist[key] = state_dist.get(key, 0) + 1
    
    return {
        "site_id": site_id,
        "total_active_states": len(states),
        "state_distribution": state_dist,
        "asset_count": len(assets)
    }

@where_router.get("/outcomes/export")
async def export_outcomes_where(
    days: int = Query(30, ge=1, le=365)
):
    """
    Export verified outcomes for evidence.
    
    WHERE lens: provides exportable evidence of savings.
    """
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    outcomes = await db.outcomes.find(
        {"verified_at": {"$gte": cutoff}},
        {"_id": 0}
    ).to_list(1000)
    
    # Calculate totals
    total_savings = sum(o.get("savings_value", 0) for o in outcomes)
    high_confidence = [o for o in outcomes if o.get("confidence_band") == "HIGH"]
    
    return {
        "period_days": days,
        "outcomes_count": len(outcomes),
        "total_verified_savings": round(total_savings, 2),
        "high_confidence_count": len(high_confidence),
        "outcomes": outcomes
    }


# =============================================================================
# INGESTION ROUTES
# =============================================================================

@api_router.post("/ingest/signals")
async def ingest_signals(batch: SignalBatchIngest):
    """
    Ingest batch of signals.
    
    This is the entry point for data into RAMP.
    """
    if not ramp:
        raise HTTPException(status_code=500, detail="RAMP not initialized")
    
    ingested = 0
    errors = []
    
    for signal in batch.signals:
        try:
            timestamp = signal.timestamp or datetime.now(timezone.utc)
            quality = SignalQuality(signal.quality) if signal.quality else SignalQuality.GOOD
            
            await ramp.ingestion.ingest_signal(
                asset_id=signal.asset_id,
                signal_type=signal.signal_type,
                value=signal.value,
                unit=signal.unit,
                timestamp=timestamp,
                quality=quality
            )
            ingested += 1
        except Exception as e:
            errors.append({"signal": signal.model_dump(), "error": str(e)})
    
    return {
        "ingested": ingested,
        "errors": errors,
        "total": len(batch.signals)
    }


# =============================================================================
# LEGACY/STATUS ROUTES
# =============================================================================

@api_router.get("/")
async def root():
    return {"message": "RAMP Command Centre API", "version": "0.1.0"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    _ = await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    return status_checks


# =============================================================================
# INCLUDE ROUTERS
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def startup_event():
    """Initialize RAMP application on startup."""
    global ramp
    ramp = get_ramp_app(db)
    await ramp.start()
    logger.info("RAMP Command Centre started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global ramp
    if ramp:
        await ramp.stop()
    client.close()
    logger.info("RAMP Command Centre stopped")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()