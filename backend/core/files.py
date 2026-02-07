"""
File lifecycle management utilities.
Handles file upload, storage, movement between stages, and cleanup.
"""
import os
import shutil
import uuid
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List
import mimetypes

from .database import (
    create_file, update_file, update_file_status,
    create_job, FileStatus, JobType, list_files
)
from .naming import normalize_site_id, generate_standard_filename, extract_site_from_filename

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


# normalize_site_id and generate_standard_filename moved to naming.py


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


def compute_file_hash(content: bytes) -> str:
    """Compute SHA-256 hash of file content."""
    return hashlib.sha256(content).hexdigest()


def check_for_duplicate(
    filename: str,
    site_id: str,
    content_hash: str
) -> Optional[Dict[str, Any]]:
    """
    Check if a duplicate file already exists.

    A duplicate is defined as:
    - Same standardized filename AND same site_id, OR
    - Same content hash (regardless of filename)

    Returns the existing file record if duplicate found, None otherwise.
    """
    # Get all completed files for this site
    existing_files = list_files(site_id=site_id, status=FileStatus.COMPLETED)

    # Generate what the standardized filename would be
    standard_filename = generate_standard_filename(site_id, filename)

    for file_record in existing_files:
        # Check for same standardized filename
        if file_record.get('filename') == standard_filename:
            return file_record

        # Check for same content hash (if stored)
        if file_record.get('content_hash') == content_hash:
            return file_record

    return None


def save_uploaded_file(
    file_content: bytes,
    filename: str,
    site_id: Optional[str] = None,
    content_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Save an uploaded file to the inbox.
    Automatically renames to standard format: {SITE}_{YYYY-MM-DD}.{ext}

    Returns the file record from the database.

    Raises:
        ValueError: If file type not allowed or site cannot be determined
    """
    # Validate file type
    is_valid, error = validate_file(filename, content_type)
    if not is_valid:
        raise ValueError(error)

    # Validate site can be determined
    # If no site_id provided, check if we can extract from filename
    if not site_id:
        extracted_site = extract_site_from_filename(filename)
        if not extracted_site:
            raise ValueError(
                f"Cannot determine site from filename '{filename}'. "
                "Please select a site or use the naming format: 'MM.DD.YY - Site Name.xlsx' "
                "(e.g., '01.15.25 - PSEG NHQ.xlsx')"
            )

    # Normalize site_id (infer from filename if not provided)
    normalized_site = normalize_site_id(site_id, filename)

    # Check for duplicates before creating file
    content_hash = compute_file_hash(file_content)
    existing = check_for_duplicate(filename, normalized_site, content_hash)
    if existing:
        existing_name = existing.get('filename', 'unknown')
        raise ValueError(
            f"Duplicate file detected. A file with the same content or name "
            f"already exists for site '{normalized_site}': {existing_name}"
        )

    # Generate ID and paths
    file_id = generate_file_id()
    file_type = get_file_type(filename)
    file_dir = INBOX_DIR / file_id
    file_dir.mkdir(parents=True, exist_ok=True)

    # Generate standardized filename
    standard_filename = generate_standard_filename(normalized_site, filename)

    # Save the file with standardized name
    file_path = file_dir / standard_filename
    with open(file_path, 'wb') as f:
        f.write(file_content)

    # Save metadata (keep both original and standard filenames)
    metadata = {
        "id": file_id,
        "filename": standard_filename,
        "original_filename": filename,
        "file_type": file_type,
        "site_id": normalized_site,
        "content_type": content_type,
        "size": len(file_content),
        "uploaded_at": datetime.utcnow().isoformat()
    }
    metadata_path = file_dir / "metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    # Create database record with standardized filename and content hash
    file_record = create_file(
        file_id=file_id,
        filename=standard_filename,
        original_path=str(file_path),
        file_type=file_type,
        file_size=len(file_content),
        site_id=normalized_site,
        content_hash=content_hash
    )

    # Queue a processing job
    job_id = str(uuid.uuid4())
    create_job(job_id, JobType.PARSE, file_id, priority=1)

    return file_record


def move_to_processed(
    file_id: str,
    site_id: str,
    parsed_data: Dict[str, Any],
    site_name: Optional[str] = None,
    inventory_date: Optional[str] = None
) -> str:
    """
    Move a file from inbox to processed folder.
    Renames and organizes by site name and inventory date.

    Args:
        file_id: Unique file identifier
        site_id: Slugified site ID for database
        parsed_data: Parsed file contents
        site_name: Human-readable site name (e.g., "PSEG - NHQ") for folder/filename
        inventory_date: ISO date string (YYYY-MM-DD) from Excel content

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

    # Use site_name for folder organization, fall back to site_id
    folder_name = site_name if site_name else site_id

    # Use inventory_date for date organization, fall back to current date
    if inventory_date:
        date_month = inventory_date[:7]  # "YYYY-MM"
    else:
        date_month = datetime.utcnow().strftime("%Y-%m")
        inventory_date = datetime.utcnow().strftime("%Y-%m-%d")

    # Create destination directory: data/processed/{SITE_NAME}/{YYYY-MM}/
    dest_dir = PROCESSED_DIR / folder_name / date_month
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Generate standardized filename: {SITE_NAME}_{YYYY-MM-DD}.xlsx
    ext = original_file.suffix.lower()
    base_filename = f"{folder_name}_{inventory_date}{ext}"

    # Handle duplicates by appending counter
    dest_path = dest_dir / base_filename
    counter = 2
    while dest_path.exists():
        base_filename = f"{folder_name}_{inventory_date}_{counter}{ext}"
        dest_path = dest_dir / base_filename
        counter += 1

    # Move and rename file
    shutil.move(str(original_file), str(dest_path))

    # Save parsed data alongside (use file_id prefix for uniqueness)
    parsed_path = dest_dir / f"{file_id}_parsed.json"
    with open(parsed_path, 'w') as f:
        json.dump(parsed_data, f, indent=2)

    # Clean up inbox folder
    shutil.rmtree(inbox_path)

    # Update database with new filename, path, and inventory_date
    update_file(
        file_id,
        filename=base_filename,
        current_path=str(dest_path),
        parsed_data=json.dumps(parsed_data),
        inventory_date=inventory_date
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


def delete_file(file_id: str) -> Dict[str, Any]:
    """
    Completely delete a file and all associated data.
    Removes: physical files, database records, embeddings.
    """
    from .database import get_file, delete_file_record

    # Get file info first
    file_record = get_file(file_id)
    if not file_record:
        raise FileNotFoundError(f"File {file_id} not found in database")

    deleted_paths = []
    errors = []

    # Delete from inbox if exists
    inbox_path = INBOX_DIR / file_id
    if inbox_path.exists():
        try:
            shutil.rmtree(inbox_path)
            deleted_paths.append(str(inbox_path))
        except Exception as e:
            errors.append(f"Failed to delete inbox: {e}")

    # Delete from processed if exists (check all sites)
    for site_dir in PROCESSED_DIR.iterdir():
        if site_dir.is_dir():
            for date_dir in site_dir.iterdir():
                if date_dir.is_dir():
                    # Check if this directory contains our file
                    for f in date_dir.iterdir():
                        if file_id in f.name or (file_record.get('filename') and file_record['filename'] in f.name):
                            try:
                                if f.is_file():
                                    f.unlink()
                                else:
                                    shutil.rmtree(f)
                                deleted_paths.append(str(f))
                            except Exception as e:
                                errors.append(f"Failed to delete {f}: {e}")

    # Delete from failed if exists
    failed_path = FAILED_DIR / file_id
    if failed_path.exists():
        try:
            shutil.rmtree(failed_path)
            deleted_paths.append(str(failed_path))
        except Exception as e:
            errors.append(f"Failed to delete failed dir: {e}")

    # Delete database records
    db_deleted = delete_file_record(file_id)

    return {
        "success": db_deleted,
        "file_id": file_id,
        "deleted_paths": deleted_paths,
        "errors": errors if errors else None
    }


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
