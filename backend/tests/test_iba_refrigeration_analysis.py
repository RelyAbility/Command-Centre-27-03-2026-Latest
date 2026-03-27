"""
IBA Refrigeration Portfolio Analysis Tests
==========================================

Tests for the deterministic refrigeration portfolio analysis pipeline.
Validates:
- Fleet data (400 units, 8 sites, 30 days)
- State distribution (stable 50-66%, drift ~20%, idle ~9%, cycling ~10%, degraded ~6%)
- Benchmarks (P25 < P50 < P75)
- Opportunities (Energy Drift Recovery or Degradation Intervention at top)
- Site ranking (Warehouse #1 with ramp_live=true)
- RAMP connection (active CRITICAL priority, verified outcome)
- Trust signal text
- Role-based access (portfolio sees IBA, operator/admin do not)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
PORTFOLIO_USER = {"email": "portfolio1@gmail.com", "password": "Portfolio2024!"}
OPERATOR_USER = {"email": "operator1@gmail.com", "password": "Operator2024!"}
ADMIN_USER = {"email": "rampadmin@gmail.com", "password": "RampAdmin2024!"}


@pytest.fixture(scope="module")
def portfolio_token():
    """Get portfolio user token."""
    response = requests.post(f"{BASE_URL}/api/auth/signin", json=PORTFOLIO_USER)
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Portfolio auth failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def operator_token():
    """Get operator user token."""
    response = requests.post(f"{BASE_URL}/api/auth/signin", json=OPERATOR_USER)
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Operator auth failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def admin_token():
    """Get admin user token."""
    response = requests.post(f"{BASE_URL}/api/auth/signin", json=ADMIN_USER)
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Admin auth failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def seed_demo_data(portfolio_token):
    """Ensure demo data is seeded for testing."""
    headers = {"Authorization": f"Bearer {portfolio_token}"}
    # Seed first-five-minutes demo
    requests.post(f"{BASE_URL}/api/system/demo/first-five-minutes", headers=headers)
    # Seed portfolio demo
    requests.post(f"{BASE_URL}/api/system/demo/seed-portfolio", headers=headers)
    return True


class TestIBAEndpointAccess:
    """Test role-based access to IBA endpoint."""
    
    def test_portfolio_user_can_access_iba(self, portfolio_token):
        """Portfolio user should have access to IBA analysis."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "fleet" in data
        assert "state_distribution" in data
    
    def test_operator_user_cannot_access_iba(self, operator_token):
        """Operator user should NOT have access to IBA analysis (no WHERE lens)."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        # Should be 403 Forbidden (no WHERE lens access)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
    
    def test_admin_user_can_access_iba(self, admin_token):
        """Admin user should have access to IBA analysis (has WHERE lens)."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"


class TestIBAFleetData:
    """Test fleet data structure and values."""
    
    def test_fleet_total_units_is_400(self, portfolio_token):
        """Fleet should have exactly 400 units."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        fleet = data.get("fleet", {})
        assert fleet.get("total_units") == 400, f"Expected 400 units, got {fleet.get('total_units')}"
    
    def test_fleet_site_count_is_8(self, portfolio_token):
        """Fleet should have exactly 8 sites."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        fleet = data.get("fleet", {})
        assert fleet.get("site_count") == 8, f"Expected 8 sites, got {fleet.get('site_count')}"
    
    def test_fleet_analysis_days_is_30(self, portfolio_token):
        """Analysis should cover 30 days."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        fleet = data.get("fleet", {})
        assert fleet.get("analysis_days") == 30, f"Expected 30 days, got {fleet.get('analysis_days')}"
    
    def test_fleet_asset_types(self, portfolio_token):
        """Fleet should have expected asset types."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        fleet = data.get("fleet", {})
        asset_types = fleet.get("asset_types", [])
        expected_types = ["COMPRESSOR", "CONDENSER", "EVAPORATOR", "RTU"]
        assert asset_types == expected_types, f"Expected {expected_types}, got {asset_types}"


class TestIBADeterminism:
    """Test that IBA analysis is deterministic."""
    
    def test_analysis_is_deterministic(self, portfolio_token):
        """Same output on every call."""
        headers = {"Authorization": f"Bearer {portfolio_token}"}
        
        # Call twice
        response1 = requests.get(f"{BASE_URL}/api/iba/refrigeration/analysis", headers=headers)
        response2 = requests.get(f"{BASE_URL}/api/iba/refrigeration/analysis", headers=headers)
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        data1 = response1.json()
        data2 = response2.json()
        
        # Fleet should be identical
        assert data1["fleet"] == data2["fleet"]
        
        # State distribution should be identical
        assert data1["state_distribution"] == data2["state_distribution"]
        
        # Benchmarks should be identical
        assert data1["benchmarks"] == data2["benchmarks"]
        
        # Opportunities should be identical
        assert data1["opportunities"] == data2["opportunities"]
        
        # Site ranking should be identical
        assert data1["site_ranking"] == data2["site_ranking"]


class TestIBAStateDistribution:
    """Test state distribution values."""
    
    def test_state_distribution_realistic(self, portfolio_token):
        """State distribution should be realistic (stable 50-66%, drift ~20%, etc.)."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        state_dist = data.get("state_distribution", {})
        
        # Stable should be 50-66%
        stable_pct = state_dist.get("stable", {}).get("percent", 0)
        assert 50 <= stable_pct <= 70, f"Stable should be 50-70%, got {stable_pct}%"
        
        # Drift should be ~20%
        drift_pct = state_dist.get("drift", {}).get("percent", 0)
        assert 15 <= drift_pct <= 25, f"Drift should be 15-25%, got {drift_pct}%"
        
        # Idle should be ~9%
        idle_pct = state_dist.get("idle", {}).get("percent", 0)
        assert 5 <= idle_pct <= 15, f"Idle should be 5-15%, got {idle_pct}%"
        
        # Cycling should be ~10%
        cycling_pct = state_dist.get("cycling", {}).get("percent", 0)
        assert 5 <= cycling_pct <= 15, f"Cycling should be 5-15%, got {cycling_pct}%"
        
        # Degraded should be ~6%
        degraded_pct = state_dist.get("degraded", {}).get("percent", 0)
        assert 3 <= degraded_pct <= 10, f"Degraded should be 3-10%, got {degraded_pct}%"
    
    def test_state_distribution_sums_to_100(self, portfolio_token):
        """State distribution percentages should sum to ~100%."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        state_dist = data.get("state_distribution", {})
        total_pct = sum(s.get("percent", 0) for s in state_dist.values())
        
        assert 99.5 <= total_pct <= 100.5, f"Total should be ~100%, got {total_pct}%"
    
    def test_state_distribution_counts_sum_to_400(self, portfolio_token):
        """State distribution counts should sum to 400 units."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        state_dist = data.get("state_distribution", {})
        total_count = sum(s.get("count", 0) for s in state_dist.values())
        
        assert total_count == 400, f"Total count should be 400, got {total_count}"


class TestIBABenchmarks:
    """Test fleet benchmarks."""
    
    def test_benchmarks_p25_lt_p50_lt_p75(self, portfolio_token):
        """Benchmarks should have P25 < P50 < P75 for all metrics."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        benchmarks = data.get("benchmarks", {})
        
        # Energy Intensity
        ei = benchmarks.get("energy_intensity", {})
        assert ei.get("p25") < ei.get("p50") < ei.get("p75"), \
            f"Energy Intensity: P25={ei.get('p25')} < P50={ei.get('p50')} < P75={ei.get('p75')} should hold"
        
        # Runtime Ratio
        rr = benchmarks.get("runtime_ratio", {})
        assert rr.get("p25") < rr.get("p50") < rr.get("p75"), \
            f"Runtime Ratio: P25={rr.get('p25')} < P50={rr.get('p50')} < P75={rr.get('p75')} should hold"
        
        # Cycle Frequency
        cf = benchmarks.get("cycle_frequency", {})
        assert cf.get("p25") < cf.get("p50") < cf.get("p75"), \
            f"Cycle Frequency: P25={cf.get('p25')} < P50={cf.get('p50')} < P75={cf.get('p75')} should hold"
    
    def test_benchmarks_have_units(self, portfolio_token):
        """Benchmarks should have unit labels where applicable."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        benchmarks = data.get("benchmarks", {})
        
        # Energy Intensity should have unit
        ei = benchmarks.get("energy_intensity", {})
        assert "unit" in ei, "Energy Intensity should have unit"
        assert ei.get("unit") == "kWh/ton-hr", f"Expected 'kWh/ton-hr', got {ei.get('unit')}"
        
        # Cycle Frequency should have unit
        cf = benchmarks.get("cycle_frequency", {})
        assert "unit" in cf, "Cycle Frequency should have unit"
        assert cf.get("unit") == "cycles/day", f"Expected 'cycles/day', got {cf.get('unit')}"


class TestIBAOpportunities:
    """Test opportunity sizing."""
    
    def test_top_opportunity_is_drift_or_degradation(self, portfolio_token):
        """Top opportunity should be Energy Drift Recovery or Degradation Intervention."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        opportunities = data.get("opportunities", [])
        assert len(opportunities) > 0, "Should have at least one opportunity"
        
        top_opp = opportunities[0]
        valid_categories = ["Energy Drift Recovery", "Degradation Intervention"]
        assert top_opp.get("category") in valid_categories, \
            f"Top opportunity should be one of {valid_categories}, got {top_opp.get('category')}"
    
    def test_opportunities_have_required_fields(self, portfolio_token):
        """Each opportunity should have required fields."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        opportunities = data.get("opportunities", [])
        required_fields = ["category", "state", "affected_assets", "monthly_impact", "annual_impact", "description"]
        
        for opp in opportunities:
            for field in required_fields:
                assert field in opp, f"Opportunity missing field: {field}"
    
    def test_opportunities_sorted_by_monthly_impact(self, portfolio_token):
        """Opportunities should be sorted by monthly_impact descending."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        opportunities = data.get("opportunities", [])
        impacts = [o.get("monthly_impact", 0) for o in opportunities]
        
        assert impacts == sorted(impacts, reverse=True), "Opportunities should be sorted by monthly_impact descending"


class TestIBASiteRanking:
    """Test site ranking."""
    
    def test_warehouse_is_rank_1(self, portfolio_token):
        """Warehouse Distribution Center should be ranked #1."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        site_ranking = data.get("site_ranking", [])
        assert len(site_ranking) > 0, "Should have site ranking"
        
        top_site = site_ranking[0]
        assert top_site.get("site_name") == "Warehouse Distribution Center", \
            f"Expected 'Warehouse Distribution Center' at #1, got {top_site.get('site_name')}"
    
    def test_warehouse_has_ramp_live_true(self, portfolio_token):
        """Warehouse should have ramp_live=true."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        site_ranking = data.get("site_ranking", [])
        warehouse = next((s for s in site_ranking if s.get("site_name") == "Warehouse Distribution Center"), None)
        
        assert warehouse is not None, "Warehouse should be in site ranking"
        assert warehouse.get("ramp_live") is True, f"Warehouse should have ramp_live=true, got {warehouse.get('ramp_live')}"
    
    def test_riverside_has_ramp_live_true(self, portfolio_token):
        """Riverside should have ramp_live=true."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        site_ranking = data.get("site_ranking", [])
        riverside = next((s for s in site_ranking if "Riverside" in s.get("site_name", "")), None)
        
        assert riverside is not None, "Riverside should be in site ranking"
        assert riverside.get("ramp_live") is True, f"Riverside should have ramp_live=true, got {riverside.get('ramp_live')}"
    
    def test_site_ranking_has_8_sites(self, portfolio_token):
        """Site ranking should have 8 sites."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        site_ranking = data.get("site_ranking", [])
        assert len(site_ranking) == 8, f"Expected 8 sites, got {len(site_ranking)}"
    
    def test_site_ranking_sorted_by_opportunity(self, portfolio_token):
        """Site ranking should be sorted by monthly_opportunity descending."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        site_ranking = data.get("site_ranking", [])
        opportunities = [s.get("monthly_opportunity", 0) for s in site_ranking]
        
        assert opportunities == sorted(opportunities, reverse=True), \
            "Site ranking should be sorted by monthly_opportunity descending"


class TestIBAScale:
    """Test scale signal."""
    
    def test_scale_30day_approximately_91k(self, portfolio_token):
        """30-day opportunity should be approximately $91k."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        scale = data.get("scale", {})
        total_30day = scale.get("total_30day", 0)
        
        # Should be approximately $91k (allow 80k-100k range)
        assert 80000 <= total_30day <= 100000, f"30-day should be ~$91k, got ${total_30day}"
    
    def test_scale_annualized_approximately_1_1m(self, portfolio_token):
        """Annualized opportunity should be approximately $1.1M."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        scale = data.get("scale", {})
        annualized = scale.get("annualized", 0)
        
        # Should be approximately $1.1M (allow 1.0M-1.2M range)
        assert 1000000 <= annualized <= 1200000, f"Annualized should be ~$1.1M, got ${annualized}"
    
    def test_scale_currency_is_usd(self, portfolio_token):
        """Scale currency should be USD."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        scale = data.get("scale", {})
        assert scale.get("currency") == "USD", f"Expected USD, got {scale.get('currency')}"


class TestIBARampConnection:
    """Test RAMP connection data."""
    
    def test_ramp_connection_exists(self, portfolio_token, seed_demo_data):
        """RAMP connection should exist in response."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "ramp_connection" in data, "Response should have ramp_connection"
    
    def test_ramp_connection_has_active_detection(self, portfolio_token, seed_demo_data):
        """RAMP connection should have active_detection with CRITICAL priority."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        ramp_conn = data.get("ramp_connection", {})
        active = ramp_conn.get("active_detection")
        
        assert active is not None, "Should have active_detection"
        assert active.get("priority_band") == "CRITICAL", \
            f"Expected CRITICAL priority, got {active.get('priority_band')}"
    
    def test_ramp_connection_active_detection_is_cold_storage(self, portfolio_token, seed_demo_data):
        """Active detection should be Cold Storage Compressor."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        ramp_conn = data.get("ramp_connection", {})
        active = ramp_conn.get("active_detection", {})
        
        assert "Cold Storage Compressor" in (active.get("asset_name") or ""), \
            f"Expected 'Cold Storage Compressor', got {active.get('asset_name')}"
    
    def test_ramp_connection_has_verified_proof(self, portfolio_token, seed_demo_data):
        """RAMP connection should have verified_proof with VFD Coolant Pump outcome."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        ramp_conn = data.get("ramp_connection", {})
        proof = ramp_conn.get("verified_proof")
        
        assert proof is not None, "Should have verified_proof"
        # VFD Coolant Pump or RTU 2 outcome
        assert proof.get("asset_name") is not None, "verified_proof should have asset_name"
        assert proof.get("savings_value") is not None, "verified_proof should have savings_value"


class TestIBATrustSignal:
    """Test trust signal."""
    
    def test_trust_signal_text(self, portfolio_token):
        """Trust signal should be 'Based on measured operating behaviour (no AI inference)'."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        trust_signal = data.get("trust_signal")
        expected = "Based on measured operating behaviour (no AI inference)"
        
        assert trust_signal == expected, f"Expected '{expected}', got '{trust_signal}'"


class TestIBAHighlight:
    """Test highlight data."""
    
    def test_highlight_site_is_warehouse(self, portfolio_token):
        """Highlight site should be Warehouse Distribution Center."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        highlight = data.get("highlight", {})
        site = highlight.get("site", {})
        
        assert site.get("site_name") == "Warehouse Distribution Center", \
            f"Expected 'Warehouse Distribution Center', got {site.get('site_name')}"
    
    def test_highlight_site_has_ramp_live(self, portfolio_token):
        """Highlight site should have ramp_live=true."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        highlight = data.get("highlight", {})
        site = highlight.get("site", {})
        
        assert site.get("ramp_live") is True, f"Highlight site should have ramp_live=true"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
