"""
Search API router.
Product search using MOG catalog text matching.
"""
import logging
from fastapi import APIRouter, HTTPException, Form, Query
from typing import Optional

# Import purchase match state to access the initialized MOG embedding index
from backend.api.routers.purchase_match import _purchase_match_state, _init_purchase_match

router = APIRouter(tags=["Search"])
logger = logging.getLogger(__name__)


@router.post("/api/search")
def search_documents(
    query: str = Form(...),
    limit: int = Form(10),
    file_id: Optional[str] = Form(None),
    site_id: Optional[str] = Form(None),
    date_from: Optional[str] = Form(None),
    date_to: Optional[str] = Form(None),
    sort_by: str = Form("relevance")
):
    """
    Search for products in the MOG catalog.
    Uses text matching on product descriptions.
    """
    # Ensure purchase match (and MOG index) is initialized
    _init_purchase_match()

    mog_index = _purchase_match_state.get("mog_index")
    if not mog_index:
        raise HTTPException(status_code=503, detail="Product search not available. MOG not loaded.")

    # Text search - find items where description contains query terms
    query_upper = query.upper()
    query_words = query_upper.split()

    results = []
    for item in mog_index.all_items():
        desc_upper = item.description.upper()
        # Check if all query words appear in description
        if all(word in desc_upper for word in query_words):
            results.append({
                "sku": item.sku,
                "description": item.description,
                "vendor": item.vendor,
                "price": float(item.price) if item.price else None,
                "match": "exact"
            })

    # Sort by description length (shorter = more specific match)
    results.sort(key=lambda x: len(x["description"]))

    return {"results": results[:limit], "count": len(results), "query": query}
