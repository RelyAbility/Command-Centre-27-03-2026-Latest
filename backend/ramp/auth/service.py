"""
RAMP Auth Service
=================

Database operations for user role management.
Integrates with Supabase Auth for user authentication.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import text
import os
import logging

from ramp.db import generate_id, now_utc, to_json
from ramp.auth import (
    UserRole,
    UserRoleAssignment,
    create_access_token,
    AuthenticatedUser
)

logger = logging.getLogger(__name__)

# Supabase configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")


def is_supabase_configured() -> bool:
    """Check if Supabase Auth is configured."""
    return bool(SUPABASE_URL and SUPABASE_ANON_KEY)


class AuthService:
    """
    Service for user authentication and role management.
    """
    
    def __init__(self, db):
        """
        Initialize with database client.
        
        Args:
            db: RAMPDatabase instance
        """
        self.db = db
        self._supabase = None
        self._supabase_admin = None
    
    @property
    def supabase(self):
        """Get Supabase client (lazy initialization)."""
        if not is_supabase_configured():
            raise ValueError(
                "Supabase Auth not configured. "
                "Set SUPABASE_URL and SUPABASE_ANON_KEY in backend/.env"
            )
        if self._supabase is None:
            from supabase import create_client
            self._supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        return self._supabase
    
    @property
    def supabase_admin(self):
        """Get Supabase admin client (lazy initialization)."""
        if not SUPABASE_SERVICE_ROLE_KEY:
            raise ValueError(
                "Supabase service role key not configured. "
                "Set SUPABASE_SERVICE_ROLE_KEY in backend/.env"
            )
        if self._supabase_admin is None:
            from supabase import create_client
            self._supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        return self._supabase_admin
    
    # =========================================================================
    # AUTHENTICATION
    # =========================================================================
    
    async def sign_up(
        self, 
        email: str, 
        password: str,
        full_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register a new user with Supabase Auth.
        
        Note: User will NOT have a role assignment until admin assigns one.
        """
        if not is_supabase_configured():
            return {
                "error": "Supabase Auth not configured",
                "details": "Set SUPABASE_URL and SUPABASE_ANON_KEY in backend/.env"
            }
        
        try:
            response = self.supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "full_name": full_name
                    }
                }
            })
            
            if not response.user:
                return {"error": "User creation failed"}
            
            return {
                "user_id": response.user.id,
                "email": response.user.email,
                "full_name": full_name,
                "message": "User created. Awaiting role assignment by admin."
            }
            
        except Exception as e:
            logger.error(f"Sign up error: {e}")
            return {"error": str(e)}
    
    async def sign_in(
        self, 
        email: str, 
        password: str
    ) -> Dict[str, Any]:
        """
        Authenticate user and return access token if role is assigned.
        """
        if not is_supabase_configured():
            return {
                "error": "Supabase Auth not configured",
                "details": "Set SUPABASE_URL and SUPABASE_ANON_KEY in backend/.env"
            }
        
        try:
            # Authenticate with Supabase
            response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if not response.user:
                return {"error": "Invalid credentials"}
            
            user_id = response.user.id
            
            # Check for role assignment
            role_assignment = await self.get_role_assignment_by_user_id(str(user_id))
            
            if not role_assignment:
                return {
                    "error": "No role assigned",
                    "message": "Your account exists but no role has been assigned. Contact your administrator.",
                    "user_id": str(user_id),
                    "email": email
                }
            
            if not role_assignment.get("is_active", False):
                return {
                    "error": "Account inactive",
                    "message": "Your account has been deactivated. Contact your administrator."
                }
            
            # Create access token
            access_token = create_access_token(
                user_id=str(user_id),
                email=email,
                role=UserRole(role_assignment["role"]),
                organisation_id=role_assignment["organisation_id"],
                site_ids=role_assignment.get("site_ids")
            )
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "user_id": str(user_id),
                    "email": email,
                    "full_name": role_assignment.get("full_name"),
                    "role": role_assignment["role"],
                    "organisation_id": role_assignment["organisation_id"],
                    "site_ids": role_assignment.get("site_ids")
                }
            }
            
        except Exception as e:
            logger.error(f"Sign in error: {e}")
            return {"error": "Authentication failed"}
    
    async def sign_out(self) -> Dict[str, Any]:
        """
        Sign out current user from Supabase.
        
        Note: Client should also discard the JWT token.
        """
        try:
            self.supabase.auth.sign_out()
            return {"message": "Signed out successfully"}
        except Exception as e:
            logger.error(f"Sign out error: {e}")
            return {"error": str(e)}
    
    # =========================================================================
    # ROLE MANAGEMENT
    # =========================================================================
    
    async def assign_role(
        self,
        user_id: str,
        email: str,
        role: UserRole,
        organisation_id: str,
        site_ids: Optional[List[str]] = None,
        full_name: Optional[str] = None,
        assigned_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Assign a role to a user.
        
        This is an admin-only operation.
        """
        role_id = generate_id()
        now = now_utc()
        
        # For admin role, site_ids can be null (all sites)
        # For operator/portfolio, site_ids should be specified
        if role != UserRole.ADMIN and not site_ids:
            return {"error": "site_ids required for non-admin roles"}
        
        try:
            stmt = text("""
                INSERT INTO ramp_user_roles 
                    (id, user_id, email, full_name, role, organisation_id, 
                     site_ids, is_active, created_at, updated_at, created_by)
                VALUES 
                    (:id, :user_id, :email, :full_name, :role, :organisation_id,
                     CAST(:site_ids AS json), :is_active, :created_at, :updated_at, :created_by)
                ON CONFLICT (user_id) DO UPDATE SET
                    email = :email,
                    full_name = COALESCE(:full_name, ramp_user_roles.full_name),
                    role = :role,
                    organisation_id = :organisation_id,
                    site_ids = CAST(:site_ids AS json),
                    is_active = :is_active,
                    updated_at = :updated_at
                RETURNING *
            """)
            
            result = await self.db.session.execute(stmt, {
                "id": role_id,
                "user_id": user_id,
                "email": email,
                "full_name": full_name,
                "role": role.value if isinstance(role, UserRole) else role,
                "organisation_id": organisation_id,
                "site_ids": to_json(site_ids) if site_ids else None,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
                "created_by": assigned_by
            })
            
            await self.db.session.commit()
            row = result.mappings().first()
            
            return dict(row) if row else {"id": role_id, "user_id": user_id, "role": role}
            
        except Exception as e:
            logger.error(f"Assign role error: {e}")
            await self.db.session.rollback()
            return {"error": str(e)}
    
    async def update_role(
        self,
        user_id: str,
        role: Optional[UserRole] = None,
        site_ids: Optional[List[str]] = None,
        is_active: Optional[bool] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update a user's role assignment.
        """
        now = now_utc()
        
        # Build dynamic update
        updates = ["updated_at = :updated_at"]
        params = {"user_id": user_id, "updated_at": now}
        
        if role is not None:
            updates.append("role = :role")
            params["role"] = role.value if isinstance(role, UserRole) else role
        
        if site_ids is not None:
            updates.append("site_ids = CAST(:site_ids AS json)")
            params["site_ids"] = to_json(site_ids)
        
        if is_active is not None:
            updates.append("is_active = :is_active")
            params["is_active"] = is_active
        
        try:
            stmt = text(f"""
                UPDATE ramp_user_roles 
                SET {', '.join(updates)}
                WHERE user_id = :user_id
                RETURNING *
            """)
            
            result = await self.db.session.execute(stmt, params)
            await self.db.session.commit()
            
            row = result.mappings().first()
            return dict(row) if row else None
            
        except Exception as e:
            logger.error(f"Update role error: {e}")
            await self.db.session.rollback()
            return None
    
    async def revoke_role(self, user_id: str) -> bool:
        """
        Revoke a user's role (deactivate, don't delete).
        """
        result = await self.update_role(user_id, is_active=False)
        return result is not None
    
    async def get_role_assignment_by_user_id(
        self, 
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get role assignment for a user by their Supabase user ID.
        """
        try:
            result = await self.db.session.execute(
                text("SELECT * FROM ramp_user_roles WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            row = result.mappings().first()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Get role error: {e}")
            return None
    
    async def get_role_assignment_by_email(
        self, 
        email: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get role assignment for a user by email.
        """
        try:
            result = await self.db.session.execute(
                text("SELECT * FROM ramp_user_roles WHERE email = :email"),
                {"email": email}
            )
            row = result.mappings().first()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Get role by email error: {e}")
            return None
    
    async def list_users(
        self,
        organisation_id: Optional[str] = None,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        List users with optional filters.
        """
        conditions = []
        params = {}
        
        if organisation_id:
            conditions.append("organisation_id = :organisation_id")
            params["organisation_id"] = organisation_id
        
        if role:
            conditions.append("role = :role")
            params["role"] = role.value if isinstance(role, UserRole) else role
        
        if is_active is not None:
            conditions.append("is_active = :is_active")
            params["is_active"] = is_active
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        try:
            result = await self.db.session.execute(
                text(f"SELECT * FROM ramp_user_roles WHERE {where_clause} ORDER BY created_at DESC"),
                params
            )
            return [dict(row) for row in result.mappings()]
        except Exception as e:
            logger.error(f"List users error: {e}")
            return []
    
    # =========================================================================
    # BOOTSTRAP ADMIN
    # =========================================================================
    
    async def bootstrap_admin(
        self,
        email: str,
        password: str,
        full_name: str,
        organisation_id: str
    ) -> Dict[str, Any]:
        """
        Bootstrap the first admin user.
        
        This should only be used during initial system setup.
        Checks if any admin exists first.
        """
        # Check if any admin exists
        existing_admins = await self.list_users(role=UserRole.ADMIN)
        if existing_admins:
            return {"error": "Admin already exists. Use normal admin flow."}
        
        # Sign up the user
        signup_result = await self.sign_up(email, password, full_name)
        if "error" in signup_result:
            return signup_result
        
        # Assign admin role
        role_result = await self.assign_role(
            user_id=signup_result["user_id"],
            email=email,
            role=UserRole.ADMIN,
            organisation_id=organisation_id,
            site_ids=None,  # Admin has access to all sites
            full_name=full_name,
            assigned_by="system_bootstrap"
        )
        
        if "error" in role_result:
            return role_result
        
        return {
            "status": "admin_created",
            "user_id": signup_result["user_id"],
            "email": email,
            "role": "admin",
            "message": "Admin user created. You can now sign in."
        }
