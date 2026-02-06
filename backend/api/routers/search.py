"""
Search and embeddings API router.
"""
import logging
from fastapi import APIRouter, HTTPException, Form, Query
from typing import Optional
import uuid

from backend.core.database import FileStatus, JobType, list_files, create_job
from backend.core.embeddings import (
    search, find_similar, get_embedding_stats, delete_file_embeddings,
    reset_collection, search_unified
)
from backend.core.collections import COLLECTIONS
# Import purchase match state to access the initialized MOG embedding index
from backend.api.routers.purchase_match import _purchase_match_state, _init_purchase_match

router = APIRouter(tags=["Search"])
logger = logging.getLogger(__name__)


# ============== Search API ==============

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


@router.get("/api/search/similar/{file_id}")
def get_similar_documents(
    file_id: str,
    chunk: int = Query(0),
    limit: int = Query(5)
):
    """Find documents similar to a specific file chunk."""
    results = find_similar(file_id, chunk_index=chunk, limit=limit)
    return {"results": results, "count": len(results), "file_id": file_id}


@router.post("/api/search/unified")
def unified_search(
    query: str = Form(...),
    limit: int = Form(10),
    collections: Optional[str] = Form(None),
    date_from: Optional[str] = Form(None),
    date_to: Optional[str] = Form(None),
    site_id: Optional[str] = Form(None)
):
    """
    Search across multiple collections.
    - collections: comma-separated list (e.g., "knowledge_base,living_memory") or empty for all
    """
    collection_list = None
    if collections:
        collection_list = [c.strip() for c in collections.split(",") if c.strip()]

    results = search_unified(
        query=query,
        limit=limit,
        collections=collection_list,
        date_from=date_from,
        date_to=date_to,
        site_id=site_id
    )
    return {"results": results, "count": len(results), "query": query}


@router.post("/api/search/{collection_name}")
def search_collection(
    collection_name: str,
    query: str = Form(...),
    limit: int = Form(10),
    file_id: Optional[str] = Form(None),
    site_id: Optional[str] = Form(None),
    date_from: Optional[str] = Form(None),
    date_to: Optional[str] = Form(None),
    sort_by: str = Form("relevance")
):
    """Search within a specific collection."""
    if collection_name not in COLLECTIONS:
        raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' not found")

    results = search(
        query,
        limit=limit,
        file_id=file_id,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        site_id=site_id,
        collection_name=collection_name
    )
    return {"results": results, "count": len(results), "collection": collection_name}


# ============== Embeddings API ==============

@router.delete("/api/embeddings/{file_id}")
def remove_file_embeddings(file_id: str):
    """Delete all embeddings for a file."""
    count = delete_file_embeddings(file_id)
    return {"success": True, "deleted_count": count}


@router.get("/api/embeddings/stats")
def embedding_statistics():
    """Get embedding system statistics."""
    return get_embedding_stats()


@router.post("/api/embeddings/reset")
def reset_embeddings():
    """
    Reset the embedding collection. Required when changing embedding models.
    WARNING: This deletes all existing embeddings. Re-embedding is needed after.
    """
    result = reset_collection()
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Reset failed"))
    return result


@router.post("/api/embeddings/reindex")
def reindex_all_embeddings():
    """
    Queue re-embedding jobs for all completed files.
    Use after resetting embeddings or changing models.
    """
    files = list_files(status=FileStatus.COMPLETED, limit=500)

    queued = 0
    for f in files:
        job_id = str(uuid.uuid4())
        create_job(job_id, JobType.EMBED, f["id"], priority=1)
        queued += 1

    return {
        "success": True,
        "message": f"Queued {queued} files for re-embedding",
        "queued_count": queued
    }
