"""
Job management API router.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from backend.core.database import (
    JobStatus, JobType,
    get_job, list_jobs, retry_failed_jobs,
    cancel_job, cancel_all_jobs, get_stats
)
from backend.core.files import get_inbox_files, get_processed_files, cleanup_old_files
from backend.core.worker import get_scheduler_status

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


@router.get("")
def get_jobs(
    status: Optional[str] = Query(None),
    job_type: Optional[str] = Query(None),
    limit: int = Query(100, le=500)
):
    """List jobs with optional filters."""
    job_status = JobStatus(status) if status else None
    jtype = JobType(job_type) if job_type else None
    jobs = list_jobs(status=job_status, job_type=jtype, limit=limit)
    return {"jobs": jobs, "count": len(jobs)}


@router.get("/{job_id}")
def get_job_detail(job_id: str):
    """Get job details by ID."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/retry-failed")
def retry_all_failed_jobs():
    """Re-queue all failed jobs that haven't exceeded max attempts."""
    count = retry_failed_jobs()
    return {"success": True, "requeued_count": count}


@router.post("/{job_id}/cancel")
def cancel_job_endpoint(job_id: str):
    """Cancel a queued or running job."""
    result = cancel_job(job_id)
    if not result:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"success": True, "job": result}


@router.post("/cancel-all")
def cancel_all_jobs_endpoint():
    """Cancel all queued and running jobs."""
    count = cancel_all_jobs()
    return {"success": True, "cancelled_count": count}


# Stats endpoints - related to jobs/files system

stats_router = APIRouter(prefix="/api/stats", tags=["Stats"])


@stats_router.get("")
def get_system_stats():
    """Get system statistics."""
    stats = get_stats()
    return stats


@stats_router.get("/inbox")
def get_inbox_stats():
    """Get inbox file list."""
    files = get_inbox_files()
    return {"files": files, "count": len(files)}


@stats_router.get("/processed")
def get_processed_stats(site_id: Optional[str] = Query(None)):
    """Get processed files list."""
    files = get_processed_files(site_id)
    return {"files": files, "count": len(files)}


# Maintenance endpoints

maintenance_router = APIRouter(prefix="/api/maintenance", tags=["Maintenance"])


@maintenance_router.post("/cleanup")
def run_cleanup(days: int = Query(30, ge=1, le=365)):
    """Delete old failed files."""
    deleted = cleanup_old_files(days)
    return {"success": True, "deleted_count": deleted}


# Worker status endpoint

worker_router = APIRouter(prefix="/api/worker", tags=["Worker"])


@worker_router.get("/status")
def worker_status():
    """Get background worker status."""
    return get_scheduler_status()
