"""
RAMP Site Scope Filtering
==========================

Helpers for filtering data by user's site scope.
Used by HOW and WHERE lens routes to enforce access boundaries.
"""

from typing import List, Dict, Any, Optional
from ramp.auth import AuthenticatedUser, UserRole


def get_user_site_filter(user: AuthenticatedUser) -> Optional[List[str]]:
    """
    Get the site filter for a user.
    
    Returns:
    - None if user has access to all sites (admin with no site_ids)
    - List of site_ids the user can access
    """
    if user.role == UserRole.ADMIN and user.site_ids is None:
        return None  # Admin with no restrictions
    return user.site_ids or []


def filter_by_site_scope(
    items: List[Dict[str, Any]], 
    user: AuthenticatedUser,
    site_id_field: str = "site_id"
) -> List[Dict[str, Any]]:
    """
    Filter a list of items by user's site scope.
    
    Args:
        items: List of dictionaries to filter
        user: Authenticated user with site scope
        site_id_field: Field name containing site_id
        
    Returns:
        Filtered list containing only items in user's scope
    """
    site_filter = get_user_site_filter(user)
    
    if site_filter is None:
        # Admin with all access
        return items
    
    if not site_filter:
        # No sites assigned - return empty
        return []
    
    return [
        item for item in items
        if item.get(site_id_field) in site_filter
    ]


def filter_priorities_by_scope(
    priorities: List[Dict[str, Any]],
    user: AuthenticatedUser,
    assets_lookup: Dict[str, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Filter priorities by user's site scope.
    
    Priorities don't have site_id directly - need to look up via asset.
    """
    site_filter = get_user_site_filter(user)
    
    if site_filter is None:
        return priorities
    
    if not site_filter:
        return []
    
    filtered = []
    for p in priorities:
        asset_id = p.get("asset_id")
        asset = assets_lookup.get(asset_id, {})
        site_id = asset.get("site_id")
        
        if site_id and site_id in site_filter:
            filtered.append(p)
    
    return filtered


def filter_states_by_scope(
    states: List[Dict[str, Any]],
    user: AuthenticatedUser,
    assets_lookup: Dict[str, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Filter states by user's site scope.
    
    States don't have site_id directly - need to look up via asset.
    """
    site_filter = get_user_site_filter(user)
    
    if site_filter is None:
        return states
    
    if not site_filter:
        return []
    
    filtered = []
    for s in states:
        asset_id = s.get("asset_id")
        asset = assets_lookup.get(asset_id, {})
        site_id = asset.get("site_id")
        
        if site_id and site_id in site_filter:
            filtered.append(s)
    
    return filtered


def check_asset_in_scope(
    asset_id: str,
    user: AuthenticatedUser,
    asset_lookup: Dict[str, Dict[str, Any]]
) -> bool:
    """
    Check if an asset is within user's site scope.
    """
    site_filter = get_user_site_filter(user)
    
    if site_filter is None:
        return True
    
    asset = asset_lookup.get(asset_id, {})
    site_id = asset.get("site_id")
    
    return site_id in site_filter if site_id else False


def check_site_in_scope(site_id: str, user: AuthenticatedUser) -> bool:
    """
    Check if a site is within user's scope.
    """
    site_filter = get_user_site_filter(user)
    
    if site_filter is None:
        return True
    
    return site_id in site_filter


async def build_asset_lookup_with_sites(db) -> Dict[str, Dict[str, Any]]:
    """
    Build asset lookup with site_id populated.
    
    Assets don't have site_id directly - need to join through system.
    """
    from sqlalchemy import text
    
    result = await db.session.execute(text("""
        SELECT a.id, a.name, a.system_id, sys.site_id
        FROM ramp_assets a
        JOIN ramp_systems sys ON a.system_id = sys.id
    """))
    
    return {
        row[0]: {
            "id": row[0],
            "name": row[1],
            "system_id": row[2],
            "site_id": row[3]
        }
        for row in result.fetchall()
    }
