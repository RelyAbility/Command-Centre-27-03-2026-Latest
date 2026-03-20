"""
Test First Five Minutes Demo Feature
=====================================

Tests the First 5 Minutes onboarding experience for RAMP:
1. Demo creates 4 realistic assets with baselines
2. Completed loop shows verified outcome
3. Current value at risk with breakdown
4. 3 priority actions displayed
5. Continuous monitoring status
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestFirstFiveMinutesDemo:
    """Test the First Five Minutes demo endpoint"""
    
    def test_first_five_minutes_endpoint_returns_200(self, api_client):
        """Test that the demo endpoint is accessible and returns 200"""
        # This API takes ~22 seconds according to context
        response = api_client.post(f"{BASE_URL}/api/system/demo/first-five-minutes", timeout=60)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "status" in data
        assert data["status"] == "ready"
        print(f"SUCCESS: First five minutes demo returned status: {data['status']}")
    
    def test_narrative_structure(self, api_client):
        """Test that narrative has all required sections"""
        response = api_client.post(f"{BASE_URL}/api/system/demo/first-five-minutes", timeout=60)
        data = response.json()
        
        assert "narrative" in data
        narrative = data["narrative"]
        
        # Check all required sections exist
        required_sections = ["site", "completed_loop", "current_value_at_risk", "priority_actions", "continuous_monitoring"]
        for section in required_sections:
            assert section in narrative, f"Missing section: {section}"
            print(f"SUCCESS: Found section '{section}'")
    
    def test_site_context_has_4_assets(self, api_client):
        """Test that site shows 4 assets monitored"""
        response = api_client.post(f"{BASE_URL}/api/system/demo/first-five-minutes", timeout=60)
        narrative = response.json()["narrative"]
        
        site = narrative["site"]
        assert site["assets_monitored"] == 4, f"Expected 4 assets, got {site['assets_monitored']}"
        assert site["baseline_data_days"] == 14, f"Expected 14 days baseline, got {site['baseline_data_days']}"
        assert "systems" in site and len(site["systems"]) == 3
        print(f"SUCCESS: Site has {site['assets_monitored']} assets with {site['baseline_data_days']} days baseline data")
        print(f"Systems: {site['systems']}")
    
    def test_completed_loop_verified_outcome(self, api_client):
        """Test that completed loop shows verified outcome with savings and confidence"""
        response = api_client.post(f"{BASE_URL}/api/system/demo/first-five-minutes", timeout=60)
        narrative = response.json()["narrative"]
        
        completed_loop = narrative["completed_loop"]
        
        # Check required fields
        assert "asset" in completed_loop, "Missing asset in completed_loop"
        assert "issue" in completed_loop, "Missing issue in completed_loop"
        assert "action" in completed_loop, "Missing action in completed_loop"
        assert "outcome" in completed_loop, "Missing outcome in completed_loop"
        
        # Asset should be VFD Coolant Pump
        assert "VFD" in completed_loop["asset"], f"Expected VFD Pump, got {completed_loop['asset']}"
        
        # Outcome should mention savings and confidence
        assert "savings" in completed_loop["outcome"].lower() or "verified" in completed_loop["outcome"].lower()
        assert "91%" in completed_loop["outcome"] or "confidence" in completed_loop["outcome"].lower()
        
        print(f"SUCCESS: Completed loop for {completed_loop['asset']}")
        print(f"  Issue: {completed_loop['issue']}")
        print(f"  Action: {completed_loop['action']}")
        print(f"  Outcome: {completed_loop['outcome']}")
    
    def test_value_at_risk_total_and_breakdown(self, api_client):
        """Test value at risk shows total with breakdown by priority band"""
        response = api_client.post(f"{BASE_URL}/api/system/demo/first-five-minutes", timeout=60)
        narrative = response.json()["narrative"]
        
        var = narrative["current_value_at_risk"]
        
        assert "total_per_day" in var
        assert var["total_per_day"] > 0, "Total VaR should be positive"
        assert "breakdown" in var
        assert len(var["breakdown"]) >= 3, f"Expected 3+ items in breakdown, got {len(var['breakdown'])}"
        
        # Check breakdown structure
        for item in var["breakdown"]:
            assert "asset" in item
            assert "var" in item
            assert "band" in item
            assert item["band"] in ["HIGH", "MEDIUM", "LOW", "CRITICAL"]
        
        # Verify total matches sum of breakdown
        breakdown_sum = sum(item["var"] for item in var["breakdown"])
        assert abs(var["total_per_day"] - breakdown_sum) < 1, f"Total {var['total_per_day']} doesn't match breakdown sum {breakdown_sum}"
        
        print(f"SUCCESS: Value at Risk total: ${var['total_per_day']}/day")
        print(f"  Breakdown: {var['breakdown']}")
    
    def test_priority_actions_has_3_actions(self, api_client):
        """Test that 3 priority actions are returned with rank, asset, issue, action"""
        response = api_client.post(f"{BASE_URL}/api/system/demo/first-five-minutes", timeout=60)
        narrative = response.json()["narrative"]
        
        actions = narrative["priority_actions"]
        assert len(actions) == 3, f"Expected 3 priority actions, got {len(actions)}"
        
        for i, action in enumerate(actions):
            assert action["rank"] == i + 1, f"Expected rank {i+1}, got {action['rank']}"
            assert "asset" in action, f"Missing asset in action {i+1}"
            assert "issue" in action, f"Missing issue in action {i+1}"
            assert "band" in action, f"Missing band in action {i+1}"
            assert "confidence" in action, f"Missing confidence in action {i+1}"
            assert "var_per_day" in action, f"Missing var_per_day in action {i+1}"
            assert "recommended_action" in action, f"Missing recommended_action in action {i+1}"
            assert "state_id" in action, f"Missing state_id in action {i+1}"
            
            print(f"SUCCESS: Action {action['rank']}: {action['asset']} - {action['band']} - ${action['var_per_day']}/day")
    
    def test_priority_bands_correct_order(self, api_client):
        """Test priority bands are HIGH, MEDIUM, LOW in order"""
        response = api_client.post(f"{BASE_URL}/api/system/demo/first-five-minutes", timeout=60)
        actions = response.json()["narrative"]["priority_actions"]
        
        bands = [a["band"] for a in actions]
        expected = ["HIGH", "MEDIUM", "LOW"]
        assert bands == expected, f"Expected bands {expected}, got {bands}"
        print(f"SUCCESS: Priority bands in correct order: {bands}")
    
    def test_continuous_monitoring_status(self, api_client):
        """Test continuous monitoring shows healthy and active state counts"""
        response = api_client.post(f"{BASE_URL}/api/system/demo/first-five-minutes", timeout=60)
        narrative = response.json()["narrative"]
        
        cm = narrative["continuous_monitoring"]
        
        assert "assets_healthy" in cm
        assert "assets_in_state" in cm
        assert cm["assets_healthy"] == 1, f"Expected 1 healthy, got {cm['assets_healthy']}"
        assert cm["assets_in_state"] == 3, f"Expected 3 in state, got {cm['assets_in_state']}"
        
        print(f"SUCCESS: Continuous monitoring - {cm['assets_healthy']} healthy, {cm['assets_in_state']} in state")


class TestValueSummaryAfterDemo:
    """Test value summary endpoint after demo is run"""
    
    @pytest.fixture(autouse=True)
    def setup_demo(self, api_client):
        """Run demo before these tests"""
        api_client.post(f"{BASE_URL}/api/system/demo/first-five-minutes", timeout=60)
    
    def test_value_summary_has_loop_integrity(self, api_client):
        """Test that value summary shows loop integrity status"""
        response = api_client.get(f"{BASE_URL}/api/system/value-summary", timeout=30)
        assert response.status_code == 200
        
        data = response.json()
        assert "loop_integrity" in data
        
        integrity = data["loop_integrity"]
        assert "verified" in integrity
        assert "pending" in integrity
        assert "status" in integrity
        
        # After demo, we should have 1 verified outcome (VFD pump)
        assert integrity["verified"] >= 1, f"Expected at least 1 verified, got {integrity['verified']}"
        print(f"SUCCESS: Loop integrity - {integrity['verified']} verified, status: {integrity['status']}")


class TestInterventionFromPriority:
    """Test creating intervention from a priority action"""
    
    @pytest.fixture(autouse=True)
    def setup_demo(self, api_client):
        """Run demo to get state_ids"""
        response = api_client.post(f"{BASE_URL}/api/system/demo/first-five-minutes", timeout=60)
        self.narrative = response.json()["narrative"]
    
    def test_create_intervention_for_priority(self, api_client):
        """Test creating an intervention using state_id from priority action"""
        action = self.narrative["priority_actions"][0]
        state_id = action["state_id"]
        
        response = api_client.post(f"{BASE_URL}/api/how/interventions", json={
            "state_id": state_id,
            "intervention_type": "ADJUSTMENT",
            "description": "Test intervention for demo priority",
            "created_by": "test@example.com"
        }, timeout=30)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "intervention_id" in data
        assert "message" in data
        assert "frozen" in data["message"].lower() or "baseline" in data["message"].lower()
        
        print(f"SUCCESS: Created intervention {data['intervention_id']} - {data['message']}")


class TestHealthCheck:
    """Basic health check"""
    
    def test_health_endpoint(self, api_client):
        """Test health endpoint"""
        response = api_client.get(f"{BASE_URL}/api/system/health", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"SUCCESS: API is healthy")
