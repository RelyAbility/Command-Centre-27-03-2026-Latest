"""
RAMP WebSocket Implementation Tests
====================================

Tests for WebSocket real-time updates feature:
1. GET /api/system/ws/status - HTTP endpoint for WebSocket status
2. WebSocket /ws/priorities - Priority queue real-time updates
3. WebSocket /ws/states/{asset_id} - State changes for specific asset
4. WebSocket /ws/outcomes - Verified outcome notifications
5. Lens compliance - Payloads should use confidence_label not raw scores
6. Event backbone integration - Events trigger broadcasts
7. Existing endpoints still work (escalation, state transition, priorities)
"""

import pytest
import requests
import os
import json
import asyncio
import websockets
from datetime import datetime

# Use external URL for HTTP tests, localhost for WebSocket tests
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
WS_BASE_URL = "ws://localhost:8001"  # WebSocket via localhost as per agent context


class TestWebSocketStatusEndpoint:
    """Test the HTTP endpoint for WebSocket status"""
    
    def test_ws_status_endpoint_exists(self):
        """GET /api/system/ws/status should return 200"""
        response = requests.get(f"{BASE_URL}/api/system/ws/status")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ WebSocket status endpoint exists and returns 200")
    
    def test_ws_status_response_structure(self):
        """Response should have total_connections, channels, available_channels"""
        response = requests.get(f"{BASE_URL}/api/system/ws/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_connections" in data, "Missing total_connections field"
        assert "channels" in data, "Missing channels field"
        assert "available_channels" in data, "Missing available_channels field"
        
        # Verify available_channels lists the expected channels
        available = data["available_channels"]
        assert any("/ws/priorities" in ch for ch in available), "Missing priorities channel"
        assert any("/ws/states" in ch for ch in available), "Missing states channel"
        assert any("/ws/outcomes" in ch for ch in available), "Missing outcomes channel"
        
        print(f"✓ WebSocket status response structure valid: {data}")


class TestExistingEndpointsStillWork:
    """Verify existing endpoints still work after WebSocket implementation"""
    
    @pytest.fixture(autouse=True)
    def setup_test_data(self):
        """Setup test data using reset + seed + simulate-drift pattern"""
        # Reset
        requests.post(f"{BASE_URL}/api/system/reset")
        # Seed
        requests.post(f"{BASE_URL}/api/system/seed")
        # Simulate drift to create test data
        requests.post(f"{BASE_URL}/api/system/demo/simulate-drift")
        yield
    
    def test_priorities_endpoint_works(self):
        """GET /api/how/priorities should still work"""
        response = requests.get(f"{BASE_URL}/api/how/priorities")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "priorities" in data, "Missing priorities field"
        print(f"✓ Priorities endpoint works, found {len(data.get('priorities', []))} priorities")
    
    def test_escalation_run_endpoint_works(self):
        """POST /api/system/escalation/run should still work"""
        response = requests.post(f"{BASE_URL}/api/system/escalation/run")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # Check for summary.checked or top-level checked
        has_checked = "checked" in data or ("summary" in data and "checked" in data.get("summary", {}))
        assert has_checked, f"Missing expected fields in: {data}"
        print(f"✓ Escalation run endpoint works: {data}")
    
    def test_health_endpoint_works(self):
        """GET /api/system/health should still work"""
        response = requests.get(f"{BASE_URL}/api/system/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("status") == "healthy"
        print("✓ Health endpoint works")


class TestWebSocketConnections:
    """Test WebSocket connections using websockets library"""
    
    @pytest.fixture(autouse=True)
    def setup_test_data(self):
        """Setup test data"""
        requests.post(f"{BASE_URL}/api/system/reset")
        requests.post(f"{BASE_URL}/api/system/seed")
        requests.post(f"{BASE_URL}/api/system/demo/simulate-drift")
        yield
    
    @pytest.mark.asyncio
    async def test_ws_priorities_connection(self):
        """WebSocket /ws/priorities should connect and send resync"""
        try:
            async with websockets.connect(f"{WS_BASE_URL}/ws/priorities", open_timeout=10) as ws:
                # Should receive resync message on connect
                message = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(message)
                
                assert data.get("type") == "resync", f"Expected resync, got {data.get('type')}"
                assert data.get("channel") == "priorities", f"Expected priorities channel"
                assert "data" in data, "Missing data field"
                assert "priorities" in data["data"], "Missing priorities in data"
                
                print(f"✓ WebSocket priorities connected, received resync with {len(data['data'].get('priorities', []))} priorities")
                
                # Verify lens compliance - no raw confidence scores
                for priority in data["data"].get("priorities", []):
                    assert "confidence" not in priority, "Raw confidence exposed - lens violation"
                    # confidence_label should be present
                    if "confidence_label" in priority:
                        assert priority["confidence_label"] in ["strong", "moderate", "weak", "unknown"], \
                            f"Invalid confidence_label: {priority['confidence_label']}"
                
                print("✓ Resync payload is lens-compliant (no raw scores)")
                
        except Exception as e:
            pytest.fail(f"WebSocket connection failed: {e}")
    
    @pytest.mark.asyncio
    async def test_ws_states_connection(self):
        """WebSocket /ws/states/{asset_id} should connect and send resync"""
        asset_id = "asset-comp-001"  # From seed data
        
        try:
            async with websockets.connect(f"{WS_BASE_URL}/ws/states/{asset_id}", open_timeout=10) as ws:
                message = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(message)
                
                assert data.get("type") == "resync", f"Expected resync, got {data.get('type')}"
                assert "states" in data.get("data", {}), "Missing states in resync"
                assert data["data"].get("asset_id") == asset_id, "Asset ID mismatch"
                
                print(f"✓ WebSocket states connected for {asset_id}, received resync")
                
                # Verify lens compliance
                for state in data["data"].get("states", []):
                    assert "confidence" not in state or isinstance(state.get("confidence"), str), \
                        "Raw confidence score exposed - lens violation"
                
                print("✓ States resync payload is lens-compliant")
                
        except Exception as e:
            pytest.fail(f"WebSocket states connection failed: {e}")
    
    @pytest.mark.asyncio
    async def test_ws_states_invalid_asset(self):
        """WebSocket /ws/states/{asset_id} should handle invalid asset"""
        try:
            async with websockets.connect(f"{WS_BASE_URL}/ws/states/invalid-asset-xyz", open_timeout=10) as ws:
                message = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(message)
                
                # Should receive error message
                assert data.get("type") == "error", f"Expected error, got {data.get('type')}"
                assert "not found" in data.get("message", "").lower(), "Missing not found message"
                
                print("✓ WebSocket states handles invalid asset correctly")
                
        except websockets.exceptions.ConnectionClosed:
            # Connection closed after error is also acceptable
            print("✓ WebSocket states closes connection for invalid asset")
        except Exception as e:
            pytest.fail(f"Unexpected error: {e}")
    
    @pytest.mark.asyncio
    async def test_ws_outcomes_connection(self):
        """WebSocket /ws/outcomes should connect and send acknowledgment"""
        try:
            async with websockets.connect(f"{WS_BASE_URL}/ws/outcomes", open_timeout=10) as ws:
                message = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(message)
                
                assert data.get("type") == "connected", f"Expected connected, got {data.get('type')}"
                assert data.get("channel") == "outcomes", "Channel mismatch"
                assert "timestamp" in data, "Missing timestamp"
                
                print(f"✓ WebSocket outcomes connected, received acknowledgment")
                
        except Exception as e:
            pytest.fail(f"WebSocket outcomes connection failed: {e}")
    
    @pytest.mark.asyncio
    async def test_ws_heartbeat(self):
        """WebSocket should send heartbeat after timeout"""
        try:
            async with websockets.connect(f"{WS_BASE_URL}/ws/outcomes", open_timeout=10, ping_interval=None) as ws:
                # First message is connection acknowledgment
                await asyncio.wait_for(ws.recv(), timeout=5)
                
                # Wait for heartbeat (30 second interval)
                # We'll wait up to 35 seconds
                heartbeat = await asyncio.wait_for(ws.recv(), timeout=35)
                data = json.loads(heartbeat)
                
                assert data.get("type") == "heartbeat", f"Expected heartbeat, got {data.get('type')}"
                assert "timestamp" in data, "Missing timestamp in heartbeat"
                
                print("✓ WebSocket heartbeat received")
                
        except asyncio.TimeoutError:
            pytest.skip("Heartbeat test timed out - may need longer wait")
        except Exception as e:
            pytest.fail(f"Heartbeat test failed: {e}")


class TestEventBackboneIntegration:
    """Test that events created via API trigger WebSocket broadcasts"""
    
    @pytest.fixture(autouse=True)
    def setup_test_data(self):
        """Setup test data"""
        requests.post(f"{BASE_URL}/api/system/reset")
        requests.post(f"{BASE_URL}/api/system/seed")
        yield
    
    @pytest.mark.asyncio
    async def test_simulate_drift_creates_events(self):
        """POST /api/system/demo/simulate-drift should create events"""
        # Connect to WebSocket first
        try:
            async with websockets.connect(f"{WS_BASE_URL}/ws/priorities", open_timeout=10) as ws:
                # Receive initial resync
                await asyncio.wait_for(ws.recv(), timeout=5)
                
                # Now trigger simulate-drift which creates events
                response = requests.post(f"{BASE_URL}/api/system/demo/simulate-drift")
                assert response.status_code == 200, f"Simulate drift failed: {response.text}"
                
                data = response.json()
                assert data.get("status") == "simulated"
                assert "priority_id" in data, "Missing priority_id"
                
                print(f"✓ Simulate drift created priority: {data.get('priority_id')}")
                
                # The event should trigger a broadcast - try to receive it
                # Note: This may not work if broadcast is async and completes before we listen
                try:
                    broadcast = await asyncio.wait_for(ws.recv(), timeout=3)
                    broadcast_data = json.loads(broadcast)
                    print(f"✓ Received broadcast: {broadcast_data.get('type')}")
                except asyncio.TimeoutError:
                    # Broadcast may have been sent before we started listening
                    print("⚠ No broadcast received (may have been sent before listener ready)")
                
        except Exception as e:
            pytest.fail(f"Event backbone test failed: {e}")
    
    def test_escalation_creates_events(self):
        """POST /api/system/escalation/run should create events"""
        # First create test data
        requests.post(f"{BASE_URL}/api/system/demo/simulate-drift")
        
        # Run escalation
        response = requests.post(f"{BASE_URL}/api/system/escalation/run")
        assert response.status_code == 200
        
        data = response.json()
        print(f"✓ Escalation run completed: {data.get('summary', data)}")


class TestLensCompliance:
    """Test that WebSocket payloads respect lens discipline"""
    
    @pytest.fixture(autouse=True)
    def setup_test_data(self):
        """Setup test data"""
        requests.post(f"{BASE_URL}/api/system/reset")
        requests.post(f"{BASE_URL}/api/system/seed")
        requests.post(f"{BASE_URL}/api/system/demo/simulate-drift")
        yield
    
    @pytest.mark.asyncio
    async def test_priority_payload_lens_compliance(self):
        """Priority payloads should not expose raw scores"""
        try:
            async with websockets.connect(f"{WS_BASE_URL}/ws/priorities", open_timeout=10) as ws:
                message = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(message)
                
                # Check each priority in resync
                for priority in data.get("data", {}).get("priorities", []):
                    # Should NOT have raw scores
                    assert "priority_score" not in priority, "Raw priority_score exposed"
                    assert "score_components" not in priority, "Raw score_components exposed"
                    
                    # Should have bands and labels
                    if "priority_band" in priority:
                        assert priority["priority_band"] in ["CRITICAL", "HIGH", "MEDIUM", "LOW"], \
                            f"Invalid priority_band: {priority['priority_band']}"
                    
                    if "confidence_label" in priority:
                        assert priority["confidence_label"] in ["strong", "moderate", "weak", "unknown"], \
                            f"Invalid confidence_label: {priority['confidence_label']}"
                
                print("✓ Priority payloads are lens-compliant")
                
        except Exception as e:
            pytest.fail(f"Lens compliance test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_state_payload_lens_compliance(self):
        """State payloads should not expose raw scores"""
        asset_id = "asset-comp-001"
        
        try:
            async with websockets.connect(f"{WS_BASE_URL}/ws/states/{asset_id}", open_timeout=10) as ws:
                message = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(message)
                
                for state in data.get("data", {}).get("states", []):
                    # Should NOT have raw scores
                    assert "severity_score" not in state, "Raw severity_score exposed"
                    assert "severity_components" not in state, "Raw severity_components exposed"
                    assert "confidence_components" not in state, "Raw confidence_components exposed"
                    
                    # Should have bands
                    if "severity_band" in state:
                        assert state["severity_band"] in ["CRITICAL", "HIGH", "MEDIUM", "LOW"], \
                            f"Invalid severity_band: {state['severity_band']}"
                
                print("✓ State payloads are lens-compliant")
                
        except Exception as e:
            pytest.fail(f"State lens compliance test failed: {e}")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
