"""
Multi-collection management for RAG system.

Collections:
- knowledge_base: Static SOPs, inventory, company knowledge
- food_knowledge: Expandable recipes, food science, reference
- living_memory: Personal schedules, notes, work files
"""
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    chromadb = None

logger = logging.getLogger(__name__)

# Collection definitions
COLLECTIONS = {
    "knowledge_base": {
        "description": "SOPs, training materials, and company knowledge",
        "icon": "book",
        "color": "amber",
        "type": "static",  # Rarely changes, company reference
    },
    "inventory": {
        "description": "Uploaded inventory documents and count sheets",
        "icon": "package",
        "color": "emerald",
        "type": "dynamic",  # Updated with each upload
    },
    "food_knowledge": {
        "description": "Food science, recipes, and reference materials",
        "icon": "utensils",
        "color": "green",
        "type": "expandable",  # Grows over time
    },
    "living_memory": {
        "description": "Personal schedules, notes, and work files",
        "icon": "brain",
        "color": "purple",
        "type": "dynamic",  # Changes frequently
    }
}

# Default collection for backwards compatibility
DEFAULT_COLLECTION = "knowledge_base"

# ChromaDB persistence directory
CHROMA_DIR = Path(__file__).resolve().parents[2] / "data" / "embeddings" / "chroma"

# Data directories for each collection
DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "collections"


def get_chroma_client():
    """Get ChromaDB client with persistence."""
    if not CHROMADB_AVAILABLE:
        logger.warning("ChromaDB not installed. Run: pip install chromadb")
        return None

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False)
    )
    return client


def get_collection(name: str = DEFAULT_COLLECTION, create: bool = True):
    """
    Get or create a specific collection.

    Args:
        name: Collection name (must be in COLLECTIONS)
        create: If True, create collection if it doesn't exist

    Returns:
        ChromaDB collection or None
    """
    if not CHROMADB_AVAILABLE:
        return None

    if name not in COLLECTIONS:
        logger.error(f"Unknown collection: {name}. Valid: {list(COLLECTIONS.keys())}")
        return None

    client = get_chroma_client()
    if not client:
        return None

    collection_meta = COLLECTIONS[name]

    if create:
        return client.get_or_create_collection(
            name=name,
            metadata={"description": collection_meta["description"]}
        )
    else:
        try:
            return client.get_collection(name=name)
        except Exception:
            return None


def list_collections() -> List[Dict[str, Any]]:
    """
    List all collections with their stats.

    Returns:
        List of collection info dicts
    """
    client = get_chroma_client()
    if not client:
        return []

    result = []

    for name, meta in COLLECTIONS.items():
        info = {
            "name": name,
            "description": meta["description"],
            "icon": meta["icon"],
            "color": meta["color"],
            "type": meta["type"],
            "chunk_count": 0,
            "exists": False
        }

        try:
            collection = client.get_collection(name=name)
            info["chunk_count"] = collection.count()
            info["exists"] = True
        except Exception:
            # Collection doesn't exist yet
            pass

        result.append(info)

    return result


def get_collection_stats(name: str) -> Dict[str, Any]:
    """
    Get detailed stats for a specific collection.

    Args:
        name: Collection name

    Returns:
        Stats dict with counts, metadata, etc.
    """
    if name not in COLLECTIONS:
        return {"error": f"Unknown collection: {name}"}

    collection = get_collection(name, create=False)
    meta = COLLECTIONS[name]

    stats = {
        "name": name,
        "description": meta["description"],
        "icon": meta["icon"],
        "color": meta["color"],
        "type": meta["type"],
        "exists": collection is not None,
        "chunk_count": 0,
        "file_count": 0,
        "sites": [],
        "date_range": {"earliest": None, "latest": None}
    }

    if not collection:
        return stats

    try:
        stats["chunk_count"] = collection.count()

        # Get unique file IDs and sites
        if stats["chunk_count"] > 0:
            # Sample some chunks to get metadata
            sample = collection.get(limit=1000, include=["metadatas"])

            file_ids = set()
            sites = set()
            dates = []

            for meta in sample.get("metadatas", []):
                if meta.get("file_id"):
                    file_ids.add(meta["file_id"])
                if meta.get("site_id"):
                    sites.add(meta["site_id"])
                if meta.get("date"):
                    dates.append(meta["date"])

            stats["file_count"] = len(file_ids)
            stats["sites"] = sorted(list(sites))

            if dates:
                stats["date_range"] = {
                    "earliest": min(dates),
                    "latest": max(dates)
                }

    except Exception as e:
        logger.error(f"Error getting stats for {name}: {e}")

    return stats


def ensure_data_directories():
    """Create data directories for all collections."""
    for name in COLLECTIONS:
        collection_dir = DATA_DIR / name
        (collection_dir / "inbox").mkdir(parents=True, exist_ok=True)
        (collection_dir / "processed").mkdir(parents=True, exist_ok=True)

    # Special subdirs for living_memory
    living_dir = DATA_DIR / "living_memory"
    (living_dir / "schedules").mkdir(parents=True, exist_ok=True)
    (living_dir / "notes").mkdir(parents=True, exist_ok=True)

    logger.info(f"Ensured data directories at {DATA_DIR}")


def migrate_spectre_to_knowledge_base() -> Dict[str, Any]:
    """
    Migrate existing spectre_documents collection to knowledge_base.

    This creates a new collection with the same data and then
    optionally deletes the old one.

    Returns:
        Migration result dict
    """
    if not CHROMADB_AVAILABLE:
        return {"error": "ChromaDB not available"}

    client = get_chroma_client()
    if not client:
        return {"error": "Could not get ChromaDB client"}

    # Check if old collection exists
    try:
        old_collection = client.get_collection(name="spectre_documents")
        old_count = old_collection.count()
    except Exception:
        return {
            "success": True,
            "message": "No spectre_documents collection to migrate",
            "migrated": 0
        }

    if old_count == 0:
        return {
            "success": True,
            "message": "spectre_documents is empty, nothing to migrate",
            "migrated": 0
        }

    # Get or create the new collection
    new_collection = client.get_or_create_collection(
        name="knowledge_base",
        metadata={"description": COLLECTIONS["knowledge_base"]["description"]}
    )

    # Check if already migrated
    new_count = new_collection.count()
    if new_count >= old_count:
        return {
            "success": True,
            "message": f"knowledge_base already has {new_count} chunks (old had {old_count})",
            "migrated": 0,
            "already_migrated": True
        }

    # Migrate in batches
    batch_size = 100
    offset = 0
    migrated = 0

    while True:
        # Get batch from old collection
        batch = old_collection.get(
            limit=batch_size,
            offset=offset,
            include=["embeddings", "documents", "metadatas"]
        )

        if not batch["ids"]:
            break

        # Upsert into new collection
        new_collection.upsert(
            ids=batch["ids"],
            embeddings=batch["embeddings"],
            documents=batch["documents"],
            metadatas=batch["metadatas"]
        )

        migrated += len(batch["ids"])
        offset += batch_size

        logger.info(f"Migrated {migrated}/{old_count} chunks")

    # Verify migration
    final_count = new_collection.count()

    return {
        "success": True,
        "message": f"Migrated {migrated} chunks from spectre_documents to knowledge_base",
        "migrated": migrated,
        "old_count": old_count,
        "new_count": final_count
    }


def delete_old_collection() -> Dict[str, Any]:
    """Delete the old spectre_documents collection after migration."""
    if not CHROMADB_AVAILABLE:
        return {"error": "ChromaDB not available"}

    client = get_chroma_client()
    if not client:
        return {"error": "Could not get ChromaDB client"}

    try:
        client.delete_collection(name="spectre_documents")
        return {"success": True, "message": "Deleted spectre_documents collection"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def collection_exists(name: str) -> bool:
    """Check if a collection exists in ChromaDB."""
    client = get_chroma_client()
    if not client:
        return False

    try:
        client.get_collection(name=name)
        return True
    except Exception:
        return False
