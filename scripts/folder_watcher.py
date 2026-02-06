#!/usr/bin/env python3
"""
Folder Watcher for Spectre
Monitors a directory for new xlsx/csv/pdf files and uploads them to the API.
"""
import os
import sys
import time
import logging
import requests
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configuration
WATCH_DIR = os.environ.get("SPECTRE_WATCH_DIR", os.path.expanduser("~/spectre-inbox"))
API_URL = os.environ.get("SPECTRE_API_URL", "http://localhost:8000")
PROCESSED_DIR = os.path.join(WATCH_DIR, "processed")
FAILED_DIR = os.path.join(WATCH_DIR, "failed")
ALLOWED_EXTENSIONS = {'.xlsx', '.csv', '.pdf'}

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.expanduser("~/.local/share/spectre/watcher.log"))
    ]
)
logger = logging.getLogger(__name__)


def ensure_dirs():
    """Create necessary directories."""
    for d in [WATCH_DIR, PROCESSED_DIR, FAILED_DIR]:
        Path(d).mkdir(parents=True, exist_ok=True)
    # Also ensure log dir
    Path(os.path.expanduser("~/.local/share/spectre")).mkdir(parents=True, exist_ok=True)


def upload_file(filepath: str) -> bool:
    """Upload a file to the Spectre API."""
    filename = os.path.basename(filepath)
    logger.info(f"Uploading: {filename}")

    try:
        with open(filepath, 'rb') as f:
            files = {'file': (filename, f)}
            response = requests.post(
                f"{API_URL}/api/files/upload",
                files=files,
                timeout=60
            )

        if response.status_code == 200:
            result = response.json()
            logger.info(f"Uploaded successfully: {filename} -> {result.get('file_id', 'unknown')}")
            return True
        else:
            logger.error(f"Upload failed ({response.status_code}): {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error - is the backend running at {API_URL}?")
        return False
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return False


def move_file(filepath: str, dest_dir: str):
    """Move file to destination directory."""
    filename = os.path.basename(filepath)
    dest = os.path.join(dest_dir, filename)

    # Handle duplicate names
    if os.path.exists(dest):
        base, ext = os.path.splitext(filename)
        timestamp = int(time.time())
        dest = os.path.join(dest_dir, f"{base}_{timestamp}{ext}")

    os.rename(filepath, dest)
    logger.info(f"Moved to: {dest}")


def process_file(filepath: str):
    """Process a single file: upload and move."""
    ext = Path(filepath).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        logger.debug(f"Ignoring non-data file: {filepath}")
        return

    # Wait a moment to ensure file is fully written
    time.sleep(1)

    # Check file still exists (might have been moved)
    if not os.path.exists(filepath):
        return

    success = upload_file(filepath)

    if success:
        move_file(filepath, PROCESSED_DIR)
    else:
        move_file(filepath, FAILED_DIR)


class FileHandler(FileSystemEventHandler):
    """Handle file system events."""

    def on_created(self, event):
        if event.is_directory:
            return
        # Skip files in processed/failed subdirs
        if '/processed/' in event.src_path or '/failed/' in event.src_path:
            return
        process_file(event.src_path)

    def on_moved(self, event):
        if event.is_directory:
            return
        # Handle files moved into the watch directory
        if '/processed/' in event.dest_path or '/failed/' in event.dest_path:
            return
        process_file(event.dest_path)


def process_existing():
    """Process any files already in the watch directory."""
    logger.info(f"Checking for existing files in {WATCH_DIR}")
    for filename in os.listdir(WATCH_DIR):
        filepath = os.path.join(WATCH_DIR, filename)
        if os.path.isfile(filepath):
            ext = Path(filepath).suffix.lower()
            if ext in ALLOWED_EXTENSIONS:
                logger.info(f"Found existing file: {filename}")
                process_file(filepath)


def main():
    ensure_dirs()
    logger.info(f"Spectre Folder Watcher starting...")
    logger.info(f"  Watch directory: {WATCH_DIR}")
    logger.info(f"  API URL: {API_URL}")
    logger.info(f"  Allowed extensions: {ALLOWED_EXTENSIONS}")

    # Process any existing files first
    process_existing()

    # Start watching
    event_handler = FileHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCH_DIR, recursive=False)
    observer.start()

    logger.info("Watching for new files... (Ctrl+C to stop)")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping watcher...")
        observer.stop()

    observer.join()
    logger.info("Watcher stopped.")


if __name__ == "__main__":
    main()
