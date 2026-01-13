"""
Database package for Spectre.

This package provides modular database access with backwards compatibility.
All functions are re-exported here so existing imports continue working:

    from backend.core.database import get_file, list_cart_items  # still works
    from backend.core.db import get_file, list_cart_items        # also works
"""

# Base - enums, connection, initialization
from .base import (
    DB_PATH,
    FileStatus,
    JobStatus,
    JobType,
    ScoreStatus,
    ALLOWED_FILE_COLUMNS,
    ALLOWED_JOB_COLUMNS,
    DEFAULT_LOCATION_ORDER,
    get_db,
    init_db,
    migrate_db,
)

# Files
from .files import (
    create_file,
    get_file,
    list_files,
    update_file,
    update_file_status,
    delete_file_record,
)

# Jobs
from .jobs import (
    create_job,
    get_job,
    get_next_job,
    list_jobs,
    update_job_status,
    retry_failed_jobs,
    cancel_job,
    cancel_all_jobs,
)

# Embeddings (SQLite records)
from .embeddings_db import (
    create_embedding,
    get_file_embeddings,
)

# Stats
from .stats import get_stats

# Sites
from .sites import (
    auto_format_site_name,
    get_site,
    get_site_display_name,
    list_sites,
    update_site_display_name,
)

# Scores
from .scores import (
    save_unit_score,
    get_unit_score,
    list_unit_scores,
    get_all_site_ids_with_scores,
    save_score_snapshot,
    get_score_history,
    get_latest_snapshot_date,
    get_score_trend,
)

# Ignored items
from .ignored import (
    add_ignored_item,
    get_ignored_item,
    remove_ignored_item,
    list_ignored_items,
    get_ignored_skus,
)

# Shopping cart
from .cart import (
    add_cart_item,
    get_cart_item,
    update_cart_item_quantity,
    remove_cart_item,
    list_cart_items,
    get_cart_summary,
    clear_cart,
    bulk_add_cart_items,
)

# Off-catalog items
from .catalog import (
    create_off_catalog_item,
    get_off_catalog_item,
    get_off_catalog_item_by_dist,
    update_off_catalog_item,
    delete_off_catalog_item,
    list_off_catalog_items,
    bulk_import_off_catalog_items,
    generate_cust_num,
)

# Count sessions
from .counting import (
    create_count_session,
    get_count_session,
    list_count_sessions,
    update_count_session,
    add_count_item,
    get_count_item,
    list_count_items,
    bulk_add_count_items,
    delete_count_session,
)

# Item locations
from .locations import (
    get_item_location,
    set_item_location,
    bulk_set_item_locations,
    list_item_locations,
    get_location_summary,
    delete_item_location,
    clear_item_locations,
    get_location_order,
    set_location_order,
    reset_location_order,
    list_available_locations,
    get_location_sort_key,
)

# Rooms
from .rooms import (
    list_rooms,
    get_room,
    create_custom_room,
    update_custom_room,
    delete_custom_room,
    get_items_by_room,
    move_item_to_room,
    bulk_move_items,
)

# Inventory snapshots
from .snapshots import (
    create_inventory_snapshot,
    get_inventory_snapshot,
    list_inventory_snapshots,
    restore_inventory_snapshot,
    delete_inventory_snapshot,
    get_latest_snapshot,
)

# Utilities
from .utils import (
    now,
    parse_json_field,
    to_json,
    build_where_clause,
    build_list_query,
    row_to_dict,
    rows_to_dicts,
)

# For backwards compatibility with `from backend.core.database import *`
__all__ = [
    # Base
    "DB_PATH",
    "FileStatus",
    "JobStatus",
    "JobType",
    "ScoreStatus",
    "ALLOWED_FILE_COLUMNS",
    "ALLOWED_JOB_COLUMNS",
    "DEFAULT_LOCATION_ORDER",
    "get_db",
    "init_db",
    "migrate_db",
    # Files
    "create_file",
    "get_file",
    "list_files",
    "update_file",
    "update_file_status",
    "delete_file_record",
    # Jobs
    "create_job",
    "get_job",
    "get_next_job",
    "list_jobs",
    "update_job_status",
    "retry_failed_jobs",
    "cancel_job",
    "cancel_all_jobs",
    # Embeddings
    "create_embedding",
    "get_file_embeddings",
    # Stats
    "get_stats",
    # Sites
    "auto_format_site_name",
    "get_site",
    "get_site_display_name",
    "list_sites",
    "update_site_display_name",
    # Scores
    "save_unit_score",
    "get_unit_score",
    "list_unit_scores",
    "get_all_site_ids_with_scores",
    "save_score_snapshot",
    "get_score_history",
    "get_latest_snapshot_date",
    "get_score_trend",
    # Ignored
    "add_ignored_item",
    "get_ignored_item",
    "remove_ignored_item",
    "list_ignored_items",
    "get_ignored_skus",
    # Cart
    "add_cart_item",
    "get_cart_item",
    "update_cart_item_quantity",
    "remove_cart_item",
    "list_cart_items",
    "get_cart_summary",
    "clear_cart",
    "bulk_add_cart_items",
    # Catalog
    "create_off_catalog_item",
    "get_off_catalog_item",
    "get_off_catalog_item_by_dist",
    "update_off_catalog_item",
    "delete_off_catalog_item",
    "list_off_catalog_items",
    "bulk_import_off_catalog_items",
    "generate_cust_num",
    # Counting
    "create_count_session",
    "get_count_session",
    "list_count_sessions",
    "update_count_session",
    "add_count_item",
    "get_count_item",
    "list_count_items",
    "bulk_add_count_items",
    "delete_count_session",
    # Locations
    "get_item_location",
    "set_item_location",
    "bulk_set_item_locations",
    "list_item_locations",
    "get_location_summary",
    "delete_item_location",
    "clear_item_locations",
    "get_location_order",
    "set_location_order",
    "reset_location_order",
    "list_available_locations",
    "get_location_sort_key",
    # Rooms
    "list_rooms",
    "get_room",
    "create_custom_room",
    "update_custom_room",
    "delete_custom_room",
    "get_items_by_room",
    "move_item_to_room",
    "bulk_move_items",
    # Snapshots
    "create_inventory_snapshot",
    "get_inventory_snapshot",
    "list_inventory_snapshots",
    "restore_inventory_snapshot",
    "delete_inventory_snapshot",
    "get_latest_snapshot",
    # Utils
    "now",
    "parse_json_field",
    "to_json",
    "build_where_clause",
    "build_list_query",
    "row_to_dict",
    "rows_to_dicts",
]
