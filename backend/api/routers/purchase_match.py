"""
Purchase match API router.
"""
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException, Form, Query
from fastapi.responses import Response

from backend.core.database import (
    add_ignored_item, remove_ignored_item, list_ignored_items, get_ignored_skus,
    bulk_add_cart_items, get_cart_summary,
    create_inventory_snapshot
)
from backend.api.models import IgnoreItemRequest

# Import purchase match module
from nebula.purchase_match import (
    load_config, load_canon, build_index,
    match_inventory, summarize_results,
    format_console, MatchFlag
)
from nebula.purchase_match.parsed_adapter import ParsedFileInventoryAdapter
from nebula.purchase_match.mog import load_mog_directory
from nebula.purchase_match.mog_embeddings import MOGEmbeddingIndex
from nebula.purchase_match.matcher import set_embedding_index

router = APIRouter(tags=["Purchase Match"])

# Configuration
ROOT_DIR = Path(__file__).resolve().parents[3]

# Global state for purchase match (loaded on first use)
_purchase_match_state = {
    "config": None,
    "ips_index": None,
    "mog_index": None,
    "mog_embedding_index": None,
    "adapter": None,
    "initialized": False,
}


def _init_purchase_match():
    """Initialize purchase match components if not already done."""
    if _purchase_match_state["initialized"]:
        return True

    try:
        config_path = ROOT_DIR / "nebula" / "purchase_match" / "unit_vendor_config.json"
        ips_dir = ROOT_DIR / "Invoice Purchasing Summaries"
        mog_dir = ROOT_DIR / "FULL MOGS"
        data_dir = ROOT_DIR / "data" / "processed"

        _purchase_match_state["config"] = load_config(config_path)

        if ips_dir.exists():
            ips_files = list(ips_dir.glob("*.xlsx"))
            if ips_files:
                records = load_canon(ips_files, _purchase_match_state["config"])
                _purchase_match_state["ips_index"] = build_index(records)
                _purchase_match_state["index"] = _purchase_match_state["ips_index"]

        if mog_dir.exists():
            _purchase_match_state["mog_index"] = load_mog_directory(mog_dir)

            if _purchase_match_state["mog_index"]:
                try:
                    embedding_index = MOGEmbeddingIndex()
                    if embedding_index.build_index(_purchase_match_state["mog_index"]):
                        _purchase_match_state["mog_embedding_index"] = embedding_index
                        set_embedding_index(embedding_index)
                        print(f"MOG embedding index ready for semantic matching")
                except Exception as e:
                    print(f"Warning: Could not build embedding index: {e}")

        if data_dir.exists():
            _purchase_match_state["adapter"] = ParsedFileInventoryAdapter(
                data_dir, _purchase_match_state["config"]
            )

        _purchase_match_state["initialized"] = True
        return True
    except Exception as e:
        print(f"Warning: Failed to initialize purchase match: {e}")
        return False


@router.post("/api/mog/search")
def search_mog_catalog(
    query: str = Form(...),
    limit: int = Form(10)
):
    """Search vendor catalogs by description using semantic search."""
    _init_purchase_match()

    embedding_index = _purchase_match_state.get("mog_embedding_index")
    if not embedding_index or not embedding_index.is_ready:
        raise HTTPException(status_code=503, detail="Catalog search not available. MOG embedding index not ready.")

    results = embedding_index.find_similar(query, limit=limit)
    return {
        "query": query,
        "results": results,
        "count": len(results)
    }


@router.get("/api/purchase-match/status")
def purchase_match_status():
    """Get purchase match system status."""
    _init_purchase_match()

    ips_index = _purchase_match_state.get("ips_index")
    mog_index = _purchase_match_state.get("mog_index")
    embedding_index = _purchase_match_state.get("mog_embedding_index")
    adapter = _purchase_match_state.get("adapter")

    return {
        "initialized": _purchase_match_state["initialized"],
        "ips_loaded": ips_index is not None,
        "ips_record_count": ips_index.record_count if ips_index else 0,
        "mog_loaded": mog_index is not None,
        "mog_item_count": mog_index.total_items if mog_index else 0,
        "mog_vendors": mog_index.vendors if mog_index else [],
        "embedding_ready": embedding_index is not None and embedding_index.is_ready,
        "inventory_loaded": adapter is not None,
        "available_units": adapter.get_all_units() if adapter else [],
        "canon_loaded": ips_index is not None,
        "canon_record_count": ips_index.record_count if ips_index else 0,
    }


@router.get("/api/purchase-match/units")
def purchase_match_units():
    """Get list of units available for matching."""
    _init_purchase_match()

    adapter = _purchase_match_state.get("adapter")
    if not adapter:
        raise HTTPException(status_code=503, detail="Inventory adapter not initialized")

    return {"units": adapter.get_all_units()}


@router.get("/api/purchase-match/run/{unit}")
def run_purchase_match(unit: str, include_clean: bool = Query(False)):
    """
    Run purchase match diagnostic for a unit.

    Combines IPS (purchases) + MOG (catalogs) + Inventory for robust analysis.
    Returns items grouped by status with full details and light suggestions.
    """
    _init_purchase_match()

    config = _purchase_match_state.get("config")
    ips_index = _purchase_match_state.get("ips_index")
    mog_index = _purchase_match_state.get("mog_index")
    adapter = _purchase_match_state.get("adapter")

    if not config or not ips_index:
        raise HTTPException(status_code=503, detail="Purchase data not loaded. Upload IPS files first.")

    if not adapter:
        raise HTTPException(status_code=503, detail="Inventory adapter not initialized")

    inventory = adapter.get_inventory_for_unit(unit)
    if not inventory:
        raise HTTPException(status_code=404, detail=f"No inventory found for unit: {unit}")

    ignored_skus = get_ignored_skus(unit)

    results = match_inventory(
        inventory, ips_index, config,
        mog_index=mog_index,
        ignored_skus=ignored_skus
    )
    summary = summarize_results(results)

    likely_typos = []
    orderable = []
    unknown = []
    ignored = []
    clean = []

    for r in results:
        item = {
            "sku": r.inventory_item.sku,
            "description": r.inventory_item.description,
            "quantity": float(r.inventory_item.quantity),
            "price": float(r.inventory_item.price) if r.inventory_item.price else None,
            "vendor": r.inventory_item.vendor,
            "reason": r.reason,
        }

        if r.flag == MatchFlag.LIKELY_TYPO and r.suggested_sku:
            item["suggestion"] = {
                "sku": r.suggested_sku.sku,
                "description": r.suggested_sku.description,
                "vendor": r.suggested_sku.vendor,
                "price": float(r.suggested_sku.price) if r.suggested_sku.price else None,
                "similarity": round(r.suggested_sku.similarity * 100),
            }
            likely_typos.append(item)

        elif r.flag == MatchFlag.ORDERABLE and r.mog_match:
            item["catalog"] = {
                "vendor": r.mog_match.vendor,
                "description": r.mog_match.description,
                "price": float(r.mog_match.price) if r.mog_match.price else None,
            }
            orderable.append(item)

        elif r.flag == MatchFlag.UNKNOWN:
            unknown.append(item)

        elif r.flag == MatchFlag.IGNORED:
            ignored.append(item)

        elif r.flag == MatchFlag.CLEAN:
            if include_clean:
                clean.append(item)

    return {
        "unit": unit,
        "summary": summary,
        "likely_typos": likely_typos,
        "orderable": orderable,
        "unknown": unknown,
        "ignored": ignored,
        "clean": clean if include_clean else None,
        "mismatches": likely_typos,
        "orphans": unknown,
    }


@router.get("/api/purchase-match/report/{unit}")
def purchase_match_report(unit: str):
    """Get formatted text report for a unit."""
    _init_purchase_match()

    config = _purchase_match_state.get("config")
    index = _purchase_match_state.get("index")
    adapter = _purchase_match_state.get("adapter")

    if not config or not index or not adapter:
        raise HTTPException(status_code=503, detail="Purchase match not initialized")

    inventory = adapter.get_inventory_for_unit(unit)
    if not inventory:
        raise HTTPException(status_code=404, detail=f"No inventory found for unit: {unit}")

    results = match_inventory(inventory, index, config)
    report = format_console(results)

    return Response(content=report, media_type="text/plain")


@router.post("/api/purchase-match/reload")
def reload_purchase_match():
    """Reload purchase match data (IPS files and inventory)."""
    _purchase_match_state["initialized"] = False
    success = _init_purchase_match()

    if not success:
        raise HTTPException(status_code=500, detail="Failed to reload purchase match data")

    return purchase_match_status()


# ============== Ignore List API ==============

@router.get("/api/purchase-match/{site_id}/ignored")
def get_ignored_items(site_id: str):
    """List all ignored items for a site."""
    items = list_ignored_items(site_id)
    return {
        "site_id": site_id,
        "items": items,
        "count": len(items)
    }


@router.post("/api/purchase-match/{site_id}/ignore")
def add_item_to_ignore_list(site_id: str, request: IgnoreItemRequest):
    """Add an item to the site's ignore list."""
    item = add_ignored_item(
        site_id=site_id,
        sku=request.sku,
        reason=request.reason,
        notes=request.notes
    )
    return {
        "success": True,
        "item": item
    }


@router.delete("/api/purchase-match/{site_id}/ignore/{sku}")
def remove_item_from_ignore_list(site_id: str, sku: str):
    """Remove an item from the site's ignore list."""
    removed = remove_ignored_item(site_id, sku)
    if not removed:
        raise HTTPException(status_code=404, detail="Item not found in ignore list")
    return {
        "success": True,
        "message": f"Removed {sku} from ignore list"
    }


# ============== Auto-Clean & Cart Integration ==============

@router.post("/api/inventory/auto-clean/{site_id}")
def auto_clean_inventory(
    site_id: str,
    create_snapshot_flag: bool = Form(True),
    apply_typo_fixes: bool = Form(True)
):
    """
    Auto-clean inventory by applying purchase match corrections.
    Creates a snapshot first for safe state return.
    """
    _init_purchase_match()

    config = _purchase_match_state.get("config")
    ips_index = _purchase_match_state.get("ips_index")
    mog_index = _purchase_match_state.get("mog_index")
    adapter = _purchase_match_state.get("adapter")

    if not config or not ips_index or not adapter:
        raise HTTPException(status_code=503, detail="Purchase match data not available")

    inventory = adapter.get_inventory_for_unit(site_id)
    if not inventory:
        raise HTTPException(status_code=404, detail=f"No inventory found for unit: {site_id}")

    ignored_skus = get_ignored_skus(site_id)

    results = match_inventory(
        inventory, ips_index, config,
        mog_index=mog_index,
        ignored_skus=ignored_skus
    )

    original_items = []
    for item in inventory:
        original_items.append({
            "sku": item.sku,
            "description": item.description,
            "quantity": float(item.quantity) if item.quantity else 0,
            "uom": item.uom,
            "unit_price": float(item.price) if item.price else 0,
            "vendor": item.vendor,
            "location": getattr(item, 'location', None)
        })

    snapshot = None
    if create_snapshot_flag:
        snapshot = create_inventory_snapshot(
            site_id=site_id,
            snapshot_data=original_items,
            name=f"Pre-clean {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )

    cleaned_items = []
    fixes_applied = []

    for r in results:
        item_data = {
            "sku": r.inventory_item.sku,
            "description": r.inventory_item.description,
            "quantity": float(r.inventory_item.quantity) if r.inventory_item.quantity else 0,
            "uom": r.inventory_item.uom,
            "unit_price": float(r.inventory_item.price) if r.inventory_item.price else 0,
            "vendor": r.inventory_item.vendor,
        }

        if apply_typo_fixes and r.flag == MatchFlag.LIKELY_TYPO and r.suggested_sku:
            fixes_applied.append({
                "original_sku": r.inventory_item.sku,
                "corrected_sku": r.suggested_sku.sku,
                "description": r.inventory_item.description,
                "similarity": round(r.suggested_sku.similarity * 100)
            })
            item_data["sku"] = r.suggested_sku.sku

        cleaned_items.append(item_data)

    return {
        "site_id": site_id,
        "snapshot_id": snapshot["id"] if snapshot else None,
        "original_count": len(original_items),
        "cleaned_count": len(cleaned_items),
        "fixes_applied": fixes_applied,
        "cleaned_items": cleaned_items
    }


@router.post("/api/purchase-match/{site_id}/add-to-cart")
def add_purchase_match_to_cart(
    site_id: str,
    category: str = Form(...),
    apply_corrections: bool = Form(True)
):
    """
    Add items from purchase match results to shopping cart.

    Categories:
    - orderable: Items found in MOG catalog but not purchased yet
    - likely_typos: Items with SKU corrections (optionally apply fixes)
    - unknown: Items not found in any catalog
    """
    _init_purchase_match()

    config = _purchase_match_state.get("config")
    ips_index = _purchase_match_state.get("ips_index")
    mog_index = _purchase_match_state.get("mog_index")
    adapter = _purchase_match_state.get("adapter")

    if not config or not ips_index or not adapter:
        raise HTTPException(status_code=503, detail="Purchase match data not available")

    inventory = adapter.get_inventory_for_unit(site_id)
    if not inventory:
        raise HTTPException(status_code=404, detail=f"No inventory found for unit: {site_id}")

    ignored_skus = get_ignored_skus(site_id)

    results = match_inventory(
        inventory, ips_index, config,
        mog_index=mog_index,
        ignored_skus=ignored_skus
    )

    cart_items = []

    for r in results:
        if category == "orderable" and r.flag == MatchFlag.ORDERABLE and r.mog_match:
            cart_items.append({
                "sku": r.inventory_item.sku,
                "description": r.mog_match.description or r.inventory_item.description,
                "quantity": float(r.inventory_item.quantity) if r.inventory_item.quantity else 1,
                "unit_price": float(r.mog_match.price) if r.mog_match.price else None,
                "uom": r.inventory_item.uom,
                "vendor": r.mog_match.vendor,
            })

        elif category == "likely_typos" and r.flag == MatchFlag.LIKELY_TYPO and r.suggested_sku:
            sku = r.suggested_sku.sku if apply_corrections else r.inventory_item.sku
            cart_items.append({
                "sku": sku,
                "description": r.inventory_item.description,
                "quantity": float(r.inventory_item.quantity) if r.inventory_item.quantity else 1,
                "unit_price": float(r.suggested_sku.price) if r.suggested_sku.price else None,
                "uom": r.inventory_item.uom,
                "vendor": r.suggested_sku.vendor,
                "notes": f"Corrected from {r.inventory_item.sku}" if apply_corrections else None,
            })

        elif category == "unknown" and r.flag == MatchFlag.UNKNOWN:
            cart_items.append({
                "sku": r.inventory_item.sku,
                "description": r.inventory_item.description,
                "quantity": float(r.inventory_item.quantity) if r.inventory_item.quantity else 1,
                "unit_price": float(r.inventory_item.price) if r.inventory_item.price else None,
                "uom": r.inventory_item.uom,
                "vendor": r.inventory_item.vendor,
                "notes": "Unknown item - needs review",
            })

    if not cart_items:
        return {
            "success": True,
            "added_count": 0,
            "message": f"No {category} items to add"
        }

    count = bulk_add_cart_items(site_id, cart_items, source=f"purchase_match_{category}")

    return {
        "success": True,
        "added_count": count,
        "category": category,
        "summary": get_cart_summary(site_id)
    }
