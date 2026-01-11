"""
Embedding pipeline using Ollama (qwen3-embedding) and ChromaDB.

Supports multiple collections:
- culinart_bible: Static SOPs, inventory, company knowledge
- food_knowledge: Expandable recipes, food science, reference
- living_memory: Personal schedules, notes, work files
"""
import logging
import os
import uuid
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import requests

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    chromadb = None

from .database import create_embedding, get_file_embeddings
from .collections import (
    COLLECTIONS,
    DEFAULT_COLLECTION,
    get_collection as get_named_collection,
    get_chroma_client,
    CHROMA_DIR
)

logger = logging.getLogger(__name__)

# Configuration
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = "nomic-embed-text:v1.5"

# Chunking settings
MAX_CHUNK_SIZE = 500  # characters
CHUNK_OVERLAP = 50


def get_collection(name: str = DEFAULT_COLLECTION, force_fresh: bool = False):
    """Get or create a document collection.

    Args:
        name: Collection name (culinart_bible, food_knowledge, living_memory)
        force_fresh: If True, create a completely new client connection
    """
    return get_named_collection(name, create=True)


def embed_text(text: str) -> Optional[List[float]]:
    """
    Generate embedding for text using Ollama.
    Returns None if embedding fails.
    """
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={
                "model": EMBED_MODEL,
                "prompt": text
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        return data.get("embedding")
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        return None


def embed_batch(texts: List[str]) -> List[Optional[List[float]]]:
    """Embed multiple texts. Returns list of embeddings (None for failures)."""
    return [embed_text(t) for t in texts]


def chunk_text(text: str, max_size: int = MAX_CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping chunks."""
    if len(text) <= max_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + max_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap

    return chunks


def chunk_rows(rows: List[Dict], max_size: int = MAX_CHUNK_SIZE) -> List[Dict[str, Any]]:
    """
    Convert rows of data into embeddable chunks.
    Groups multiple rows into chunks that fit the size limit.
    """
    chunks = []
    current_chunk = []
    current_size = 0

    for i, row in enumerate(rows):
        row_text = " | ".join(str(v) for v in row.values() if v)
        row_size = len(row_text)

        if current_size + row_size > max_size and current_chunk:
            # Save current chunk
            chunks.append({
                "text": "\n".join(r["text"] for r in current_chunk),
                "row_indices": [r["index"] for r in current_chunk],
                "row_count": len(current_chunk)
            })
            current_chunk = []
            current_size = 0

        current_chunk.append({"text": row_text, "index": i})
        current_size += row_size + 1  # +1 for newline

    # Don't forget the last chunk
    if current_chunk:
        chunks.append({
            "text": "\n".join(r["text"] for r in current_chunk),
            "row_indices": [r["index"] for r in current_chunk],
            "row_count": len(current_chunk)
        })

    return chunks


def embed_document(
    file_id: str,
    parsed_data: Dict[str, Any],
    site_id: Optional[str] = None,
    filename: Optional[str] = None,
    file_date: Optional[str] = None,
    collection_name: str = DEFAULT_COLLECTION
) -> Dict[str, Any]:
    """
    Generate embeddings for a parsed document and store in ChromaDB.

    Args:
        file_id: The file ID
        parsed_data: Parsed document data with 'rows' and 'headers' (and optionally 'text_content' for PDFs)
        site_id: Optional site identifier
        filename: Original filename
        file_date: Date string (ISO format) for the file, defaults to now
        collection_name: Target collection (culinart_bible, food_knowledge, living_memory)

    Returns:
        Result dict with chunk count and status
    """
    collection = get_collection(collection_name)
    if not collection:
        return {"error": "ChromaDB not available", "chunks": 0}

    rows = parsed_data.get("rows", [])
    headers = parsed_data.get("headers", [])
    text_content = parsed_data.get("text_content", [])  # For PDFs

    # If no rows but has text_content (PDF with text but no tables), convert to rows
    if not rows and text_content:
        rows = [{"content": block.get("content", ""), "page": block.get("page", 0)}
                for block in text_content if block.get("content")]
        headers = ["content", "page"]

    if not rows:
        return {"error": "No content to embed", "chunks": 0}

    # Use provided date or current timestamp
    embed_date = file_date or datetime.now().isoformat()

    # Create chunks from rows
    chunks = chunk_rows(rows)

    embedded_count = 0
    failed_count = 0

    for i, chunk in enumerate(chunks):
        chunk_id = f"{file_id}_chunk_{i}"
        text = chunk["text"]

        # Generate embedding
        embedding = embed_text(text)
        if not embedding:
            failed_count += 1
            continue

        # Store in ChromaDB with date metadata
        try:
            collection.upsert(
                ids=[chunk_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[{
                    "file_id": file_id,
                    "site_id": site_id or "",
                    "filename": filename or "",
                    "chunk_index": i,
                    "row_indices": json.dumps(chunk["row_indices"]),
                    "row_count": chunk["row_count"],
                    "headers": json.dumps(headers),
                    "date": embed_date,
                    "date_epoch": int(datetime.fromisoformat(embed_date.replace('Z', '+00:00')).timestamp()) if embed_date else 0,
                    "collection": collection_name
                }]
            )
            embedded_count += 1

            # Also store in SQLite for reference
            create_embedding(
                embedding_id=chunk_id,
                file_id=file_id,
                chunk_index=i,
                chunk_text=text[:500],  # Truncate for storage
                metadata={
                    "row_indices": chunk["row_indices"],
                    "row_count": chunk["row_count"],
                    "date": embed_date
                }
            )

        except Exception as e:
            logger.error(f"Failed to store chunk {chunk_id}: {e}")
            failed_count += 1

    return {
        "success": True,
        "chunks_embedded": embedded_count,
        "chunks_failed": failed_count,
        "total_chunks": len(chunks)
    }


def search(
    query: str,
    limit: int = 10,
    file_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sort_by: str = "relevance",
    site_id: Optional[str] = None,
    collection_name: str = DEFAULT_COLLECTION
) -> List[Dict[str, Any]]:
    """
    Search for similar documents using semantic search with date awareness.

    Args:
        query: Search query text
        limit: Maximum number of results
        file_id: Optional file ID to filter results
        date_from: Optional start date (ISO format YYYY-MM-DD)
        date_to: Optional end date (ISO format YYYY-MM-DD)
        sort_by: 'relevance' (default), 'date_desc', 'date_asc', or 'site'
        site_id: Optional site ID to filter results
        collection_name: Collection to search (culinart_bible, food_knowledge, living_memory)

    Returns:
        List of matching chunks with scores, sorted as requested
    """
    collection = get_collection(collection_name)
    if not collection:
        return []

    # Generate query embedding
    query_embedding = embed_text(query)
    if not query_embedding:
        return []

    # Build filter conditions
    where_conditions = []

    if file_id:
        where_conditions.append({"file_id": file_id})

    if site_id:
        where_conditions.append({"site_id": site_id})

    # Date filtering using epoch timestamps
    if date_from:
        try:
            from_epoch = int(datetime.fromisoformat(date_from).timestamp())
            where_conditions.append({"date_epoch": {"$gte": from_epoch}})
        except ValueError:
            logger.warning(f"Invalid date_from format: {date_from}")

    if date_to:
        try:
            # Add 1 day to include the entire end date
            to_epoch = int(datetime.fromisoformat(date_to).timestamp()) + 86400
            where_conditions.append({"date_epoch": {"$lte": to_epoch}})
        except ValueError:
            logger.warning(f"Invalid date_to format: {date_to}")

    # Combine conditions
    where_filter = None
    if len(where_conditions) == 1:
        where_filter = where_conditions[0]
    elif len(where_conditions) > 1:
        where_filter = {"$and": where_conditions}

    try:
        # Fetch more results for post-sorting if needed
        fetch_limit = limit * 3 if sort_by != "relevance" else limit

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=fetch_limit,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )

        # Format results
        formatted = []
        for i in range(len(results["ids"][0])):
            metadata = results["metadatas"][0][i]
            formatted.append({
                "id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "metadata": metadata,
                "distance": results["distances"][0][i],
                "score": 1 - results["distances"][0][i],
                "date": metadata.get("date", ""),
                "date_epoch": metadata.get("date_epoch", 0),
                "collection": collection_name
            })

        # Sort results
        if sort_by == "date_desc":
            formatted.sort(key=lambda x: x.get("date_epoch", 0), reverse=True)
        elif sort_by == "date_asc":
            formatted.sort(key=lambda x: x.get("date_epoch", 0))
        elif sort_by == "site":
            # Sort by site, then by relevance within each site
            formatted.sort(key=lambda x: (x.get("metadata", {}).get("site_id", ""), -x.get("score", 0)))
        # else: keep relevance order (default from ChromaDB)

        return formatted[:limit]

    except Exception as e:
        logger.error(f"Search failed: {e}")
        return []


def find_similar(
    file_id: str,
    chunk_index: int = 0,
    limit: int = 5,
    collection_name: str = DEFAULT_COLLECTION
) -> List[Dict[str, Any]]:
    """Find documents similar to a specific chunk."""
    collection = get_collection(collection_name)
    if not collection:
        return []

    chunk_id = f"{file_id}_chunk_{chunk_index}"

    try:
        # Get the chunk's embedding
        result = collection.get(ids=[chunk_id], include=["embeddings"])
        if not result["embeddings"]:
            return []

        embedding = result["embeddings"][0]

        # Search for similar (excluding self)
        results = collection.query(
            query_embeddings=[embedding],
            n_results=limit + 1,  # +1 to account for self
            include=["documents", "metadatas", "distances"]
        )

        # Filter out self and format
        formatted = []
        for i in range(len(results["ids"][0])):
            if results["ids"][0][i] == chunk_id:
                continue
            formatted.append({
                "id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],
                "score": 1 - results["distances"][0][i]
            })

        return formatted[:limit]

    except Exception as e:
        logger.error(f"Similar search failed: {e}")
        return []


def delete_file_embeddings(file_id: str, collection_name: str = DEFAULT_COLLECTION) -> int:
    """Delete all embeddings for a file. Returns count deleted."""
    collection = get_collection(collection_name)
    if not collection:
        return 0

    try:
        # Get all chunk IDs for this file
        results = collection.get(
            where={"file_id": file_id},
            include=[]
        )

        if results["ids"]:
            collection.delete(ids=results["ids"])
            return len(results["ids"])

        return 0

    except Exception as e:
        logger.error(f"Failed to delete embeddings for {file_id}: {e}")
        return 0


def get_embedding_stats(collection_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Get embedding statistics.

    Args:
        collection_name: Specific collection, or None for all collections
    """
    from .collections import list_collections

    if collection_name:
        collection = get_collection(collection_name)
        if not collection:
            return {"available": False, "error": f"Collection {collection_name} not available"}

        try:
            count = collection.count()
            return {
                "available": True,
                "collection": collection_name,
                "total_chunks": count,
                "model": EMBED_MODEL
            }
        except Exception as e:
            return {"available": False, "error": str(e)}
    else:
        # Return stats for all collections
        collections = list_collections()
        total_chunks = sum(c.get("chunk_count", 0) for c in collections)

        return {
            "available": True,
            "collections": collections,
            "total_chunks": total_chunks,
            "model": EMBED_MODEL
        }


def reset_collection(collection_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Reset embedding collection(s). Required when changing embedding models.

    Args:
        collection_name: Specific collection to reset, or None for all
    """
    import shutil

    try:
        if collection_name:
            # Reset just one collection
            client = get_chroma_client()
            if client:
                try:
                    client.delete_collection(name=collection_name)
                    logger.info(f"Deleted collection: {collection_name}")
                except Exception:
                    pass  # Collection might not exist

                # Recreate it
                meta = COLLECTIONS.get(collection_name, {})
                client.get_or_create_collection(
                    name=collection_name,
                    metadata={"description": meta.get("description", "")}
                )
                logger.info(f"Created fresh collection: {collection_name}")

            return {"success": True, "message": f"Collection {collection_name} reset"}
        else:
            # Reset all - wipe the entire chroma directory
            if CHROMA_DIR.exists():
                shutil.rmtree(CHROMA_DIR)
                logger.info(f"Removed chroma directory: {CHROMA_DIR}")

            CHROMA_DIR.mkdir(parents=True, exist_ok=True)

            # Recreate all collections
            client = chromadb.PersistentClient(
                path=str(CHROMA_DIR),
                settings=Settings(anonymized_telemetry=False)
            )
            for name, meta in COLLECTIONS.items():
                client.get_or_create_collection(
                    name=name,
                    metadata={"description": meta["description"]}
                )
                logger.info(f"Created collection: {name}")

            return {"success": True, "message": f"All collections reset. Ready for {EMBED_MODEL}"}

    except Exception as e:
        logger.error(f"Failed to reset collection: {e}")
        return {"error": str(e), "success": False}


def search_unified(
    query: str,
    limit: int = 10,
    collections: Optional[List[str]] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    site_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search across multiple collections and merge results.

    Args:
        query: Search query text
        limit: Maximum total results
        collections: List of collection names to search, or None for all
        date_from: Optional start date filter
        date_to: Optional end date filter
        site_id: Optional site filter

    Returns:
        Merged results from all collections, sorted by relevance score
    """
    target_collections = collections or list(COLLECTIONS.keys())

    all_results = []

    # Search each collection
    for coll_name in target_collections:
        if coll_name not in COLLECTIONS:
            continue

        results = search(
            query=query,
            limit=limit,  # Get limit from each, then merge
            date_from=date_from,
            date_to=date_to,
            site_id=site_id,
            collection_name=coll_name
        )
        all_results.extend(results)

    # Sort by score descending and limit
    all_results.sort(key=lambda x: x.get("score", 0), reverse=True)

    return all_results[:limit]
