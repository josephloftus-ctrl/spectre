"""
File database operations.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
import json

from .base import get_db, FileStatus, ALLOWED_FILE_COLUMNS


def create_file(
    file_id: str,
    filename: str,
    original_path: str,
    file_type: str,
    file_size: int,
    site_id: Optional[str] = None,
    collection: str = "knowledge_base"
) -> Dict[str, Any]:
    """Create a new file record."""
    now = datetime.utcnow().isoformat()

    with get_db() as conn:
        conn.execute("""
            INSERT INTO files (id, filename, original_path, current_path, file_type, file_size, site_id, collection, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (file_id, filename, original_path, original_path, file_type, file_size, site_id, collection, FileStatus.PENDING.value, now, now))

    return get_file(file_id)


def get_file(file_id: str) -> Optional[Dict[str, Any]]:
    """Get a file by ID."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
        if row:
            return dict(row)
    return None


def list_files(
    status: Optional[FileStatus] = None,
    site_id: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """List files with optional filters."""
    query = "SELECT * FROM files WHERE 1=1"
    params = []

    if status:
        query += " AND status = ?"
        params.append(status.value)

    if site_id:
        query += " AND site_id = ?"
        params.append(site_id)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def update_file(file_id: str, **updates) -> Optional[Dict[str, Any]]:
    """Update a file record."""
    if not updates:
        return get_file(file_id)

    # Validate column names to prevent SQL injection
    invalid_cols = set(updates.keys()) - ALLOWED_FILE_COLUMNS - {'updated_at'}
    if invalid_cols:
        raise ValueError(f"Invalid column names: {invalid_cols}")

    updates["updated_at"] = datetime.utcnow().isoformat()

    set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
    values = list(updates.values()) + [file_id]

    with get_db() as conn:
        conn.execute(f"UPDATE files SET {set_clause} WHERE id = ?", values)

    return get_file(file_id)


def update_file_status(
    file_id: str,
    status: FileStatus,
    error_message: Optional[str] = None,
    parsed_data: Optional[Dict] = None
) -> Optional[Dict[str, Any]]:
    """Update file status with optional error/data."""
    updates = {"status": status.value}

    if error_message:
        updates["error_message"] = error_message

    if parsed_data:
        updates["parsed_data"] = json.dumps(parsed_data)

    if status == FileStatus.COMPLETED:
        updates["processed_at"] = datetime.utcnow().isoformat()

    return update_file(file_id, **updates)


def delete_file_record(file_id: str) -> bool:
    """Delete a file record and its associated jobs/embeddings from the database."""
    with get_db() as conn:
        # Delete associated jobs
        conn.execute("DELETE FROM jobs WHERE file_id = ?", (file_id,))
        # Delete associated embeddings record
        conn.execute("DELETE FROM embeddings WHERE file_id = ?", (file_id,))
        # Delete the file record
        result = conn.execute("DELETE FROM files WHERE id = ?", (file_id,))
        return result.rowcount > 0
