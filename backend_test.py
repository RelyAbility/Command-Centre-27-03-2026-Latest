#!/usr/bin/env python3
"""
RAMP Command Centre MVP Backend Testing
======================================

Tests all backend APIs and event flows as specified in the review request:
- System health check at /api/system/health
- Seed demo data at POST /api/system/seed
- Simulate active drift at POST /api/system/demo/simulate-drift
- HOW lens APIs (priorities, asset states, interventions)
- WHERE lens APIs (portfolio summary, site states)
- Event flow verification
"""

import requests
import json
import time
import sys
from datetime import datetime
from typing import Dict, Any, Optional

class RAMPAPITester:
    def __init__(self, base_url="https://ramp-industrial-ai.preview.emergentagent.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.tests_run = 0
        self.tests_passed = 0
        self.test_data = {}  # Store created entities for later tests
        
    def log(self, message: str, level: str = "INFO"):
        """Log test messages with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def run_test(self, name: str, method: str, endpoint: str, expected_status: int = 200, 
                 data: Optional[Dict] = None, headers: Optional[Dict] = None) -> tuple[bool, Dict]:
        """Run a single API test and return success status and response data."""
        url = f"{self.base_url}{endpoint}"
        if headers is None:
            headers = {'Content-Type': 'application/json'}
        
        self.tests_run += 1
        self.log(f"🔍 Testing {name}...")
        self.log(f"   {method} {endpoint}")
        
        try:
            if method == 'GET':
                response = self.session.get(url, headers=headers)
            elif method == 'POST':
                response = self.session.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = self.session.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = self.session.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            success = response.status_code == expected_status
            
            try:
                response_data = response.json()
            except:
                response_data = {"raw_text": response.text}
            
            if success:
                self.tests_passed += 1
                self.log(f"✅ PASSED - Status: {response.status_code}")
                if response_data:
                    self.log(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
            else:
                self.log(f"❌ FAILED - Expected {expected_status}, got {response.status_code}")
                self.log(f"   Response: {json.dumps(response_data, indent=2)[:500]}...")
            
            return success, response_data
            
        except Exception as e:
            self.log(f"❌ FAILED - Error: {str(e)}", "ERROR")
            return False, {}
    
    def test_system_health(self) -> bool:
        """Test system health check."""
        success, data = self.run_test(
            "System Health Check",
            "GET",
            "/api/system/health"
        )
        
        if success:
            # Verify response structure
            required_fields = ["status", "version", "ramp_initialized"]
            missing_fields = [f for f in required_fields if f not in data]
            if missing_fields:
                self.log(f"❌ Missing fields in health response: {missing_fields}", "ERROR")
                return False
            
            if data.get("status") != "healthy":
                self.log(f"❌ System not healthy: {data.get('status')}", "ERROR")
                return False
        
        return success
    
    def test_seed_demo_data(self) -> bool:
        """Test seeding demo data."""
        success, data = self.run_test(
            "Seed Demo Data",
            "POST",
            "/api/system/seed"
        )
        
        if success:
            # Store seeded data info for later use
            self.test_data['seed_result'] = data
            
            # Verify seeding worked
            if data.get("status") != "seeded":
                self.log(f"❌ Seeding failed: {data}", "ERROR")
                return False
        
        return success
    
    def test_simulate_drift(self) -> bool:
        """Test simulating active drift condition."""
        success, data = self.run_test(
            "Simulate Active Drift",
            "POST",
            "/api/system/demo/simulate-drift"
        )
        
        if success:
            # Store drift simulation results
            self.test_data['drift_result'] = data
            
            # Verify drift simulation worked
            required_fields = ["status", "asset_id", "signals_ingested", "active_states"]
            missing_fields = [f for f in required_fields if f not in data]
            if missing_fields:
                self.log(f"❌ Missing fields in drift response: {missing_fields}", "ERROR")
                return False
            
            if data.get("status") != "simulated":
                self.log(f"❌ Drift simulation failed: {data.get('status')}", "ERROR")
                return False
            
            # Check that signals were ingested and states created
            if data.get("signals_ingested", 0) == 0:
                self.log("❌ No signals were ingested during drift simulation", "ERROR")
                return False
        
        return success
    
    def test_how_priorities(self) -> bool:
        """Test HOW lens - get active priorities."""
        success, data = self.run_test(
            "HOW Lens: Get Priorities",
            "GET",
            "/api/how/priorities"
        )
        
        if success:
            # Store priorities for later tests
            self.test_data['priorities'] = data
            
            # Verify response structure
            if "priorities" not in data or "count" not in data:
                self.log("❌ Invalid priorities response structure", "ERROR")
                return False
            
            priorities = data.get("priorities", [])
            self.log(f"   Found {len(priorities)} active priorities")
            
            # If there are priorities, verify structure
            if priorities:
                first_priority = priorities[0]
                required_fields = ["priority_id", "asset_id", "state_id", "priority_band", "drivers"]
                missing_fields = [f for f in required_fields if f not in first_priority]
                if missing_fields:
                    self.log(f"❌ Missing fields in priority: {missing_fields}", "ERROR")
                    return False
        
        return success
    
    def test_how_asset_state(self) -> bool:
        """Test HOW lens - get asset state information."""
        # Use asset from drift simulation
        asset_id = self.test_data.get('drift_result', {}).get('asset_id', 'asset-comp-001')
        
        success, data = self.run_test(
            f"HOW Lens: Get Asset State ({asset_id})",
            "GET",
            f"/api/how/assets/{asset_id}/state"
        )
        
        if success:
            # Verify response structure
            required_fields = ["asset_id", "asset_name", "active_states", "recent_states"]
            missing_fields = [f for f in required_fields if f not in data]
            if missing_fields:
                self.log(f"❌ Missing fields in asset state response: {missing_fields}", "ERROR")
                return False
            
            active_states = data.get("active_states", [])
            recent_states = data.get("recent_states", [])
            
            self.log(f"   Active states: {len(active_states)}, Recent states: {len(recent_states)}")
            
            # Store asset state for intervention tests
            self.test_data['asset_state'] = data
        
        return success
    
    def test_how_create_intervention(self) -> bool:
        """Test HOW lens - create intervention."""
        # Get active state from previous test
        asset_state = self.test_data.get('asset_state', {})
        active_states = asset_state.get('active_states', [])
        
        if not active_states:
            self.log("⚠️  No active states found for intervention test", "WARN")
            return True  # Skip test if no active states
        
        state_id = active_states[0].get('state_id')
        if not state_id:
            self.log("❌ No valid state_id found for intervention", "ERROR")
            return False
        
        intervention_data = {
            "state_id": state_id,
            "intervention_type": "adjustment",
            "description": "Test intervention for energy optimization",
            "created_by": "test_user"
        }
        
        success, data = self.run_test(
            "HOW Lens: Create Intervention",
            "POST",
            "/api/how/interventions",
            data=intervention_data
        )
        
        if success:
            # Store intervention ID for completion test
            self.test_data['intervention'] = data
            
            # Verify response structure
            required_fields = ["intervention_id", "state_id", "message"]
            missing_fields = [f for f in required_fields if f not in data]
            if missing_fields:
                self.log(f"❌ Missing fields in intervention response: {missing_fields}", "ERROR")
                return False
        
        return success
    
    def test_how_complete_intervention(self) -> bool:
        """Test HOW lens - complete intervention."""
        intervention = self.test_data.get('intervention', {})
        intervention_id = intervention.get('intervention_id')
        
        if not intervention_id:
            self.log("⚠️  No intervention ID found for completion test", "WARN")
            return True  # Skip test if no intervention created
        
        completion_data = {
            "intervention_id": intervention_id
        }
        
        success, data = self.run_test(
            "HOW Lens: Complete Intervention",
            "POST",
            "/api/how/interventions/complete",
            data=completion_data
        )
        
        if success:
            # Verify response structure
            required_fields = ["intervention_id", "message"]
            missing_fields = [f for f in required_fields if f not in data]
            if missing_fields:
                self.log(f"❌ Missing fields in completion response: {missing_fields}", "ERROR")
                return False
        
        return success
    
    def test_where_priorities_summary(self) -> bool:
        """Test WHERE lens - get priorities summary."""
        success, data = self.run_test(
            "WHERE Lens: Get Priorities Summary",
            "GET",
            "/api/where/priorities/summary"
        )
        
        if success:
            # Verify response structure
            required_fields = ["distribution", "total_active", "total_value_at_risk_per_day", "currency"]
            missing_fields = [f for f in required_fields if f not in data]
            if missing_fields:
                self.log(f"❌ Missing fields in priorities summary: {missing_fields}", "ERROR")
                return False
            
            distribution = data.get("distribution", {})
            total_active = data.get("total_active", 0)
            
            self.log(f"   Priority distribution: {distribution}")
            self.log(f"   Total active priorities: {total_active}")
        
        return success
    
    def test_where_site_states(self) -> bool:
        """Test WHERE lens - get site states."""
        # Use a test site ID - in a real system this would come from seed data
        site_id = "site-factory-001"  # This should exist in seeded data
        
        success, data = self.run_test(
            f"WHERE Lens: Get Site States ({site_id})",
            "GET",
            f"/api/where/sites/{site_id}/states"
        )
        
        if success:
            # Verify response structure
            required_fields = ["site_id", "total_active_states", "state_distribution", "asset_count"]
            missing_fields = [f for f in required_fields if f not in data]
            if missing_fields:
                self.log(f"❌ Missing fields in site states response: {missing_fields}", "ERROR")
                return False
            
            total_states = data.get("total_active_states", 0)
            asset_count = data.get("asset_count", 0)
            
            self.log(f"   Total active states: {total_states}, Assets: {asset_count}")
        
        return success
    
    def test_event_flow_verification(self) -> bool:
        """Verify the event flow works: signal_ingested → metric_calculated → state_started → priority_created."""
        self.log("🔄 Verifying event flow by checking created entities...")
        
        # Check if drift simulation created the expected chain of entities
        drift_result = self.test_data.get('drift_result', {})
        
        # Verify signals were ingested
        signals_ingested = drift_result.get("signals_ingested", 0)
        if signals_ingested == 0:
            self.log("❌ Event flow: No signals were ingested", "ERROR")
            return False
        
        self.log(f"✅ Event flow: {signals_ingested} signals ingested")
        
        # Verify baselines were established
        baselines = drift_result.get("baselines_established", 0)
        if baselines == 0:
            self.log("❌ Event flow: No baselines were established", "ERROR")
            return False
        
        self.log(f"✅ Event flow: {baselines} baselines established")
        
        # Verify states were created
        active_states = drift_result.get("active_states", 0)
        if active_states == 0:
            self.log("❌ Event flow: No active states were created", "ERROR")
            return False
        
        self.log(f"✅ Event flow: {active_states} active states created")
        
        # Verify priorities were created
        priorities_data = self.test_data.get('priorities', {})
        priority_count = priorities_data.get("count", 0)
        if priority_count == 0:
            self.log("❌ Event flow: No priorities were created", "ERROR")
            return False
        
        self.log(f"✅ Event flow: {priority_count} priorities created")
        
        self.log("✅ Complete event flow verified: Signal → Baseline → State → Priority")
        return True
    
    def run_comprehensive_test(self) -> bool:
        """Run all tests in the proper sequence."""
        self.log("🚀 Starting RAMP Command Centre MVP Backend Testing")
        self.log("=" * 60)
        
        # Test sequence - order matters for data dependencies
        test_sequence = [
            ("System Health Check", self.test_system_health),
            ("Seed Demo Data", self.test_seed_demo_data),
            ("Simulate Active Drift", self.test_simulate_drift),
            ("HOW Lens: Priorities", self.test_how_priorities),
            ("HOW Lens: Asset State", self.test_how_asset_state),
            ("HOW Lens: Create Intervention", self.test_how_create_intervention),
            ("HOW Lens: Complete Intervention", self.test_how_complete_intervention),
            ("WHERE Lens: Priorities Summary", self.test_where_priorities_summary),
            ("WHERE Lens: Site States", self.test_where_site_states),
            ("Event Flow Verification", self.test_event_flow_verification)
        ]
        
        all_passed = True
        failed_tests = []
        
        for test_name, test_func in test_sequence:
            self.log("-" * 40)
            try:
                result = test_func()
                if not result:
                    all_passed = False
                    failed_tests.append(test_name)
            except Exception as e:
                self.log(f"❌ {test_name} failed with exception: {str(e)}", "ERROR")
                all_passed = False
                failed_tests.append(test_name)
            
            # Small delay between tests
            time.sleep(0.5)
        
        # Print summary
        self.log("=" * 60)
        self.log("📊 TESTING SUMMARY")
        self.log(f"   Total tests run: {self.tests_run}")
        self.log(f"   Tests passed: {self.tests_passed}")
        self.log(f"   Tests failed: {self.tests_run - self.tests_passed}")
        self.log(f"   Success rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if failed_tests:
            self.log(f"   Failed tests: {', '.join(failed_tests)}", "ERROR")
        
        if all_passed:
            self.log("🎉 ALL TESTS PASSED - RAMP MVP is working correctly!")
        else:
            self.log("⚠️  Some tests failed - see details above", "WARN")
        
        return all_passed


def main():
    """Main test execution."""
    tester = RAMPAPITester()
    success = tester.run_comprehensive_test()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())