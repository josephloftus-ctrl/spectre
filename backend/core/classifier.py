"""
ABC-XYZ Inventory Classification Module

Classifies inventory items by:
- ABC: Value contribution (A=top 80%, B=next 15%, C=bottom 5%)
- XYZ: Demand variability (X=stable, Y=moderate, Z=unpredictable)

Classifications are calculated per-site and stored for use in:
- Health score weighting (A items matter more)
- Count prioritization in Steady (A items first)
- Analytics dashboards
"""

import statistics
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from backend.core.db.base import get_db

logger = logging.getLogger(__name__)


# ABC thresholds (cumulative % of total value)
ABC_THRESHOLDS = {
    'A': 0.80,  # Top 80% of value
    'B': 0.95,  # Next 15% of value
    'C': 1.00   # Bottom 5% of value
}

# XYZ thresholds (coefficient of variation)
XYZ_THRESHOLDS = {
    'X': 0.25,  # CV < 0.25 (stable)
    'Y': 0.50,  # CV 0.25-0.50 (moderate)
    'Z': 1.00   # CV > 0.50 (unpredictable)
}

# Minimum weeks of data required for XYZ classification
MIN_WEEKS_FOR_CLASSIFICATION = 4

# ABC score multipliers for health scoring
ABC_SCORE_MULTIPLIERS = {
    'A': 1.5,   # A items: flags count 50% more
    'B': 1.0,   # B items: unchanged
    'C': 0.5,   # C items: flags count 50% less
    None: 1.0   # Unclassified: unchanged
}


def get_latest_item_values(site_id: str) -> List[Dict[str, Any]]:
    """
    Get the latest inventory values for all items at a site.
    Uses the most recent week's snapshot.

    Returns:
        List of dicts with 'sku' and 'total_value' keys
    """
    with get_db() as conn:
        # Get the most recent week_ending for this site
        cursor = conn.execute("""
            SELECT week_ending
            FROM inventory_item_history
            WHERE site_id = ?
            ORDER BY week_ending DESC
            LIMIT 1
        """, (site_id,))

        row = cursor.fetchone()
        if not row:
            return []

        latest_week = row[0]

        # Get all items from that week
        cursor = conn.execute("""
            SELECT sku, total_value, quantity, description
            FROM inventory_item_history
            WHERE site_id = ? AND week_ending = ?
        """, (site_id, latest_week))

        items = []
        for row in cursor.fetchall():
            items.append({
                'sku': row[0],
                'total_value': row[1] or 0,
                'quantity': row[2] or 0,
                'description': row[3] or ''
            })

        return items


def get_item_quantity_history(site_id: str, weeks: int = 12) -> Dict[str, List[float]]:
    """
    Get weekly quantity history for all items at a site.

    Args:
        site_id: Site identifier
        weeks: Number of weeks to look back

    Returns:
        Dict mapping SKU to list of weekly quantities (oldest to newest)
    """
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT sku, week_ending, quantity
            FROM inventory_item_history
            WHERE site_id = ?
            ORDER BY sku, week_ending ASC
        """, (site_id,))

        # Group by SKU
        history: Dict[str, List[Tuple[str, float]]] = {}
        for row in cursor.fetchall():
            sku = row[0]
            week = row[1]
            qty = row[2] or 0

            if sku not in history:
                history[sku] = []
            history[sku].append((week, qty))

        # Convert to just quantities, keeping only recent weeks
        result: Dict[str, List[float]] = {}
        for sku, week_data in history.items():
            # Take the most recent 'weeks' entries
            recent = week_data[-weeks:] if len(week_data) > weeks else week_data
            result[sku] = [qty for _, qty in recent]

        return result


def calculate_abc_classification(site_id: str) -> Dict[str, Tuple[str, float]]:
    """
    Calculate ABC class for all items at a site.

    Algorithm:
    1. Get latest inventory snapshot for site
    2. Sort items by total_value descending
    3. Calculate cumulative % of total value
    4. Assign A/B/C based on cumulative thresholds

    Returns:
        Dict mapping SKU to (class, total_value)
    """
    items = get_latest_item_values(site_id)

    if not items:
        logger.debug(f"No items found for site {site_id}")
        return {}

    # Sort by value descending
    sorted_items = sorted(items, key=lambda x: x['total_value'], reverse=True)

    # Calculate total value
    total = sum(i['total_value'] for i in sorted_items)
    if total == 0:
        logger.debug(f"Total value is 0 for site {site_id}")
        return {}

    # Assign classifications based on cumulative percentage
    cumulative = 0
    classifications: Dict[str, Tuple[str, float]] = {}

    for item in sorted_items:
        cumulative += item['total_value']
        pct = cumulative / total

        if pct <= ABC_THRESHOLDS['A']:
            abc_class = 'A'
        elif pct <= ABC_THRESHOLDS['B']:
            abc_class = 'B'
        else:
            abc_class = 'C'

        classifications[item['sku']] = (abc_class, item['total_value'])

    return classifications


def calculate_xyz_classification(site_id: str) -> Dict[str, Tuple[Optional[str], Optional[float], int, float]]:
    """
    Calculate XYZ class for all items at a site.

    Algorithm:
    1. Get weekly quantities from inventory_item_history
    2. For items with >= MIN_WEEKS_FOR_CLASSIFICATION weeks of data:
       - Calculate mean and std dev of quantities
       - CV = std_dev / mean (coefficient of variation)
    3. Assign X/Y/Z based on CV thresholds

    Returns:
        Dict mapping SKU to (class, cv_score, weeks_of_data, avg_quantity)
        class is None if insufficient data
    """
    history = get_item_quantity_history(site_id, weeks=12)
    classifications: Dict[str, Tuple[Optional[str], Optional[float], int, float]] = {}

    for sku, weekly_quantities in history.items():
        weeks_of_data = len(weekly_quantities)

        if weeks_of_data < MIN_WEEKS_FOR_CLASSIFICATION:
            # Insufficient data
            avg = statistics.mean(weekly_quantities) if weekly_quantities else 0
            classifications[sku] = (None, None, weeks_of_data, avg)
            continue

        mean = statistics.mean(weekly_quantities)

        if mean == 0:
            # No average quantity = highly unpredictable
            classifications[sku] = ('Z', 1.0, weeks_of_data, 0)
            continue

        std_dev = statistics.stdev(weekly_quantities)
        cv = std_dev / mean

        if cv < XYZ_THRESHOLDS['X']:
            xyz_class = 'X'
        elif cv < XYZ_THRESHOLDS['Y']:
            xyz_class = 'Y'
        else:
            xyz_class = 'Z'

        classifications[sku] = (xyz_class, round(cv, 4), weeks_of_data, round(mean, 2))

    return classifications


def upsert_classification(
    site_id: str,
    sku: str,
    abc_class: Optional[str],
    xyz_class: Optional[str],
    combined_class: Optional[str],
    total_value: float,
    avg_quantity: float,
    cv_score: Optional[float],
    weeks_of_data: int
) -> None:
    """
    Insert or update a classification record.
    """
    with get_db() as conn:
        now = datetime.utcnow().isoformat()
        item_id = str(uuid.uuid4())

        conn.execute("""
            INSERT INTO item_classifications
                (id, site_id, sku, abc_class, xyz_class, combined_class,
                 total_value, avg_quantity, cv_score, weeks_of_data,
                 last_calculated, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(site_id, sku) DO UPDATE SET
                abc_class = excluded.abc_class,
                xyz_class = excluded.xyz_class,
                combined_class = excluded.combined_class,
                total_value = excluded.total_value,
                avg_quantity = excluded.avg_quantity,
                cv_score = excluded.cv_score,
                weeks_of_data = excluded.weeks_of_data,
                last_calculated = excluded.last_calculated,
                updated_at = excluded.updated_at
        """, (item_id, site_id, sku, abc_class, xyz_class, combined_class,
              total_value, avg_quantity, cv_score, weeks_of_data, now, now, now))


def refresh_classifications(site_id: str) -> int:
    """
    Recalculate and store all classifications for a site.
    Called after inventory upload completes.

    Returns:
        Number of items classified
    """
    logger.info(f"Refreshing classifications for site {site_id}")

    abc = calculate_abc_classification(site_id)
    xyz = calculate_xyz_classification(site_id)

    # Merge all SKUs from both calculations
    all_skus = set(abc.keys()) | set(xyz.keys())
    count = 0

    for sku in all_skus:
        abc_class, total_value = abc.get(sku, (None, 0))
        xyz_class, cv_score, weeks_of_data, avg_quantity = xyz.get(sku, (None, None, 0, 0))

        # Build combined class (e.g., "AX", "BY", "CZ")
        combined = None
        if abc_class and xyz_class:
            combined = f"{abc_class}{xyz_class}"
        elif abc_class:
            combined = abc_class
        elif xyz_class:
            combined = xyz_class

        upsert_classification(
            site_id=site_id,
            sku=sku,
            abc_class=abc_class,
            xyz_class=xyz_class,
            combined_class=combined,
            total_value=total_value,
            avg_quantity=avg_quantity,
            cv_score=cv_score,
            weeks_of_data=weeks_of_data
        )
        count += 1

    logger.info(f"Classified {count} items for site {site_id}")
    return count


def get_site_classifications(site_id: str) -> Dict[str, str]:
    """
    Get ABC classifications for a site as a simple lookup dict.
    Used by flag_checker for score multipliers.

    Returns:
        Dict mapping SKU to ABC class ('A', 'B', 'C', or None)
    """
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT sku, abc_class
            FROM item_classifications
            WHERE site_id = ?
        """, (site_id,))

        return {row[0]: row[1] for row in cursor.fetchall()}


def get_abc_multiplier(sku: str, site_id: str, classifications: Optional[Dict[str, str]] = None) -> float:
    """
    Get the ABC score multiplier for an item.

    Args:
        sku: Item SKU
        site_id: Site ID
        classifications: Optional pre-loaded {sku: abc_class} dict

    Returns:
        Multiplier (1.5, 1.0, or 0.5)
    """
    if classifications is None:
        classifications = get_site_classifications(site_id)

    abc_class = classifications.get(sku)
    return ABC_SCORE_MULTIPLIERS.get(abc_class, 1.0)


def get_all_classifications(site_id: str) -> List[Dict[str, Any]]:
    """
    Get all classification records for a site.
    Used by API endpoints.

    Returns:
        List of classification dicts
    """
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT sku, abc_class, xyz_class, combined_class,
                   total_value, avg_quantity, cv_score, weeks_of_data,
                   last_calculated
            FROM item_classifications
            WHERE site_id = ?
            ORDER BY total_value DESC
        """, (site_id,))

        results = []
        for row in cursor.fetchall():
            results.append({
                'sku': row[0],
                'abc_class': row[1],
                'xyz_class': row[2],
                'combined_class': row[3],
                'total_value': row[4],
                'avg_quantity': row[5],
                'cv_score': row[6],
                'weeks_of_data': row[7],
                'last_calculated': row[8]
            })

        return results


def get_classification_summary(site_id: str) -> Dict[str, Any]:
    """
    Get summary statistics for classifications at a site.

    Returns:
        Dict with abc_distribution, xyz_distribution, and nine_box counts
    """
    with get_db() as conn:
        # ABC distribution
        cursor = conn.execute("""
            SELECT abc_class, COUNT(*), SUM(total_value)
            FROM item_classifications
            WHERE site_id = ?
            GROUP BY abc_class
        """, (site_id,))

        abc_dist = {}
        total_value = 0
        for row in cursor.fetchall():
            cls = row[0] or 'unclassified'
            abc_dist[cls] = {
                'count': row[1],
                'total_value': row[2] or 0
            }
            total_value += row[2] or 0

        # Calculate percentages
        for cls, data in abc_dist.items():
            data['pct_of_value'] = round((data['total_value'] / total_value * 100) if total_value > 0 else 0, 1)

        # XYZ distribution
        cursor = conn.execute("""
            SELECT xyz_class, COUNT(*), AVG(cv_score)
            FROM item_classifications
            WHERE site_id = ?
            GROUP BY xyz_class
        """, (site_id,))

        xyz_dist = {}
        for row in cursor.fetchall():
            cls = row[0] or 'unclassified'
            xyz_dist[cls] = {
                'count': row[1],
                'avg_cv': round(row[2], 3) if row[2] else None
            }

        # Nine-box counts
        cursor = conn.execute("""
            SELECT combined_class, COUNT(*)
            FROM item_classifications
            WHERE site_id = ? AND combined_class IS NOT NULL
            GROUP BY combined_class
        """, (site_id,))

        nine_box = {}
        for row in cursor.fetchall():
            nine_box[row[0]] = row[1]

        # Get last calculated timestamp
        cursor = conn.execute("""
            SELECT MAX(last_calculated)
            FROM item_classifications
            WHERE site_id = ?
        """, (site_id,))

        last_calc = cursor.fetchone()
        last_calculated = last_calc[0] if last_calc else None

        return {
            'abc_distribution': abc_dist,
            'xyz_distribution': xyz_dist,
            'nine_box': nine_box,
            'last_calculated': last_calculated
        }


def get_classified_items(
    site_id: str,
    abc_class: Optional[str] = None,
    xyz_class: Optional[str] = None,
    sort_by: str = 'value',
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Get items with optional filtering by classification.

    Args:
        site_id: Site identifier
        abc_class: Filter by A, B, or C (optional)
        xyz_class: Filter by X, Y, or Z (optional)
        sort_by: 'value', 'cv', or 'sku'
        limit: Max items to return

    Returns:
        List of classification records
    """
    query = """
        SELECT sku, abc_class, xyz_class, combined_class,
               total_value, avg_quantity, cv_score, weeks_of_data
        FROM item_classifications
        WHERE site_id = ?
    """
    params: List[Any] = [site_id]

    if abc_class:
        query += " AND abc_class = ?"
        params.append(abc_class)

    if xyz_class:
        query += " AND xyz_class = ?"
        params.append(xyz_class)

    # Sort order
    if sort_by == 'cv':
        query += " ORDER BY cv_score DESC"
    elif sort_by == 'sku':
        query += " ORDER BY sku"
    else:  # default: value
        query += " ORDER BY total_value DESC"

    query += " LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        cursor = conn.execute(query, params)

        results = []
        for row in cursor.fetchall():
            results.append({
                'sku': row[0],
                'abc_class': row[1],
                'xyz_class': row[2],
                'combined_class': row[3],
                'total_value': row[4],
                'avg_quantity': row[5],
                'cv_score': row[6],
                'weeks_of_data': row[7]
            })

        return results
