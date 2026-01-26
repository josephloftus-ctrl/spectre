"""
Export API router.
"""
from enum import Enum
from fastapi import APIRouter, HTTPException, Form, Query
from fastapi.responses import StreamingResponse
from datetime import datetime
from urllib.parse import quote
from typing import Optional
import json
import re

from backend.core.database import (
    get_count_session, get_site_display_name
)
from backend.core.xlsx_export import (
    create_inventory_upload_workbook,
    create_valuation_report_workbook,
    export_count_session_for_upload,
    export_cart_for_upload,
    export_inventory_for_upload,
    export_count_session_as_valuation,
    export_inventory_as_valuation,
)
from backend.core.unified_export import (
    create_unified_inventory_export,
    create_unified_cart_export,
    validate_ordermaestro_format,
)

router = APIRouter(prefix="/api/export", tags=["Export"])


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe use in Content-Disposition header."""
    safe = re.sub(r'[^\w\s\-\.]', '_', filename)
    return quote(safe, safe='')


class ExportFormat(str, Enum):
    """Export format options."""
    UPLOAD = "upload"
    VALUATION = "valuation"


@router.get("/cart/{site_id}")
def export_cart(
    site_id: str,
    format: ExportFormat = Query(ExportFormat.UPLOAD, description="Export format")
):
    """
    Export shopping cart as XLSX.

    Formats:
    - upload: OrderMaestro cart upload template (4 cols: Dist #, GTIN, Quantity, Break Quantity)
    - valuation: Valuation report format for archiving (14 cols, 3 sheets)
    """
    try:
        buffer = export_cart_for_upload(site_id)
        site_name = get_site_display_name(site_id)
        filename = f"Cart_Upload_{site_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx"
        safe_filename = sanitize_filename(filename)

        def iterfile():
            yield buffer.getvalue()

        return StreamingResponse(
            iterfile(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=\"{safe_filename}\"; filename*=UTF-8''{safe_filename}"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/count-session/{session_id}")
def export_count_session(
    session_id: str,
    format: ExportFormat = Query(ExportFormat.UPLOAD, description="Export format")
):
    """
    Export count session as XLSX.

    Formats:
    - upload: Inventory upload template (23 cols) for uploading counts to OrderMaestro
    - valuation: Valuation report format (14 cols, 3 sheets) for archiving
    """
    try:
        session = get_count_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        site_name = get_site_display_name(session["site_id"])

        if format == ExportFormat.UPLOAD:
            buffer = export_count_session_for_upload(session_id)
            filename = f"Inventory_Upload_{site_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx"
        else:
            buffer = export_count_session_as_valuation(session_id)
            filename = f"Valuation_{site_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx"

        safe_filename = sanitize_filename(filename)

        def iterfile():
            yield buffer.getvalue()

        return StreamingResponse(
            iterfile(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=\"{safe_filename}\"; filename*=UTF-8''{safe_filename}"
            }
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/inventory/{site_id}")
def export_inventory(
    site_id: str,
    format: str = Form("valuation"),
    include_modifications: bool = Form(False),
    items: Optional[str] = Form(None)
):
    """
    Export inventory as XLSX.

    Formats:
    - upload: Inventory upload template (23 cols) for uploading to OrderMaestro
    - valuation: Valuation report format (14 cols, 3 sheets) for archiving

    Can export from:
    - Database (parsed files)
    - Custom items passed in request body
    - With or without pending modifications applied
    """
    site_name = get_site_display_name(site_id)
    use_upload_format = format.lower() == "upload"

    try:
        if items:
            item_list = json.loads(items)
            if use_upload_format:
                buffer = create_inventory_upload_workbook(items=item_list)
            else:
                buffer = create_valuation_report_workbook(
                    site_name=site_name,
                    items=item_list
                )
        else:
            if use_upload_format:
                buffer = export_inventory_for_upload(site_id)
            else:
                buffer = export_inventory_as_valuation(site_id)

        if use_upload_format:
            filename = f"Inventory_Upload_{site_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx"
        else:
            filename = f"Valuation_{site_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx"

        safe_filename = sanitize_filename(filename)

        def iterfile():
            yield buffer.getvalue()

        return StreamingResponse(
            iterfile(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=\"{safe_filename}\"; filename*=UTF-8''{safe_filename}"
            }
        )
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in items parameter")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unified/{site_id}")
def export_unified_inventory(
    site_id: str,
    include_off_catalog: bool = Query(True, description="Include off-catalog items"),
    sort_by_walking_order: bool = Query(True, description="Sort by location walking order"),
    auto_categorize: bool = Query(True, description="Auto-categorize uncategorized items"),
    validate_distributors: bool = Query(True, description="Check for flagged distributors"),
    validate_gl_codes: bool = Query(True, description="Flag items with missing/multiple GL codes"),
    exclude_never_count: bool = Query(False, description="Exclude NEVER INVENTORY items"),
):
    """
    Export unified inventory as OrderMaestro-compatible XLSX.

    This is the primary export endpoint for creating inventory uploads.
    It combines:
    - Main inventory items from parsed files
    - Off-catalog items (custom items not in MOG)
    - Auto-categorization using plugin keywords
    - Location-based sorting (walking order)
    - Distributor validation and warnings
    - GL code validation (missing/multiple)

    Returns:
    - XLSX file with 23-column OrderMaestro upload format
    - Highlighted rows: yellow (off-catalog), red (distributor warning), orange (GL code issue)
    """
    try:
        buffer, metadata = create_unified_inventory_export(
            site_id=site_id,
            include_off_catalog=include_off_catalog,
            sort_by_walking_order=sort_by_walking_order,
            auto_categorize=auto_categorize,
            validate_distributor_flags=validate_distributors,
            validate_gl_codes_flag=validate_gl_codes,
            exclude_never_count=exclude_never_count,
        )

        site_name = get_site_display_name(site_id)
        filename = f"Inventory_Upload_{site_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx"
        safe_filename = sanitize_filename(filename)

        def iterfile():
            yield buffer.getvalue()

        return StreamingResponse(
            iterfile(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=\"{safe_filename}\"; filename*=UTF-8''{safe_filename}",
                "X-Export-Metadata": json.dumps(metadata),
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unified/{site_id}/metadata")
def get_unified_export_metadata(
    site_id: str,
    include_off_catalog: bool = Query(True),
    auto_categorize: bool = Query(True),
    validate_distributors: bool = Query(True),
    validate_gl_codes: bool = Query(True),
    exclude_never_count: bool = Query(False),
):
    """
    Get metadata about what a unified export would contain without downloading.

    Useful for preview/confirmation before export.
    Returns counts and any validation issues (GL codes, distributors).
    """
    try:
        _, metadata = create_unified_inventory_export(
            site_id=site_id,
            include_off_catalog=include_off_catalog,
            sort_by_walking_order=False,  # Skip sorting for metadata-only
            auto_categorize=auto_categorize,
            validate_distributor_flags=validate_distributors,
            validate_gl_codes_flag=validate_gl_codes,
            exclude_never_count=exclude_never_count,
        )
        return metadata
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unified/cart/{site_id}")
def export_unified_cart(
    site_id: str,
    validate_distributors: bool = Query(True, description="Check for flagged distributors"),
):
    """
    Export shopping cart with validation as OrderMaestro-compatible XLSX.

    Returns:
    - XLSX with 4 columns: Dist #, GTIN, Quantity, Break Quantity
    - Validation warnings in metadata header
    """
    try:
        buffer, metadata = create_unified_cart_export(
            site_id=site_id,
            validate_distributor_flags=validate_distributors,
        )

        site_name = get_site_display_name(site_id)
        filename = f"Cart_Upload_{site_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx"
        safe_filename = sanitize_filename(filename)

        def iterfile():
            yield buffer.getvalue()

        return StreamingResponse(
            iterfile(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=\"{safe_filename}\"; filename*=UTF-8''{safe_filename}",
                "X-Export-Metadata": json.dumps(metadata),
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate")
def validate_export_data(
    items: str = Form(..., description="JSON array of items to validate"),
):
    """
    Validate items for OrderMaestro upload compatibility.

    Returns list of validation errors/warnings without creating a file.
    """
    try:
        item_list = json.loads(items)
        errors = validate_ordermaestro_format(item_list)
        return {
            "valid": len(errors) == 0,
            "item_count": len(item_list),
            "error_count": len(errors),
            "errors": errors[:50],  # Limit to first 50 errors
        }
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in items parameter")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
