"""
Embedding record database operations.

Note: This tracks embedding metadata in SQLite.
The actual embeddings are stored in ChromaDB.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
import json

from .base import get_db


def create_embedding(
    embedding_id: str,
    file_id: str,
    chunk_index: int,
    chunk_text: str,
    metadata: Optional[Dict] = None,
    collection: str = "culinart_bible"
) -> Dict[str, Any]:
    """Create or update an embedding record."""
    now = datetime.utcnow().isoformat()

    with get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO embeddings (id, file_id, chunk_index, chunk_text, metadata, collection, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (embedding_id, file_id, chunk_index, chunk_text, json.dumps(metadata or {}), collection, now))

    return {"id": embedding_id, "file_id": file_id, "chunk_index": chunk_index, "collection": collection}


def get_file_embeddings(file_id: str) -> List[Dict[str, Any]]:
    """Get all embeddings for a file."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM embeddings WHERE file_id = ? ORDER BY chunk_index",
            (file_id,)
        ).fetchall()
        return [dict(row) for row in rows]
