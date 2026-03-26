"""
RAMP Proof of Value Dashboard Tests
====================================

Tests for the single-page value dashboard that demonstrates:
1. Where value is being lost (current VaR/day)
2. What to do about it (top priority actions with recoverable value + confidence)
3. What has been recovered (verified outcomes with savings, confidence, time to verify)
4. Is the system working (loop integrity: verified vs pending vs insufficient)
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://ramp-industrial-ai.preview.emergentagent.com').rstrip('/')


class TestValueSummaryEndpoint:
    """Tests for GET /api/system/value-summary endpoint"""
    
    def test_value_summary_endpoint_returns_200(self):
        """Test value-summary endpoint exists and returns 200"""
        response = requests.get(f"{BASE_URL}/api/system/value-summary")
        assert response.status_code == 200
        print(f"✓ Value summary endpoint returns 200")
    
    def test_value_summary_has_required_sections(self):
        """Test that response contains all four required sections"""
        response = requests.get(f"{BASE_URL}/api/system/value-summary")
        assert response.status_code == 200
        data = response.json()
        
        required_sections = [
            "value_at_risk",  # Section 1: Where value is being lost
            "top_actions",    # Section 2: What to do about it  
            "recovered_value",# Section 3: What has been recovered
            "loop_integrity"  # Section 4: Is the system working
        ]
        
        for section in required_sections:
            assert section in data, f"Missing required section: {section}"
            print(f"✓ Section '{section}' present")
        
        # Also check timestamp and currency
        assert "timestamp" in data
        assert "currency" in data
        print(f"✓ Timestamp and currency present")
    
    def test_value_at_risk_structure(self):
        """Test Value at Risk section structure (Section 1)"""
        response = requests.get(f"{BASE_URL}/api/system/value-summary")
        data = response.json()
        
        var = data["value_at_risk"]
        
        # Required fields
        assert "total_per_day" in var, "Missing total_per_day"
        assert "active_priorities" in var, "Missing active_priorities"
        assert "breakdown_by_band" in var, "Missing breakdown_by_band"
        
        # Validate types
        assert isinstance(var["total_per_day"], (int, float)), "total_per_day must be numeric"
        assert isinstance(var["active_priorities"], int), "active_priorities must be integer"
        
        # Validate breakdown has all bands
        breakdown = var["breakdown_by_band"]
        for band in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            assert band in breakdown, f"Missing band: {band}"
            
        print(f"✓ Value at Risk: ${var['total_per_day']}/day, {var['active_priorities']} priorities")
        print(f"✓ Breakdown: {breakdown}")
    
    def test_top_actions_structure(self):
        """Test Top Priority Actions section structure (Section 2)"""
        response = requests.get(f"{BASE_URL}/api/system/value-summary")
        data = response.json()
        
        top_actions = data["top_actions"]
        assert isinstance(top_actions, list), "top_actions must be a list"
        
        if len(top_actions) > 0:
            action = top_actions[0]
            
            # Required fields for each action
            required_fields = [
                "priority_id", "state_id", "asset_id", "asset_name",
                "priority_band", "state_type", "state_family",
                "value_at_risk_per_day", "confidence", "confidence_band"
            ]
            
            for field in required_fields:
                assert field in action, f"Missing field in action: {field}"
            
            # Validate confidence is between 0 and 1
            assert 0 <= action["confidence"] <= 1, f"Confidence {action['confidence']} out of range"
            
            # Validate band is valid
            valid_bands = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
            assert action["priority_band"] in valid_bands, f"Invalid priority band: {action['priority_band']}"
            
            valid_confidence_bands = ["HIGH", "MEDIUM", "LOW", "INSUFFICIENT"]
            assert action["confidence_band"] in valid_confidence_bands
            
            print(f"✓ Top action: {action['asset_name']} ({action['priority_band']})")
            print(f"  VaR: ${action['value_at_risk_per_day']}/day, Confidence: {action['confidence']} ({action['confidence_band']})")
        else:
            print("✓ No top actions currently (empty list is valid)")
    
    def test_recovered_value_structure(self):
        """Test Value Recovered section structure (Section 3)"""
        response = requests.get(f"{BASE_URL}/api/system/value-summary")
        data = response.json()
        
        recovered = data["recovered_value"]
        
        # Required fields
        assert "total_savings" in recovered, "Missing total_savings"
        assert "verified_outcomes_count" in recovered, "Missing verified_outcomes_count"
        assert "recent_outcomes" in recovered, "Missing recent_outcomes"
        
        assert isinstance(recovered["total_savings"], (int, float)), "total_savings must be numeric"
        assert isinstance(recovered["recent_outcomes"], list), "recent_outcomes must be a list"
        
        if len(recovered["recent_outcomes"]) > 0:
            outcome = recovered["recent_outcomes"][0]
            
            # Required fields for each outcome
            required_fields = [
                "outcome_id", "asset_name", "intervention_type",
                "savings_value", "savings_unit", "savings_type",
                "confidence", "confidence_band", "time_to_verify_hours"
            ]
            
            for field in required_fields:
                assert field in outcome, f"Missing field in outcome: {field}"
            
            print(f"✓ Recent outcome: {outcome['asset_name']}")
            print(f"  Savings: {outcome['savings_value']} {outcome['savings_unit']}, Time to verify: {outcome['time_to_verify_hours']}h")
        else:
            print("✓ No verified outcomes yet (empty list is valid)")
    
    def test_loop_integrity_structure(self):
        """Test Loop Integrity section structure (Section 4)"""
        response = requests.get(f"{BASE_URL}/api/system/value-summary")
        data = response.json()
        
        integrity = data["loop_integrity"]
        
        # Required fields
        assert "verified" in integrity, "Missing verified count"
        assert "pending" in integrity, "Missing pending count"
        assert "insufficient_data" in integrity, "Missing insufficient_data count"
        assert "total_outcomes" in integrity, "Missing total_outcomes"
        assert "verification_rate_percent" in integrity, "Missing verification_rate_percent"
        assert "status" in integrity, "Missing status"
        
        # Validate counts are non-negative integers
        for field in ["verified", "pending", "insufficient_data", "total_outcomes"]:
            assert isinstance(integrity[field], int), f"{field} must be integer"
            assert integrity[field] >= 0, f"{field} must be non-negative"
        
        # Validate status is one of expected values
        valid_statuses = ["HEALTHY", "DEGRADED", "POOR"]
        assert integrity["status"] in valid_statuses, f"Invalid status: {integrity['status']}"
        
        # Validation: total should equal sum of categories
        expected_total = integrity["verified"] + integrity["pending"] + integrity["insufficient_data"]
        assert integrity["total_outcomes"] == expected_total, "Total doesn't match sum"
        
        print(f"✓ Loop Integrity: {integrity['status']}")
        print(f"  Verified: {integrity['verified']}, Pending: {integrity['pending']}, Insufficient: {integrity['insufficient_data']}")
        print(f"  Verification Rate: {integrity['verification_rate_percent']}%")
    
    def test_loop_status_based_on_verification_rate(self):
        """Test that loop status correctly reflects verification rate"""
        response = requests.get(f"{BASE_URL}/api/system/value-summary")
        data = response.json()
        
        integrity = data["loop_integrity"]
        rate = integrity["verification_rate_percent"]
        status = integrity["status"]
        
        # Rule: >= 70% = HEALTHY, >= 40% = DEGRADED, < 40% = POOR
        if rate is None:
            # No processed outcomes - should default to HEALTHY
            assert status == "HEALTHY", f"Expected HEALTHY when rate is None, got {status}"
            print("✓ Status is HEALTHY when no outcomes processed")
        elif rate >= 70:
            assert status == "HEALTHY", f"Expected HEALTHY for {rate}%, got {status}"
            print(f"✓ Status is HEALTHY for {rate}%")
        elif rate >= 40:
            assert status == "DEGRADED", f"Expected DEGRADED for {rate}%, got {status}"
            print(f"✓ Status is DEGRADED for {rate}%")
        else:
            assert status == "POOR", f"Expected POOR for {rate}%, got {status}"
            print(f"✓ Status is POOR for {rate}%")


class TestRunDemoEndpoint:
    """Tests for POST /api/system/demo/complete-verification-flow endpoint"""
    
    def test_run_demo_creates_full_flow(self):
        """Test Run Demo creates complete verification flow"""
        response = requests.post(f"{BASE_URL}/api/system/demo/complete-verification-flow")
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "complete"
        assert "flow_summary" in data
        
        flow = data["flow_summary"]
        
        # Verify all steps created
        steps = ["1_baseline", "2_state", "3_priority", "4_intervention", "5_outcome"]
        for step in steps:
            assert step in flow, f"Missing step: {step}"
            
        # Verify outcome is VERIFIED with savings
        outcome = flow["5_outcome"]
        assert outcome["status"] == "VERIFIED", f"Expected VERIFIED, got {outcome['status']}"
        assert outcome["savings_value"] is not None
        assert outcome["confidence_band"] is not None
        
        print(f"✓ Full flow created: baseline→state→priority→intervention→outcome")
        print(f"✓ Outcome: status={outcome['status']}, savings={outcome['savings_value']}")
    
    def test_run_demo_updates_value_summary(self):
        """Test that Run Demo updates the value summary"""
        # Run demo
        requests.post(f"{BASE_URL}/api/system/demo/complete-verification-flow")
        
        # Get value summary
        response = requests.get(f"{BASE_URL}/api/system/value-summary")
        data = response.json()
        
        # After demo, should have at least 1 verified outcome
        assert data["loop_integrity"]["verified"] >= 1, "Should have at least 1 verified outcome after demo"
        
        # Should have total savings > 0
        assert data["recovered_value"]["total_savings"] > 0, "Should have savings after demo"
        
        print(f"✓ Value summary updated after demo")
        print(f"  Verified: {data['loop_integrity']['verified']}")
        print(f"  Total savings: ${data['recovered_value']['total_savings']}")


class TestInterventionCreation:
    """Tests for POST /api/how/interventions endpoint"""
    
    def test_intervention_creation(self):
        """Test creating an intervention"""
        # First ensure we have data by running demo
        requests.post(f"{BASE_URL}/api/system/demo/complete-verification-flow")
        
        # Get top actions
        summary_response = requests.get(f"{BASE_URL}/api/system/value-summary")
        top_actions = summary_response.json().get("top_actions", [])
        
        if len(top_actions) > 0:
            action = top_actions[0]
            state_id = action["state_id"]
            
            # Create intervention
            intervention_response = requests.post(f"{BASE_URL}/api/how/interventions", json={
                "state_id": state_id,
                "intervention_type": "CALIBRATION",
                "description": "Test intervention from automated testing",
                "created_by": "test@example.com"
            })
            
            assert intervention_response.status_code == 200
            data = intervention_response.json()
            
            assert "intervention_id" in data
            assert "message" in data
            # Message should indicate baseline was frozen
            assert "frozen" in data["message"].lower(), f"Expected 'frozen' in message, got: {data['message']}"
            
            print(f"✓ Intervention created: {data['intervention_id']}")
            print(f"✓ Message: {data['message']}")
        else:
            print("! No active actions to create intervention on")
            pytest.skip("No active actions available")


class TestValueBreakdownByBand:
    """Tests for VaR breakdown by priority band"""
    
    def test_var_breakdown_sums_to_total(self):
        """Test that VaR breakdown by band sums to total"""
        response = requests.get(f"{BASE_URL}/api/system/value-summary")
        data = response.json()
        
        var = data["value_at_risk"]
        breakdown = var["breakdown_by_band"]
        
        # Sum all bands
        total_from_breakdown = sum(breakdown.values())
        
        # Should equal total (with small tolerance for rounding)
        difference = abs(var["total_per_day"] - total_from_breakdown)
        assert difference < 0.01, f"Breakdown sum ({total_from_breakdown}) doesn't match total ({var['total_per_day']})"
        
        print(f"✓ VaR breakdown sum: ${total_from_breakdown} matches total: ${var['total_per_day']}")


class TestTopActionsLimit:
    """Tests for top actions limit"""
    
    def test_top_actions_limited_to_max(self):
        """Test that top_actions returns max 5 items"""
        response = requests.get(f"{BASE_URL}/api/system/value-summary")
        data = response.json()
        
        top_actions = data["top_actions"]
        
        # Should be at most 5 items
        assert len(top_actions) <= 5, f"Expected max 5 top actions, got {len(top_actions)}"
        
        print(f"✓ Top actions count: {len(top_actions)} (max 5)")


class TestDataConsistency:
    """Tests for data consistency across value summary"""
    
    def test_verified_count_matches_outcomes_list(self):
        """Test that verified count matches recent outcomes list length"""
        response = requests.get(f"{BASE_URL}/api/system/value-summary")
        data = response.json()
        
        recovered = data["recovered_value"]
        
        # verified_outcomes_count should equal length of recent_outcomes
        # Note: recent_outcomes may be limited to 5, so we compare with min
        if recovered["verified_outcomes_count"] <= 5:
            assert recovered["verified_outcomes_count"] == len(recovered["recent_outcomes"])
        else:
            # If more than 5 verified, recent_outcomes should have 5
            assert len(recovered["recent_outcomes"]) == 5
            
        print(f"✓ Verified count: {recovered['verified_outcomes_count']}, Recent outcomes shown: {len(recovered['recent_outcomes'])}")


# Run specific test to verify critical path
if __name__ == "__main__":
    import sys
    pytest.main([__file__, "-v", "--tb=short"])
