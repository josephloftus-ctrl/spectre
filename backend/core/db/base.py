"""
Database base module - connection management, initialization, and enums.
"""
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from enum import Enum
import json

# Database location
DB_PATH = Path(__file__).resolve().parents[3] / "data" / "spectre.db"


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

# Default walking order (used when no custom order exists)
DEFAULT_LOCATION_ORDER = {
    'Freezer': 1,
    'Walk In Cooler': 2,
    'Beverage Room': 3,
    'Dry Storage Food': 4,
    'Dry Storage Supplies': 5,
    'Chemical Locker': 6,
    'NEVER INVENTORY': 99,
    'UNASSIGNED': 100,
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
                collection TEXT DEFAULT 'knowledge_base',
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
                collection TEXT DEFAULT 'knowledge_base',
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

            -- Off-catalog items (custom items not in Master Order Guide)
            -- Required fields for OrderMaestro upload: Dist # and Cust #
            CREATE TABLE IF NOT EXISTS off_catalog_items (
                id TEXT PRIMARY KEY,
                site_id TEXT NOT NULL,
                dist_num TEXT NOT NULL,      -- Dist # - item number for ordering
                cust_num TEXT NOT NULL,      -- Cust # - unique ID for barcode scanning
                description TEXT,            -- Item Description
                pack TEXT,                   -- Pack size (e.g., "4/64 OZ")
                uom TEXT,                    -- Unit of measure (CS, EA, etc.)
                break_uom TEXT,              -- Break unit of measure
                unit_price REAL,             -- Price per unit
                break_price REAL,            -- Break price
                distributor TEXT,            -- Distributor/vendor name
                distribution_center TEXT,    -- DC Name
                brand TEXT,
                manufacturer TEXT,           -- Mfg
                manufacturer_num TEXT,       -- Mfg #
                gtin TEXT,                   -- GTIN barcode
                upc TEXT,                    -- UPC barcode
                catch_weight INTEGER DEFAULT 0,
                average_weight REAL,
                units_per_case INTEGER,
                location TEXT,               -- Storage location
                area TEXT,                   -- Sub-location
                place TEXT,                  -- Secondary sub-location
                notes TEXT,
                is_active INTEGER DEFAULT 1, -- Soft delete flag
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(site_id, cust_num)
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

            -- Item locations for smart sorting during counts
            CREATE TABLE IF NOT EXISTS item_locations (
                id TEXT PRIMARY KEY,
                site_id TEXT NOT NULL,
                sku TEXT NOT NULL,
                location TEXT NOT NULL,  -- Freezer, Walk In Cooler, etc.
                zone TEXT,               -- Sub-area within location
                sort_order INTEGER DEFAULT 0,  -- Manual sort order within location
                never_count INTEGER DEFAULT 0, -- Flag for items to skip
                auto_assigned INTEGER DEFAULT 1, -- Was location auto-assigned?
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(site_id, sku)
            );

            -- Location walking order per site (customizable)
            CREATE TABLE IF NOT EXISTS location_order (
                id TEXT PRIMARY KEY,
                site_id TEXT NOT NULL,
                location TEXT NOT NULL,
                sort_order INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(site_id, location)
            );

            -- Custom rooms per site (user-created rooms beyond predefined)
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
            CREATE INDEX IF NOT EXISTS idx_item_locations_site ON item_locations(site_id);
            CREATE INDEX IF NOT EXISTS idx_item_locations_location ON item_locations(location);
            CREATE INDEX IF NOT EXISTS idx_location_order_site ON location_order(site_id);
            CREATE INDEX IF NOT EXISTS idx_off_catalog_site ON off_catalog_items(site_id);
            CREATE INDEX IF NOT EXISTS idx_off_catalog_dist ON off_catalog_items(dist_num);
            CREATE INDEX IF NOT EXISTS idx_custom_rooms_site ON custom_rooms(site_id);
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
            conn.execute("ALTER TABLE files ADD COLUMN collection TEXT DEFAULT 'knowledge_base'")

        # Check if collection column exists in embeddings table
        cursor = conn.execute("PRAGMA table_info(embeddings)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'collection' not in columns:
            conn.execute("ALTER TABLE embeddings ADD COLUMN collection TEXT DEFAULT 'knowledge_base'")

        # Create custom_rooms table if it doesn't exist (for existing databases)
        conn.execute("""
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
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_custom_rooms_site ON custom_rooms(site_id)")
