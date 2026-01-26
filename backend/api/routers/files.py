"""
File management API router.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional
from urllib.parse import quote
import uuid
import re

from backend.core.database import (
    FileStatus, JobType,
    get_file, list_files, create_job, update_file
)


class FileUpdateRequest(BaseModel):
    """Request body for updating file metadata."""
    inventory_date: Optional[str] = None
    site_id: Optional[str] = None
    filename: Optional[str] = None
from backend.core.files import (
    save_uploaded_file, retry_failed_file, get_file_content, delete_file
)

router = APIRouter(prefix="/api/files", tags=["Files"])


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe use in Content-Disposition header."""
    safe = re.sub(r'[^\w\s\-\.]', '_', filename)
    return quote(safe, safe='')


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    site_id: Optional[str] = Form(None)
):
    """Upload a new file for processing."""
    try:
        content = await file.read()
        file_record = save_uploaded_file(
            file_content=content,
            filename=file.filename,
            site_id=site_id,
            content_type=file.content_type
        )
        return {"success": True, "file": file_record}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("")
def get_files(
    status: Optional[str] = Query(None),
    site_id: Optional[str] = Query(None),
    limit: int = Query(100, le=500)
):
    """List files with optional filters."""
    file_status = FileStatus(status) if status else None
    files = list_files(status=file_status, site_id=site_id, limit=limit)
    return {"files": files, "count": len(files)}


@router.get("/{file_id}")
def get_file_detail(file_id: str):
    """Get file details by ID."""
    file_record = get_file(file_id)
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")
    return file_record


@router.patch("/{file_id}")
def update_file_metadata(file_id: str, request: FileUpdateRequest):
    """Update file metadata (inventory_date, site_id, filename)."""
    file_record = get_file(file_id)
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    # Build updates dict from non-None fields
    updates = {}
    if request.inventory_date is not None:
        updates["inventory_date"] = request.inventory_date
    if request.site_id is not None:
        updates["site_id"] = request.site_id
    if request.filename is not None:
        updates["filename"] = request.filename

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updated = update_file(file_id, updates)
    return updated


@router.get("/{file_id}/download")
def download_file(file_id: str):
    """Download a file."""
    try:
        content, filename = get_file_content(file_id)
        safe_filename = sanitize_filename(filename)
        return Response(
            content=content,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}"
            }
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")


@router.post("/{file_id}/retry")
def retry_file(file_id: str):
    """Retry processing a failed file."""
    try:
        file_record = retry_failed_file(file_id)
        return {"success": True, "file": file_record}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")


@router.delete("/{file_id}")
def delete_file_endpoint(file_id: str):
    """Delete a file and all associated data (embeddings, jobs, physical files)."""
    try:
        result = delete_file(file_id)
        return result
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{file_id}/reembed")
def reembed_file(file_id: str):
    """Queue a new embedding job for an existing file."""
    file_record = get_file(file_id)
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    if file_record.get("status") != "completed":
        raise HTTPException(status_code=400, detail="File must be in completed status to re-embed")

    job_id = str(uuid.uuid4())
    create_job(job_id, JobType.EMBED, file_id, priority=1)

    return {"success": True, "job_id": job_id, "message": "Embedding job queued"}
