"""
RAMP Seed Data
==============

Demo site configuration and simulated signal data
for demonstrating the full end-to-end loop.

Scenario: Energy drift detection → intervention → verified savings
"""

from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
import random

from .models.schema import (
    Organisation, Site, System, Asset, Rule,
    AssetClass, SiteCategory, StateFamily,
    generate_id, now_utc
)


def get_demo_organisation() -> Dict[str, Any]:
    """Create demo organisation."""
    return Organisation(
        id="demo-org-001",
        name="Demo Manufacturing Corp",
        created_at=now_utc()
    ).model_dump()


def get_demo_site() -> Dict[str, Any]:
    """Create demo site with economic configuration."""
    return Site(
        id="demo-site-001",
        organisation_id="demo-org-001",
        name="Riverside Manufacturing",
        timezone="America/Chicago",
        currency="USD",
        energy_tariff=0.11,
        hourly_production_value=600,
        operating_hours_per_day=20,
        site_category=SiteCategory.MANUFACTURING,
        created_at=now_utc()
    ).model_dump()


def get_demo_systems() -> List[Dict[str, Any]]:
    """Create demo systems."""
    return [
        System(
            id="sys-compressed-air",
            site_id="demo-site-001",
            name="Compressed Air System",
            created_at=now_utc()
        ).model_dump(),
        System(
            id="sys-hvac",
            site_id="demo-site-001",
            name="Building HVAC",
            created_at=now_utc()
        ).model_dump()
    ]


def get_demo_assets() -> List[Dict[str, Any]]:
    """Create demo assets."""
    return [
        Asset(
            id="asset-comp-001",
            system_id="sys-compressed-air",
            name="Main Compressor A",
            asset_class=AssetClass.COMPRESSOR,
            criticality_score=85,
            estimated_repair_cost=6000,
            created_at=now_utc()
        ).model_dump(),
        Asset(
            id="asset-comp-002",
            system_id="sys-compressed-air",
            name="Backup Compressor B",
            asset_class=AssetClass.COMPRESSOR,
            criticality_score=45,
            created_at=now_utc()
        ).model_dump(),
        Asset(
            id="asset-ahu-001",
            system_id="sys-hvac",
            name="Air Handling Unit 1",
            asset_class=AssetClass.HVAC,
            criticality_score=60,
            created_at=now_utc()
        ).model_dump()
    ]


def get_default_rules() -> List[Dict[str, Any]]:
    """
    Create V1 default rules.
    
    These are the threshold definitions for state detection.
    """
    rules = []
    
    # Energy states
    rules.append(Rule(
        id="rule-energy-drift",
        name="Energy Drift Detection",
        description="Detect sustained energy consumption above baseline",
        state_family=StateFamily.ENERGY,
        state_type="DRIFT",
        metric_type="energy_intensity",
        operator="gt",
        threshold_multiplier=1.15,  # >15% above baseline
        duration_threshold_minutes=30,
        severity_base=4,
        is_active=True,
        created_at=now_utc()
    ).model_dump())
    
    rules.append(Rule(
        id="rule-energy-spike",
        name="Energy Spike Detection",
        description="Detect sudden energy consumption spike",
        state_family=StateFamily.ENERGY,
        state_type="SPIKE",
        metric_type="energy_intensity",
        operator="gt",
        threshold_multiplier=1.40,  # >40% above baseline
        duration_threshold_minutes=5,
        severity_base=5,
        is_active=True,
        created_at=now_utc()
    ).model_dump())
    
    rules.append(Rule(
        id="rule-energy-overconsumption",
        name="Overconsumption Detection",
        description="Detect prolonged overconsumption",
        state_family=StateFamily.ENERGY,
        state_type="OVERCONSUMPTION",
        metric_type="energy_intensity",
        operator="gt",
        threshold_multiplier=1.25,  # >25% above baseline
        duration_threshold_minutes=240,  # 4 hours
        severity_base=5,
        is_active=True,
        created_at=now_utc()
    ).model_dump())
    
    rules.append(Rule(
        id="rule-energy-underutil",
        name="Underutilisation Detection",
        description="Detect low load factor",
        state_family=StateFamily.ENERGY,
        state_type="UNDERUTILISATION",
        metric_type="load_factor",
        operator="lt",
        threshold_multiplier=0.60,  # <60% of baseline
        duration_threshold_minutes=60,
        severity_base=3,
        is_active=True,
        created_at=now_utc()
    ).model_dump())
    
    # Maintenance states
    rules.append(Rule(
        id="rule-maint-degrading",
        name="Degradation Detection",
        description="Detect equipment degradation via vibration",
        state_family=StateFamily.MAINTENANCE,
        state_type="DEGRADING",
        metric_type="vibration",
        operator="gt",
        threshold_multiplier=1.20,  # >20% above baseline
        duration_threshold_minutes=120,  # 2 hours
        severity_base=5,
        is_active=True,
        created_at=now_utc()
    ).model_dump())
    
    rules.append(Rule(
        id="rule-maint-alert",
        name="Maintenance Alert",
        description="High vibration alert",
        state_family=StateFamily.MAINTENANCE,
        state_type="ALERT",
        metric_type="vibration",
        operator="gt",
        threshold_multiplier=1.50,  # >50% above baseline
        duration_threshold_minutes=30,
        severity_base=6,
        is_active=True,
        created_at=now_utc()
    ).model_dump())
    
    return rules


def generate_demo_signals(
    asset_id: str = "asset-comp-001",
    hours_normal: int = 24,
    hours_drift: int = 3,
    hours_post_intervention: int = 5,
    baseline_value: float = 45.0
) -> List[Dict[str, Any]]:
    """
    Generate simulated signal data for demo scenario.
    
    Timeline:
    1. Normal operation (establish baseline)
    2. Drift begins (elevated consumption)
    3. Post-intervention (return to normal)
    
    Args:
        asset_id: Asset to generate signals for
        hours_normal: Hours of normal operation
        hours_drift: Hours of drift condition
        hours_post_intervention: Hours after intervention
        baseline_value: Normal energy consumption (kWh/hr)
        
    Returns:
        List of signal dicts ready for ingestion
    """
    signals = []
    base_time = now_utc() - timedelta(hours=hours_normal + hours_drift + hours_post_intervention)
    
    # Phase 1: Normal operation (establish baseline)
    for i in range(hours_normal * 4):  # 15-min intervals
        timestamp = base_time + timedelta(minutes=i * 15)
        value = baseline_value + random.uniform(-2, 2)  # Normal variance
        
        signals.append({
            "asset_id": asset_id,
            "signal_type": "energy_consumption",
            "value": round(value, 2),
            "unit": "kWh",
            "timestamp": timestamp,
            "quality": "GOOD"
        })
    
    # Phase 2: Drift condition
    drift_start = base_time + timedelta(hours=hours_normal)
    drift_value = baseline_value * 1.20  # 20% above baseline
    
    for i in range(hours_drift * 4):
        timestamp = drift_start + timedelta(minutes=i * 15)
        value = drift_value + random.uniform(-1, 3)  # Elevated with variance
        
        signals.append({
            "asset_id": asset_id,
            "signal_type": "energy_consumption",
            "value": round(value, 2),
            "unit": "kWh",
            "timestamp": timestamp,
            "quality": "GOOD"
        })
    
    # Phase 3: Post-intervention (return to normal)
    post_start = drift_start + timedelta(hours=hours_drift)
    
    for i in range(hours_post_intervention * 4):
        timestamp = post_start + timedelta(minutes=i * 15)
        value = baseline_value + random.uniform(-2, 2)  # Back to normal
        
        signals.append({
            "asset_id": asset_id,
            "signal_type": "energy_consumption",
            "value": round(value, 2),
            "unit": "kWh",
            "timestamp": timestamp,
            "quality": "GOOD"
        })
    
    return signals


async def seed_demo_data(db):
    """
    Seed the database with demo data.
    
    This creates:
    - Organisation
    - Site with economic config
    - Systems
    - Assets
    - Default rules
    """
    # Clear existing demo data
    await db.organisations.delete_many({"id": "demo-org-001"})
    await db.sites.delete_many({"id": "demo-site-001"})
    await db.systems.delete_many({"site_id": "demo-site-001"})
    await db.assets.delete_many({"system_id": {"$in": ["sys-compressed-air", "sys-hvac"]}})
    await db.rules.delete_many({})  # Clear all rules for clean start
    
    # Insert demo data
    org = get_demo_organisation()
    org["created_at"] = org["created_at"].isoformat()
    await db.organisations.insert_one(org)
    
    site = get_demo_site()
    site["created_at"] = site["created_at"].isoformat()
    await db.sites.insert_one(site)
    
    for system in get_demo_systems():
        system["created_at"] = system["created_at"].isoformat()
        await db.systems.insert_one(system)
    
    for asset in get_demo_assets():
        asset["created_at"] = asset["created_at"].isoformat()
        await db.assets.insert_one(asset)
    
    for rule in get_default_rules():
        rule["created_at"] = rule["created_at"].isoformat()
        await db.rules.insert_one(rule)
    
    return {
        "organisation": "demo-org-001",
        "site": "demo-site-001",
        "systems": ["sys-compressed-air", "sys-hvac"],
        "assets": ["asset-comp-001", "asset-comp-002", "asset-ahu-001"],
        "rules": 6
    }
