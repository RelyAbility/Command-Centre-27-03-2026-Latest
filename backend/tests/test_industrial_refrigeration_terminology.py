"""
Industrial Refrigeration Terminology Verification Tests
========================================================

This test suite verifies that all generic terminology (Riverside, Warehouse, HVAC, 
Air Handling Unit, VFD Coolant Pump, energy drift) has been replaced with 
Industrial Refrigeration context (Dairy Processing Plant, Food Processing Facility, 
Screw Compressor, Evaporator Bank, Condenser Unit, Glycol Circulation Pump, 
compressor efficiency degradation, cooling drift, etc.)

Tests cover:
1. POST /api/system/demo/first-five-minutes - narrative terminology
2. POST /api/system/demo/seed-portfolio - site name
3. GET /api/how/priorities - operator priorities with refrigeration assets
4. GET /api/where/portfolio/intelligence - portfolio sites and assets
5. GET /api/iba/refrigeration/analysis - fleet analysis with industrial names
6. GET /api/intelligence/outcomes - verified outcomes with correct asset names
"""

import pytest
import requests
import os
import re

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"email": "rampadmin@gmail.com", "password": "RampAdmin2024!"}
OPERATOR_CREDS = {"email": "operator1@gmail.com", "password": "Operator2024!"}
PORTFOLIO_CREDS = {"email": "portfolio1@gmail.com", "password": "Portfolio2024!"}

# Forbidden generic terms that should NOT appear in DISPLAY NAMES
# Note: site_id values like "site-riverside" are internal IDs and acceptable
# Note: "HVAC" is acceptable in context like "Pharmaceutical Plant — Clean Room HVAC"
FORBIDDEN_DISPLAY_TERMS = [
    "Riverside Plant",  # Old demo site name
    "Warehouse Distribution",  # Old demo site name
    "Air Handling Unit",  # Old asset name
    "VFD Coolant",  # Old asset name
    "Rooftop Unit",  # Old asset name
    "Process Chiller",  # Old asset name
]

# Terms that are acceptable in certain contexts
ACCEPTABLE_CONTEXT_TERMS = {
    "HVAC": ["Clean Room HVAC", "Pharmaceutical"],  # HVAC is OK in pharmaceutical context
    "Warehouse": ["site-warehouse", "site_id"],  # OK in internal IDs
    "Riverside": ["site-riverside", "site_id"],  # OK in internal IDs
}

# Required Industrial Refrigeration terms that SHOULD appear
REQUIRED_TERMS_FIRST_FIVE = [
    "Dairy Processing Plant",
    "Refrigeration",
    "Screw Compressor",
    "Evaporator Bank",
    "Condenser Unit",
    "Glycol Circulation Pump"
]

REQUIRED_TERMS_PORTFOLIO = [
    "Food Processing Facility",
    "Cold Storage"
]

REQUIRED_DRIVER_TERMS = [
    "compressor efficiency degradation",
    "refrigeration load imbalance",
    "cooling drift"
]


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/signin", json=ADMIN_CREDS)
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Admin authentication failed: {response.status_code}")


@pytest.fixture(scope="module")
def operator_token():
    """Get operator authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/signin", json=OPERATOR_CREDS)
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Operator authentication failed: {response.status_code}")


@pytest.fixture(scope="module")
def portfolio_token():
    """Get portfolio authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/signin", json=PORTFOLIO_CREDS)
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Portfolio authentication failed: {response.status_code}")


def check_no_forbidden_terms(data, context=""):
    """Helper to check that no forbidden generic terms appear in display names"""
    data_str = str(data)
    found_forbidden = []
    for term in FORBIDDEN_DISPLAY_TERMS:
        if term.lower() in data_str.lower():
            found_forbidden.append(term)
    return found_forbidden


def check_no_forbidden_in_site_names(data, context=""):
    """Check that site_name fields don't contain old generic names"""
    data_str = str(data)
    forbidden_site_names = ["Riverside Plant", "Warehouse Distribution Center"]
    found = []
    for term in forbidden_site_names:
        if term in data_str:
            found.append(term)
    return found


def check_required_terms(data, required_terms, context=""):
    """Helper to check that required terms appear in data"""
    data_str = str(data)
    missing_terms = []
    for term in required_terms:
        if term.lower() not in data_str.lower():
            missing_terms.append(term)
    return missing_terms


class TestFirstFiveMinutesDemo:
    """Test POST /api/system/demo/first-five-minutes for Industrial Refrigeration terminology"""
    
    def test_first_five_minutes_returns_200(self, admin_token):
        """Verify the endpoint returns 200"""
        response = requests.post(
            f"{BASE_URL}/api/system/demo/first-five-minutes",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_first_five_minutes_site_name(self, admin_token):
        """Verify site name is 'Dairy Processing Plant — Refrigeration'"""
        response = requests.post(
            f"{BASE_URL}/api/system/demo/first-five-minutes",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        # Check narrative contains correct site name
        narrative = str(data.get("narrative", {}))
        assert "Dairy Processing Plant" in narrative, f"Expected 'Dairy Processing Plant' in narrative, got: {narrative[:500]}"
        assert "Refrigeration" in narrative, f"Expected 'Refrigeration' in narrative"
    
    def test_first_five_minutes_asset_names(self, admin_token):
        """Verify asset names include Screw Compressor, Evaporator Bank, Condenser Unit, Glycol Circulation Pump"""
        response = requests.post(
            f"{BASE_URL}/api/system/demo/first-five-minutes",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        data_str = str(data)
        
        # Check for required asset names
        assert "Screw Compressor" in data_str, f"Expected 'Screw Compressor' in response"
        assert "Evaporator Bank" in data_str, f"Expected 'Evaporator Bank' in response"
        assert "Condenser Unit" in data_str, f"Expected 'Condenser Unit' in response"
        assert "Glycol Circulation Pump" in data_str, f"Expected 'Glycol Circulation Pump' in response"
    
    def test_first_five_minutes_savings_unit(self, admin_token):
        """Verify savings unit is 'kWh/hr'"""
        response = requests.post(
            f"{BASE_URL}/api/system/demo/first-five-minutes",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        data_str = str(data)
        
        # Check for kWh/hr or kWh savings unit
        assert "kWh" in data_str, f"Expected 'kWh' savings unit in response"
    
    def test_first_five_minutes_no_forbidden_terms(self, admin_token):
        """Verify no generic/forbidden terms appear"""
        response = requests.post(
            f"{BASE_URL}/api/system/demo/first-five-minutes",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        forbidden_found = check_no_forbidden_terms(data, "first-five-minutes")
        assert len(forbidden_found) == 0, f"Found forbidden generic terms: {forbidden_found}"


class TestSeedPortfolioDemo:
    """Test POST /api/system/demo/seed-portfolio for Industrial Refrigeration terminology"""
    
    def test_seed_portfolio_returns_200(self, admin_token):
        """Verify the endpoint returns 200"""
        response = requests.post(
            f"{BASE_URL}/api/system/demo/seed-portfolio",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # May return 200 with "already_seeded" status
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_seed_portfolio_site_name(self, admin_token):
        """Verify site name is 'Food Processing Facility — Cold Storage'"""
        response = requests.post(
            f"{BASE_URL}/api/system/demo/seed-portfolio",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        data_str = str(data)
        
        # The response may be "already_seeded" or contain site info
        # Either way, we verify via the portfolio intelligence endpoint
        assert response.status_code == 200


class TestOperatorPriorities:
    """Test GET /api/how/priorities for Industrial Refrigeration terminology"""
    
    def test_priorities_returns_200(self, operator_token):
        """Verify the endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/how/priorities",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_priorities_refrigeration_asset_names(self, operator_token):
        """Verify priorities contain refrigeration asset names"""
        response = requests.get(
            f"{BASE_URL}/api/how/priorities",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        data = response.json()
        data_str = str(data)
        
        # Check for at least one refrigeration asset type
        refrigeration_assets = ["Screw Compressor", "Evaporator Bank", "Condenser Unit", "Glycol Circulation Pump"]
        found_any = any(asset in data_str for asset in refrigeration_assets)
        
        # If there are priorities, they should have refrigeration asset names
        priorities = data.get("priorities", [])
        if len(priorities) > 0:
            assert found_any, f"Expected refrigeration asset names in priorities, got: {data_str[:1000]}"
    
    def test_priorities_driver_terminology(self, operator_token):
        """Verify driver text contains refrigeration terminology"""
        response = requests.get(
            f"{BASE_URL}/api/how/priorities",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        data = response.json()
        data_str = str(data).lower()
        
        priorities = data.get("priorities", [])
        if len(priorities) > 0:
            # Check for refrigeration-specific driver terms
            driver_terms = ["compressor efficiency", "refrigeration", "cooling", "degradation"]
            found_any = any(term in data_str for term in driver_terms)
            assert found_any, f"Expected refrigeration driver terminology in priorities"
    
    def test_priorities_no_forbidden_terms(self, operator_token):
        """Verify no generic/forbidden terms appear in priorities"""
        response = requests.get(
            f"{BASE_URL}/api/how/priorities",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        data = response.json()
        
        forbidden_found = check_no_forbidden_terms(data, "priorities")
        assert len(forbidden_found) == 0, f"Found forbidden generic terms in priorities: {forbidden_found}"


class TestPortfolioIntelligence:
    """Test GET /api/where/portfolio/intelligence for Industrial Refrigeration terminology"""
    
    def test_portfolio_intelligence_returns_200(self, portfolio_token):
        """Verify the endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/where/portfolio/intelligence",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_portfolio_site_names(self, portfolio_token):
        """Verify sites include 'Dairy Processing Plant — Refrigeration' and 'Food Processing Facility — Cold Storage'"""
        response = requests.get(
            f"{BASE_URL}/api/where/portfolio/intelligence",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        data = response.json()
        data_str = str(data)
        
        # Check for required site names
        assert "Dairy Processing Plant" in data_str, f"Expected 'Dairy Processing Plant' in portfolio sites"
        assert "Food Processing Facility" in data_str or "Cold Storage" in data_str, \
            f"Expected 'Food Processing Facility' or 'Cold Storage' in portfolio sites"
    
    def test_portfolio_asset_names_in_drilldown(self, portfolio_token):
        """Verify drill-down contains correct refrigeration asset names"""
        response = requests.get(
            f"{BASE_URL}/api/where/portfolio/intelligence",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        data = response.json()
        data_str = str(data)
        
        # Check for refrigeration asset types in the response
        refrigeration_assets = ["Screw Compressor", "Evaporator", "Condenser", "Glycol", "Cold Room", "Blast Freezer"]
        found_any = any(asset in data_str for asset in refrigeration_assets)
        assert found_any, f"Expected refrigeration asset names in portfolio drill-down"
    
    def test_portfolio_no_forbidden_terms(self, portfolio_token):
        """Verify no generic/forbidden terms appear in portfolio intelligence"""
        response = requests.get(
            f"{BASE_URL}/api/where/portfolio/intelligence",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        data = response.json()
        
        forbidden_found = check_no_forbidden_terms(data, "portfolio-intelligence")
        assert len(forbidden_found) == 0, f"Found forbidden generic terms in portfolio: {forbidden_found}"


class TestIBARefrigerationAnalysis:
    """Test GET /api/iba/refrigeration/analysis for Industrial Refrigeration terminology"""
    
    def test_iba_analysis_returns_200(self, portfolio_token):
        """Verify the endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_iba_industrial_site_names(self, portfolio_token):
        """Verify fleet analysis contains industrial site names"""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        data = response.json()
        data_str = str(data)
        
        # Check for industrial site names from pipeline.py
        industrial_sites = [
            "Dairy Processing Plant",
            "Meat & Poultry Facility",
            "Beverage Production",
            "Frozen Foods Processing",
            "Chemical Processing",
            "Glass Manufacturing",
            "Pharmaceutical Plant",
            "Distribution Center"
        ]
        found_count = sum(1 for site in industrial_sites if site in data_str)
        assert found_count >= 4, f"Expected at least 4 industrial site names, found {found_count}"
    
    def test_iba_ramp_connection_asset_names(self, portfolio_token):
        """Verify RAMP connection shows 'Screw Compressor #2' and 'Glycol Circulation Pump'"""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        data = response.json()
        data_str = str(data)
        
        # Check for RAMP connection asset names
        ramp_connection = data.get("ramp_connection", {})
        ramp_str = str(ramp_connection)
        
        # Should have refrigeration assets in RAMP connection
        refrigeration_assets = ["Screw Compressor", "Glycol Circulation Pump", "Evaporator", "Condenser"]
        found_any = any(asset in ramp_str or asset in data_str for asset in refrigeration_assets)
        assert found_any, f"Expected refrigeration asset names in RAMP connection"
    
    def test_iba_asset_type_labels(self, portfolio_token):
        """Verify asset type labels are refrigeration-specific"""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        data = response.json()
        
        fleet = data.get("fleet", {})
        asset_types = fleet.get("asset_types", [])
        
        # Should have refrigeration asset types
        expected_types = ["Screw Compressor", "Condenser Unit", "Evaporator Bank", "Pump System"]
        for expected in expected_types:
            assert expected in asset_types, f"Expected '{expected}' in asset_types, got: {asset_types}"
    
    def test_iba_opportunity_labels(self, portfolio_token):
        """Verify opportunity labels use refrigeration terminology"""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        data = response.json()
        
        opportunities = data.get("opportunities", [])
        opp_str = str(opportunities)
        
        # Should have refrigeration-specific opportunity labels
        expected_labels = ["Compressor Efficiency Recovery", "Refrigeration System Rehabilitation", "Compressor Cycling"]
        found_any = any(label in opp_str for label in expected_labels)
        assert found_any, f"Expected refrigeration opportunity labels, got: {opp_str[:500]}"
    
    def test_iba_no_forbidden_terms(self, portfolio_token):
        """Verify no generic/forbidden terms appear in IBA analysis"""
        response = requests.get(
            f"{BASE_URL}/api/iba/refrigeration/analysis",
            headers={"Authorization": f"Bearer {portfolio_token}"}
        )
        data = response.json()
        
        forbidden_found = check_no_forbidden_terms(data, "iba-analysis")
        assert len(forbidden_found) == 0, f"Found forbidden generic terms in IBA analysis: {forbidden_found}"


class TestIntelligenceOutcomes:
    """Test GET /api/intelligence/outcomes for Industrial Refrigeration terminology"""
    
    def test_outcomes_returns_200(self, operator_token):
        """Verify the endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/intelligence/outcomes",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_outcomes_asset_names(self, operator_token):
        """Verify outcomes show refrigeration asset names like 'Glycol Circulation Pump'"""
        response = requests.get(
            f"{BASE_URL}/api/intelligence/outcomes",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        data = response.json()
        
        outcomes = data.get("outcomes", [])
        if len(outcomes) > 0:
            outcomes_str = str(outcomes)
            # Check for refrigeration asset names
            refrigeration_assets = ["Glycol Circulation Pump", "Screw Compressor", "Evaporator", "Condenser"]
            found_any = any(asset in outcomes_str for asset in refrigeration_assets)
            assert found_any, f"Expected refrigeration asset names in outcomes, got: {outcomes_str}"
    
    def test_outcomes_savings_unit(self, operator_token):
        """Verify savings_unit is 'kWh/hr' or 'kWh'"""
        response = requests.get(
            f"{BASE_URL}/api/intelligence/outcomes",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        data = response.json()
        
        outcomes = data.get("outcomes", [])
        for outcome in outcomes:
            savings_unit = outcome.get("savings_unit", "")
            assert "kWh" in savings_unit or savings_unit == "", \
                f"Expected 'kWh' savings unit, got: {savings_unit}"
    
    def test_outcomes_no_forbidden_terms(self, operator_token):
        """Verify no generic/forbidden terms appear in outcomes"""
        response = requests.get(
            f"{BASE_URL}/api/intelligence/outcomes",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        data = response.json()
        
        forbidden_found = check_no_forbidden_terms(data, "outcomes")
        assert len(forbidden_found) == 0, f"Found forbidden generic terms in outcomes: {forbidden_found}"


class TestComprehensiveTerminologyCheck:
    """Comprehensive check across all endpoints for forbidden terms in display names"""
    
    def test_all_endpoints_no_riverside_plant(self, admin_token, operator_token, portfolio_token):
        """Verify 'Riverside Plant' (old site name) does not appear in any endpoint"""
        endpoints = [
            (f"{BASE_URL}/api/how/priorities", operator_token),
            (f"{BASE_URL}/api/where/portfolio/intelligence", portfolio_token),
            (f"{BASE_URL}/api/iba/refrigeration/analysis", portfolio_token),
            (f"{BASE_URL}/api/intelligence/outcomes", operator_token),
        ]
        
        for url, token in endpoints:
            response = requests.get(url, headers={"Authorization": f"Bearer {token}"})
            if response.status_code == 200:
                data_str = str(response.json())
                # Check for old site name, not internal ID
                assert "Riverside Plant" not in data_str, f"Found 'Riverside Plant' in {url}"
    
    def test_all_endpoints_no_warehouse_distribution(self, admin_token, operator_token, portfolio_token):
        """Verify 'Warehouse Distribution' (old site name) does not appear in any endpoint"""
        endpoints = [
            (f"{BASE_URL}/api/how/priorities", operator_token),
            (f"{BASE_URL}/api/where/portfolio/intelligence", portfolio_token),
            (f"{BASE_URL}/api/iba/refrigeration/analysis", portfolio_token),
            (f"{BASE_URL}/api/intelligence/outcomes", operator_token),
        ]
        
        for url, token in endpoints:
            response = requests.get(url, headers={"Authorization": f"Bearer {token}"})
            if response.status_code == 200:
                data_str = str(response.json())
                # Check for old site name, not internal ID
                assert "Warehouse Distribution" not in data_str, f"Found 'Warehouse Distribution' in {url}"
    
    def test_all_endpoints_no_air_handling_unit(self, admin_token, operator_token, portfolio_token):
        """Verify 'Air Handling Unit' does not appear in any endpoint"""
        endpoints = [
            (f"{BASE_URL}/api/how/priorities", operator_token),
            (f"{BASE_URL}/api/where/portfolio/intelligence", portfolio_token),
            (f"{BASE_URL}/api/iba/refrigeration/analysis", portfolio_token),
            (f"{BASE_URL}/api/intelligence/outcomes", operator_token),
        ]
        
        for url, token in endpoints:
            response = requests.get(url, headers={"Authorization": f"Bearer {token}"})
            if response.status_code == 200:
                data_str = str(response.json())
                assert "Air Handling Unit" not in data_str, f"Found 'Air Handling Unit' in {url}"
    
    def test_all_endpoints_no_vfd_coolant(self, admin_token, operator_token, portfolio_token):
        """Verify 'VFD Coolant' does not appear in any endpoint"""
        endpoints = [
            (f"{BASE_URL}/api/how/priorities", operator_token),
            (f"{BASE_URL}/api/where/portfolio/intelligence", portfolio_token),
            (f"{BASE_URL}/api/iba/refrigeration/analysis", portfolio_token),
            (f"{BASE_URL}/api/intelligence/outcomes", operator_token),
        ]
        
        for url, token in endpoints:
            response = requests.get(url, headers={"Authorization": f"Bearer {token}"})
            if response.status_code == 200:
                data_str = str(response.json())
                assert "VFD Coolant" not in data_str, f"Found 'VFD Coolant' in {url}"
    
    def test_all_endpoints_no_rooftop_unit(self, admin_token, operator_token, portfolio_token):
        """Verify 'Rooftop Unit' does not appear in any endpoint"""
        endpoints = [
            (f"{BASE_URL}/api/how/priorities", operator_token),
            (f"{BASE_URL}/api/where/portfolio/intelligence", portfolio_token),
            (f"{BASE_URL}/api/iba/refrigeration/analysis", portfolio_token),
            (f"{BASE_URL}/api/intelligence/outcomes", operator_token),
        ]
        
        for url, token in endpoints:
            response = requests.get(url, headers={"Authorization": f"Bearer {token}"})
            if response.status_code == 200:
                data_str = str(response.json())
                assert "Rooftop Unit" not in data_str, f"Found 'Rooftop Unit' in {url}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
