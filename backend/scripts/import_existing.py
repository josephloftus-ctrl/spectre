#!/usr/bin/env python3
"""
Import existing inventory files into the processing pipeline.
Registers files in database and queues them for processing.
"""

import sys
import uuid
import shutil
import json
from pathlib import Path
from datetime import datetime

# Add parent to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.core.database import get_db, FileStatus, JobStatus, JobType

# Paths
SORTED_DIR = Path(__file__).resolve().parents[2] / "sorted" / "by_site"
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
INBOX_DIR = DATA_DIR / "inbox"


def import_file(file_path: Path, site_id: str) -> str:
    """Import a single file into the system."""
    file_id = str(uuid.uuid4())

    # Create inbox directory for this file
    inbox_path = INBOX_DIR / file_id
    inbox_path.mkdir(parents=True, exist_ok=True)

    # Copy file to inbox
    dest_path = inbox_path / file_path.name
    shutil.copy2(file_path, dest_path)

    # Create metadata
    metadata = {
        "filename": file_path.name,
        "original_path": str(file_path),
        "file_type": file_path.suffix.lower().lstrip('.'),
        "size": file_path.stat().st_size,
        "site_id": site_id,
        "imported_at": datetime.now().isoformat()
    }

    with open(inbox_path / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    # Register in database
    now = datetime.now().isoformat()

    with get_db() as conn:
        cursor = conn.cursor()

        # Insert file record
        cursor.execute("""
            INSERT INTO files (id, filename, original_path, current_path, file_type, file_size, site_id, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            file_id,
            file_path.name,
            str(file_path),
            str(dest_path),
            metadata["file_type"],
            metadata["size"],
            site_id,
            FileStatus.PENDING.value,
            now,
            now
        ))

        # Create processing job
        job_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO jobs (id, job_type, file_id, status, priority, attempts, max_attempts, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job_id,
            JobType.PARSE.value,
            file_id,
            JobStatus.QUEUED.value,
            1,
            0,
            3,
            now
        ))

    return file_id


def import_site(site_dir: Path) -> int:
    """Import all files from a site directory."""
    site_id = site_dir.name
    count = 0

    # Find all xlsx files recursively
    for xlsx_file in site_dir.rglob("*.xlsx"):
        try:
            file_id = import_file(xlsx_file, site_id)
            print(f"  Imported: {xlsx_file.name} -> {file_id}")
            count += 1
        except Exception as e:
            print(f"  FAILED: {xlsx_file.name} - {e}")

    return count


def main():
    """Main import function."""
    print("=" * 60)
    print("Importing existing inventory files")
    print("=" * 60)

    if not SORTED_DIR.exists():
        print(f"ERROR: Sorted directory not found: {SORTED_DIR}")
        return

    # Ensure inbox exists
    INBOX_DIR.mkdir(parents=True, exist_ok=True)

    total = 0

    # Process each site
    for site_dir in SORTED_DIR.iterdir():
        if site_dir.is_dir():
            print(f"\nSite: {site_dir.name}")
            count = import_site(site_dir)
            total += count
            print(f"  Total files imported: {count}")

    print("\n" + "=" * 60)
    print(f"COMPLETE: {total} files imported and queued for processing")
    print("The background worker will process them automatically.")
    print("=" * 60)


if __name__ == "__main__":
    main()
