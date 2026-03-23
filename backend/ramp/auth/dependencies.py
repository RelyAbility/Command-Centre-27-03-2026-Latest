"""
RAMP Auth Dependencies
======================

FastAPI dependencies for authentication and authorization.
Enforces role + scope access control aligned with HOW/WHERE lens separation.
"""

from typing import Optional, List
from fastapi import Depends, HTTPException, status, Query, WebSocket
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

from ramp.auth import (
    verify_token,
    get_authenticated_user,
    AuthenticatedUser,
    UserRole,
    LensAccess,
    TokenPayload
)

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer(auto_error=False)


# =============================================================================
# CORE DEPENDENCIES
# =============================================================================

async def get_token_payload(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> TokenPayload:
    """
    Extract and verify JWT token from Authorization header.
    
    Raises 401 if no token or invalid token.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = verify_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return payload


async def get_current_user(
    token_payload: TokenPayload = Depends(get_token_payload)
) -> AuthenticatedUser:
    """
    Get the authenticated user context from the token.
    
    Returns AuthenticatedUser with role and scope information.
    """
    return get_authenticated_user(token_payload)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[AuthenticatedUser]:
    """
    Get user if authenticated, None if not.
    
    Use for endpoints that work differently for authenticated vs anonymous users.
    """
    if credentials is None:
        return None
    
    token = credentials.credentials
    payload = verify_token(token)
    
    if payload is None:
        return None
    
    return get_authenticated_user(payload)


# =============================================================================
# ROLE-BASED DEPENDENCIES
# =============================================================================

async def require_operator(
    user: AuthenticatedUser = Depends(get_current_user)
) -> AuthenticatedUser:
    """
    Require operator role (or admin).
    
    Operators have HOW lens access.
    """
    if user.role not in [UserRole.OPERATOR, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator access required"
        )
    return user


async def require_portfolio(
    user: AuthenticatedUser = Depends(get_current_user)
) -> AuthenticatedUser:
    """
    Require portfolio role (or admin).
    
    Portfolio managers have WHERE lens access.
    """
    if user.role not in [UserRole.PORTFOLIO, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Portfolio access required"
        )
    return user


async def require_admin(
    user: AuthenticatedUser = Depends(get_current_user)
) -> AuthenticatedUser:
    """
    Require admin role.
    
    Admins have full access to both lenses.
    """
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user


# =============================================================================
# LENS-BASED DEPENDENCIES
# =============================================================================

async def require_how_lens_access(
    user: AuthenticatedUser = Depends(get_current_user)
) -> AuthenticatedUser:
    """
    Require HOW lens access.
    
    HOW lens = operator view. Allowed roles: operator, admin.
    """
    if not user.can_access_how_lens():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="HOW lens access required (operator or admin role)"
        )
    return user


async def require_where_lens_access(
    user: AuthenticatedUser = Depends(get_current_user)
) -> AuthenticatedUser:
    """
    Require WHERE lens access.
    
    WHERE lens = portfolio view. Allowed roles: portfolio, admin.
    """
    if not user.can_access_where_lens():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="WHERE lens access required (portfolio or admin role)"
        )
    return user


# =============================================================================
# SCOPE-BASED DEPENDENCIES
# =============================================================================

def require_site_access(site_id: str):
    """
    Factory for site access dependency.
    
    Usage:
        @router.get("/sites/{site_id}/data")
        async def get_site_data(
            site_id: str,
            user: AuthenticatedUser = Depends(require_site_access(site_id))
        ):
            ...
    """
    async def dependency(
        user: AuthenticatedUser = Depends(get_current_user)
    ) -> AuthenticatedUser:
        if not user.has_site_access(site_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access to site {site_id} not authorized"
            )
        return user
    return dependency


class SiteAccessChecker:
    """
    Dependency class for checking site access from path parameter.
    
    Usage:
        @router.get("/sites/{site_id}/data")
        async def get_site_data(
            site_id: str,
            user: AuthenticatedUser = Depends(SiteAccessChecker())
        ):
            ...
    """
    async def __call__(
        self,
        site_id: str,
        user: AuthenticatedUser = Depends(get_current_user)
    ) -> AuthenticatedUser:
        if not user.has_site_access(site_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access to site {site_id} not authorized"
            )
        return user


class OrganisationAccessChecker:
    """
    Dependency class for checking organisation access.
    """
    async def __call__(
        self,
        organisation_id: str,
        user: AuthenticatedUser = Depends(get_current_user)
    ) -> AuthenticatedUser:
        if not user.has_organisation_access(organisation_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access to organisation {organisation_id} not authorized"
            )
        return user


# =============================================================================
# WEBSOCKET AUTHENTICATION
# =============================================================================

async def authenticate_websocket(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
) -> Optional[AuthenticatedUser]:
    """
    Authenticate WebSocket connection via token query parameter.
    
    Usage:
        @app.websocket("/ws/priorities")
        async def websocket_priorities(
            websocket: WebSocket,
            user: Optional[AuthenticatedUser] = Depends(authenticate_websocket)
        ):
            if user is None:
                await websocket.close(code=4001, reason="Authentication required")
                return
            ...
    
    Returns None if no token or invalid token (caller should close connection).
    """
    if token is None:
        return None
    
    payload = verify_token(token)
    if payload is None:
        return None
    
    return get_authenticated_user(payload)


async def require_websocket_auth(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
) -> AuthenticatedUser:
    """
    Require WebSocket authentication - closes connection if not authenticated.
    
    This dependency will close the WebSocket with code 4001 if authentication fails.
    """
    user = await authenticate_websocket(websocket, token)
    
    if user is None:
        await websocket.close(code=4001, reason="Authentication required")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="WebSocket authentication required"
        )
    
    return user


async def require_websocket_how_access(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
) -> AuthenticatedUser:
    """
    Require WebSocket authentication with HOW lens access.
    """
    user = await authenticate_websocket(websocket, token)
    
    if user is None:
        await websocket.close(code=4001, reason="Authentication required")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="WebSocket authentication required"
        )
    
    if not user.can_access_how_lens():
        await websocket.close(code=4003, reason="HOW lens access required")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="HOW lens access required"
        )
    
    return user


async def require_websocket_where_access(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
) -> AuthenticatedUser:
    """
    Require WebSocket authentication with WHERE lens access.
    """
    user = await authenticate_websocket(websocket, token)
    
    if user is None:
        await websocket.close(code=4001, reason="Authentication required")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="WebSocket authentication required"
        )
    
    if not user.can_access_where_lens():
        await websocket.close(code=4003, reason="WHERE lens access required")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="WHERE lens access required"
        )
    
    return user


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def filter_by_user_scope(
    items: List[dict],
    user: AuthenticatedUser,
    site_id_field: str = "site_id"
) -> List[dict]:
    """
    Filter a list of items by user's site scope.
    
    For admins with no site restrictions, returns all items.
    For other users, filters to only items matching their accessible sites.
    """
    accessible_sites = user.get_accessible_sites()
    
    if accessible_sites is None:
        return items
    
    return [
        item for item in items
        if item.get(site_id_field) in accessible_sites
    ]


def check_scope_for_operation(
    user: AuthenticatedUser,
    site_id: Optional[str] = None,
    organisation_id: Optional[str] = None
) -> bool:
    """
    Check if user has scope for an operation.
    
    Returns True if user has access to the specified scope.
    """
    if organisation_id and not user.has_organisation_access(organisation_id):
        return False
    
    if site_id and not user.has_site_access(site_id):
        return False
    
    return True
