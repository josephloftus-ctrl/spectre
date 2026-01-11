"""
File lifecycle management utilities.
Handles file upload, storage, movement between stages, and cleanup.
"""
import os
import shutil
import uuid
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
import mimetypes

from .database import (
    create_file, update_file, update_file_status,
    create_job, FileStatus, JobType
)

# Base data directory
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
INBOX_DIR = DATA_DIR / "inbox"
PROCESSED_DIR = DATA_DIR / "processed"
FAILED_DIR = DATA_DIR / "failed"
EXPORTS_DIR = DATA_DIR / "exports"

# Ensure directories exist
for d in [INBOX_DIR, PROCESSED_DIR, FAILED_DIR, EXPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Allowed file types
ALLOWED_EXTENSIONS = {'.xlsx', '.xls', '.csv', '.pdf'}
ALLOWED_MIMETYPES = {
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-excel',
    'text/csv',
    'application/pdf'
}


def generate_file_id() -> str:
    """Generate a unique file ID."""
    return str(uuid.uuid4())


def get_file_type(filename: str) -> Optional[str]:
    """Get file type from filename."""
    ext = Path(filename).suffix.lower()
    if ext in ALLOWED_EXTENSIONS:
        return ext[1:]  # Remove the dot
    return None


def validate_file(filename: str, content_type: Optional[str] = None) -> Tuple[bool, str]:
    """
    Validate if file is allowed.
    Returns (is_valid, error_message).
    """
    ext = Path(filename).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        return False, f"File type '{ext}' not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"

    if content_type and content_type not in ALLOWED_MIMETYPES:
        # Be lenient - some systems report wrong MIME types
        pass

    return True, ""


def save_uploaded_file(
    file_content: bytes,
    filename: str,
    site_id: Optional[str] = None,
    content_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Save an uploaded file to the inbox.

    Returns the file record from the database.
    """
    # Validate
    is_valid, error = validate_file(filename, content_type)
    if not is_valid:
        raise ValueError(error)

    # Generate ID and paths
    file_id = generate_file_id()
    file_type = get_file_type(filename)
    file_dir = INBOX_DIR / file_id
    file_dir.mkdir(parents=True, exist_ok=True)

    # Save the file
    file_path = file_dir / filename
    with open(file_path, 'wb') as f:
        f.write(file_content)

    # Save metadata
    metadata = {
        "id": file_id,
        "filename": filename,
        "file_type": file_type,
        "site_id": site_id,
        "content_type": content_type,
        "size": len(file_content),
        "uploaded_at": datetime.utcnow().isoformat()
    }
    metadata_path = file_dir / "metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    # Create database record
    file_record = create_file(
        file_id=file_id,
        filename=filename,
        original_path=str(file_path),
        file_type=file_type,
        file_size=len(file_content),
        site_id=site_id
    )

    # Queue a processing job
    job_id = str(uuid.uuid4())
    create_job(job_id, JobType.PARSE, file_id, priority=1)

    return file_record


def move_to_processed(file_id: str, site_id: str, parsed_data: Dict[str, Any]) -> str:
    """
    Move a file from inbox to processed folder.
    Organizes by site and date.

    Returns the new path.
    """
    inbox_path = INBOX_DIR / file_id

    if not inbox_path.exists():
        raise FileNotFoundError(f"File {file_id} not found in inbox")

    # Find the original file
    files = list(inbox_path.glob("*"))
    original_file = None
    for f in files:
        if f.name != "metadata.json":
            original_file = f
            break

    if not original_file:
        raise FileNotFoundError(f"No file found in {inbox_path}")

    # Create destination path
    date_str = datetime.utcnow().strftime("%Y-%m")
    dest_dir = PROCESSED_DIR / site_id / date_str
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Move file
    dest_path = dest_dir / f"{file_id}_{original_file.name}"
    shutil.move(str(original_file), str(dest_path))

    # Save parsed data alongside
    parsed_path = dest_dir / f"{file_id}_parsed.json"
    with open(parsed_path, 'w') as f:
        json.dump(parsed_data, f, indent=2)

    # Clean up inbox folder
    shutil.rmtree(inbox_path)

    # Update database
    update_file(
        file_id,
        current_path=str(dest_path),
        parsed_data=json.dumps(parsed_data)
    )
    update_file_status(file_id, FileStatus.COMPLETED, parsed_data=parsed_data)

    return str(dest_path)


def move_to_failed(file_id: str, error_message: str) -> str:
    """
    Move a file from inbox to failed folder.

    Returns the new path.
    """
    inbox_path = INBOX_DIR / file_id

    if not inbox_path.exists():
        # File might have been moved already
        update_file_status(file_id, FileStatus.FAILED, error_message=error_message)
        return ""

    # Create destination
    dest_dir = FAILED_DIR / file_id
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Move entire folder
    for item in inbox_path.iterdir():
        shutil.move(str(item), str(dest_dir / item.name))

    # Save error log
    error_path = dest_dir / "error.log"
    with open(error_path, 'w') as f:
        f.write(f"Failed at: {datetime.utcnow().isoformat()}\n")
        f.write(f"Error: {error_message}\n")

    # Clean up inbox folder
    inbox_path.rmdir()

    # Update database
    update_file_status(file_id, FileStatus.FAILED, error_message=error_message)

    return str(dest_dir)


def retry_failed_file(file_id: str) -> Dict[str, Any]:
    """
    Move a failed file back to inbox for reprocessing.
    """
    failed_path = FAILED_DIR / file_id

    if not failed_path.exists():
        raise FileNotFoundError(f"Failed file {file_id} not found")

    # Create inbox destination
    inbox_path = INBOX_DIR / file_id
    inbox_path.mkdir(parents=True, exist_ok=True)

    # Move files back (except error.log)
    for item in failed_path.iterdir():
        if item.name != "error.log":
            shutil.move(str(item), str(inbox_path / item.name))

    # Clean up failed folder
    shutil.rmtree(failed_path)

    # Update database and create new job
    update_file_status(file_id, FileStatus.PENDING)
    job_id = str(uuid.uuid4())
    create_job(job_id, JobType.PARSE, file_id, priority=2)  # Higher priority for retries

    from .database import get_file
    return get_file(file_id)


def get_inbox_files() -> list:
    """Get list of files in inbox."""
    files = []
    for file_dir in INBOX_DIR.iterdir():
        if file_dir.is_dir():
            metadata_path = file_dir / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path) as f:
                    files.append(json.load(f))
    return files


def get_processed_files(site_id: Optional[str] = None) -> list:
    """Get list of processed files, optionally filtered by site."""
    files = []
    search_dir = PROCESSED_DIR / site_id if site_id else PROCESSED_DIR

    if not search_dir.exists():
        return files

    for path in search_dir.rglob("*_parsed.json"):
        with open(path) as f:
            data = json.load(f)
            data["path"] = str(path.parent / path.name.replace("_parsed.json", ""))
            files.append(data)

    return files


def cleanup_old_files(days: int = 30) -> int:
    """
    Delete files older than specified days from failed folder.
    Returns count of deleted files.
    """
    from datetime import timedelta

    cutoff = datetime.utcnow() - timedelta(days=days)
    deleted = 0

    for file_dir in FAILED_DIR.iterdir():
        if file_dir.is_dir():
            metadata_path = file_dir / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path) as f:
                    metadata = json.load(f)
                    uploaded_at = datetime.fromisoformat(metadata.get("uploaded_at", ""))
                    if uploaded_at < cutoff:
                        shutil.rmtree(file_dir)
                        deleted += 1

    return deleted


def get_file_content(file_id: str) -> Tuple[bytes, str]:
    """
    Get file content and filename.
    Searches inbox, processed, and failed folders.
    """
    # Check inbox
    inbox_path = INBOX_DIR / file_id
    if inbox_path.exists():
        for f in inbox_path.iterdir():
            if f.name != "metadata.json":
                return f.read_bytes(), f.name

    # Check processed (need to search by file_id prefix)
    for path in PROCESSED_DIR.rglob(f"{file_id}_*"):
        if not path.name.endswith("_parsed.json"):
            return path.read_bytes(), path.name.replace(f"{file_id}_", "")

    # Check failed
    failed_path = FAILED_DIR / file_id
    if failed_path.exists():
        for f in failed_path.iterdir():
            if f.name not in ("metadata.json", "error.log"):
                return f.read_bytes(), f.name

    raise FileNotFoundError(f"File {file_id} not found")
