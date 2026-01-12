"""
Sites API router.
"""
from fastapi import APIRouter, HTTPException, Form
from typing import Optional

from backend.core.database import (
    get_site, list_sites, update_site_display_name, auto_format_site_name
)

router = APIRouter(prefix="/api/sites", tags=["Sites"])


@router.get("")
def get_all_sites():
    """
    List all sites with their display names.
    Auto-formats site_id if no custom name is set.
    """
    sites = list_sites()
    return {
        "sites": sites,
        "count": len(sites)
    }


@router.get("/{site_id}")
def get_site_detail_by_id(site_id: str):
    """Get site details including display name."""
    site = get_site(site_id)
    if not site:
        return {
            "site_id": site_id,
            "display_name": auto_format_site_name(site_id),
            "is_custom": False
        }
    return {
        "site_id": site["site_id"],
        "display_name": site["display_name"],
        "is_custom": site["is_custom"],
        "created_at": site.get("created_at"),
        "updated_at": site.get("updated_at")
    }


@router.put("/{site_id}")
def update_site_name(
    site_id: str,
    display_name: Optional[str] = Form(None)
):
    """
    Update the display name for a site.
    Pass display_name=None or empty string to reset to auto-formatted name.
    """
    site = update_site_display_name(site_id, display_name if display_name else None)
    return {
        "success": True,
        "site": site
    }
