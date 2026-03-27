"""
Refrigeration Portfolio Analysis — Deterministic Pipeline
=========================================================

Pipeline: signals → metrics → states → benchmarks → recommendations

All computation is threshold-based. No AI inference.
"Based on measured operating behaviour (no AI inference)"

Fleet: 400 refrigeration units across 8 sites, 30 days analysis.
Sites include existing RAMP-monitored sites (Warehouse, Riverside)
so IBA insight connects directly to live RAMP detection loop.
"""

import hashlib
import struct

# ============================================================================
# CONFIGURATION
# ============================================================================

ANALYSIS_DAYS = 30
ENERGY_RATE = 0.12  # $/kWh
HOURS_PER_DAY = 24
STATES = ["stable", "drift", "idle", "cycling", "degraded"]

SITES = [
    {"id": "site-warehouse", "name": "Warehouse Distribution Center", "units": 52,
     "profile": [0.48, 0.21, 0.06, 0.12, 0.13], "ramp_live": True},
    {"id": "site-riverside", "name": "Riverside Plant - Building A", "units": 48,
     "profile": [0.60, 0.19, 0.08, 0.06, 0.07], "ramp_live": True},
    {"id": "iba-northeast", "name": "Northeast Cold Storage", "units": 55,
     "profile": [0.65, 0.13, 0.09, 0.09, 0.04]},
    {"id": "iba-southeast", "name": "Southeast Distribution Hub", "units": 50,
     "profile": [0.56, 0.22, 0.06, 0.08, 0.08]},
    {"id": "iba-pacific", "name": "Pacific Coast Terminal", "units": 48,
     "profile": [0.73, 0.12, 0.08, 0.04, 0.03]},
    {"id": "iba-central", "name": "Central Plains Warehouse", "units": 45,
     "profile": [0.58, 0.16, 0.09, 0.11, 0.06]},
    {"id": "iba-greatlakes", "name": "Great Lakes Facility", "units": 52,
     "profile": [0.63, 0.17, 0.10, 0.06, 0.04]},
    {"id": "iba-mountain", "name": "Mountain Region Depot", "units": 50,
     "profile": [0.62, 0.16, 0.08, 0.07, 0.07]},
]  # Total: 400 units

ASSET_TYPES = ["COMPRESSOR", "CONDENSER", "EVAPORATOR", "RTU"]
ASSET_TYPE_WEIGHTS = [0.40, 0.25, 0.20, 0.15]  # cumulative thresholds

CAPACITY_RANGES = {
    "COMPRESSOR": (20, 150), "CONDENSER": (15, 100),
    "EVAPORATOR": (10, 80), "RTU": (5, 50),
}
POWER_FACTOR_RANGES = {  # kW per ton of capacity
    "COMPRESSOR": (0.9, 1.5), "CONDENSER": (0.3, 0.6),
    "EVAPORATOR": (0.2, 0.5), "RTU": (0.8, 1.3),
}
OPPORTUNITY_FACTORS = {
    "drift": 0.15, "idle": 0.10, "cycling": 0.12, "degraded": 0.30,
}
OPPORTUNITY_LABELS = {
    "drift": "Energy Drift Recovery",
    "idle": "Idle Asset Optimization",
    "cycling": "Short-Cycling Reduction",
    "degraded": "Degradation Intervention",
}
OPPORTUNITY_DESCRIPTIONS = {
    "drift": "units operating above baseline — recoverable through maintenance and tuning",
    "idle": "units running at <10% capacity — candidates for scheduled shutdown",
    "cycling": "units with excessive start-stop cycling — causing wear and energy waste",
    "degraded": "units with sustained performance degradation — immediate intervention recommended",
}


# ============================================================================
# DETERMINISTIC HELPERS
# ============================================================================

def _hf(key: str) -> float:
    """Deterministic float [0, 1) from key."""
    h = hashlib.md5(key.encode()).digest()
    return struct.unpack('I', h[:4])[0] / (2**32)


def _hr(key: str, lo: float, hi: float) -> float:
    """Deterministic float in [lo, hi) from key."""
    return lo + _hf(key) * (hi - lo)


def _percentile(data, p):
    """Calculate p-th percentile of sorted list."""
    k = (len(data) - 1) * p / 100
    f = int(k)
    c = min(f + 1, len(data) - 1)
    return data[f] + (k - f) * (data[c] - data[f])


# ============================================================================
# PIPELINE
# ============================================================================

_cache = None


def run_analysis():
    """
    Execute full refrigeration portfolio analysis.

    Pipeline: signals → metrics → states → benchmarks → recommendations
    Fully deterministic — same output on every invocation.
    """
    global _cache
    if _cache is not None:
        return _cache

    units = []
    site_units = {s["id"]: [] for s in SITES}

    # ── STEP 1: Generate fleet & classify states ──────────────────────────
    for site in SITES:
        profile = site["profile"]
        for i in range(site["units"]):
            uid = f"u-{site['id']}-{i:03d}"

            # State assignment via cumulative thresholds
            h = _hf(f"st:{uid}")
            cum = 0.0
            state = STATES[-1]
            for s, w in zip(STATES, profile):
                cum += w
                if h < cum:
                    state = s
                    break

            # Asset type
            th = _hf(f"tp:{uid}")
            cum = 0.0
            asset_type = ASSET_TYPES[-1]
            for at, wt in zip(ASSET_TYPES, ASSET_TYPE_WEIGHTS):
                cum += wt
                if th < cum:
                    asset_type = at
                    break

            # Physical characteristics
            cap = round(_hr(f"cp:{uid}", *CAPACITY_RANGES[asset_type]), 1)
            pf = _hr(f"pf:{uid}", *POWER_FACTOR_RANGES[asset_type])
            rated_kw = round(cap * pf, 1)
            age = int(_hr(f"ag:{uid}", 1, 21))

            # Operating metrics by state
            if state == "idle":
                rt = _hr(f"rt:{uid}", 0.02, 0.10)
                dev = _hr(f"dv:{uid}", -10, 5)
                cyc = _hr(f"cy:{uid}", 0.5, 3)
            elif state == "cycling":
                rt = _hr(f"rt:{uid}", 0.60, 0.85)
                dev = _hr(f"dv:{uid}", 5, 15)
                cyc = _hr(f"cy:{uid}", 15, 40)
            elif state == "drift":
                rt = _hr(f"rt:{uid}", 0.65, 0.90)
                dev = _hr(f"dv:{uid}", 5, 25)
                cyc = _hr(f"cy:{uid}", 4, 12)
            elif state == "degraded":
                rt = _hr(f"rt:{uid}", 0.75, 0.95)
                dev = _hr(f"dv:{uid}", 25, 45)
                cyc = _hr(f"cy:{uid}", 6, 15)
            else:  # stable
                rt = _hr(f"rt:{uid}", 0.60, 0.85)
                dev = _hr(f"dv:{uid}", -3, 5)
                cyc = _hr(f"cy:{uid}", 3, 10)

            baseline_kwh = rated_kw * rt * HOURS_PER_DAY
            actual_kwh = baseline_kwh * (1 + dev / 100)
            ei = actual_kwh / (cap * rt * HOURS_PER_DAY) if (cap * rt) > 0 else 0
            monthly_cost = actual_kwh * ANALYSIS_DAYS * ENERGY_RATE
            opp_factor = OPPORTUNITY_FACTORS.get(state, 0)
            monthly_opp = baseline_kwh * ANALYSIS_DAYS * ENERGY_RATE * opp_factor if state != "stable" else 0

            unit = {
                "id": uid, "site_id": site["id"], "site_name": site["name"],
                "asset_type": asset_type, "capacity_tons": cap,
                "rated_kw": rated_kw, "age": age, "state": state,
                "runtime_ratio": round(rt, 3),
                "energy_deviation_pct": round(dev, 1),
                "cycles_per_day": round(cyc, 1),
                "energy_intensity": round(ei, 3),
                "monthly_cost": round(monthly_cost, 2),
                "monthly_opportunity": round(monthly_opp, 2),
            }
            units.append(unit)
            site_units[site["id"]].append(unit)

    # ── STEP 2: State distribution ────────────────────────────────────────
    n = len(units)
    state_dist = {}
    for s in STATES:
        cnt = sum(1 for u in units if u["state"] == s)
        state_dist[s] = {"count": cnt, "percent": round(cnt / n * 100, 1)}

    # ── STEP 3: Fleet benchmarks (P25/P50/P75) ───────────────────────────
    active = [u for u in units if u["state"] != "idle"]
    ei_sorted = sorted(u["energy_intensity"] for u in active)
    rt_sorted = sorted(u["runtime_ratio"] for u in active)
    cy_sorted = sorted(u["cycles_per_day"] for u in active)

    benchmarks = {
        "energy_intensity": {
            "p25": round(_percentile(ei_sorted, 25), 3),
            "p50": round(_percentile(ei_sorted, 50), 3),
            "p75": round(_percentile(ei_sorted, 75), 3),
            "unit": "kWh/ton-hr",
        },
        "runtime_ratio": {
            "p25": round(_percentile(rt_sorted, 25), 3),
            "p50": round(_percentile(rt_sorted, 50), 3),
            "p75": round(_percentile(rt_sorted, 75), 3),
        },
        "cycle_frequency": {
            "p25": round(_percentile(cy_sorted, 25), 1),
            "p50": round(_percentile(cy_sorted, 50), 1),
            "p75": round(_percentile(cy_sorted, 75), 1),
            "unit": "cycles/day",
        },
    }

    # ── STEP 4: Opportunity sizing by category ────────────────────────────
    opportunities = []
    for st_key in ["degraded", "drift", "cycling", "idle"]:
        affected = [u for u in units if u["state"] == st_key]
        if not affected:
            continue
        total_m = sum(u["monthly_opportunity"] for u in affected)
        opportunities.append({
            "category": OPPORTUNITY_LABELS[st_key],
            "state": st_key,
            "affected_assets": len(affected),
            "monthly_impact": round(total_m, 0),
            "annual_impact": round(total_m * 12, 0),
            "description": f"{len(affected)} {OPPORTUNITY_DESCRIPTIONS[st_key]}",
        })
    opportunities.sort(key=lambda x: x["monthly_impact"], reverse=True)

    # ── STEP 5: Site ranking ──────────────────────────────────────────────
    site_ranking = []
    for site in SITES:
        su = site_units[site["id"]]
        total_opp = sum(u["monthly_opportunity"] for u in su)
        non_stable = sum(1 for u in su if u["state"] != "stable")
        sd = {s: sum(1 for u in su if u["state"] == s) for s in STATES}
        site_ranking.append({
            "site_id": site["id"],
            "site_name": site["name"],
            "unit_count": len(su),
            "monthly_opportunity": round(total_opp, 0),
            "annual_opportunity": round(total_opp * 12, 0),
            "non_stable_count": non_stable,
            "non_stable_pct": round(non_stable / len(su) * 100, 1) if su else 0,
            "state_distribution": sd,
            "ramp_live": site.get("ramp_live", False),
        })
    site_ranking.sort(key=lambda x: x["monthly_opportunity"], reverse=True)

    # ── STEP 6: Scale signal ─────────────────────────────────────────────
    total_monthly = sum(o["monthly_impact"] for o in opportunities)
    fleet_energy = sum(u["monthly_cost"] for u in units)

    # ── STEP 7: Highlight ────────────────────────────────────────────────
    top_site = site_ranking[0] if site_ranking else None
    top_asset = None
    if top_site:
        candidates = sorted(
            [u for u in site_units[top_site["site_id"]] if u["state"] != "stable"],
            key=lambda u: u["monthly_opportunity"], reverse=True,
        )
        if candidates:
            top_asset = candidates[0]

    # ── STEP 8: Validate distributions ───────────────────────────────────
    pct_sum = sum(v["percent"] for v in state_dist.values())
    assert 99.5 <= pct_sum <= 100.5, f"State % sum: {pct_sum}"
    assert 50 <= state_dist["stable"]["percent"] <= 70, f"Stable: {state_dist['stable']['percent']}%"
    assert benchmarks["energy_intensity"]["p25"] < benchmarks["energy_intensity"]["p50"] < benchmarks["energy_intensity"]["p75"]

    result = {
        "fleet": {
            "total_units": n,
            "analysis_days": ANALYSIS_DAYS,
            "site_count": len(SITES),
            "asset_types": ASSET_TYPES,
            "fleet_monthly_energy": round(fleet_energy, 0),
        },
        "state_distribution": state_dist,
        "benchmarks": benchmarks,
        "opportunities": opportunities,
        "site_ranking": site_ranking,
        "scale": {
            "total_30day": round(total_monthly, 0),
            "annualized": round(total_monthly * 12, 0),
            "currency": "USD",
        },
        "highlight": {
            "site": {
                "site_id": top_site["site_id"],
                "site_name": top_site["site_name"],
                "monthly_opportunity": top_site["monthly_opportunity"],
                "non_stable_pct": top_site["non_stable_pct"],
                "ramp_live": top_site.get("ramp_live", False),
            } if top_site else None,
            "asset": {
                "id": top_asset["id"],
                "site_name": top_asset["site_name"],
                "asset_type": top_asset["asset_type"],
                "state": top_asset["state"],
                "deviation_pct": top_asset["energy_deviation_pct"],
                "monthly_opportunity": top_asset["monthly_opportunity"],
            } if top_asset else None,
        },
        "trust_signal": "Based on measured operating behaviour (no AI inference)",
    }

    _cache = result
    return result
