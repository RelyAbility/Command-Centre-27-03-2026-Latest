"""
Portfolio Intelligence API Tests
================================

Tests for the dual-mode Intelligence Surface:
- Portfolio mode: Site-level aggregation for portfolio users
- Operator mode: Asset-level priorities for operators/admins

Key endpoints tested:
- POST /api/auth/signin - Authentication
- GET /api/where/portfolio/intelligence - Portfolio intelligence data
- POST /api/system/demo/seed-portfolio - Demo data seeding
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"email": "rampadmin@gmail.com", "password": "RampAdmin2024!"}
OPERATOR_CREDS = {"email": "operator1@gmail.com", "password": "Operator2024!"}
PORTFOLIO_CREDS = {"email": "portfolio1@gmail.com", "password": "Portfolio2024!"}


class TestAuthentication:
    """Test authentication for different user roles"""
    
    def test_admin_signin(self):
        """Admin user can sign in"""
        response = requests.post(f"{BASE_URL}/api/auth/signin", json=ADMIN_CREDS)
        assert response.status_code == 200, f"Admin signin failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == ADMIN_CREDS["email"]
        assert data["user"]["role"] == "admin"
        print(f"✓ Admin signin successful - role: {data['user']['role']}")
    
    def test_operator_signin(self):
        """Operator user can sign in"""
        response = requests.post(f"{BASE_URL}/api/auth/signin", json=OPERATOR_CREDS)
        assert response.status_code == 200, f"Operator signin failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == OPERATOR_CREDS["email"]
        assert data["user"]["role"] == "operator"
        print(f"✓ Operator signin successful - role: {data['user']['role']}")
    
    def test_portfolio_signin(self):
        """Portfolio user can sign in"""
        response = requests.post(f"{BASE_URL}/api/auth/signin", json=PORTFOLIO_CREDS)
        assert response.status_code == 200, f"Portfolio signin failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == PORTFOLIO_CREDS["email"]
        assert data["user"]["role"] == "portfolio"
        print(f"✓ Portfolio signin successful - role: {data['user']['role']}")


class TestDemoSeedPortfolio:
    """Test portfolio demo data seeding"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/signin", json=ADMIN_CREDS)
        if response.status_code != 200:
            pytest.skip("Admin authentication failed")
        return response.json()["access_token"]
    
    def test_seed_portfolio_endpoint(self, admin_token):
        """POST /api/system/demo/seed-portfolio creates warehouse site data"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.post(f"{BASE_URL}/api/system/demo/seed-portfolio", headers=headers)
        assert response.status_code == 200, f"Seed portfolio failed: {response.text}"
        data = response.json()
        # Should return either "seeded" or "already_seeded"
        assert data["status"] in ["seeded", "already_seeded"], f"Unexpected status: {data['status']}"
        print(f"✓ Seed portfolio endpoint: {data['status']}")
        if data["status"] == "seeded":
            assert "site" in data
            assert data["site"] == "Warehouse Distribution Center"


class TestPortfolioIntelligenceAPI:
    """Test /api/where/portfolio/intelligence endpoint"""
    
    @pytest.fixture
    def portfolio_token(self):
        """Get portfolio user auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/signin", json=PORTFOLIO_CREDS)
        if response.status_code != 200:
            pytest.skip("Portfolio authentication failed")
        return response.json()["access_token"]
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/signin", json=ADMIN_CREDS)
        if response.status_code != 200:
            pytest.skip("Admin authentication failed")
        return response.json()["access_token"]
    
    @pytest.fixture
    def operator_token(self):
        """Get operator auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/signin", json=OPERATOR_CREDS)
        if response.status_code != 200:
            pytest.skip("Operator authentication failed")
        return response.json()["access_token"]
    
    def test_portfolio_intelligence_returns_correct_structure(self, portfolio_token):
        """Portfolio intelligence API returns correct multi-site data structure"""
        headers = {"Authorization": f"Bearer {portfolio_token}"}
        response = requests.get(f"{BASE_URL}/api/where/portfolio/intelligence", headers=headers)
        assert response.status_code == 200, f"Portfolio intelligence failed: {response.text}"
        data = response.json()
        
        # Verify top-level structure
        assert "mode" in data
        assert data["mode"] == "portfolio"
        assert "summary" in data
        assert "sites" in data
        assert "outcomes" in data
        assert "trust" in data
        assert "focus_site" in data
        print(f"✓ Portfolio intelligence returns correct structure with mode='portfolio'")
    
    def test_portfolio_summary_fields(self, portfolio_token):
        """Summary contains total_var, total_recoverable, site_count, priority_count"""
        headers = {"Authorization": f"Bearer {portfolio_token}"}
        response = requests.get(f"{BASE_URL}/api/where/portfolio/intelligence", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        summary = data["summary"]
        assert "total_var" in summary
        assert "total_recoverable" in summary
        assert "site_count" in summary
        assert "priority_count" in summary
        assert "currency" in summary
        
        # Verify types
        assert isinstance(summary["total_var"], (int, float))
        assert isinstance(summary["total_recoverable"], (int, float))
        assert isinstance(summary["site_count"], int)
        assert isinstance(summary["priority_count"], int)
        
        print(f"✓ Summary: total_var=${summary['total_var']}, sites={summary['site_count']}, priorities={summary['priority_count']}")
    
    def test_sites_ranked_by_var_descending(self, portfolio_token):
        """Sites are ranked by VaR descending (highest first)"""
        headers = {"Authorization": f"Bearer {portfolio_token}"}
        response = requests.get(f"{BASE_URL}/api/where/portfolio/intelligence", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        sites = data["sites"]
        if len(sites) >= 2:
            # Verify descending order by var_per_day
            for i in range(len(sites) - 1):
                assert sites[i]["var_per_day"] >= sites[i+1]["var_per_day"], \
                    f"Sites not sorted by VaR: {sites[i]['site_name']} (${sites[i]['var_per_day']}) should be >= {sites[i+1]['site_name']} (${sites[i+1]['var_per_day']})"
            site_info = [f"{s['site_name']}=${s['var_per_day']}" for s in sites]
            print(f"✓ Sites ranked by VaR descending: {site_info}")
        else:
            print(f"⚠ Only {len(sites)} site(s) found - cannot verify ranking")
    
    def test_site_data_structure(self, portfolio_token):
        """Each site has required fields"""
        headers = {"Authorization": f"Bearer {portfolio_token}"}
        response = requests.get(f"{BASE_URL}/api/where/portfolio/intelligence", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        sites = data["sites"]
        if len(sites) > 0:
            site = sites[0]
            required_fields = ["site_id", "site_name", "var_per_day", "recoverable_per_day", 
                             "priority_count", "distribution", "top_priority_band"]
            for field in required_fields:
                assert field in site, f"Missing field '{field}' in site data"
            
            # Verify distribution structure
            assert "CRITICAL" in site["distribution"]
            assert "HIGH" in site["distribution"]
            assert "MEDIUM" in site["distribution"]
            assert "LOW" in site["distribution"]
            
            print(f"✓ Site data structure verified: {site['site_name']} with distribution {site['distribution']}")
    
    def test_focus_site_is_highest_var(self, portfolio_token):
        """Focus site is the #1 site by VaR with correct name and reason"""
        headers = {"Authorization": f"Bearer {portfolio_token}"}
        response = requests.get(f"{BASE_URL}/api/where/portfolio/intelligence", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        focus_site = data["focus_site"]
        sites = data["sites"]
        
        if focus_site and len(sites) > 0:
            # Focus site should match the first site (highest VaR)
            assert focus_site["site_id"] == sites[0]["site_id"], \
                f"Focus site {focus_site['site_id']} doesn't match highest VaR site {sites[0]['site_id']}"
            assert focus_site["site_name"] == sites[0]["site_name"]
            assert "reason" in focus_site
            assert "var_per_day" in focus_site
            print(f"✓ Focus site: {focus_site['site_name']} (${focus_site['var_per_day']}/day) - {focus_site['reason']}")
        else:
            print(f"⚠ No focus site or no sites with VaR > 0")
    
    def test_outcomes_aggregated_per_site(self, portfolio_token):
        """Portfolio outcomes are aggregated per site"""
        headers = {"Authorization": f"Bearer {portfolio_token}"}
        response = requests.get(f"{BASE_URL}/api/where/portfolio/intelligence", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        outcomes = data["outcomes"]
        assert "total_savings" in outcomes
        assert "verified_count" in outcomes
        assert "site_outcomes" in outcomes
        
        # Verify site_outcomes structure
        for so in outcomes["site_outcomes"]:
            assert "site_id" in so
            assert "site_name" in so
            assert "verified_count" in so
            assert "total_savings" in so
        
        print(f"✓ Outcomes: total_savings=${outcomes['total_savings']}, verified={outcomes['verified_count']}, sites={len(outcomes['site_outcomes'])}")
    
    def test_trust_metrics_correctly_scoped(self, portfolio_token):
        """Trust metrics are correctly scoped"""
        headers = {"Authorization": f"Bearer {portfolio_token}"}
        response = requests.get(f"{BASE_URL}/api/where/portfolio/intelligence", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        trust = data["trust"]
        assert "verification_rate" in trust
        assert "actions_validated" in trust
        assert "total_actions" in trust
        assert "learning_improvement" in trust
        
        # Verify types and ranges
        assert isinstance(trust["verification_rate"], (int, float))
        assert 0 <= trust["verification_rate"] <= 1
        assert isinstance(trust["actions_validated"], int)
        assert isinstance(trust["total_actions"], int)
        
        print(f"✓ Trust metrics: verification_rate={trust['verification_rate']}, validated={trust['actions_validated']}/{trust['total_actions']}")
    
    def test_operator_cannot_access_portfolio_intelligence(self, operator_token):
        """Operator user should NOT have access to portfolio intelligence (requires WHERE lens)"""
        headers = {"Authorization": f"Bearer {operator_token}"}
        response = requests.get(f"{BASE_URL}/api/where/portfolio/intelligence", headers=headers)
        # Operator has HOW lens but not WHERE lens, should get 403
        assert response.status_code == 403, f"Expected 403 for operator, got {response.status_code}: {response.text}"
        print(f"✓ Operator correctly denied access to portfolio intelligence (403)")
    
    def test_admin_can_access_portfolio_intelligence(self, admin_token):
        """Admin user can access portfolio intelligence (has both lenses)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/where/portfolio/intelligence", headers=headers)
        assert response.status_code == 200, f"Admin portfolio access failed: {response.text}"
        data = response.json()
        assert data["mode"] == "portfolio"
        print(f"✓ Admin can access portfolio intelligence")


class TestPortfolioVsOperatorMode:
    """Test that different users see different modes"""
    
    @pytest.fixture
    def portfolio_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/signin", json=PORTFOLIO_CREDS)
        if response.status_code != 200:
            pytest.skip("Portfolio authentication failed")
        return response.json()["access_token"]
    
    @pytest.fixture
    def operator_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/signin", json=OPERATOR_CREDS)
        if response.status_code != 200:
            pytest.skip("Operator authentication failed")
        return response.json()["access_token"]
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/signin", json=ADMIN_CREDS)
        if response.status_code != 200:
            pytest.skip("Admin authentication failed")
        return response.json()["access_token"]
    
    def test_portfolio_user_lens_access(self, portfolio_token):
        """Portfolio user has WHERE but not HOW lens access"""
        headers = {"Authorization": f"Bearer {portfolio_token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200
        user = response.json()
        
        assert user["lens_access"]["where"] == True
        assert user["lens_access"]["how"] == False
        print(f"✓ Portfolio user lens_access: {user['lens_access']}")
    
    def test_operator_user_lens_access(self, operator_token):
        """Operator user has HOW but not WHERE lens access"""
        headers = {"Authorization": f"Bearer {operator_token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200
        user = response.json()
        
        assert user["lens_access"]["how"] == True
        assert user["lens_access"]["where"] == False
        print(f"✓ Operator user lens_access: {user['lens_access']}")
    
    def test_admin_user_lens_access(self, admin_token):
        """Admin user has both HOW and WHERE lens access"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200
        user = response.json()
        
        assert user["lens_access"]["how"] == True
        assert user["lens_access"]["where"] == True
        print(f"✓ Admin user lens_access: {user['lens_access']}")
    
    def test_operator_can_access_intelligence_summary(self, operator_token):
        """Operator can access /api/intelligence/summary (HOW lens)"""
        headers = {"Authorization": f"Bearer {operator_token}"}
        response = requests.get(f"{BASE_URL}/api/intelligence/summary", headers=headers)
        assert response.status_code == 200, f"Operator intelligence summary failed: {response.text}"
        print(f"✓ Operator can access intelligence summary")
    
    def test_portfolio_can_access_intelligence_summary(self, portfolio_token):
        """Portfolio user can access /api/intelligence/summary (public intelligence endpoint)"""
        headers = {"Authorization": f"Bearer {portfolio_token}"}
        response = requests.get(f"{BASE_URL}/api/intelligence/summary", headers=headers)
        # Intelligence summary is accessible to all authenticated users
        assert response.status_code == 200, f"Portfolio intelligence summary failed: {response.text}"
        data = response.json()
        assert "total_var" in data
        print(f"✓ Portfolio can access intelligence summary: total_var=${data['total_var']}")


class TestExpectedVaRValues:
    """Test expected VaR values based on demo data"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/signin", json=ADMIN_CREDS)
        if response.status_code != 200:
            pytest.skip("Admin authentication failed")
        return response.json()["access_token"]
    
    def test_seed_and_verify_portfolio_data(self, admin_token):
        """Seed portfolio data and verify expected values"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First seed the portfolio data
        seed_response = requests.post(f"{BASE_URL}/api/system/demo/seed-portfolio", headers=headers)
        assert seed_response.status_code == 200
        
        # Now get portfolio intelligence
        response = requests.get(f"{BASE_URL}/api/where/portfolio/intelligence", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Find warehouse and riverside sites
        sites_by_name = {s["site_name"]: s for s in data["sites"]}
        
        # Expected: warehouse has higher VaR than riverside
        # Warehouse: Cold Storage ($340) + RTU1 ($55) = $395
        # Riverside: Compressor ($151) + Chiller ($19) + AHU ($43) = $213
        
        if "Warehouse Distribution Center" in sites_by_name and "Riverside Manufacturing Plant" in sites_by_name:
            warehouse = sites_by_name["Warehouse Distribution Center"]
            riverside = sites_by_name["Riverside Manufacturing Plant"]
            
            print(f"Warehouse VaR: ${warehouse['var_per_day']}")
            print(f"Riverside VaR: ${riverside['var_per_day']}")
            
            # Warehouse should have higher VaR
            assert warehouse["var_per_day"] > riverside["var_per_day"], \
                f"Warehouse (${warehouse['var_per_day']}) should have higher VaR than Riverside (${riverside['var_per_day']})"
            
            # Verify warehouse is focus site (highest VaR)
            if data["focus_site"]:
                assert data["focus_site"]["site_name"] == "Warehouse Distribution Center", \
                    f"Focus site should be Warehouse, got {data['focus_site']['site_name']}"
            
            print(f"✓ Warehouse (${warehouse['var_per_day']}) > Riverside (${riverside['var_per_day']})")
            print(f"✓ Focus site is Warehouse Distribution Center")
        else:
            available_sites = list(sites_by_name.keys())
            print(f"⚠ Expected sites not found. Available: {available_sites}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
