"""
Iteration 14: Scaled Economics & Single-Industry Narrative Tests
================================================================

Tests for P0 'Demo Refinement — Rockwell Readiness' pass:
1. Scale economics to enterprise level ($10k-50k/day per site, $5-25M/yr portfolio)
2. Single-industry narrative (all food processing/dairy/refrigeration — no chemical, glass, pharma)
3. Strengthen verified outcomes with annualized financial terms and fleet-scale replication
4. Add benchmark interpretation (P75 = top quartile inefficiency, etc.)
5. Strengthen Portfolio→Action→Outcome narrative ('Detected → prioritised → resolved → verified → scaled')
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://industrial-demo-1.preview.emergentagent.com')

# Test credentials
PORTFOLIO_CREDS = {"email": "portfolio1@gmail.com", "password": "Portfolio2024!"}
OPERATOR_CREDS = {"email": "operator1@gmail.com", "password": "Operator2024!"}
ADMIN_CREDS = {"email": "rampadmin@gmail.com", "password": "RampAdmin2024!"}

# Forbidden industry terms (should NOT appear in any site names)
FORBIDDEN_INDUSTRIES = ['Chemical', 'Glass', 'Pharmaceutical', 'Pharma']


@pytest.fixture(scope="module")
def portfolio_token():
    """Get portfolio user token."""
    response = requests.post(
        f"{BASE_URL}/api/auth/signin",
        json=PORTFOLIO_CREDS
    )
    assert response.status_code == 200, f"Portfolio login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def operator_token():
    """Get operator user token."""
    response = requests.post(
        f"{BASE_URL}/api/auth/signin",
        json=OPERATOR_CREDS
    )
    assert response.status_code == 200, f"Operator login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def seed_demo_data():
    """Seed demo data before tests."""
    # Seed first-five-minutes
    response = requests.post(f"{BASE_URL}/api/system/demo/first-five-minutes")
    assert response.status_code == 200, f"First-five-minutes seed failed: {response.text}"
    
    # Seed portfolio
    response = requests.post(f"{BASE_URL}/api/system/demo/seed-portfolio")
    assert response.status_code == 200, f"Seed-portfolio failed: {response.text}"
    
    return True


class TestFirstFiveMinutesScaledEconomics:
    """Test POST /api/system/demo/first-five-minutes returns scaled VaR values."""
    
    def test_first_five_minutes_returns_scaled_var(self, seed_demo_data):
        """Verify scaled VaR: Screw Compressor ~$7,560/day, Evaporator ~$2,125/day, Condenser ~$945/day."""
        response = requests.post(f"{BASE_URL}/api/system/demo/first-five-minutes")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ready"
        
        # Check current_value_at_risk breakdown
        var_breakdown = data["narrative"]["current_value_at_risk"]["breakdown"]
        
        # Find each asset's VaR
        compressor_var = next((a["var"] for a in var_breakdown if "Screw Compressor" in a["asset"]), None)
        evaporator_var = next((a["var"] for a in var_breakdown if "Evaporator" in a["asset"]), None)
        condenser_var = next((a["var"] for a in var_breakdown if "Condenser" in a["asset"]), None)
        
        # Verify scaled values (enterprise level)
        assert compressor_var is not None, "Screw Compressor VaR not found"
        assert compressor_var >= 7000, f"Screw Compressor VaR should be ~$7,560/day, got ${compressor_var}"
        assert compressor_var <= 8000, f"Screw Compressor VaR should be ~$7,560/day, got ${compressor_var}"
        
        assert evaporator_var is not None, "Evaporator VaR not found"
        assert evaporator_var >= 2000, f"Evaporator VaR should be ~$2,125/day, got ${evaporator_var}"
        assert evaporator_var <= 2500, f"Evaporator VaR should be ~$2,125/day, got ${evaporator_var}"
        
        assert condenser_var is not None, "Condenser VaR not found"
        assert condenser_var >= 800, f"Condenser VaR should be ~$945/day, got ${condenser_var}"
        assert condenser_var <= 1100, f"Condenser VaR should be ~$945/day, got ${condenser_var}"
    
    def test_first_five_minutes_total_var_enterprise_scale(self, seed_demo_data):
        """Verify total VaR is ~$10,630/day (enterprise scale)."""
        response = requests.post(f"{BASE_URL}/api/system/demo/first-five-minutes")
        assert response.status_code == 200
        
        data = response.json()
        total_var = data["narrative"]["current_value_at_risk"]["total_per_day"]
        
        # Should be around $10,630/day
        assert total_var >= 10000, f"Total VaR should be ~$10,630/day, got ${total_var}"
        assert total_var <= 11500, f"Total VaR should be ~$10,630/day, got ${total_var}"
    
    def test_completed_loop_annualized_outcome(self, seed_demo_data):
        """Verify completed_loop mentions '$34/day ($12,410/yr annualised)'."""
        response = requests.post(f"{BASE_URL}/api/system/demo/first-five-minutes")
        assert response.status_code == 200
        
        data = response.json()
        completed_loop = data["narrative"]["completed_loop"]
        outcome_text = completed_loop["outcome"]
        
        # Check for $34/day
        assert "$34" in outcome_text, f"Outcome should mention $34/day, got: {outcome_text}"
        
        # Check for annualized value
        assert "12,410" in outcome_text or "12410" in outcome_text, \
            f"Outcome should mention $12,410/yr annualised, got: {outcome_text}"
        
        # Check for 'annualised' keyword
        assert "annualised" in outcome_text.lower() or "annualized" in outcome_text.lower(), \
            f"Outcome should mention 'annualised', got: {outcome_text}"


class TestSeedPortfolioScaledPriorities:
    """Test POST /api/system/demo/seed-portfolio creates scaled priorities."""
    
    def test_seed_portfolio_creates_food_processing_facility(self, seed_demo_data):
        """Verify Food Processing Facility is created."""
        response = requests.post(f"{BASE_URL}/api/system/demo/seed-portfolio")
        assert response.status_code == 200
        
        data = response.json()
        # Check site name contains Food Processing
        assert "Food Processing" in data.get("site", ""), \
            f"Site should be Food Processing Facility, got: {data.get('site')}"


class TestIBARefrigerationAnalysis:
    """Test GET /api/iba/refrigeration/analysis returns correct scaled values."""
    
    def test_iba_returns_800k_plus_30day_opportunity(self, portfolio_token, seed_demo_data):
        """Verify $800k+ 30-day opportunity."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        total_30day = data["scale"]["total_30day"]
        
        assert total_30day >= 800000, f"30-day opportunity should be $800k+, got ${total_30day:,.0f}"
    
    def test_iba_returns_9m_plus_annualized(self, portfolio_token, seed_demo_data):
        """Verify $9M+ annualized opportunity."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        annualized = data["scale"]["annualized"]
        
        assert annualized >= 9000000, f"Annualized opportunity should be $9M+, got ${annualized:,.0f}"
    
    def test_iba_fleet_asset_type_counts(self, portfolio_token, seed_demo_data):
        """Verify fleet asset_type_counts object with correct asset types."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        asset_type_counts = data["fleet"]["asset_type_counts"]
        
        # Verify all required asset types exist
        required_types = ["Screw Compressor", "Condenser Unit", "Evaporator Bank", "Pump System"]
        for asset_type in required_types:
            assert asset_type in asset_type_counts, f"Missing asset type: {asset_type}"
            assert asset_type_counts[asset_type] > 0, f"Asset type {asset_type} should have count > 0"
    
    def test_iba_site_ranking_only_food_dairy_refrigeration(self, portfolio_token, seed_demo_data):
        """Verify site_ranking contains ONLY food/dairy/refrigeration industry sites."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        site_ranking = data["site_ranking"]
        
        for site in site_ranking:
            site_name = site["site_name"]
            # Check no forbidden industries
            for forbidden in FORBIDDEN_INDUSTRIES:
                assert forbidden.lower() not in site_name.lower(), \
                    f"Site '{site_name}' contains forbidden industry term '{forbidden}'"
    
    def test_iba_ramp_connection_verified_proof_format(self, portfolio_token, seed_demo_data):
        """Verify ramp_connection verified_proof shows savings_unit='$/day' and savings_value=34.0."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        ramp_connection = data.get("ramp_connection", {})
        verified_proof = ramp_connection.get("verified_proof", {})
        
        assert verified_proof, "ramp_connection.verified_proof should exist"
        assert verified_proof.get("savings_unit") == "$/day", \
            f"savings_unit should be '$/day', got: {verified_proof.get('savings_unit')}"
        assert verified_proof.get("savings_value") == 34.0, \
            f"savings_value should be 34.0, got: {verified_proof.get('savings_value')}"
    
    def test_iba_ramp_connection_message_contains_detected_across_portfolio(self, portfolio_token, seed_demo_data):
        """Verify ramp_connection.message contains 'Detected across portfolio assets'."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        ramp_connection = data.get("ramp_connection", {})
        message = ramp_connection.get("message", "")
        
        assert "Detected across portfolio" in message or "detected across portfolio" in message.lower(), \
            f"ramp_connection.message should contain 'Detected across portfolio assets', got: {message}"


class TestIntelligenceOutcomesOperator:
    """Test GET /api/intelligence/outcomes for operator returns correct format."""
    
    def test_outcomes_returns_savings_unit_per_day(self, operator_token, seed_demo_data):
        """Verify savings_unit='$/day' and total_savings around $34."""
        response = requests.get(
            f"{BASE_URL}/api/intelligence/outcomes",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        
        # Check total_savings
        total_savings = data.get("total_savings", 0)
        assert total_savings >= 30, f"total_savings should be around $34, got ${total_savings}"
        assert total_savings <= 60, f"total_savings should be around $34, got ${total_savings}"
        
        # Check individual outcomes have $/day unit
        outcomes = data.get("outcomes", [])
        assert len(outcomes) > 0, "Should have at least one outcome"
        
        for outcome in outcomes:
            savings_unit = outcome.get("savings_unit", "")
            assert "$/day" in savings_unit or "$" in savings_unit, \
                f"savings_unit should be '$/day', got: {savings_unit}"


class TestSingleIndustryNarrative:
    """Test that all site names are food/dairy/refrigeration industry only."""
    
    def test_no_chemical_sites_in_iba(self, portfolio_token, seed_demo_data):
        """Verify no 'Chemical' in any site name."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        site_ranking = data["site_ranking"]
        
        for site in site_ranking:
            assert "chemical" not in site["site_name"].lower(), \
                f"Found forbidden 'Chemical' in site: {site['site_name']}"
    
    def test_no_glass_sites_in_iba(self, portfolio_token, seed_demo_data):
        """Verify no 'Glass' in any site name."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        site_ranking = data["site_ranking"]
        
        for site in site_ranking:
            assert "glass" not in site["site_name"].lower(), \
                f"Found forbidden 'Glass' in site: {site['site_name']}"
    
    def test_no_pharmaceutical_sites_in_iba(self, portfolio_token, seed_demo_data):
        """Verify no 'Pharmaceutical' or 'Pharma' in any site name."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        site_ranking = data["site_ranking"]
        
        for site in site_ranking:
            site_name_lower = site["site_name"].lower()
            assert "pharmaceutical" not in site_name_lower, \
                f"Found forbidden 'Pharmaceutical' in site: {site['site_name']}"
            assert "pharma" not in site_name_lower, \
                f"Found forbidden 'Pharma' in site: {site['site_name']}"
    
    def test_all_sites_are_food_dairy_refrigeration(self, portfolio_token, seed_demo_data):
        """Verify all sites are food/dairy/refrigeration related."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        site_ranking = data["site_ranking"]
        
        # Valid industry keywords
        valid_keywords = [
            'dairy', 'food', 'meat', 'poultry', 'beverage', 'frozen', 
            'cheese', 'milk', 'seafood', 'cold', 'refrigeration', 'cooling',
            'processing', 'storage', 'distribution'
        ]
        
        for site in site_ranking:
            site_name_lower = site["site_name"].lower()
            has_valid_keyword = any(kw in site_name_lower for kw in valid_keywords)
            assert has_valid_keyword, \
                f"Site '{site['site_name']}' doesn't appear to be food/dairy/refrigeration industry"


class TestBenchmarkInterpretation:
    """Test that benchmarks have interpretation text."""
    
    def test_benchmarks_exist_in_iba(self, portfolio_token, seed_demo_data):
        """Verify benchmarks object exists with p25, p50, p75 values."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        benchmarks = data.get("benchmarks", {})
        
        # Check energy_intensity benchmark
        ei = benchmarks.get("energy_intensity", {})
        assert "p25" in ei, "energy_intensity should have p25"
        assert "p50" in ei, "energy_intensity should have p50"
        assert "p75" in ei, "energy_intensity should have p75"
        assert ei["p25"] < ei["p50"] < ei["p75"], "Benchmark values should be p25 < p50 < p75"
        
        # Check runtime_ratio benchmark
        rr = benchmarks.get("runtime_ratio", {})
        assert "p25" in rr, "runtime_ratio should have p25"
        assert "p50" in rr, "runtime_ratio should have p50"
        assert "p75" in rr, "runtime_ratio should have p75"
        
        # Check cycle_frequency benchmark
        cf = benchmarks.get("cycle_frequency", {})
        assert "p25" in cf, "cycle_frequency should have p25"
        assert "p50" in cf, "cycle_frequency should have p50"
        assert "p75" in cf, "cycle_frequency should have p75"


class TestConnectorNarrative:
    """Test the Portfolio→Action→Outcome narrative."""
    
    def test_ramp_connection_has_active_detection(self, portfolio_token, seed_demo_data):
        """Verify ramp_connection has active_detection with priority details."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        ramp_connection = data.get("ramp_connection", {})
        active_detection = ramp_connection.get("active_detection", {})
        
        assert active_detection, "ramp_connection should have active_detection"
        assert "priority_band" in active_detection, "active_detection should have priority_band"
        assert "asset_name" in active_detection, "active_detection should have asset_name"
        assert "var_per_day" in active_detection, "active_detection should have var_per_day"
    
    def test_ramp_connection_has_verified_proof(self, portfolio_token, seed_demo_data):
        """Verify ramp_connection has verified_proof with savings details."""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        ramp_connection = data.get("ramp_connection", {})
        verified_proof = ramp_connection.get("verified_proof", {})
        
        assert verified_proof, "ramp_connection should have verified_proof"
        assert "asset_name" in verified_proof, "verified_proof should have asset_name"
        assert "savings_value" in verified_proof, "verified_proof should have savings_value"
        assert "savings_unit" in verified_proof, "verified_proof should have savings_unit"
        assert "verified_at" in verified_proof, "verified_proof should have verified_at"


class TestLiveVaREnterpriseScale:
    """Test that live VaR values are enterprise-scale ($10k+/day)."""
    
    def test_portfolio_var_is_enterprise_scale(self, portfolio_token, seed_demo_data):
        """Verify portfolio VaR is $10k+/day."""
        response = requests.get(
            f"{BASE_URL}/api/where/portfolio/intelligence",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        total_var = data.get("summary", {}).get("total_var", 0)
        
        # Should be enterprise scale ($10k+/day)
        assert total_var >= 10000, f"Portfolio VaR should be $10k+/day, got ${total_var:,.0f}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
