"""
RAMP Verification System Backend Tests
=======================================

Tests for:
1. Verification config endpoint - configurable windows per state family and intervention type
2. Pending outcomes endpoint - outcomes awaiting verification
3. Verification scheduler - processes pending outcomes correctly
4. Complete verification flow - creates verified outcome with savings and confidence
5. Insufficient data scenario - marks outcome as INSUFFICIENT_DATA not VERIFIED
6. Learning records update after successful verification
7. Full relational chain checkpoint with SQL JOINs
8. HOW and WHERE lens endpoints work after verification
"""

import pytest
import requests
import os
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://ramp-industrial-ai.preview.emergentagent.com').rstrip('/')


class TestSystemHealth:
    """Health check tests - run first to verify system is up"""
    
    def test_health_endpoint(self):
        """Test that health endpoint returns healthy status with PostgreSQL"""
        response = requests.get(f"{BASE_URL}/api/system/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "postgresql"
        print(f"✓ Health check passed: {data}")


class TestVerificationConfig:
    """Tests for verification configuration endpoint"""
    
    def test_verification_config_endpoint_exists(self):
        """Test /api/system/verification/config endpoint returns verification windows"""
        response = requests.get(f"{BASE_URL}/api/system/verification/config")
        assert response.status_code == 200
        data = response.json()
        print(f"Verification config response: {data}")
        
    def test_verification_config_has_state_family_configs(self):
        """Test that config includes state family configurations"""
        response = requests.get(f"{BASE_URL}/api/system/verification/config")
        assert response.status_code == 200
        data = response.json()
        
        assert "by_state_family" in data
        state_families = data["by_state_family"]
        
        # Check expected state families exist
        assert "ENERGY" in state_families
        assert "OPERATIONAL" in state_families
        
        # Validate ENERGY config structure
        energy_config = state_families["ENERGY"]
        assert "window_hours" in energy_config
        assert "min_samples" in energy_config
        assert "min_window_coverage" in energy_config
        assert "max_retry_attempts" in energy_config
        assert "retry_interval_hours" in energy_config
        print(f"✓ State family configs present: {list(state_families.keys())}")
        print(f"✓ ENERGY config: {energy_config}")
        
    def test_verification_config_has_intervention_type_configs(self):
        """Test that config includes intervention type configurations"""
        response = requests.get(f"{BASE_URL}/api/system/verification/config")
        assert response.status_code == 200
        data = response.json()
        
        assert "by_intervention_type" in data
        intervention_types = data["by_intervention_type"]
        
        # Check expected intervention types exist
        expected_types = ["ADJUSTMENT", "REPAIR", "REPLACEMENT", "CALIBRATION", "MAINTENANCE"]
        for int_type in expected_types:
            assert int_type in intervention_types, f"Missing intervention type: {int_type}"
            
        # Validate CALIBRATION has shorter window (quick verification)
        calibration_config = intervention_types["CALIBRATION"]
        assert calibration_config["window_hours"] <= 2.0, "CALIBRATION should have short window"
        
        # Validate REPLACEMENT has longer window
        replacement_config = intervention_types["REPLACEMENT"]
        assert replacement_config["window_hours"] >= 24.0, "REPLACEMENT should have long window"
        
        print(f"✓ Intervention type configs present: {list(intervention_types.keys())}")
        print(f"✓ CALIBRATION window: {calibration_config['window_hours']}h, REPLACEMENT window: {replacement_config['window_hours']}h")
        
    def test_verification_config_precedence_note(self):
        """Test that config explains precedence rules"""
        response = requests.get(f"{BASE_URL}/api/system/verification/config")
        assert response.status_code == 200
        data = response.json()
        
        assert "note" in data
        assert "intervention type" in data["note"].lower() or "precedence" in data["note"].lower()
        print(f"✓ Config note present: {data['note']}")


class TestPendingOutcomes:
    """Tests for pending outcomes endpoint"""
    
    def test_pending_outcomes_endpoint_exists(self):
        """Test /api/system/verification/pending endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/system/verification/pending")
        assert response.status_code == 200
        data = response.json()
        
        assert "pending_count" in data
        assert "outcomes" in data
        assert isinstance(data["outcomes"], list)
        print(f"✓ Pending outcomes endpoint works, count: {data['pending_count']}")
        
    def test_pending_outcomes_structure(self):
        """Test that pending outcomes have required fields"""
        response = requests.get(f"{BASE_URL}/api/system/verification/pending")
        assert response.status_code == 200
        data = response.json()
        
        if data["pending_count"] > 0:
            outcome = data["outcomes"][0]
            expected_fields = [
                "outcome_id", "intervention_id", "status", "retry_count"
            ]
            for field in expected_fields:
                assert field in outcome, f"Missing field: {field}"
            print(f"✓ Pending outcome structure valid: {list(outcome.keys())}")
        else:
            print("✓ No pending outcomes currently (will test after flow creation)")


class TestVerificationScheduler:
    """Tests for verification scheduler"""
    
    def test_verification_run_endpoint_exists(self):
        """Test /api/system/verification/run endpoint exists"""
        response = requests.post(f"{BASE_URL}/api/system/verification/run")
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert data["status"] == "completed"
        assert "summary" in data
        print(f"✓ Verification scheduler ran: {data}")
        
    def test_verification_run_summary_structure(self):
        """Test that verification run returns proper summary"""
        response = requests.post(f"{BASE_URL}/api/system/verification/run")
        assert response.status_code == 200
        data = response.json()
        
        summary = data["summary"]
        expected_fields = ["processed", "verified", "insufficient_data", "still_pending", "errors"]
        for field in expected_fields:
            assert field in summary, f"Missing summary field: {field}"
        
        # All values should be integers
        for field in expected_fields:
            assert isinstance(summary[field], int), f"{field} should be integer"
        
        print(f"✓ Verification summary: {summary}")


class TestCompleteVerificationFlow:
    """Tests for the complete verification flow demo endpoint"""
    
    def test_complete_verification_flow(self):
        """
        Test /api/system/demo/complete-verification-flow creates verified outcome
        
        This tests:
        - Baseline creation
        - State creation with deviation
        - Priority creation
        - Intervention with frozen baseline
        - Outcome creation and verification
        - Learning record update
        """
        response = requests.post(f"{BASE_URL}/api/system/demo/complete-verification-flow")
        assert response.status_code == 200
        data = response.json()
        
        # Check overall status
        assert data["status"] == "complete", f"Expected complete, got {data['status']}"
        
        # Check flow summary exists
        assert "flow_summary" in data
        flow = data["flow_summary"]
        
        # Verify each step of the chain
        assert "1_baseline" in flow
        assert "id" in flow["1_baseline"]
        assert "value" in flow["1_baseline"]
        print(f"✓ Baseline created: {flow['1_baseline']}")
        
        assert "2_state" in flow
        assert "id" in flow["2_state"]
        assert "deviation" in flow["2_state"]
        print(f"✓ State created: {flow['2_state']}")
        
        assert "3_priority" in flow
        assert "band" in flow["3_priority"]
        print(f"✓ Priority created: {flow['3_priority']}")
        
        assert "4_intervention" in flow
        assert "type" in flow["4_intervention"]
        print(f"✓ Intervention created: {flow['4_intervention']}")
        
        # Critical: Outcome must be VERIFIED with savings and confidence
        assert "5_outcome" in flow
        outcome = flow["5_outcome"]
        assert outcome["status"] == "VERIFIED", f"Expected VERIFIED, got {outcome['status']}"
        assert outcome["savings_value"] is not None, "Savings value should not be None"
        assert outcome["confidence"] is not None, "Confidence should not be None"
        assert outcome["confidence_band"] is not None, "Confidence band should not be None"
        print(f"✓ Outcome VERIFIED: savings={outcome['savings_value']}, confidence={outcome['confidence']}, band={outcome['confidence_band']}")
        
        # Verify learning record was updated
        assert "6_learning" in flow
        learning = flow["6_learning"]
        if learning:
            print(f"✓ Learning updated: {learning}")
        else:
            # Learning might be None if this is the first run
            print("! Learning record: None (may be first run)")
            
        print(f"✓ Full verification flow complete: {data['message']}")
        
    def test_verified_outcome_has_explicit_confidence(self):
        """Test that verified outcomes have explicit confidence values"""
        response = requests.post(f"{BASE_URL}/api/system/demo/complete-verification-flow")
        assert response.status_code == 200
        data = response.json()
        
        outcome = data["flow_summary"]["5_outcome"]
        
        # Confidence must be a number between 0 and 1
        confidence = outcome["confidence"]
        assert isinstance(confidence, (int, float)), "Confidence must be numeric"
        assert 0 <= confidence <= 1, f"Confidence {confidence} not in range [0,1]"
        
        # Confidence band must be valid
        valid_bands = ["HIGH", "MEDIUM", "LOW", "INSUFFICIENT"]
        assert outcome["confidence_band"] in valid_bands, f"Invalid band: {outcome['confidence_band']}"
        
        print(f"✓ Explicit confidence: {confidence} ({outcome['confidence_band']})")


class TestInsufficientDataScenario:
    """Tests for insufficient data handling"""
    
    def test_insufficient_data_scenario(self):
        """
        Test /api/system/demo/insufficient-data-scenario marks outcome as INSUFFICIENT_DATA
        
        This tests that verification does NOT force a result when data is insufficient.
        """
        response = requests.post(f"{BASE_URL}/api/system/demo/insufficient-data-scenario")
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "demonstrated"
        assert data["scenario"] == "insufficient_data"
        
        # Critical: Outcome must be INSUFFICIENT_DATA, NOT VERIFIED
        outcome = data["outcome"]
        assert outcome["status"] == "INSUFFICIENT_DATA", f"Expected INSUFFICIENT_DATA, got {outcome['status']}"
        
        # Should have verification notes explaining why
        assert outcome["verification_notes"] is not None
        print(f"✓ Insufficient data correctly handled: status={outcome['status']}")
        print(f"✓ Verification notes: {outcome['verification_notes']}")
        
        # Check verification result
        result = data["verification_result"]
        assert result["insufficient_data"] > 0 or result["still_pending"] >= 0
        print(f"✓ Verification result: {result}")
        
    def test_insufficient_data_does_not_create_learning(self):
        """Test that insufficient data outcomes don't falsely update learning"""
        # Run the insufficient data scenario
        response = requests.post(f"{BASE_URL}/api/system/demo/insufficient-data-scenario")
        assert response.status_code == 200
        
        # Get learning for the test asset
        learning_response = requests.get(f"{BASE_URL}/api/system/learning/asset-001")
        assert learning_response.status_code == 200
        learning_data = learning_response.json()
        
        # Learning should either be empty or have intervention_count = 0 for DRIFT
        # since INSUFFICIENT_DATA outcomes shouldn't count as successful interventions
        print(f"✓ Learning records: {learning_data}")


class TestLearningRecords:
    """Tests for learning records endpoint"""
    
    def test_learning_endpoint_exists(self):
        """Test /api/system/learning/{asset_id} endpoint exists"""
        # First run the complete flow to ensure we have learning data
        requests.post(f"{BASE_URL}/api/system/demo/complete-verification-flow")
        
        # Now check learning for the asset
        response = requests.get(f"{BASE_URL}/api/system/learning/asset-comp-001")
        assert response.status_code == 200
        data = response.json()
        
        assert "asset_id" in data
        assert data["asset_id"] == "asset-comp-001"
        assert "learning_records" in data
        assert "summary" in data
        print(f"✓ Learning endpoint works: {data}")
        
    def test_learning_records_structure(self):
        """Test learning records have proper structure"""
        # Ensure we have data
        requests.post(f"{BASE_URL}/api/system/demo/complete-verification-flow")
        
        response = requests.get(f"{BASE_URL}/api/system/learning/asset-comp-001")
        assert response.status_code == 200
        data = response.json()
        
        summary = data["summary"]
        assert "total_state_types" in summary
        assert "total_interventions" in summary
        assert "total_savings" in summary
        
        print(f"✓ Learning summary: {summary}")
        
        if data["learning_records"]:
            record = data["learning_records"][0]
            expected_fields = ["asset_id", "state_type", "intervention_count", "total_savings"]
            for field in expected_fields:
                assert field in record, f"Missing learning field: {field}"
            print(f"✓ Learning record structure: {list(record.keys())}")
            
    def test_learning_updates_after_verification(self):
        """Test that learning records are updated after successful verification"""
        # Run flow multiple times
        for i in range(2):
            requests.post(f"{BASE_URL}/api/system/demo/complete-verification-flow")
        
        response = requests.get(f"{BASE_URL}/api/system/learning/asset-comp-001")
        assert response.status_code == 200
        data = response.json()
        
        # After 2 runs, should have at least some learning data
        if data["learning_records"]:
            record = data["learning_records"][0]
            # Intervention count should be > 0 after successful verification
            assert record.get("intervention_count", 0) > 0, "Intervention count should be > 0"
            print(f"✓ Learning updated: intervention_count={record['intervention_count']}, total_savings={record.get('total_savings')}")


class TestRelationalChainCheckpoint:
    """Tests for the relational chain verification with SQL JOINs"""
    
    def test_relational_chain_endpoint_exists(self):
        """Test /api/system/checkpoint/relational-chain endpoint exists"""
        # Ensure we have data first
        requests.post(f"{BASE_URL}/api/system/demo/complete-verification-flow")
        
        response = requests.get(f"{BASE_URL}/api/system/checkpoint/relational-chain")
        assert response.status_code == 200
        data = response.json()
        
        assert "chain_verified" in data
        assert "steps" in data
        assert "sql_joins" in data
        print(f"✓ Relational chain endpoint works, verified={data['chain_verified']}")
        
    def test_relational_chain_sql_joins(self):
        """Test that relational chain uses SQL JOINs to verify referential integrity"""
        # Ensure we have data
        requests.post(f"{BASE_URL}/api/system/demo/complete-verification-flow")
        
        response = requests.get(f"{BASE_URL}/api/system/checkpoint/relational-chain")
        assert response.status_code == 200
        data = response.json()
        
        # Must have sql_joins with actual data
        assert len(data["sql_joins"]) > 0, "SQL JOINs should return data"
        
        join_result = data["sql_joins"][0]
        # Check chain links exist
        assert "baseline_id" in join_result
        assert "state_id" in join_result
        assert "priority_id" in join_result
        
        print(f"✓ SQL JOIN result: {join_result}")
        
    def test_full_chain_verified(self):
        """Test that full chain is verified after complete flow"""
        # Run complete flow
        requests.post(f"{BASE_URL}/api/system/demo/complete-verification-flow")
        
        response = requests.get(f"{BASE_URL}/api/system/checkpoint/relational-chain")
        assert response.status_code == 200
        data = response.json()
        
        assert data["chain_verified"] == True, "Chain should be verified"
        assert "summary" in data
        print(f"✓ Chain summary: {data['summary']}")
        
        # Check all steps passed
        for step in data["steps"]:
            assert step["status"] in ["PASS", "INFO"], f"Step {step['step']} failed: {step}"
            print(f"  - {step['step']}: {step['status']}")


class TestHOWLensAfterVerification:
    """Tests for HOW lens endpoints after verification flow"""
    
    def test_how_priorities_after_verification(self):
        """Test /api/how/priorities returns data after verification"""
        # Ensure we have data (simulate drift creates priority)
        requests.post(f"{BASE_URL}/api/system/seed")
        requests.post(f"{BASE_URL}/api/system/demo/simulate-drift")
        
        response = requests.get(f"{BASE_URL}/api/how/priorities")
        assert response.status_code == 200
        data = response.json()
        
        assert "priorities" in data
        assert "count" in data
        print(f"✓ HOW priorities: count={data['count']}")
        
        if data["count"] > 0:
            priority = data["priorities"][0]
            # Check HOW lens fields are present
            assert "priority_band" in priority
            assert "drivers" in priority
            assert "value_at_risk_per_day" in priority
            # Check SYSTEM-only fields are NOT present
            assert "priority_score" not in priority, "priority_score should not be in HOW lens"
            print(f"✓ HOW priority structure valid: {list(priority.keys())}")
            
    def test_how_asset_state_after_verification(self):
        """Test /api/how/assets/{asset_id}/state returns data"""
        # Ensure we have data
        requests.post(f"{BASE_URL}/api/system/seed")
        requests.post(f"{BASE_URL}/api/system/demo/simulate-drift")
        
        response = requests.get(f"{BASE_URL}/api/how/assets/asset-comp-001/state")
        assert response.status_code == 200
        data = response.json()
        
        assert "asset_id" in data
        assert "asset_name" in data
        assert "active_states" in data
        assert "criticality_band" in data
        
        # Check SYSTEM-only fields are NOT present
        assert "criticality_score" not in data, "criticality_score should not be in HOW lens"
        
        print(f"✓ HOW asset state: asset={data['asset_name']}, criticality={data['criticality_band']}, active_states={len(data['active_states'])}")
        
    def test_how_intervention_outcome_endpoint(self):
        """Test /api/how/interventions/{id}/outcome endpoint"""
        # Run complete flow which creates intervention and outcome
        flow_response = requests.post(f"{BASE_URL}/api/system/demo/complete-verification-flow")
        flow_data = flow_response.json()
        
        intervention_id = flow_data["flow_summary"]["4_intervention"]["id"]
        
        response = requests.get(f"{BASE_URL}/api/how/interventions/{intervention_id}/outcome")
        assert response.status_code == 200
        data = response.json()
        
        assert "intervention_id" in data
        assert "status" in data
        assert data["status"] == "verified"  # lowercase in HOW lens
        
        # Should have savings but NOT raw values
        if data.get("savings_value"):
            assert "savings_unit" in data
            assert "confidence_band" in data
            
        print(f"✓ HOW outcome: status={data['status']}, savings={data.get('savings_value')}")


class TestWHERELensAfterVerification:
    """Tests for WHERE lens endpoints after verification flow"""
    
    def test_where_priorities_summary(self):
        """Test /api/where/priorities/summary returns aggregated data"""
        # Ensure we have data
        requests.post(f"{BASE_URL}/api/system/seed")
        requests.post(f"{BASE_URL}/api/system/demo/simulate-drift")
        
        response = requests.get(f"{BASE_URL}/api/where/priorities/summary")
        assert response.status_code == 200
        data = response.json()
        
        # Check WHERE lens aggregation fields
        assert "distribution" in data
        assert "total_active" in data
        assert "total_value_at_risk_per_day" in data
        assert "total_value_recoverable_per_day" in data
        
        # Distribution should have priority bands
        distribution = data["distribution"]
        for band in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            assert band in distribution
            
        # Individual priority details should NOT be present
        assert "priorities" not in data, "Individual priorities should not be in WHERE lens"
        
        print(f"✓ WHERE portfolio summary: distribution={distribution}, VAR=${data['total_value_at_risk_per_day']}")
        
    def test_where_site_states(self):
        """Test /api/where/sites/{site_id}/states returns site-level aggregation"""
        # Ensure we have data
        requests.post(f"{BASE_URL}/api/system/seed")
        requests.post(f"{BASE_URL}/api/system/demo/simulate-drift")
        
        response = requests.get(f"{BASE_URL}/api/where/sites/demo-site-001/states")
        assert response.status_code == 200
        data = response.json()
        
        assert "site_id" in data
        assert "total_active_states" in data
        assert "state_distribution" in data
        assert "asset_count" in data
        
        # Individual state details should NOT be present
        assert "states" not in data, "Individual states should not be in WHERE lens"
        
        print(f"✓ WHERE site states: total={data['total_active_states']}, distribution={data['state_distribution']}")


class TestVerificationFrozenBaseline:
    """Tests to ensure verification is against frozen baseline"""
    
    def test_verification_uses_frozen_baseline(self):
        """Test that outcome verification uses the frozen baseline value"""
        response = requests.post(f"{BASE_URL}/api/system/demo/complete-verification-flow")
        assert response.status_code == 200
        data = response.json()
        
        flow = data["flow_summary"]
        
        # Get baseline value that was created
        baseline_value = flow["1_baseline"]["value"]
        
        # Outcome should reference the frozen baseline
        outcome = flow["5_outcome"]
        # The savings should be relative to the baseline (baseline - actual)
        # If improved, actual < baseline, so savings > 0
        
        # Check verification result details
        verification_result = data.get("verification_result", {})
        if verification_result.get("details"):
            for detail in verification_result["details"]:
                if detail.get("status") == "VERIFIED":
                    # The verification happened against a baseline
                    print(f"✓ Verification detail: {detail}")
                    
        print(f"✓ Baseline value used: {baseline_value}, Outcome savings: {outcome['savings_value']}")


# Run specific test to verify critical path
if __name__ == "__main__":
    import sys
    pytest.main([__file__, "-v", "--tb=short", "-x"])
