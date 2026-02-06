"""
Classifications API router.

Provides endpoints for ABC-XYZ inventory classification data.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from backend.core.classifier import (
    refresh_classifications,
    get_all_classifications,
    get_classification_summary,
    get_classified_items
)

router = APIRouter(prefix="/api/classifications", tags=["Classifications"])


@router.get("/{site_id}")
def get_site_classifications(site_id: str):
    """
    Get all item classifications for a site.
    Used by Steady to sync classifications.
    """
    items = get_all_classifications(site_id)
    summary = get_classification_summary(site_id)

    # Count by class
    a_count = sum(1 for i in items if i['abc_class'] == 'A')
    b_count = sum(1 for i in items if i['abc_class'] == 'B')
    c_count = sum(1 for i in items if i['abc_class'] == 'C')
    unclassified = sum(1 for i in items if i['abc_class'] is None)

    return {
        "site_id": site_id,
        "items": items,
        "summary": {
            "a_count": a_count,
            "b_count": b_count,
            "c_count": c_count,
            "unclassified_count": unclassified,
            "total": len(items)
        },
        "last_calculated": summary.get('last_calculated')
    }


@router.get("/{site_id}/summary")
def get_site_classification_summary(site_id: str):
    """
    Get classification distribution for dashboard display.
    Includes ABC distribution, XYZ distribution, and 9-box matrix.
    """
    summary = get_classification_summary(site_id)

    if not summary.get('abc_distribution') and not summary.get('xyz_distribution'):
        raise HTTPException(
            status_code=404,
            detail=f"No classifications found for site {site_id}"
        )

    return {
        "site_id": site_id,
        **summary
    }


@router.post("/{site_id}/refresh")
def refresh_site_classifications(site_id: str):
    """
    Manually trigger classification recalculation for a site.
    """
    count = refresh_classifications(site_id)

    return {
        "success": True,
        "site_id": site_id,
        "items_classified": count
    }


@router.get("/{site_id}/items")
def get_site_classified_items(
    site_id: str,
    abc_class: Optional[str] = Query(None, description="Filter by A, B, or C"),
    xyz_class: Optional[str] = Query(None, description="Filter by X, Y, or Z"),
    sort_by: str = Query("value", description="Sort by: value, cv, or sku"),
    limit: int = Query(100, le=500)
):
    """
    Get items with optional filtering by classification.
    For drill-down views.
    """
    # Validate filters
    if abc_class and abc_class.upper() not in ('A', 'B', 'C'):
        raise HTTPException(
            status_code=400,
            detail="abc_class must be A, B, or C"
        )

    if xyz_class and xyz_class.upper() not in ('X', 'Y', 'Z'):
        raise HTTPException(
            status_code=400,
            detail="xyz_class must be X, Y, or Z"
        )

    if sort_by not in ('value', 'cv', 'sku'):
        raise HTTPException(
            status_code=400,
            detail="sort_by must be value, cv, or sku"
        )

    items = get_classified_items(
        site_id=site_id,
        abc_class=abc_class.upper() if abc_class else None,
        xyz_class=xyz_class.upper() if xyz_class else None,
        sort_by=sort_by,
        limit=limit
    )

    return {
        "site_id": site_id,
        "filters": {
            "abc_class": abc_class,
            "xyz_class": xyz_class
        },
        "items": items,
        "count": len(items)
    }


@router.get("/{site_id}/nine-box")
def get_nine_box_matrix(site_id: str):
    """
    Get the 9-box matrix (ABC x XYZ) for strategic analysis.
    """
    summary = get_classification_summary(site_id)

    # Ensure all 9 boxes are present
    boxes = ['AX', 'AY', 'AZ', 'BX', 'BY', 'BZ', 'CX', 'CY', 'CZ']
    nine_box = summary.get('nine_box', {})

    matrix = {box: nine_box.get(box, 0) for box in boxes}

    return {
        "site_id": site_id,
        "matrix": matrix,
        "recommendations": {
            "AX": "Tight control, precise forecasting, automated reordering",
            "AY": "Safety stock buffers, regular review cycles",
            "AZ": "High buffer stock, flexible supply agreements",
            "BX": "Standard management, periodic review",
            "BY": "Moderate safety stock, watch for pattern changes",
            "BZ": "Buffer stock, consider supplier flexibility",
            "CX": "Simplified management, bulk ordering OK",
            "CY": "Basic tracking, minimal intervention",
            "CZ": "On-demand ordering, minimal stock"
        }
    }
