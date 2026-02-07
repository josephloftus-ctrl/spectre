"""
Collections module — stub.
ChromaDB vector store has been removed. This module is kept for import compatibility.
"""
from pathlib import Path
from typing import Dict, Any, List

COLLECTIONS: Dict[str, Any] = {}
DEFAULT_COLLECTION = ""
CHROMA_DIR = Path("data/embeddings/chroma")


def get_chroma_client():
    return None


def get_collection(name: str = "", create: bool = True):
    return None


def list_collections() -> List[Dict[str, Any]]:
    return []


def get_collection_stats(name: str) -> Dict[str, Any]:
    return {"available": False, "message": "Embeddings pipeline removed"}


def collection_exists(name: str) -> bool:
    return False


def ensure_data_directories():
    pass


def migrate_spectre_to_knowledge_base() -> Dict[str, Any]:
    return {"success": True, "message": "No migration needed — embeddings removed"}


def delete_old_collection():
    pass
