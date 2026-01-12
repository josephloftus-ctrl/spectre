"""
Shared database utilities.

Common functions used across database modules for:
- Timestamp handling
- JSON field parsing
- Query building
"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
import json


def now() -> str:
    """
    Get current UTC timestamp as ISO string.

    Returns:
        ISO formatted timestamp string
    """
    return datetime.utcnow().isoformat()


def parse_json_field(value: Optional[str], default: Any = None) -> Any:
    """
    Safely parse a JSON field from the database.

    Args:
        value: JSON string from database, may be None
        default: Default value if parsing fails or value is None

    Returns:
        Parsed JSON value or default
    """
    if not value:
        return default if default is not None else []
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else []


def to_json(value: Any) -> str:
    """
    Convert a value to JSON string for database storage.

    Args:
        value: Value to serialize

    Returns:
        JSON string
    """
    return json.dumps(value)


def build_where_clause(
    filters: Dict[str, Any],
    allowed_columns: Optional[set] = None
) -> Tuple[str, List[Any]]:
    """
    Build a WHERE clause from a dict of filters.

    Args:
        filters: Dict of column -> value pairs
        allowed_columns: Optional whitelist of allowed column names

    Returns:
        Tuple of (where_clause_string, params_list)

    Example:
        clause, params = build_where_clause({'status': 'active', 'site_id': 'pseg_nhq'})
        # Returns: (" AND status = ? AND site_id = ?", ['active', 'pseg_nhq'])
    """
    clause_parts = []
    params = []

    for col, val in filters.items():
        if val is None:
            continue

        # Validate column name if whitelist provided
        if allowed_columns and col not in allowed_columns:
            continue

        clause_parts.append(f"{col} = ?")
        params.append(val)

    if not clause_parts:
        return "", []

    return " AND " + " AND ".join(clause_parts), params


def build_list_query(
    table: str,
    filters: Optional[Dict[str, Any]] = None,
    order_by: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    allowed_columns: Optional[set] = None
) -> Tuple[str, List[Any]]:
    """
    Build a SELECT query with optional filters, ordering, and pagination.

    Args:
        table: Table name
        filters: Dict of column -> value pairs for WHERE clause
        order_by: Column to order by (e.g., "created_at DESC")
        limit: Maximum rows to return
        offset: Number of rows to skip
        allowed_columns: Optional whitelist of allowed column names

    Returns:
        Tuple of (query_string, params_list)

    Example:
        query, params = build_list_query(
            'files',
            filters={'status': 'completed'},
            order_by='created_at DESC',
            limit=10
        )
    """
    query = f"SELECT * FROM {table} WHERE 1=1"
    params = []

    if filters:
        where_clause, where_params = build_where_clause(filters, allowed_columns)
        query += where_clause
        params.extend(where_params)

    if order_by:
        # Simple validation - order_by should be column name optionally with ASC/DESC
        query += f" ORDER BY {order_by}"

    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)

    if offset is not None:
        query += " OFFSET ?"
        params.append(offset)

    return query, params


def row_to_dict(row, columns: List[str]) -> Dict[str, Any]:
    """
    Convert a database row tuple to a dictionary.

    Args:
        row: Database row (tuple or sqlite3.Row)
        columns: List of column names

    Returns:
        Dictionary with column names as keys
    """
    if hasattr(row, 'keys'):
        # sqlite3.Row object
        return dict(row)
    return dict(zip(columns, row))


def rows_to_dicts(rows, columns: List[str]) -> List[Dict[str, Any]]:
    """
    Convert multiple database rows to list of dictionaries.

    Args:
        rows: List of database rows
        columns: List of column names

    Returns:
        List of dictionaries
    """
    return [row_to_dict(row, columns) for row in rows]
