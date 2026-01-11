"""
MOG Embedding Index - Semantic search for SKU suggestions.

Uses ChromaDB + Ollama embeddings to find similar items by description,
achieving much higher accuracy than word-based matching.
"""

import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
import requests

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    chromadb = None

from .mog import MOGIndex, MOGItem

logger = logging.getLogger(__name__)

# Configuration
OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text:v1.5"  # Fast, good quality
CHROMA_DIR = Path(__file__).resolve().parents[2] / "data" / "embeddings" / "mog"
COLLECTION_NAME = "mog_items"


class MOGEmbeddingIndex:
    """
    Semantic search index for MOG items using embeddings.

    Embeds item descriptions and enables fast similarity search
    to find likely matches for mistyped SKUs.
    """

    def __init__(self):
        self.collection = None
        self.items_by_id: Dict[str, MOGItem] = {}
        self._initialized = False

    def _get_collection(self):
        """Get or create ChromaDB collection."""
        if not CHROMADB_AVAILABLE:
            logger.warning("ChromaDB not available")
            return None

        CHROMA_DIR.mkdir(parents=True, exist_ok=True)

        client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False)
        )

        return client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "MOG catalog items for SKU matching"}
        )

    def _embed_text(self, text: str) -> Optional[List[float]]:
        """Generate embedding using Ollama."""
        try:
            response = requests.post(
                f"{OLLAMA_URL}/api/embeddings",
                json={"model": EMBED_MODEL, "prompt": text},
                timeout=30
            )
            response.raise_for_status()
            return response.json().get("embedding")
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            return None

    def build_index(self, mog_index: MOGIndex, force_rebuild: bool = False) -> bool:
        """
        Build embedding index from MOG catalog.

        Args:
            mog_index: The MOGIndex with all catalog items
            force_rebuild: If True, rebuild even if index exists

        Returns:
            True if successful
        """
        self.collection = self._get_collection()
        if not self.collection:
            return False

        # Check if already indexed
        existing_count = self.collection.count()
        if existing_count > 0 and not force_rebuild:
            logger.info(f"MOG embedding index already has {existing_count} items")
            # Load item mapping
            self._load_items_from_mog(mog_index)
            self._initialized = True
            return True

        # Clear and rebuild
        if force_rebuild and existing_count > 0:
            logger.info("Force rebuilding MOG embedding index...")
            # Delete all existing
            all_ids = self.collection.get()["ids"]
            if all_ids:
                self.collection.delete(ids=all_ids)

        # Get all items from MOG
        all_items = mog_index.all_items()
        if not all_items:
            logger.warning("No MOG items to index")
            return False

        logger.info(f"Building embedding index for {len(all_items)} MOG items...")

        # Process in batches
        batch_size = 100
        indexed = 0

        for i in range(0, len(all_items), batch_size):
            batch = all_items[i:i + batch_size]

            ids = []
            embeddings = []
            metadatas = []
            documents = []

            for item in batch:
                # Create searchable text
                text = f"{item.description} {item.vendor}"
                embedding = self._embed_text(text)

                if embedding:
                    item_id = f"{item.vendor}_{item.sku}"
                    ids.append(item_id)
                    embeddings.append(embedding)
                    documents.append(text)
                    metadatas.append({
                        "sku": item.sku,
                        "description": item.description,
                        "vendor": item.vendor,
                        "price": float(item.price) if item.price else 0.0
                    })
                    self.items_by_id[item_id] = item

            if ids:
                self.collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas
                )
                indexed += len(ids)
                logger.info(f"Indexed {indexed}/{len(all_items)} items...")

        self._initialized = True
        logger.info(f"MOG embedding index built with {indexed} items")
        return True

    def _load_items_from_mog(self, mog_index: MOGIndex):
        """Load item mapping from MOG index."""
        for item in mog_index.all_items():
            item_id = f"{item.vendor}_{item.sku}"
            self.items_by_id[item_id] = item

    def find_similar(
        self,
        description: str,
        limit: int = 5,
        min_score: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Find MOG items similar to the given description.

        Args:
            description: Item description to search for
            limit: Max results to return
            min_score: Minimum similarity score (0-1)

        Returns:
            List of matches with sku, description, vendor, price, similarity
        """
        if not self._initialized or not self.collection:
            return []

        # Embed query
        embedding = self._embed_text(description)
        if not embedding:
            return []

        # Search
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=limit,
            include=["metadatas", "distances"]
        )

        if not results or not results["ids"] or not results["ids"][0]:
            return []

        matches = []
        for i, item_id in enumerate(results["ids"][0]):
            # ChromaDB returns distance, convert to similarity (1 - distance for cosine)
            distance = results["distances"][0][i] if results["distances"] else 0
            # Cosine distance: 0 = identical, 2 = opposite
            # Convert to similarity: 1 = identical, 0 = opposite
            similarity = max(0, 1 - (distance / 2))

            if similarity < min_score:
                continue

            metadata = results["metadatas"][0][i] if results["metadatas"] else {}

            matches.append({
                "sku": metadata.get("sku", ""),
                "description": metadata.get("description", ""),
                "vendor": metadata.get("vendor", ""),
                "price": metadata.get("price"),
                "similarity": round(similarity * 100, 1)  # As percentage
            })

        return matches

    @property
    def is_ready(self) -> bool:
        """Check if index is ready for queries."""
        return self._initialized and self.collection is not None


# Global instance
_mog_embedding_index: Optional[MOGEmbeddingIndex] = None


def get_mog_embedding_index() -> MOGEmbeddingIndex:
    """Get or create global MOG embedding index."""
    global _mog_embedding_index
    if _mog_embedding_index is None:
        _mog_embedding_index = MOGEmbeddingIndex()
    return _mog_embedding_index


def build_mog_embeddings(mog_index: MOGIndex, force: bool = False) -> bool:
    """Build the MOG embedding index."""
    index = get_mog_embedding_index()
    return index.build_index(mog_index, force_rebuild=force)


def find_similar_items(description: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Find similar MOG items by description."""
    index = get_mog_embedding_index()
    return index.find_similar(description, limit=limit)
