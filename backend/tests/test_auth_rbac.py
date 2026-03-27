"""
RAMP Authentication and Role-Based Access Control Tests
========================================================

Tests for Phase 2 authentication with Supabase Auth and role-based access control.

Roles:
- operator: HOW lens access
- portfolio: WHERE lens access  
- admin: Both HOW and WHERE lens access

Test credentials:
- Admin: rampadmin@gmail.com / RampAdmin2024!
- Operator: operator1@gmail.com / Operator2024!
- Portfolio: portfolio1@gmail.com / Portfolio2024!
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://industrial-demo-1.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "rampadmin@gmail.com"
ADMIN_PASSWORD = "RampAdmin2024!"
OPERATOR_EMAIL = "operator1@gmail.com"
OPERATOR_PASSWORD = "Operator2024!"
PORTFOLIO_EMAIL = "portfolio1@gmail.com"
PORTFOLIO_PASSWORD = "Portfolio2024!"

# Cache tokens at module level to avoid repeated signin calls
_token_cache = {}


def get_token(email, password, role_name):
    """Get token with caching to avoid rate limits"""
    cache_key = email
    if cache_key in _token_cache:
        return _token_cache[cache_key]
    
    # Add small delay to avoid rate limiting
    time.sleep(0.5)
    
    response = requests.post(
        f"{BASE_URL}/api/auth/signin",
        json={"email": email, "password": password}
    )
    if response.status_code != 200:
        return None
    
    token = response.json().get("access_token")
    _token_cache[cache_key] = token
    return token


# =============================================================================
# AUTH STATUS TESTS
# =============================================================================

class TestAuthStatus:
    """Test auth status endpoint"""
    
    def test_auth_status_endpoint_exists(self):
        """GET /api/auth/status should return 200"""
        response = requests.get(f"{BASE_URL}/api/auth/status")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: Auth status endpoint exists")
    
    def test_auth_status_returns_configured_true(self):
        """Auth status should return configured=true when Supabase is set up"""
        response = requests.get(f"{BASE_URL}/api/auth/status")
        assert response.status_code == 200
        data = response.json()
        
        assert "supabase_configured" in data, f"Missing supabase_configured field: {data}"
        assert data["supabase_configured"] == True, f"Supabase not configured: {data}"
        assert data.get("status") == "ready", f"Status not ready: {data}"
        print(f"PASS: Auth status returns configured=true")


# =============================================================================
# SIGNIN TESTS
# =============================================================================

class TestSignIn:
    """Test signin endpoint for all user roles"""
    
    def test_admin_signin_returns_access_token(self):
        """Admin signin should return access_token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/signin",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin signin failed: {response.status_code} - {response.text}"
        data = response.json()
        
        assert "access_token" in data, f"Missing access_token: {data}"
        assert "token_type" in data, f"Missing token_type: {data}"
        assert data["token_type"] == "bearer", f"Wrong token_type: {data}"
        assert "user" in data, f"Missing user info: {data}"
        assert data["user"]["role"] == "admin", f"Wrong role: {data}"
        
        # Cache the token
        _token_cache[ADMIN_EMAIL] = data["access_token"]
        print(f"PASS: Admin signin returns access_token with role=admin")
    
    def test_operator_signin_returns_access_token(self):
        """Operator signin should return access_token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/signin",
            json={"email": OPERATOR_EMAIL, "password": OPERATOR_PASSWORD}
        )
        assert response.status_code == 200, f"Operator signin failed: {response.status_code} - {response.text}"
        data = response.json()
        
        assert "access_token" in data, f"Missing access_token: {data}"
        assert data["user"]["role"] == "operator", f"Wrong role: {data}"
        
        # Cache the token
        _token_cache[OPERATOR_EMAIL] = data["access_token"]
        print(f"PASS: Operator signin returns access_token with role=operator")
    
    def test_portfolio_signin_returns_access_token(self):
        """Portfolio signin should return access_token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/signin",
            json={"email": PORTFOLIO_EMAIL, "password": PORTFOLIO_PASSWORD}
        )
        assert response.status_code == 200, f"Portfolio signin failed: {response.status_code} - {response.text}"
        data = response.json()
        
        assert "access_token" in data, f"Missing access_token: {data}"
        assert data["user"]["role"] == "portfolio", f"Wrong role: {data}"
        
        # Cache the token
        _token_cache[PORTFOLIO_EMAIL] = data["access_token"]
        print(f"PASS: Portfolio signin returns access_token with role=portfolio")
    
    def test_invalid_credentials_returns_error(self):
        """Invalid credentials should return 401 or 403 (auth error)"""
        response = requests.post(
            f"{BASE_URL}/api/auth/signin",
            json={"email": "invalid@example.com", "password": "wrongpassword"}
        )
        # Accept both 401 (invalid credentials) and 403 (authentication failed)
        assert response.status_code in [401, 403], f"Expected 401 or 403, got {response.status_code}: {response.text}"
        print(f"PASS: Invalid credentials returns {response.status_code}")


# =============================================================================
# AUTH ME TESTS
# =============================================================================

class TestAuthMe:
    """Test /api/auth/me endpoint"""
    
    def test_auth_me_returns_user_info_for_admin(self):
        """GET /api/auth/me should return user info with role and lens access"""
        token = get_token(ADMIN_EMAIL, ADMIN_PASSWORD, "admin")
        if not token:
            pytest.skip("Admin signin failed")
        
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Auth me failed: {response.status_code} - {response.text}"
        data = response.json()
        
        assert "user_id" in data, f"Missing user_id: {data}"
        assert "email" in data, f"Missing email: {data}"
        assert "role" in data, f"Missing role: {data}"
        assert data["role"] == "admin", f"Wrong role: {data}"
        assert "lens_access" in data, f"Missing lens_access: {data}"
        assert data["lens_access"]["how"] == True, f"Admin should have HOW access: {data}"
        assert data["lens_access"]["where"] == True, f"Admin should have WHERE access: {data}"
        print(f"PASS: Auth me returns admin user info with both lens access")
    
    def test_auth_me_returns_user_info_for_operator(self):
        """Operator should have HOW lens access only"""
        token = get_token(OPERATOR_EMAIL, OPERATOR_PASSWORD, "operator")
        if not token:
            pytest.skip("Operator signin failed")
        
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Auth me failed: {response.status_code} - {response.text}"
        data = response.json()
        
        assert data["role"] == "operator", f"Wrong role: {data}"
        assert data["lens_access"]["how"] == True, f"Operator should have HOW access: {data}"
        assert data["lens_access"]["where"] == False, f"Operator should NOT have WHERE access: {data}"
        print(f"PASS: Operator has HOW lens access only")
    
    def test_auth_me_returns_user_info_for_portfolio(self):
        """Portfolio should have WHERE lens access only"""
        token = get_token(PORTFOLIO_EMAIL, PORTFOLIO_PASSWORD, "portfolio")
        if not token:
            pytest.skip("Portfolio signin failed")
        
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Auth me failed: {response.status_code} - {response.text}"
        data = response.json()
        
        assert data["role"] == "portfolio", f"Wrong role: {data}"
        assert data["lens_access"]["how"] == False, f"Portfolio should NOT have HOW access: {data}"
        assert data["lens_access"]["where"] == True, f"Portfolio should have WHERE access: {data}"
        print(f"PASS: Portfolio has WHERE lens access only")
    
    def test_auth_me_without_token_returns_401(self):
        """GET /api/auth/me without token should return 401"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("PASS: Auth me without token returns 401")


# =============================================================================
# HOW LENS ACCESS TESTS
# =============================================================================

class TestHOWLensAccess:
    """Test HOW lens access control"""
    
    def test_how_priorities_requires_auth(self):
        """GET /api/how/priorities without auth should return 401"""
        response = requests.get(f"{BASE_URL}/api/how/priorities")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("PASS: HOW priorities requires auth (401 without token)")
    
    def test_operator_can_access_how_priorities(self):
        """Operator should be able to access HOW priorities"""
        token = get_token(OPERATOR_EMAIL, OPERATOR_PASSWORD, "operator")
        if not token:
            pytest.skip("Operator signin failed")
        
        response = requests.get(
            f"{BASE_URL}/api/how/priorities",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Operator HOW access failed: {response.status_code} - {response.text}"
        print("PASS: Operator can access HOW priorities")
    
    def test_admin_can_access_how_priorities(self):
        """Admin should be able to access HOW priorities"""
        token = get_token(ADMIN_EMAIL, ADMIN_PASSWORD, "admin")
        if not token:
            pytest.skip("Admin signin failed")
        
        response = requests.get(
            f"{BASE_URL}/api/how/priorities",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Admin HOW access failed: {response.status_code} - {response.text}"
        print("PASS: Admin can access HOW priorities")
    
    def test_portfolio_cannot_access_how_priorities(self):
        """Portfolio should NOT be able to access HOW priorities (403)"""
        token = get_token(PORTFOLIO_EMAIL, PORTFOLIO_PASSWORD, "portfolio")
        if not token:
            pytest.skip("Portfolio signin failed")
        
        response = requests.get(
            f"{BASE_URL}/api/how/priorities",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("PASS: Portfolio cannot access HOW priorities (403)")


# =============================================================================
# WHERE LENS ACCESS TESTS
# =============================================================================

class TestWHERELensAccess:
    """Test WHERE lens access control"""
    
    def test_where_priorities_summary_requires_auth(self):
        """GET /api/where/priorities/summary without auth should return 401"""
        response = requests.get(f"{BASE_URL}/api/where/priorities/summary")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("PASS: WHERE priorities/summary requires auth (401 without token)")
    
    def test_portfolio_can_access_where_priorities_summary(self):
        """Portfolio should be able to access WHERE priorities/summary"""
        token = get_token(PORTFOLIO_EMAIL, PORTFOLIO_PASSWORD, "portfolio")
        if not token:
            pytest.skip("Portfolio signin failed")
        
        response = requests.get(
            f"{BASE_URL}/api/where/priorities/summary",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Portfolio WHERE access failed: {response.status_code} - {response.text}"
        print("PASS: Portfolio can access WHERE priorities/summary")
    
    def test_admin_can_access_where_priorities_summary(self):
        """Admin should be able to access WHERE priorities/summary"""
        token = get_token(ADMIN_EMAIL, ADMIN_PASSWORD, "admin")
        if not token:
            pytest.skip("Admin signin failed")
        
        response = requests.get(
            f"{BASE_URL}/api/where/priorities/summary",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Admin WHERE access failed: {response.status_code} - {response.text}"
        print("PASS: Admin can access WHERE priorities/summary")
    
    def test_operator_cannot_access_where_priorities_summary(self):
        """Operator should NOT be able to access WHERE priorities/summary (403)"""
        token = get_token(OPERATOR_EMAIL, OPERATOR_PASSWORD, "operator")
        if not token:
            pytest.skip("Operator signin failed")
        
        response = requests.get(
            f"{BASE_URL}/api/where/priorities/summary",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("PASS: Operator cannot access WHERE priorities/summary (403)")


# =============================================================================
# ADMIN ENDPOINTS TESTS
# =============================================================================

class TestAdminEndpoints:
    """Test admin-only endpoints"""
    
    def test_admin_users_list_requires_admin_role(self):
        """GET /api/auth/admin/users should require admin role"""
        token = get_token(OPERATOR_EMAIL, OPERATOR_PASSWORD, "operator")
        if not token:
            pytest.skip("Operator signin failed")
        
        response = requests.get(
            f"{BASE_URL}/api/auth/admin/users",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("PASS: Admin users list requires admin role (403 for operator)")
    
    def test_admin_can_list_users(self):
        """Admin should be able to list users"""
        token = get_token(ADMIN_EMAIL, ADMIN_PASSWORD, "admin")
        if not token:
            pytest.skip("Admin signin failed")
        
        response = requests.get(
            f"{BASE_URL}/api/auth/admin/users",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Admin list users failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "users" in data, f"Missing users field: {data}"
        assert "count" in data, f"Missing count field: {data}"
        print(f"PASS: Admin can list users (count: {data['count']})")


# =============================================================================
# WEBSOCKET AUTH TESTS
# =============================================================================

class TestWebSocketAuth:
    """Test WebSocket authentication requirements"""
    
    def test_ws_status_endpoint_exists(self):
        """WebSocket status should be accessible"""
        response = requests.get(f"{BASE_URL}/api/system/ws/status")
        assert response.status_code == 200, f"WS status failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Check that channels are listed
        assert "channels" in data, f"Missing channels: {data}"
        print(f"PASS: WebSocket status endpoint works")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
