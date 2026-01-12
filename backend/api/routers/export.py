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
