"""
Test configuration and fixtures for the Spectre backend test suite.

Provides:
- In-memory SQLite test database (isolated per test)
- FastAPI TestClient fixture
- Factory functions for creating test data
"""
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Optional
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------

def _create_test_db() -> sqlite3.Connection:
    """Create an in-memory SQLite database with the full Spectre schema."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS files (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            original_path TEXT,
            current_path TEXT,
            file_type TEXT,
            file_size INTEGER,
            site_id TEXT,
            collection TEXT DEFAULT 'knowledge_base',
            status TEXT DEFAULT 'pending',
            error_message TEXT,
            parsed_data TEXT,
            embedding_id TEXT,
            inventory_date TEXT,
            content_hash TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            processed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            job_type TEXT NOT NULL,
            file_id TEXT,
            status TEXT DEFAULT 'queued',
            priority INTEGER DEFAULT 0,
            attempts INTEGER DEFAULT 0,
            max_attempts INTEGER DEFAULT 3,
            error_message TEXT,
            result TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            started_at TEXT,
            completed_at TEXT,
            FOREIGN KEY (file_id) REFERENCES files(id)
        );

        CREATE TABLE IF NOT EXISTS embeddings (
            id TEXT PRIMARY KEY,
            file_id TEXT NOT NULL,
            chunk_index INTEGER,
            chunk_text TEXT,
            metadata TEXT,
            collection TEXT DEFAULT 'knowledge_base',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (file_id) REFERENCES files(id)
        );

        CREATE TABLE IF NOT EXISTS analysis_results (
            id TEXT PRIMARY KEY,
            file_id TEXT,
            site_id TEXT,
            analysis_type TEXT,
            result TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (file_id) REFERENCES files(id)
        );

        CREATE TABLE IF NOT EXISTS sites (
            site_id TEXT PRIMARY KEY,
            display_name TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS unit_scores (
            id TEXT PRIMARY KEY,
            file_id TEXT,
            site_id TEXT NOT NULL,
            score INTEGER DEFAULT 0,
            status TEXT DEFAULT 'clean',
            item_flag_count INTEGER DEFAULT 0,
            room_flag_count INTEGER DEFAULT 0,
            flagged_items TEXT,
            flagged_rooms TEXT,
            room_totals TEXT,
            total_value REAL DEFAULT 0,
            item_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (file_id) REFERENCES files(id)
        );

        CREATE TABLE IF NOT EXISTS score_history (
            id TEXT PRIMARY KEY,
            site_id TEXT NOT NULL,
            score INTEGER DEFAULT 0,
            status TEXT DEFAULT 'clean',
            item_flag_count INTEGER DEFAULT 0,
            room_flag_count INTEGER DEFAULT 0,
            total_value REAL DEFAULT 0,
            snapshot_date TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

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

        CREATE TABLE IF NOT EXISTS cart_items (
            id TEXT PRIMARY KEY,
            site_id TEXT NOT NULL,
            sku TEXT NOT NULL,
            description TEXT,
            quantity REAL DEFAULT 1,
            unit_price REAL,
            uom TEXT,
            vendor TEXT,
            notes TEXT,
            source TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(site_id, sku)
        );

        CREATE TABLE IF NOT EXISTS off_catalog_items (
            id TEXT PRIMARY KEY,
            site_id TEXT NOT NULL,
            dist_num TEXT NOT NULL,
            cust_num TEXT NOT NULL,
            description TEXT,
            pack TEXT,
            uom TEXT,
            break_uom TEXT,
            unit_price REAL,
            break_price REAL,
            distributor TEXT,
            distribution_center TEXT,
            brand TEXT,
            manufacturer TEXT,
            manufacturer_num TEXT,
            gtin TEXT,
            upc TEXT,
            catch_weight INTEGER DEFAULT 0,
            average_weight REAL,
            units_per_case INTEGER,
            location TEXT,
            area TEXT,
            place TEXT,
            notes TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(site_id, cust_num)
        );

        CREATE TABLE IF NOT EXISTS inventory_snapshots (
            id TEXT PRIMARY KEY,
            site_id TEXT NOT NULL,
            name TEXT,
            source_file_id TEXT,
            snapshot_data TEXT,
            item_count INTEGER DEFAULT 0,
            total_value REAL DEFAULT 0,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_file_id) REFERENCES files(id)
        );

        CREATE TABLE IF NOT EXISTS count_sessions (
            id TEXT PRIMARY KEY,
            site_id TEXT NOT NULL,
            name TEXT,
            status TEXT DEFAULT 'active',
            item_count INTEGER DEFAULT 0,
            total_value REAL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS count_items (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            sku TEXT NOT NULL,
            description TEXT,
            counted_qty REAL,
            expected_qty REAL,
            unit_price REAL,
            uom TEXT,
            location TEXT,
            variance REAL,
            notes TEXT,
            counted_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES count_sessions(id)
        );

        CREATE TABLE IF NOT EXISTS item_locations (
            id TEXT PRIMARY KEY,
            site_id TEXT NOT NULL,
            sku TEXT NOT NULL,
            location TEXT NOT NULL,
            zone TEXT,
            sort_order INTEGER DEFAULT 0,
            never_count INTEGER DEFAULT 0,
            auto_assigned INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(site_id, sku)
        );

        CREATE TABLE IF NOT EXISTS location_order (
            id TEXT PRIMARY KEY,
            site_id TEXT NOT NULL,
            location TEXT NOT NULL,
            sort_order INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(site_id, location)
        );

        CREATE TABLE IF NOT EXISTS custom_rooms (
            id TEXT PRIMARY KEY,
            site_id TEXT NOT NULL,
            name TEXT NOT NULL,
            display_name TEXT,
            sort_order INTEGER DEFAULT 50,
            color TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(site_id, name)
        );

        -- Indexes
        CREATE INDEX IF NOT EXISTS idx_files_status ON files(status);
        CREATE INDEX IF NOT EXISTS idx_files_site ON files(site_id);
        CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
        CREATE INDEX IF NOT EXISTS idx_jobs_file ON jobs(file_id);
        CREATE INDEX IF NOT EXISTS idx_unit_scores_site ON unit_scores(site_id);
        CREATE INDEX IF NOT EXISTS idx_score_history_site ON score_history(site_id);
    """)

    return conn


@contextmanager
def _test_get_db(conn: sqlite3.Connection):
    """Replacement for get_db() that uses the shared test connection."""
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


@pytest.fixture()
def test_db():
    """Provide a fresh in-memory SQLite database for each test."""
    conn = _create_test_db()
    yield conn
    conn.close()


@pytest.fixture()
def patch_db(test_db):
    """
    Patch the get_db context manager across all db modules so that
    every database call uses the in-memory test database.
    """
    cm = lambda: _test_get_db(test_db)  # noqa: E731

    with (
        patch("backend.core.db.base.get_db", cm),
        patch("backend.core.db.files.get_db", cm),
        patch("backend.core.db.jobs.get_db", cm),
        patch("backend.core.db.scores.get_db", cm),
        patch("backend.core.db.sites.get_db", cm),
        patch("backend.core.db.stats.get_db", cm),
        patch("backend.core.db.cart.get_db", cm),
        patch("backend.core.db.catalog.get_db", cm),
        patch("backend.core.db.counting.get_db", cm),
        patch("backend.core.db.locations.get_db", cm),
        patch("backend.core.db.rooms.get_db", cm),
        patch("backend.core.db.snapshots.get_db", cm),
        patch("backend.core.db.ignored.get_db", cm),
        patch("backend.core.db.embeddings_db.get_db", cm),
        patch("backend.api.routers.inventory.get_db", cm),
    ):
        yield test_db


@pytest.fixture()
def client(patch_db):
    """
    Provide a FastAPI TestClient with the database patched.

    Skips the lifespan (worker init/shutdown) to avoid APScheduler side effects.
    """
    from backend.api.main import app

    # Disable lifespan so worker doesn't start during tests
    with patch("backend.api.main.init_worker"), \
         patch("backend.api.main.stop_scheduler"):
        with TestClient(app) as c:
            yield c


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------

def create_file(
    db: sqlite3.Connection,
    *,
    file_id: Optional[str] = None,
    filename: str = "test_file.xlsx",
    site_id: str = "pseg_nhq",
    status: str = "completed",
    parsed_data: Optional[dict] = None,
    inventory_date: Optional[str] = None,
    total_value: float = 5000.0,
) -> str:
    """Insert a file record and return its ID."""
    fid = file_id or str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    pd_json = json.dumps(parsed_data) if parsed_data else None

    db.execute(
        """INSERT INTO files
           (id, filename, original_path, current_path, file_type, file_size,
            site_id, status, parsed_data, inventory_date, created_at, updated_at, processed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (fid, filename, f"/data/inbox/{filename}", f"/data/processed/{filename}",
         "xlsx", 1024, site_id, status, pd_json, inventory_date, now, now, now),
    )
    db.commit()
    return fid


def create_job(
    db: sqlite3.Connection,
    *,
    job_id: Optional[str] = None,
    job_type: str = "parse",
    file_id: Optional[str] = None,
    status: str = "queued",
    priority: int = 0,
) -> str:
    """Insert a job record and return its ID."""
    jid = job_id or str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    db.execute(
        """INSERT INTO jobs (id, job_type, file_id, status, priority, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (jid, job_type, file_id, status, priority, now),
    )
    db.commit()
    return jid


def create_score(
    db: sqlite3.Connection,
    *,
    site_id: str = "pseg_nhq",
    score: int = 5,
    status: str = "warning",
    total_value: float = 12000.0,
    item_count: int = 150,
    item_flag_count: int = 3,
    room_flag_count: int = 1,
    flagged_items: Optional[list] = None,
    flagged_rooms: Optional[list] = None,
    room_totals: Optional[dict] = None,
    file_id: Optional[str] = None,
) -> str:
    """Insert a unit_scores record and return its ID."""
    sid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    db.execute(
        """INSERT INTO unit_scores
           (id, file_id, site_id, score, status,
            item_flag_count, room_flag_count,
            flagged_items, flagged_rooms, room_totals,
            total_value, item_count, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (sid, file_id, site_id, score, status,
         item_flag_count, room_flag_count,
         json.dumps(flagged_items or []),
         json.dumps(flagged_rooms or []),
         json.dumps(room_totals or {}),
         total_value, item_count, now),
    )
    db.commit()
    return sid


def create_score_history(
    db: sqlite3.Connection,
    *,
    site_id: str = "pseg_nhq",
    score: int = 5,
    status: str = "warning",
    total_value: float = 12000.0,
    snapshot_date: str = "2026-01-20",
) -> str:
    """Insert a score_history record and return its ID."""
    hid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    db.execute(
        """INSERT INTO score_history
           (id, site_id, score, status, item_flag_count, room_flag_count,
            total_value, snapshot_date, created_at)
           VALUES (?, ?, ?, ?, 0, 0, ?, ?, ?)""",
        (hid, site_id, score, status, total_value, snapshot_date, now),
    )
    db.commit()
    return hid
