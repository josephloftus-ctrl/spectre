"""
Collections API router.
"""
from fastapi import APIRouter, HTTPException

from backend.core.collections import (
    COLLECTIONS, list_collections, get_collection_stats,
    migrate_spectre_to_knowledge_base, ensure_data_directories
)

router = APIRouter(prefix="/api/collections", tags=["Collections"])


@router.get("")
def get_collections():
    """
    List all available collections with their stats.
    Collections: knowledge_base, food_knowledge, living_memory
    """
    collections = list_collections()
    return {"collections": collections, "count": len(collections)}


@router.get("/{name}")
def get_collection_details(name: str):
    """Get detailed stats for a specific collection."""
    if name not in COLLECTIONS:
        raise HTTPException(status_code=404, detail=f"Collection '{name}' not found")
    stats = get_collection_stats(name)
    return stats


@router.post("/migrate")
def migrate_collections():
    """
    Migrate existing spectre_documents to knowledge_base.
    Run this once to rename the old collection.
    """
    result = migrate_spectre_to_knowledge_base()
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Migration failed"))
    return result


@router.post("/init")
def initialize_collections():
    """Initialize collection directories and ensure all collections exist."""
    ensure_data_directories()
    collections = list_collections()
    return {
        "success": True,
        "message": "Collections initialized",
        "collections": collections
    }
