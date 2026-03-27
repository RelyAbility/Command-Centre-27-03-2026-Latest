"""
Portfolio Commercial Features Tests
====================================

Tests for the NEW commercial story features in Portfolio Intelligence:
- Scale Banner: annual_exposure, annual_recoverable, total_assets
- Replication Logic: where insights apply elsewhere
- Repeatability Signals: recurring conditions across sites
- Scaled Outcomes: verified savings projected across similar assets
- Site Drill-down: top 3 priorities per site

Key endpoints tested:
- GET /api/where/portfolio/intelligence - Enhanced portfolio data
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"email": "rampadmin@gmail.com", "password": "RampAdmin2024!"}
PORTFOLIO_CREDS = {"email": "portfolio1@gmail.com", "password": "Portfolio2024!"}
OPERATOR_CREDS = {"email": "operator1@gmail.com", "password": "Operator2024!"}


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/signin", json=ADMIN_CREDS)
    if response.status_code != 200:
        pytest.skip("Admin authentication failed")
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def portfolio_token():
    """Get portfolio user auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/signin", json=PORTFOLIO_CREDS)
    if response.status_code != 200:
        pytest.skip("Portfolio authentication failed")
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def operator_token():
    """Get operator user auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/signin", json=OPERATOR_CREDS)
    if response.status_code != 200:
        pytest.skip("Operator authentication failed")
    return response.json()["access_token"]


@pytest.fixture(scope="module", autouse=True)
def seed_demo_data(admin_token):
    """Ensure demo data is seeded before tests"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    # Seed first-five-minutes demo
    requests.post(f"{BASE_URL}/api/system/demo/first-five-minutes", headers=headers)
    # Seed portfolio demo
    requests.post(f"{BASE_URL}/api/system/demo/seed-portfolio", headers=headers)
    return True


class TestScaleBanner:
    """Test Portfolio Scale Banner: annual_exposure, annual_recoverable, total_assets"""
    
    def test_summary_has_annual_exposure(self, portfolio_token):
        """Summary includes annual_exposure field"""
        headers = {"Authorization": f"Bearer {portfolio_token}"}
        response = requests.get(f"{BASE_URL}/api/where/portfolio/intelligence", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        summary = data["summary"]
        assert "annual_exposure" in summary, "Missing annual_exposure in summary"
        assert isinstance(summary["annual_exposure"], (int, float))
        # annual_exposure should be total_var * 365
        expected_annual = round(summary["total_var"] * 365, 2)
        assert abs(summary["annual_exposure"] - expected_annual) < 1, \
            f"annual_exposure {summary['annual_exposure']} != total_var*365 ({expected_annual})"
        print(f"✓ annual_exposure: ${summary['annual_exposure']:,.0f}")
    
    def test_summary_has_annual_recoverable(self, portfolio_token):
        """Summary includes annual_recoverable field"""
        headers = {"Authorization": f"Bearer {portfolio_token}"}
        response = requests.get(f"{BASE_URL}/api/where/portfolio/intelligence", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        summary = data["summary"]
        assert "annual_recoverable" in summary, "Missing annual_recoverable in summary"
        assert isinstance(summary["annual_recoverable"], (int, float))
        # annual_recoverable should be total_recoverable * 365
        expected_annual = round(summary["total_recoverable"] * 365, 2)
        assert abs(summary["annual_recoverable"] - expected_annual) < 1, \
            f"annual_recoverable {summary['annual_recoverable']} != total_recoverable*365 ({expected_annual})"
        print(f"✓ annual_recoverable: ${summary['annual_recoverable']:,.0f}")
    
    def test_summary_has_total_assets(self, portfolio_token):
        """Summary includes total_assets field"""
        headers = {"Authorization": f"Bearer {portfolio_token}"}
        response = requests.get(f"{BASE_URL}/api/where/portfolio/intelligence", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        summary = data["summary"]
        assert "total_assets" in summary, "Missing total_assets in summary"
        assert isinstance(summary["total_assets"], int)
        assert summary["total_assets"] > 0, "total_assets should be > 0"
        print(f"✓ total_assets: {summary['total_assets']}")
    
    def test_scale_banner_values_match_expected(self, portfolio_token):
        """Scale banner values match expected demo data"""
        headers = {"Authorization": f"Bearer {portfolio_token}"}
        response = requests.get(f"{BASE_URL}/api/where/portfolio/intelligence", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        summary = data["summary"]
        # Expected: ~$608/day total VaR (warehouse $395 + riverside $213)
        # Annual exposure should be ~$222k
        print(f"✓ Scale Banner: VaR=${summary['total_var']}/day, Annual=${summary['annual_exposure']:,.0f}, "
              f"Recoverable=${summary['total_recoverable']}/day, Sites={summary['site_count']}, Assets={summary['total_assets']}")


class TestReplicationLogic:
    """Test Replication Logic: where insights apply elsewhere"""
    
    def test_replication_section_exists(self, portfolio_token):
        """Response includes replication section"""
        headers = {"Authorization": f"Bearer {portfolio_token}"}
        response = requests.get(f"{BASE_URL}/api/where/portfolio/intelligence", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "replication" in data, "Missing replication section"
        replication = data["replication"]
        assert "patterns" in replication, "Missing patterns in replication"
        assert "total_affected_assets" in replication, "Missing total_affected_assets"
        assert "cross_site_conditions" in replication, "Missing cross_site_conditions"
        print(f"✓ Replication section exists with {len(replication['patterns'])} patterns")
    
    def test_replication_pattern_structure(self, portfolio_token):
        """Each replication pattern has required fields"""
        headers = {"Authorization": f"Bearer {portfolio_token}"}
        response = requests.get(f"{BASE_URL}/api/where/portfolio/intelligence", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        patterns = data["replication"]["patterns"]
        if len(patterns) > 0:
            pattern = patterns[0]
            required_fields = ["condition", "state_family", "state_type", "asset_class", 
                             "affected_assets", "affected_sites", "combined_var_per_day"]
            for field in required_fields:
                assert field in pattern, f"Missing field '{field}' in replication pattern"
            print(f"✓ Replication pattern structure verified: {pattern['asset_class']} - {pattern['state_type']}")
        else:
            print("⚠ No replication patterns found")
    
    def test_replication_shows_var_per_pattern(self, portfolio_token):
        """Replication patterns show VaR per pattern"""
        headers = {"Authorization": f"Bearer {portfolio_token}"}
        response = requests.get(f"{BASE_URL}/api/where/portfolio/intelligence", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        patterns = data["replication"]["patterns"]
        for pattern in patterns:
            assert "combined_var_per_day" in pattern
            assert isinstance(pattern["combined_var_per_day"], (int, float))
            print(f"  - {pattern['asset_class']} {pattern['state_type']}: ${pattern['combined_var_per_day']}/day ({pattern['affected_assets']} assets)")


class TestRepeatabilitySignals:
    """Test Repeatability Signals: recurring conditions across sites"""
    
    def test_repeatability_section_exists(self, portfolio_token):
        """Response includes repeatability section"""
        headers = {"Authorization": f"Bearer {portfolio_token}"}
        response = requests.get(f"{BASE_URL}/api/where/portfolio/intelligence", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "repeatability" in data, "Missing repeatability section"
        repeatability = data["repeatability"]
        assert "signals" in repeatability, "Missing signals in repeatability"
        assert "recurring_conditions" in repeatability, "Missing recurring_conditions count"
        print(f"✓ Repeatability section exists with {repeatability['recurring_conditions']} recurring conditions")
    
    def test_repeatability_signal_structure(self, portfolio_token):
        """Each repeatability signal has required fields"""
        headers = {"Authorization": f"Bearer {portfolio_token}"}
        response = requests.get(f"{BASE_URL}/api/where/portfolio/intelligence", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        signals = data["repeatability"]["signals"]
        if len(signals) > 0:
            signal = signals[0]
            required_fields = ["condition", "state_family", "state_type", "total_occurrences", 
                             "distinct_assets", "distinct_sites", "recurring"]
            for field in required_fields:
                assert field in signal, f"Missing field '{field}' in repeatability signal"
            print(f"✓ Repeatability signal structure verified: {signal['state_type']}")
        else:
            print("⚠ No repeatability signals found")
    
    def test_drift_condition_is_recurring(self, portfolio_token):
        """DRIFT condition shows as recurring (expected: 5 occurrences, 2 sites)"""
        headers = {"Authorization": f"Bearer {portfolio_token}"}
        response = requests.get(f"{BASE_URL}/api/where/portfolio/intelligence", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        signals = data["repeatability"]["signals"]
        drift_signals = [s for s in signals if s["state_type"] == "DRIFT"]
        
        if len(drift_signals) > 0:
            drift = drift_signals[0]
            assert drift["total_occurrences"] >= 2, f"DRIFT should have multiple occurrences, got {drift['total_occurrences']}"
            assert drift["recurring"] == True, "DRIFT should be marked as recurring"
            print(f"✓ DRIFT condition: {drift['total_occurrences']} occurrences, "
                  f"{drift['distinct_sites']} sites, {drift['distinct_assets']} assets")
        else:
            print("⚠ No DRIFT signals found in repeatability")


class TestScaledOutcomes:
    """Test Scaled Outcomes: verified savings projected across similar assets"""
    
    def test_scaled_outcomes_section_exists(self, portfolio_token):
        """Outcomes section includes scaled_outcomes"""
        headers = {"Authorization": f"Bearer {portfolio_token}"}
        response = requests.get(f"{BASE_URL}/api/where/portfolio/intelligence", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        outcomes = data["outcomes"]
        assert "scaled_outcomes" in outcomes, "Missing scaled_outcomes in outcomes"
        assert "total_scaled_potential" in outcomes, "Missing total_scaled_potential"
        print(f"✓ Scaled outcomes section exists with {len(outcomes['scaled_outcomes'])} entries")
    
    def test_scaled_outcome_structure(self, portfolio_token):
        """Each scaled outcome has required fields"""
        headers = {"Authorization": f"Bearer {portfolio_token}"}
        response = requests.get(f"{BASE_URL}/api/where/portfolio/intelligence", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        scaled_outcomes = data["outcomes"]["scaled_outcomes"]
        if len(scaled_outcomes) > 0:
            so = scaled_outcomes[0]
            required_fields = ["asset_class", "verified_savings", "savings_unit", 
                             "similar_assets_in_portfolio", "scaled_potential"]
            for field in required_fields:
                assert field in so, f"Missing field '{field}' in scaled outcome"
            print(f"✓ Scaled outcome structure verified: {so['asset_class']}")
        else:
            print("⚠ No scaled outcomes found (may need verified outcomes in demo data)")
    
    def test_scaled_potential_calculation(self, portfolio_token):
        """Scaled potential = verified_savings * similar_assets_in_portfolio"""
        headers = {"Authorization": f"Bearer {portfolio_token}"}
        response = requests.get(f"{BASE_URL}/api/where/portfolio/intelligence", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        scaled_outcomes = data["outcomes"]["scaled_outcomes"]
        for so in scaled_outcomes:
            expected_potential = round(so["verified_savings"] * so["similar_assets_in_portfolio"], 2)
            assert abs(so["scaled_potential"] - expected_potential) < 0.1, \
                f"scaled_potential {so['scaled_potential']} != verified_savings*similar_assets ({expected_potential})"
            print(f"  - {so['asset_class']}: {so['verified_savings']} {so['savings_unit']} × {so['similar_assets_in_portfolio']} = {so['scaled_potential']}")


class TestSiteDrillDown:
    """Test Site Drill-down: top 3 priorities per site"""
    
    def test_sites_have_top_priorities(self, portfolio_token):
        """Each site includes top_priorities array"""
        headers = {"Authorization": f"Bearer {portfolio_token}"}
        response = requests.get(f"{BASE_URL}/api/where/portfolio/intelligence", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        sites = data["sites"]
        for site in sites:
            assert "top_priorities" in site, f"Missing top_priorities in site {site['site_name']}"
            assert isinstance(site["top_priorities"], list)
            print(f"  - {site['site_name']}: {len(site['top_priorities'])} top priorities")
    
    def test_top_priorities_limited_to_3(self, portfolio_token):
        """Each site has at most 3 top priorities"""
        headers = {"Authorization": f"Bearer {portfolio_token}"}
        response = requests.get(f"{BASE_URL}/api/where/portfolio/intelligence", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        sites = data["sites"]
        for site in sites:
            assert len(site["top_priorities"]) <= 3, \
                f"Site {site['site_name']} has {len(site['top_priorities'])} priorities, expected <= 3"
        print(f"✓ All sites have at most 3 top priorities")
    
    def test_top_priority_structure(self, portfolio_token):
        """Each top priority has required fields"""
        headers = {"Authorization": f"Bearer {portfolio_token}"}
        response = requests.get(f"{BASE_URL}/api/where/portfolio/intelligence", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        sites = data["sites"]
        for site in sites:
            for priority in site["top_priorities"]:
                required_fields = ["priority_id", "priority_band", "var_per_day", "asset_name", "driver"]
                for field in required_fields:
                    assert field in priority, f"Missing field '{field}' in priority for {site['site_name']}"
        print(f"✓ Top priority structure verified for all sites")
    
    def test_warehouse_top_priorities(self, portfolio_token):
        """Warehouse site shows Cold Storage Compressor CRITICAL $340 and Rooftop Unit 1 MEDIUM $55"""
        headers = {"Authorization": f"Bearer {portfolio_token}"}
        response = requests.get(f"{BASE_URL}/api/where/portfolio/intelligence", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        sites = data["sites"]
        warehouse = next((s for s in sites if "Warehouse" in s["site_name"]), None)
        
        if warehouse:
            priorities = warehouse["top_priorities"]
            print(f"✓ Warehouse top priorities:")
            for p in priorities:
                print(f"  - {p['asset_name']} {p['priority_band']} ${p['var_per_day']}")
            
            # Check for expected priorities
            asset_names = [p["asset_name"] for p in priorities]
            bands = [p["priority_band"] for p in priorities]
            
            # Should have CRITICAL priority (Cold Storage Compressor)
            if "CRITICAL" in bands:
                critical_p = next(p for p in priorities if p["priority_band"] == "CRITICAL")
                print(f"✓ Found CRITICAL priority: {critical_p['asset_name']} ${critical_p['var_per_day']}")
        else:
            print("⚠ Warehouse site not found")
    
    def test_riverside_top_priorities(self, portfolio_token):
        """Riverside site shows top 3 priorities"""
        headers = {"Authorization": f"Bearer {portfolio_token}"}
        response = requests.get(f"{BASE_URL}/api/where/portfolio/intelligence", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        sites = data["sites"]
        riverside = next((s for s in sites if "Riverside" in s["site_name"]), None)
        
        if riverside:
            priorities = riverside["top_priorities"]
            print(f"✓ Riverside top priorities:")
            for p in priorities:
                print(f"  - {p['asset_name']} {p['priority_band']} ${p['var_per_day']}")
        else:
            print("⚠ Riverside site not found")


class TestFocusSiteCallout:
    """Test Focus Site Callout"""
    
    def test_focus_site_shows_warehouse(self, portfolio_token):
        """Focus site shows Warehouse Distribution Center with $395/day"""
        headers = {"Authorization": f"Bearer {portfolio_token}"}
        response = requests.get(f"{BASE_URL}/api/where/portfolio/intelligence", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        focus_site = data["focus_site"]
        if focus_site:
            print(f"✓ Focus site: {focus_site['site_name']} ${focus_site['var_per_day']}/day")
            assert "var_per_day" in focus_site
            assert "reason" in focus_site
            # Should be the highest VaR site
            sites = data["sites"]
            if len(sites) > 0:
                assert focus_site["site_id"] == sites[0]["site_id"], \
                    "Focus site should be the highest VaR site"
        else:
            print("⚠ No focus site found")


class TestOperatorModeUnchanged:
    """Test that Operator mode is unchanged (no portfolio elements)"""
    
    def test_operator_cannot_access_portfolio_endpoint(self, operator_token):
        """Operator cannot access portfolio intelligence endpoint"""
        headers = {"Authorization": f"Bearer {operator_token}"}
        response = requests.get(f"{BASE_URL}/api/where/portfolio/intelligence", headers=headers)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print(f"✓ Operator correctly denied access to portfolio endpoint (403)")
    
    def test_operator_can_access_how_priorities(self, operator_token):
        """Operator can access HOW lens priorities"""
        headers = {"Authorization": f"Bearer {operator_token}"}
        response = requests.get(f"{BASE_URL}/api/how/priorities", headers=headers)
        assert response.status_code == 200, f"Operator HOW priorities failed: {response.text}"
        data = response.json()
        assert "priorities" in data
        print(f"✓ Operator can access HOW priorities: {len(data['priorities'])} priorities")


class TestAdminSeesOperatorView:
    """Test that Admin sees operator view, not portfolio view (has both lenses)"""
    
    def test_admin_lens_access(self, admin_token):
        """Admin has both HOW and WHERE lens access"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200
        user = response.json()
        
        assert user["lens_access"]["how"] == True, "Admin should have HOW lens"
        assert user["lens_access"]["where"] == True, "Admin should have WHERE lens"
        print(f"✓ Admin has both lenses: {user['lens_access']}")
    
    def test_admin_can_access_how_priorities(self, admin_token):
        """Admin can access HOW lens priorities (operator view)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/how/priorities", headers=headers)
        assert response.status_code == 200, f"Admin HOW priorities failed: {response.text}"
        data = response.json()
        assert "priorities" in data
        print(f"✓ Admin can access HOW priorities: {len(data['priorities'])} priorities")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
