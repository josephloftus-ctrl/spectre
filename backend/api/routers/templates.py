"""
Templates API router.
"""
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from urllib.parse import quote
from typing import Optional
import re

router = APIRouter(prefix="/api/templates", tags=["Templates"])

ROOT_DIR = Path(__file__).resolve().parents[3]
TEMPLATES_DIR = ROOT_DIR / "Templates"

# Map site IDs to template filenames
TEMPLATE_MAP = {
    "pseg_nhq": "PSEG NHQ Inventory Template.xlsx",
    "pseg_hq": "PSEG NHQ Inventory Template.xlsx",
    "pseg_salem": "PSEG Salem InventoryTemplate.xlsx",
    "hope_creek": "Hope Creek InventoryTemplate.xlsx",
    "pseg_hope_creek": "Hope Creek InventoryTemplate.xlsx",
    "lm100": "LM100 Inventory Template.xlsx",
    "lockheed": "LM100 Inventory Template.xlsx",
    "lmd": "LMD Inventory Template.xlsx",
    "lockheed_bldg_d": "LMD Inventory Template.xlsx",
    "blank": "EmptyInventoryTemplate.xlsx",
    "cart": "CartTemplate.xlsx",
}


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe use in Content-Disposition header."""
    safe = re.sub(r'[^\w\s\-\.]', '_', filename)
    return quote(safe, safe='')


@router.get("")
def list_templates():
    """List all available count sheet templates."""
    templates = []
    if TEMPLATES_DIR.exists():
        for f in TEMPLATES_DIR.glob("*.xlsx"):
            templates.append({
                "filename": f.name,
                "size_kb": round(f.stat().st_size / 1024, 1),
                "modified": f.stat().st_mtime
            })
    return {
        "templates": sorted(templates, key=lambda x: x["filename"]),
        "directory": str(TEMPLATES_DIR)
    }


@router.get("/{site_id}/download")
def download_template(
    site_id: str,
    sort_by: Optional[str] = Query(None, description="Sort by: description, sku, category, vendor, price")
):
    """Download a count sheet template for a specific site, optionally sorted."""
    site_key = site_id.lower().replace("-", "_").replace(" ", "_")

    template_name = TEMPLATE_MAP.get(site_key)
    if not template_name:
        for f in TEMPLATES_DIR.glob("*.xlsx"):
            if site_key in f.name.lower().replace(" ", "_"):
                template_name = f.name
                break

    if not template_name:
        raise HTTPException(
            status_code=404,
            detail=f"No template found for site: {site_id}. Available: {list(TEMPLATE_MAP.keys())}"
        )

    template_path = TEMPLATES_DIR / template_name
    if not template_path.exists():
        raise HTTPException(status_code=404, detail=f"Template file not found: {template_name}")

    if sort_by:
        try:
            from nebula.purchase_match.sheet_writer import generate_sorted_template
            content = generate_sorted_template(template_path, sort_by)
            if not content:
                raise HTTPException(status_code=500, detail="Failed to generate sorted template")
        except ImportError:
            with open(template_path, "rb") as f:
                content = f.read()
    else:
        with open(template_path, "rb") as f:
            content = f.read()

    safe_name = sanitize_filename(template_name)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=\"{safe_name}\"; filename*=UTF-8''{safe_name}"
        }
    )
