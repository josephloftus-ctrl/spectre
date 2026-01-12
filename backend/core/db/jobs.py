"""
Job queue database operations.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
import json

from .base import get_db, JobStatus, JobType


def create_job(
    job_id: str,
    job_type: JobType,
    file_id: Optional[str] = None,
    priority: int = 0
) -> Dict[str, Any]:
    """Create a new job."""
    now = datetime.utcnow().isoformat()

    with get_db() as conn:
        conn.execute("""
            INSERT INTO jobs (id, job_type, file_id, status, priority, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (job_id, job_type.value, file_id, JobStatus.QUEUED.value, priority, now))

    return get_job(job_id)


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Get a job by ID."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if row:
            return dict(row)
    return None


def get_next_job() -> Optional[Dict[str, Any]]:
    """Get the next queued job (highest priority, oldest first)."""
    with get_db() as conn:
        row = conn.execute("""
            SELECT * FROM jobs
            WHERE status = ?
            ORDER BY priority DESC, created_at ASC
            LIMIT 1
        """, (JobStatus.QUEUED.value,)).fetchone()
        if row:
            return dict(row)
    return None


def list_jobs(
    status: Optional[JobStatus] = None,
    job_type: Optional[JobType] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """List jobs with optional filters."""
    query = "SELECT * FROM jobs WHERE 1=1"
    params = []

    if status:
        query += " AND status = ?"
        params.append(status.value)

    if job_type:
        query += " AND job_type = ?"
        params.append(job_type.value)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def update_job_status(
    job_id: str,
    status: JobStatus,
    error_message: Optional[str] = None,
    result: Optional[Dict] = None
) -> Optional[Dict[str, Any]]:
    """Update job status."""
    updates = {"status": status.value}
    now = datetime.utcnow().isoformat()

    if status == JobStatus.RUNNING:
        updates["started_at"] = now
        with get_db() as conn:
            conn.execute("UPDATE jobs SET attempts = attempts + 1 WHERE id = ?", (job_id,))

    if status in (JobStatus.COMPLETED, JobStatus.FAILED):
        updates["completed_at"] = now

    if error_message:
        updates["error_message"] = error_message

    if result:
        updates["result"] = json.dumps(result)

    set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
    values = list(updates.values()) + [job_id]

    with get_db() as conn:
        conn.execute(f"UPDATE jobs SET {set_clause} WHERE id = ?", values)

    return get_job(job_id)


def retry_failed_jobs(max_attempts: int = 3) -> int:
    """Re-queue failed jobs that haven't exceeded max attempts."""
    with get_db() as conn:
        result = conn.execute("""
            UPDATE jobs
            SET status = ?
            WHERE status = ? AND attempts < ?
        """, (JobStatus.QUEUED.value, JobStatus.FAILED.value, max_attempts))
        return result.rowcount


def cancel_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Cancel a queued or running job."""
    job = get_job(job_id)
    if not job:
        return None

    # Only cancel jobs that are queued or running
    if job["status"] not in (JobStatus.QUEUED.value, JobStatus.RUNNING.value):
        return job  # Already completed/failed/cancelled

    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute("""
            UPDATE jobs
            SET status = ?, completed_at = ?, error_message = ?
            WHERE id = ?
        """, (JobStatus.CANCELLED.value, now, "Cancelled by user", job_id))

    return get_job(job_id)


def cancel_all_jobs() -> int:
    """Cancel all queued and running jobs. Returns count cancelled."""
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        result = conn.execute("""
            UPDATE jobs
            SET status = ?, completed_at = ?, error_message = ?
            WHERE status IN (?, ?)
        """, (JobStatus.CANCELLED.value, now, "Cancelled by user",
              JobStatus.QUEUED.value, JobStatus.RUNNING.value))
        return result.rowcount
