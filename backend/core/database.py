"""
SQLite database for file and job tracking.
"""
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from enum import Enum
import json

# Database location
DB_PATH = Path(__file__).resolve().parents[2] / "data" / "spectre.db"


class FileStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    PARSE = "parse"
    EMBED = "embed"
    ANALYZE = "analyze"
    SCORE = "score"


class ScoreStatus(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    HEALTHY = "healthy"
    CLEAN = "clean"


# Whitelist of allowed columns for update operations (SQL injection prevention)
ALLOWED_FILE_COLUMNS = {
    'status', 'error_message', 'parsed_data', 'current_path',
    'embedding_id', 'updated_at', 'processed_at', 'site_id', 'filename', 'collection'
}

ALLOWED_JOB_COLUMNS = {
    'status', 'error_message', 'result', 'started_at', 'completed_at', 'attempts'
}


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize database tables."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with get_db() as conn:
        # Enable WAL mode for better concurrency (allows concurrent reads during writes)
        conn.execute("PRAGMA journal_mode=WAL")
        # Set busy timeout to 5 seconds to handle lock contention
        conn.execute("PRAGMA busy_timeout=5000")

        conn.executescript("""
            -- Files table: tracks uploaded documents
            CREATE TABLE IF NOT EXISTS files (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                original_path TEXT,
                current_path TEXT,
                file_type TEXT,
                file_size INTEGER,
                site_id TEXT,
                collection TEXT DEFAULT 'culinart_bible',
                status TEXT DEFAULT 'pending',
                error_message TEXT,
                parsed_data TEXT,  -- JSON blob of extracted data
                embedding_id TEXT,  -- Reference to ChromaDB collection
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                processed_at TEXT
            );

            -- Jobs table: tracks background processing jobs
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                job_type TEXT NOT NULL,
                file_id TEXT,
                status TEXT DEFAULT 'queued',
                priority INTEGER DEFAULT 0,
                attempts INTEGER DEFAULT 0,
                max_attempts INTEGER DEFAULT 3,
                error_message TEXT,
                result TEXT,  -- JSON blob
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                started_at TEXT,
                completed_at TEXT,
                FOREIGN KEY (file_id) REFERENCES files(id)
            );

            -- Embeddings table: tracks document chunks and their embeddings
            CREATE TABLE IF NOT EXISTS embeddings (
                id TEXT PRIMARY KEY,
                file_id TEXT NOT NULL,
                chunk_index INTEGER,
                chunk_text TEXT,
                metadata TEXT,  -- JSON blob
                collection TEXT DEFAULT 'culinart_bible',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (file_id) REFERENCES files(id)
            );

            -- Analysis results table
            CREATE TABLE IF NOT EXISTS analysis_results (
                id TEXT PRIMARY KEY,
                file_id TEXT,
                site_id TEXT,
                analysis_type TEXT,
                result TEXT,  -- JSON blob
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (file_id) REFERENCES files(id)
            );

            -- Sites table: stores site metadata and custom display names
            CREATE TABLE IF NOT EXISTS sites (
                site_id TEXT PRIMARY KEY,
                display_name TEXT,  -- Custom display name (null = use auto-formatted)
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            -- Unit scores table: tracks health scores per site/file
            CREATE TABLE IF NOT EXISTS unit_scores (
                id TEXT PRIMARY KEY,
                file_id TEXT,
                site_id TEXT NOT NULL,
                score INTEGER DEFAULT 0,
                status TEXT DEFAULT 'clean',  -- critical/warning/healthy/clean
                item_flag_count INTEGER DEFAULT 0,
                room_flag_count INTEGER DEFAULT 0,
                flagged_items TEXT,  -- JSON array
                flagged_rooms TEXT,  -- JSON array
                room_totals TEXT,    -- JSON object
                total_value REAL DEFAULT 0,
                item_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (file_id) REFERENCES files(id)
            );

            -- Score history table: weekly snapshots for trends
            CREATE TABLE IF NOT EXISTS score_history (
                id TEXT PRIMARY KEY,
                site_id TEXT NOT NULL,
                score INTEGER DEFAULT 0,
                status TEXT DEFAULT 'clean',
                item_flag_count INTEGER DEFAULT 0,
                room_flag_count INTEGER DEFAULT 0,
                total_value REAL DEFAULT 0,
                snapshot_date TEXT NOT NULL,  -- Weekly snapshot timestamp
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            -- Ignored items for purchase match (per-site)
            CREATE TABLE IF NOT EXISTS ignored_items (
                id TEXT PRIMARY KEY,
                site_id TEXT NOT NULL,
                sku TEXT NOT NULL,
                reason TEXT,
                notes TEXT,
                created_by TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(site_id, sku)
            );

            -- Shopping cart items for ordering
            CREATE TABLE IF NOT EXISTS cart_items (
                id TEXT PRIMARY KEY,
                site_id TEXT NOT NULL,
                sku TEXT NOT NULL,
                description TEXT,
                quantity REAL DEFAULT 1,
                unit_price REAL,
                uom TEXT,  -- Unit of measure (CS, EA, LB, etc.)
                vendor TEXT,
                notes TEXT,
                source TEXT,  -- 'inventory', 'catalog', 'manual'
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(site_id, sku)
            );

            -- Inventory snapshots for safe state return (auto-clean restore points)
            CREATE TABLE IF NOT EXISTS inventory_snapshots (
                id TEXT PRIMARY KEY,
                site_id TEXT NOT NULL,
                name TEXT,
                source_file_id TEXT,  -- Original file this snapshot is from
                snapshot_data TEXT,   -- JSON of full inventory state
                item_count INTEGER DEFAULT 0,
                total_value REAL DEFAULT 0,
                status TEXT DEFAULT 'active',  -- 'active', 'restored', 'archived'
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_file_id) REFERENCES files(id)
            );

            -- Count sessions for inventory counting
            CREATE TABLE IF NOT EXISTS count_sessions (
                id TEXT PRIMARY KEY,
                site_id TEXT NOT NULL,
                name TEXT,
                status TEXT DEFAULT 'active',  -- 'active', 'completed', 'exported'
                item_count INTEGER DEFAULT 0,
                total_value REAL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT
            );

            -- Count session items
            CREATE TABLE IF NOT EXISTS count_items (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                sku TEXT NOT NULL,
                description TEXT,
                counted_qty REAL,
                expected_qty REAL,
                unit_price REAL,
                uom TEXT,
                location TEXT,  -- Storage location / GL code
                variance REAL,  -- counted - expected
                notes TEXT,
                counted_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES count_sessions(id)
            );

            -- Create indexes
            CREATE INDEX IF NOT EXISTS idx_files_status ON files(status);
            CREATE INDEX IF NOT EXISTS idx_files_site ON files(site_id);
            CREATE INDEX IF NOT EXISTS idx_files_collection ON files(collection);
            CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
            CREATE INDEX IF NOT EXISTS idx_jobs_file ON jobs(file_id);
            CREATE INDEX IF NOT EXISTS idx_embeddings_file ON embeddings(file_id);
            CREATE INDEX IF NOT EXISTS idx_embeddings_collection ON embeddings(collection);
            CREATE INDEX IF NOT EXISTS idx_unit_scores_site ON unit_scores(site_id);
            CREATE INDEX IF NOT EXISTS idx_unit_scores_status ON unit_scores(status);
            CREATE INDEX IF NOT EXISTS idx_score_history_site ON score_history(site_id);
            CREATE INDEX IF NOT EXISTS idx_score_history_date ON score_history(snapshot_date);
            CREATE INDEX IF NOT EXISTS idx_ignored_items_site ON ignored_items(site_id);
            CREATE INDEX IF NOT EXISTS idx_cart_items_site ON cart_items(site_id);
            CREATE INDEX IF NOT EXISTS idx_inventory_snapshots_site ON inventory_snapshots(site_id);
            CREATE INDEX IF NOT EXISTS idx_count_sessions_site ON count_sessions(site_id);
            CREATE INDEX IF NOT EXISTS idx_count_items_session ON count_items(session_id);
        """)

    # Run migrations for existing databases
    migrate_db()


def migrate_db():
    """Run database migrations for schema changes."""
    with get_db() as conn:
        # Check if collection column exists in files table
        cursor = conn.execute("PRAGMA table_info(files)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'collection' not in columns:
            conn.execute("ALTER TABLE files ADD COLUMN collection TEXT DEFAULT 'culinart_bible'")

        # Check if collection column exists in embeddings table
        cursor = conn.execute("PRAGMA table_info(embeddings)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'collection' not in columns:
            conn.execute("ALTER TABLE embeddings ADD COLUMN collection TEXT DEFAULT 'culinart_bible'")


# ============== File Operations ==============

def create_file(
    file_id: str,
    filename: str,
    original_path: str,
    file_type: str,
    file_size: int,
    site_id: Optional[str] = None,
    collection: str = "culinart_bible"
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


# ============== Job Operations ==============

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


# ============== Embedding Operations ==============

def create_embedding(
    embedding_id: str,
    file_id: str,
    chunk_index: int,
    chunk_text: str,
    metadata: Optional[Dict] = None,
    collection: str = "culinart_bible"
) -> Dict[str, Any]:
    """Create or update an embedding record."""
    now = datetime.utcnow().isoformat()

    with get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO embeddings (id, file_id, chunk_index, chunk_text, metadata, collection, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (embedding_id, file_id, chunk_index, chunk_text, json.dumps(metadata or {}), collection, now))

    return {"id": embedding_id, "file_id": file_id, "chunk_index": chunk_index, "collection": collection}


def get_file_embeddings(file_id: str) -> List[Dict[str, Any]]:
    """Get all embeddings for a file."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM embeddings WHERE file_id = ? ORDER BY chunk_index",
            (file_id,)
        ).fetchall()
        return [dict(row) for row in rows]


# ============== Stats ==============

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


# ============== Site Operations ==============

def auto_format_site_name(site_id: str) -> str:
    """
    Auto-format a site_id into a readable display name.

    Examples:
        'pseg_nhq' -> 'PSEG NHQ'
        'lockheed_bldg_100' -> 'Lockheed Bldg 100'
        'p_and_g_greensboro' -> 'P And G Greensboro'
    """
    if not site_id:
        return ""

    # Replace underscores with spaces
    name = site_id.replace("_", " ")

    # Title case, but preserve all-caps for short words (likely acronyms)
    words = name.split()
    formatted = []
    for word in words:
        # If word is short (<=4 chars) and looks like it could be an acronym, uppercase it
        if len(word) <= 4 and word.isalpha():
            formatted.append(word.upper())
        else:
            formatted.append(word.capitalize())

    return " ".join(formatted)


def get_site(site_id: str) -> Optional[Dict[str, Any]]:
    """Get a site by ID, with auto-formatted name as fallback."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM sites WHERE site_id = ?",
            (site_id,)
        ).fetchone()

        if row:
            result = dict(row)
            # Check if display_name is custom or auto-formatted
            has_custom_name = bool(result.get("display_name"))
            if not has_custom_name:
                result["display_name"] = auto_format_site_name(site_id)
            result["is_custom"] = has_custom_name
            return result

        # Site not in table yet - return auto-formatted name
        return {
            "site_id": site_id,
            "display_name": auto_format_site_name(site_id),
            "is_custom": False,
            "created_at": None,
            "updated_at": None
        }


def get_site_display_name(site_id: str) -> str:
    """Get just the display name for a site."""
    site = get_site(site_id)
    return site.get("display_name", site_id) if site else site_id


def list_sites() -> List[Dict[str, Any]]:
    """List all known sites (from files and explicit entries)."""
    with get_db() as conn:
        # Get all unique site_ids from files
        file_sites = conn.execute(
            "SELECT DISTINCT site_id FROM files WHERE site_id IS NOT NULL"
        ).fetchall()

        # Get all sites from sites table
        explicit_sites = conn.execute("SELECT * FROM sites").fetchall()
        explicit_map = {row["site_id"]: dict(row) for row in explicit_sites}

        # Merge: explicit entries take precedence
        all_site_ids = set(row["site_id"] for row in file_sites)
        all_site_ids.update(explicit_map.keys())

        results = []
        for site_id in sorted(all_site_ids):
            if site_id in explicit_map:
                site = explicit_map[site_id]
                has_custom_name = bool(site.get("display_name"))
                if not has_custom_name:
                    site["display_name"] = auto_format_site_name(site_id)
                site["is_custom"] = has_custom_name
                results.append(site)
            else:
                results.append({
                    "site_id": site_id,
                    "display_name": auto_format_site_name(site_id),
                    "is_custom": False,
                    "created_at": None,
                    "updated_at": None
                })

        return results


def update_site_display_name(site_id: str, display_name: Optional[str]) -> Dict[str, Any]:
    """Update or create a site's display name. Pass None to reset to auto-format."""
    now = datetime.utcnow().isoformat()

    with get_db() as conn:
        # Check if site exists
        existing = conn.execute(
            "SELECT * FROM sites WHERE site_id = ?",
            (site_id,)
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE sites SET display_name = ?, updated_at = ? WHERE site_id = ?",
                (display_name, now, site_id)
            )
        else:
            conn.execute(
                "INSERT INTO sites (site_id, display_name, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (site_id, display_name, now, now)
            )

    return get_site(site_id)


# ============== Unit Score Operations ==============

def save_unit_score(
    score_id: str,
    site_id: str,
    score: int,
    status: str,
    item_flag_count: int,
    room_flag_count: int,
    flagged_items: List[Dict],
    flagged_rooms: List[Dict],
    room_totals: Dict[str, float],
    total_value: float,
    item_count: int,
    file_id: Optional[str] = None
) -> Dict[str, Any]:
    """Save or update a unit score."""
    now = datetime.utcnow().isoformat()

    with get_db() as conn:
        # Delete existing score for this site (we only keep latest)
        conn.execute("DELETE FROM unit_scores WHERE site_id = ?", (site_id,))

        conn.execute("""
            INSERT INTO unit_scores (
                id, file_id, site_id, score, status,
                item_flag_count, room_flag_count,
                flagged_items, flagged_rooms, room_totals,
                total_value, item_count, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            score_id, file_id, site_id, score, status,
            item_flag_count, room_flag_count,
            json.dumps(flagged_items), json.dumps(flagged_rooms), json.dumps(room_totals),
            total_value, item_count, now
        ))

    return get_unit_score(site_id)


def get_unit_score(site_id: str) -> Optional[Dict[str, Any]]:
    """Get the latest score for a site."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM unit_scores WHERE site_id = ?",
            (site_id,)
        ).fetchone()
        if row:
            result = dict(row)
            # Parse JSON fields
            result["flagged_items"] = json.loads(result.get("flagged_items") or "[]")
            result["flagged_rooms"] = json.loads(result.get("flagged_rooms") or "[]")
            result["room_totals"] = json.loads(result.get("room_totals") or "{}")
            return result
    return None


def list_unit_scores(
    status: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """List all unit scores, sorted by score descending (worst first)."""
    query = "SELECT * FROM unit_scores WHERE 1=1"
    params = []

    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY score DESC, site_id ASC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        results = []
        for row in rows:
            result = dict(row)
            result["flagged_items"] = json.loads(result.get("flagged_items") or "[]")
            result["flagged_rooms"] = json.loads(result.get("flagged_rooms") or "[]")
            result["room_totals"] = json.loads(result.get("room_totals") or "{}")
            results.append(result)
        return results


def get_all_site_ids_with_scores() -> List[str]:
    """Get list of all site IDs that have scores."""
    with get_db() as conn:
        rows = conn.execute("SELECT DISTINCT site_id FROM unit_scores").fetchall()
        return [row["site_id"] for row in rows]


# ============== Score History Operations ==============

def save_score_snapshot(
    snapshot_id: str,
    site_id: str,
    score: int,
    status: str,
    item_flag_count: int,
    room_flag_count: int,
    total_value: float,
    snapshot_date: str
) -> Dict[str, Any]:
    """Save a weekly score snapshot."""
    now = datetime.utcnow().isoformat()

    with get_db() as conn:
        conn.execute("""
            INSERT INTO score_history (
                id, site_id, score, status,
                item_flag_count, room_flag_count,
                total_value, snapshot_date, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            snapshot_id, site_id, score, status,
            item_flag_count, room_flag_count,
            total_value, snapshot_date, now
        ))

    return {
        "id": snapshot_id,
        "site_id": site_id,
        "score": score,
        "snapshot_date": snapshot_date
    }


def get_score_history(
    site_id: str,
    limit: int = 12  # ~3 months of weekly data
) -> List[Dict[str, Any]]:
    """Get score history for a site, most recent first."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM score_history
            WHERE site_id = ?
            ORDER BY snapshot_date DESC
            LIMIT ?
        """, (site_id, limit)).fetchall()
        return [dict(row) for row in rows]


def get_latest_snapshot_date() -> Optional[str]:
    """Get the most recent snapshot date across all sites."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT MAX(snapshot_date) as latest FROM score_history"
        ).fetchone()
        return row["latest"] if row else None


def get_score_trend(site_id: str) -> Optional[str]:
    """
    Get trend indicator for a site.

    Returns:
        'up' - Score increased (got worse)
        'down' - Score decreased (improved)
        'stable' - No change
        None - Not enough history
    """
    history = get_score_history(site_id, limit=2)
    if len(history) < 2:
        return None

    current = history[0]["score"]
    previous = history[1]["score"]

    if current > previous:
        return "up"
    elif current < previous:
        return "down"
    else:
        return "stable"


# ============== Ignored Items Operations (Purchase Match) ==============

def add_ignored_item(
    site_id: str,
    sku: str,
    reason: Optional[str] = None,
    notes: Optional[str] = None,
    created_by: Optional[str] = None
) -> Dict[str, Any]:
    """Add an item to the site's ignore list."""
    import uuid
    item_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    with get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO ignored_items (id, site_id, sku, reason, notes, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (item_id, site_id, sku, reason, notes, created_by, now))

    return get_ignored_item(site_id, sku)


def get_ignored_item(site_id: str, sku: str) -> Optional[Dict[str, Any]]:
    """Get a specific ignored item."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM ignored_items WHERE site_id = ? AND sku = ?",
            (site_id, sku)
        ).fetchone()
        if row:
            return dict(row)
    return None


def remove_ignored_item(site_id: str, sku: str) -> bool:
    """Remove an item from the site's ignore list. Returns True if item was found and removed."""
    with get_db() as conn:
        result = conn.execute(
            "DELETE FROM ignored_items WHERE site_id = ? AND sku = ?",
            (site_id, sku)
        )
        return result.rowcount > 0


def list_ignored_items(site_id: str) -> List[Dict[str, Any]]:
    """List all ignored items for a site."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM ignored_items WHERE site_id = ? ORDER BY created_at DESC",
            (site_id,)
        ).fetchall()
        return [dict(row) for row in rows]


def get_ignored_skus(site_id: str) -> set:
    """Get set of ignored SKUs for a site (for quick lookup in matcher)."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT sku FROM ignored_items WHERE site_id = ?",
            (site_id,)
        ).fetchall()
        return {row["sku"] for row in rows}


# ============== Shopping Cart Operations ==============

def add_cart_item(
    site_id: str,
    sku: str,
    description: str,
    quantity: float = 1,
    unit_price: Optional[float] = None,
    uom: Optional[str] = None,
    vendor: Optional[str] = None,
    notes: Optional[str] = None,
    source: str = "manual"
) -> Dict[str, Any]:
    """Add or update an item in the shopping cart."""
    import uuid
    item_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    with get_db() as conn:
        # Use INSERT OR REPLACE to handle duplicates (unique on site_id, sku)
        conn.execute("""
            INSERT OR REPLACE INTO cart_items
            (id, site_id, sku, description, quantity, unit_price, uom, vendor, notes, source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (item_id, site_id, sku, description, quantity, unit_price, uom, vendor, notes, source, now, now))

    return get_cart_item(site_id, sku)


def get_cart_item(site_id: str, sku: str) -> Optional[Dict[str, Any]]:
    """Get a specific cart item."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM cart_items WHERE site_id = ? AND sku = ?",
            (site_id, sku)
        ).fetchone()
        if row:
            return dict(row)
    return None


def update_cart_item_quantity(site_id: str, sku: str, quantity: float) -> Optional[Dict[str, Any]]:
    """Update quantity for a cart item."""
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute(
            "UPDATE cart_items SET quantity = ?, updated_at = ? WHERE site_id = ? AND sku = ?",
            (quantity, now, site_id, sku)
        )
    return get_cart_item(site_id, sku)


def remove_cart_item(site_id: str, sku: str) -> bool:
    """Remove an item from the cart."""
    with get_db() as conn:
        result = conn.execute(
            "DELETE FROM cart_items WHERE site_id = ? AND sku = ?",
            (site_id, sku)
        )
        return result.rowcount > 0


def list_cart_items(site_id: str) -> List[Dict[str, Any]]:
    """List all items in a site's shopping cart."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM cart_items WHERE site_id = ? ORDER BY created_at DESC",
            (site_id,)
        ).fetchall()
        return [dict(row) for row in rows]


def get_cart_summary(site_id: str) -> Dict[str, Any]:
    """Get cart summary with totals."""
    with get_db() as conn:
        row = conn.execute("""
            SELECT
                COUNT(*) as item_count,
                SUM(quantity) as total_quantity,
                SUM(quantity * COALESCE(unit_price, 0)) as total_value
            FROM cart_items WHERE site_id = ?
        """, (site_id,)).fetchone()

        return {
            "site_id": site_id,
            "item_count": row["item_count"] or 0,
            "total_quantity": row["total_quantity"] or 0,
            "total_value": row["total_value"] or 0
        }


def clear_cart(site_id: str) -> int:
    """Clear all items from a site's cart. Returns count of items removed."""
    with get_db() as conn:
        result = conn.execute("DELETE FROM cart_items WHERE site_id = ?", (site_id,))
        return result.rowcount


def bulk_add_cart_items(site_id: str, items: List[Dict[str, Any]], source: str = "bulk") -> int:
    """Add multiple items to cart at once. Returns count added."""
    import uuid
    now = datetime.utcnow().isoformat()
    added = 0

    with get_db() as conn:
        for item in items:
            item_id = str(uuid.uuid4())
            conn.execute("""
                INSERT OR REPLACE INTO cart_items
                (id, site_id, sku, description, quantity, unit_price, uom, vendor, notes, source, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item_id, site_id,
                item.get("sku", ""),
                item.get("description", ""),
                item.get("quantity", 1),
                item.get("unit_price"),
                item.get("uom"),
                item.get("vendor"),
                item.get("notes"),
                source, now, now
            ))
            added += 1

    return added


# ============== Count Session Operations ==============

def create_count_session(
    site_id: str,
    name: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new inventory count session."""
    import uuid
    session_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    if not name:
        name = f"Count {now[:10]}"

    with get_db() as conn:
        conn.execute("""
            INSERT INTO count_sessions (id, site_id, name, status, created_at, updated_at)
            VALUES (?, ?, ?, 'active', ?, ?)
        """, (session_id, site_id, name, now, now))

    return get_count_session(session_id)


def get_count_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get a count session by ID."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM count_sessions WHERE id = ?",
            (session_id,)
        ).fetchone()
        if row:
            return dict(row)
    return None


def list_count_sessions(
    site_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """List count sessions with optional filters."""
    query = "SELECT * FROM count_sessions WHERE 1=1"
    params = []

    if site_id:
        query += " AND site_id = ?"
        params.append(site_id)

    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def update_count_session(
    session_id: str,
    status: Optional[str] = None,
    name: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Update a count session."""
    now = datetime.utcnow().isoformat()

    updates = ["updated_at = ?"]
    params = [now]

    if status:
        updates.append("status = ?")
        params.append(status)
        if status == "completed":
            updates.append("completed_at = ?")
            params.append(now)

    if name:
        updates.append("name = ?")
        params.append(name)

    params.append(session_id)

    with get_db() as conn:
        conn.execute(f"UPDATE count_sessions SET {', '.join(updates)} WHERE id = ?", params)

        # Update item count and total value
        conn.execute("""
            UPDATE count_sessions SET
                item_count = (SELECT COUNT(*) FROM count_items WHERE session_id = ?),
                total_value = (SELECT SUM(counted_qty * COALESCE(unit_price, 0)) FROM count_items WHERE session_id = ?)
            WHERE id = ?
        """, (session_id, session_id, session_id))

    return get_count_session(session_id)


def add_count_item(
    session_id: str,
    sku: str,
    description: str,
    counted_qty: float,
    expected_qty: Optional[float] = None,
    unit_price: Optional[float] = None,
    uom: Optional[str] = None,
    location: Optional[str] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """Add or update a counted item in a session."""
    import uuid
    item_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    variance = None
    if expected_qty is not None:
        variance = counted_qty - expected_qty

    with get_db() as conn:
        # Check if item already exists in session
        existing = conn.execute(
            "SELECT id FROM count_items WHERE session_id = ? AND sku = ?",
            (session_id, sku)
        ).fetchone()

        if existing:
            # Update existing
            conn.execute("""
                UPDATE count_items SET
                    description = ?, counted_qty = ?, expected_qty = ?,
                    unit_price = ?, uom = ?, location = ?,
                    variance = ?, notes = ?, counted_at = ?
                WHERE session_id = ? AND sku = ?
            """, (description, counted_qty, expected_qty, unit_price, uom,
                  location, variance, notes, now, session_id, sku))
        else:
            # Insert new
            conn.execute("""
                INSERT INTO count_items
                (id, session_id, sku, description, counted_qty, expected_qty,
                 unit_price, uom, location, variance, notes, counted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (item_id, session_id, sku, description, counted_qty, expected_qty,
                  unit_price, uom, location, variance, notes, now))

    return get_count_item(session_id, sku)


def get_count_item(session_id: str, sku: str) -> Optional[Dict[str, Any]]:
    """Get a specific count item."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM count_items WHERE session_id = ? AND sku = ?",
            (session_id, sku)
        ).fetchone()
        if row:
            return dict(row)
    return None


def list_count_items(session_id: str) -> List[Dict[str, Any]]:
    """List all items in a count session."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM count_items WHERE session_id = ? ORDER BY location, sku",
            (session_id,)
        ).fetchall()
        return [dict(row) for row in rows]


def delete_count_session(session_id: str) -> bool:
    """Delete a count session and all its items."""
    with get_db() as conn:
        conn.execute("DELETE FROM count_items WHERE session_id = ?", (session_id,))
        result = conn.execute("DELETE FROM count_sessions WHERE id = ?", (session_id,))
        return result.rowcount > 0


# ============== Inventory Snapshot Operations (Safe State Return) ==============

def create_inventory_snapshot(
    site_id: str,
    snapshot_data: List[Dict[str, Any]],
    name: Optional[str] = None,
    source_file_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a snapshot of inventory state for safe restoration.
    Called before auto-clean operations.
    """
    import uuid
    snapshot_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    if not name:
        name = f"Snapshot {now[:10]}"

    # Calculate totals
    item_count = len(snapshot_data)
    total_value = sum(
        (item.get("quantity", 0) * (item.get("unit_price", 0) or 0))
        for item in snapshot_data
    )

    with get_db() as conn:
        conn.execute("""
            INSERT INTO inventory_snapshots
            (id, site_id, name, source_file_id, snapshot_data, item_count, total_value, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?)
        """, (snapshot_id, site_id, name, source_file_id, json.dumps(snapshot_data),
              item_count, total_value, now))

    return get_inventory_snapshot(snapshot_id)


def get_inventory_snapshot(snapshot_id: str) -> Optional[Dict[str, Any]]:
    """Get a snapshot by ID."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM inventory_snapshots WHERE id = ?",
            (snapshot_id,)
        ).fetchone()
        if row:
            result = dict(row)
            result["snapshot_data"] = json.loads(result.get("snapshot_data") or "[]")
            return result
    return None


def list_inventory_snapshots(
    site_id: str,
    status: Optional[str] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """List inventory snapshots for a site."""
    query = "SELECT id, site_id, name, source_file_id, item_count, total_value, status, created_at FROM inventory_snapshots WHERE site_id = ?"
    params = [site_id]

    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def restore_inventory_snapshot(snapshot_id: str) -> Optional[Dict[str, Any]]:
    """
    Mark a snapshot as restored (for tracking).
    The actual restoration would apply the snapshot_data to the inventory.
    """
    now = datetime.utcnow().isoformat()

    with get_db() as conn:
        conn.execute(
            "UPDATE inventory_snapshots SET status = 'restored' WHERE id = ?",
            (snapshot_id,)
        )

    return get_inventory_snapshot(snapshot_id)


def delete_inventory_snapshot(snapshot_id: str) -> bool:
    """Delete a snapshot."""
    with get_db() as conn:
        result = conn.execute(
            "DELETE FROM inventory_snapshots WHERE id = ?",
            (snapshot_id,)
        )
        return result.rowcount > 0


def get_latest_snapshot(site_id: str) -> Optional[Dict[str, Any]]:
    """Get the most recent active snapshot for a site."""
    with get_db() as conn:
        row = conn.execute("""
            SELECT * FROM inventory_snapshots
            WHERE site_id = ? AND status = 'active'
            ORDER BY created_at DESC
            LIMIT 1
        """, (site_id,)).fetchone()
        if row:
            result = dict(row)
            result["snapshot_data"] = json.loads(result.get("snapshot_data") or "[]")
            return result
    return None


# Initialize on import
init_db()
