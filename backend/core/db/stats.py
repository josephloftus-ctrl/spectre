"""
Database statistics operations.
"""
from typing import Dict, Any

from .base import get_db, FileStatus, JobStatus


def get_stats() -> Dict[str, Any]:
    """Get database statistics."""
    with get_db() as conn:
        file_counts = {}
        for status in FileStatus:
            count = conn.execute(
                "SELECT COUNT(*) FROM files WHERE status = ?",
                (status.value,)
            ).fetchone()[0]
            file_counts[status.value] = count

        job_counts = {}
        for status in JobStatus:
            count = conn.execute(
                "SELECT COUNT(*) FROM jobs WHERE status = ?",
                (status.value,)
            ).fetchone()[0]
            job_counts[status.value] = count

        embedding_count = conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]

        return {
            "files": file_counts,
            "jobs": job_counts,
            "embeddings": embedding_count
        }
