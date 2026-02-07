"""
Collections API router — stub.
Vector embeddings have been removed. This router is kept for API compatibility.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/collections", tags=["Collections"])


@router.get("")
def get_collections():
    """Collections are no longer used (embeddings pipeline removed)."""
    return {"collections": [], "count": 0, "message": "Embeddings pipeline removed"}
