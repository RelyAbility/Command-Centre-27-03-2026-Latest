"""
RAMP Authentication Module
==========================

Supabase Auth integration with role-based access control.

Roles:
- operator: HOW lens access, log interventions, scoped to assigned sites
- portfolio: WHERE lens access, cross-site analytics, no intervention
- admin: Full access to both lenses, user management

Scope:
- organisation_id: Required for all roles
- site_ids: Array of accessible sites (null = all for admin)
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from enum import Enum
from pydantic import BaseModel, EmailStr
import jwt
import os
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

# JWT settings - uses Supabase JWT secret
JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", os.environ.get("JWT_SECRET", ""))
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24


# =============================================================================
# ENUMS & MODELS
# =============================================================================

class UserRole(str, Enum):
    OPERATOR = "operator"
    PORTFOLIO = "portfolio"
    ADMIN = "admin"


class LensAccess(str, Enum):
    HOW = "how"      # Operator view
    WHERE = "where"  # Portfolio view
    BOTH = "both"    # Admin view


# Role to lens mapping
ROLE_LENS_ACCESS = {
    UserRole.OPERATOR: [LensAccess.HOW],
    UserRole.PORTFOLIO: [LensAccess.WHERE],
    UserRole.ADMIN: [LensAccess.HOW, LensAccess.WHERE, LensAccess.BOTH],
}


class UserRoleAssignment(BaseModel):
    """User role with scope."""
    id: str
    user_id: str
    email: str
    full_name: Optional[str] = None
    role: UserRole
    organisation_id: str
    site_ids: Optional[List[str]] = None  # None = all sites (admin only)
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TokenPayload(BaseModel):
    """JWT token payload."""
    sub: str  # user_id
    email: str
    role: UserRole
    organisation_id: str
    site_ids: Optional[List[str]] = None
    exp: int
    iat: int


class AuthenticatedUser(BaseModel):
    """Authenticated user context for request handling."""
    user_id: str
    email: str
    role: UserRole
    organisation_id: str
    site_ids: Optional[List[str]] = None
    
    def has_lens_access(self, lens: LensAccess) -> bool:
        """Check if user has access to a specific lens."""
        allowed = ROLE_LENS_ACCESS.get(self.role, [])
        return lens in allowed or LensAccess.BOTH in allowed
    
    def has_site_access(self, site_id: str) -> bool:
        """Check if user has access to a specific site."""
        if self.role == UserRole.ADMIN and self.site_ids is None:
            return True
        if self.site_ids is None:
            return False
        return site_id in self.site_ids
    
    def has_organisation_access(self, org_id: str) -> bool:
        """Check if user has access to a specific organisation."""
        return self.organisation_id == org_id
    
    def can_access_how_lens(self) -> bool:
        """Check if user can access HOW (operator) lens."""
        return self.has_lens_access(LensAccess.HOW)
    
    def can_access_where_lens(self) -> bool:
        """Check if user can access WHERE (portfolio) lens."""
        return self.has_lens_access(LensAccess.WHERE)
    
    def get_accessible_sites(self) -> Optional[List[str]]:
        """Get list of accessible sites (None = all)."""
        if self.role == UserRole.ADMIN and self.site_ids is None:
            return None
        return self.site_ids


# =============================================================================
# TOKEN OPERATIONS
# =============================================================================

def create_access_token(
    user_id: str,
    email: str,
    role: UserRole,
    organisation_id: str,
    site_ids: Optional[List[str]] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token for authenticated user.
    """
    if expires_delta is None:
        expires_delta = timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    
    payload = {
        "sub": user_id,
        "email": email,
        "role": role.value if isinstance(role, UserRole) else role,
        "organisation_id": organisation_id,
        "site_ids": site_ids,
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp())
    }
    
    encoded_jwt = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[TokenPayload]:
    """
    Verify and decode a JWT token.
    
    Returns TokenPayload if valid, None if invalid/expired.
    """
    if not JWT_SECRET:
        logger.error("JWT_SECRET not configured")
        return None
    
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM]
        )
        
        return TokenPayload(
            sub=payload["sub"],
            email=payload["email"],
            role=UserRole(payload["role"]),
            organisation_id=payload["organisation_id"],
            site_ids=payload.get("site_ids"),
            exp=payload["exp"],
            iat=payload["iat"]
        )
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None


def get_authenticated_user(token_payload: TokenPayload) -> AuthenticatedUser:
    """
    Convert token payload to authenticated user context.
    """
    return AuthenticatedUser(
        user_id=token_payload.sub,
        email=token_payload.email,
        role=token_payload.role,
        organisation_id=token_payload.organisation_id,
        site_ids=token_payload.site_ids
    )


# =============================================================================
# REQUEST MODELS
# =============================================================================

class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


class AssignRoleRequest(BaseModel):
    user_id: str
    email: str
    full_name: Optional[str] = None
    role: UserRole
    organisation_id: str
    site_ids: Optional[List[str]] = None


class UpdateRoleRequest(BaseModel):
    role: Optional[UserRole] = None
    site_ids: Optional[List[str]] = None
    is_active: Optional[bool] = None


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]
    role_assignment: Optional[Dict[str, Any]] = None


class UserInfo(BaseModel):
    user_id: str
    email: str
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    organisation_id: Optional[str] = None
    site_ids: Optional[List[str]] = None
    is_active: bool = False
    has_role: bool = False
