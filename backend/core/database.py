"""
SQLite database for file and job tracking.

This module re-exports all functions from the db package for backwards compatibility.
New code should import directly from backend.core.db instead.

Example:
    # Old (still works):
    from backend.core.database import get_file, FileStatus

    # New (preferred):
    from backend.core.db import get_file, FileStatus
"""

# Re-export everything from the db package
from backend.core.db import *

# Import init_db to auto-initialize on module load
from backend.core.db import init_db

# Initialize on import (preserves original behavior)
init_db()
