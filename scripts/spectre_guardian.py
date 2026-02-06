#!/usr/bin/env python3
"""
Spectre Guardian - Automated data quality monitor and self-healer.

Runs in the background and:
1. Detects duplicate/malformed sites
2. Auto-consolidates them to canonical names
3. Cleans up garbage entries
4. Logs all actions for review
5. Prevents future issues by enforcing naming standards

Run as: systemctl --user start spectre-guardian
"""
import os
import sys
import time
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Tuple

# Add backend to path
SCRIPT_DIR = Path(__file__).parent
BACKEND_DIR = SCRIPT_DIR.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from core.db.base import get_db
from core.naming import KNOWN_SITE_PATTERNS, slugify

# Configuration
CHECK_INTERVAL = int(os.environ.get("GUARDIAN_INTERVAL", 300))  # 5 minutes default
LOG_DIR = Path(os.path.expanduser("~/.local/share/spectre"))
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "guardian.log")
    ]
)
logger = logging.getLogger(__name__)

# Build reverse lookup: pattern -> canonical site_id
PATTERN_TO_CANONICAL: Dict[str, str] = {}
for canonical, patterns in KNOWN_SITE_PATTERNS.items():
    for pattern in patterns:
        PATTERN_TO_CANONICAL[pattern.lower().replace(' ', '_').replace('-', '_')] = canonical
        PATTERN_TO_CANONICAL[slugify(pattern)] = canonical

# Known garbage patterns to auto-delete
GARBAGE_PATTERNS = [
    r'^compass_x00',      # XML-encoded garbage
    r'_x00[0-9a-f]{2}_',  # XML entities in the middle
    r'^purchasing_',       # Purchasing reports misidentified as sites
    r'^menuworks_',        # MenuWorks reports
    r'^test_',             # Test entries
    r'^unknown$',          # Generic unknown
]


def find_canonical_site(site_id: str) -> str:
    """Find the canonical site_id for a given site_id."""
    normalized = site_id.lower().replace(' ', '_').replace('-', '_')

    # Direct match in patterns
    if normalized in PATTERN_TO_CANONICAL:
        return PATTERN_TO_CANONICAL[normalized]

    # Check if any pattern is contained in the site_id
    for pattern, canonical in PATTERN_TO_CANONICAL.items():
        if pattern in normalized or normalized in pattern:
            return canonical

    # Check for common variations
    # lockheed_100 -> lockheed_martin_bldg_100
    if 'lockheed' in normalized and '100' in normalized:
        return 'lockheed_martin_bldg_100'
    if 'lockheed' in normalized and ('bldg_d' in normalized or 'bldg d' in normalized or normalized.endswith('_d')):
        return 'lockheed_martin_bldg_d'

    # No match - return as-is
    return site_id


def is_garbage_site(site_id: str) -> bool:
    """Check if a site_id matches garbage patterns."""
    for pattern in GARBAGE_PATTERNS:
        if re.match(pattern, site_id.lower()):
            return True
    return False


def get_all_sites() -> Set[str]:
    """Get all unique site_ids across all tables."""
    sites = set()
    with get_db() as conn:
        for table in ['unit_scores', 'score_history', 'files']:
            try:
                rows = conn.execute(f"SELECT DISTINCT site_id FROM {table}").fetchall()
                sites.update(r[0] for r in rows if r[0])
            except Exception as e:
                logger.debug(f"Error reading {table}: {e}")
    return sites


def consolidate_site(old_site: str, new_site: str) -> int:
    """Consolidate old_site into new_site across all tables."""
    if old_site == new_site:
        return 0

    total_updated = 0
    with get_db() as conn:
        for table in ['unit_scores', 'score_history', 'files']:
            try:
                cursor = conn.execute(
                    f"UPDATE {table} SET site_id = ? WHERE site_id = ?",
                    (new_site, old_site)
                )
                total_updated += cursor.rowcount
            except Exception as e:
                logger.error(f"Error updating {table}: {e}")
        conn.commit()

    return total_updated


def delete_garbage_site(site_id: str) -> int:
    """Delete all records for a garbage site."""
    total_deleted = 0
    with get_db() as conn:
        for table in ['unit_scores', 'score_history', 'files']:
            try:
                cursor = conn.execute(
                    f"DELETE FROM {table} WHERE site_id = ?",
                    (site_id,)
                )
                total_deleted += cursor.rowcount
            except Exception as e:
                logger.error(f"Error deleting from {table}: {e}")
        conn.commit()

    return total_deleted


def check_and_heal() -> Dict[str, int]:
    """Run all checks and auto-heal issues."""
    stats = {
        'sites_checked': 0,
        'sites_consolidated': 0,
        'garbage_deleted': 0,
        'records_updated': 0,
    }

    sites = get_all_sites()
    stats['sites_checked'] = len(sites)

    # Track consolidations to avoid loops
    consolidations: List[Tuple[str, str]] = []
    garbage: List[str] = []

    for site_id in sites:
        # Check for garbage first
        if is_garbage_site(site_id):
            garbage.append(site_id)
            continue

        # Find canonical name
        canonical = find_canonical_site(site_id)
        if canonical != site_id:
            consolidations.append((site_id, canonical))

    # Perform consolidations
    for old_site, new_site in consolidations:
        logger.info(f"Consolidating '{old_site}' -> '{new_site}'")
        updated = consolidate_site(old_site, new_site)
        if updated > 0:
            stats['sites_consolidated'] += 1
            stats['records_updated'] += updated

    # Delete garbage
    for site_id in garbage:
        logger.info(f"Deleting garbage site: '{site_id}'")
        deleted = delete_garbage_site(site_id)
        if deleted > 0:
            stats['garbage_deleted'] += 1
            stats['records_updated'] += deleted

    return stats


def consolidate_folders():
    """Consolidate processed data folders to match canonical site names."""
    processed_dir = BACKEND_DIR.parent / "data" / "processed"
    if not processed_dir.exists():
        return

    # Map folder names to canonical
    for folder in processed_dir.iterdir():
        if not folder.is_dir():
            continue

        folder_name = folder.name
        canonical = find_canonical_site(slugify(folder_name))

        # Check if this folder should be consolidated
        if canonical != slugify(folder_name):
            # Find or create canonical folder
            # Use display name format for folder
            canonical_display = canonical.replace('_', ' ').title()
            # Special cases
            if 'lockheed_martin_bldg_100' in canonical:
                canonical_display = "Lockheed Martin, Bldg 100"
            elif 'lockheed_martin_bldg_d' in canonical:
                canonical_display = "Lockheed Martin, Bldg D"
            elif canonical.startswith('pseg_'):
                parts = canonical.split('_')
                canonical_display = "PSEG - " + ' '.join(p.title() for p in parts[1:])

            target_folder = processed_dir / canonical_display

            if folder.name != canonical_display:
                logger.info(f"Consolidating folder '{folder.name}' -> '{canonical_display}'")
                try:
                    target_folder.mkdir(exist_ok=True)
                    # Move contents
                    for item in folder.iterdir():
                        dest = target_folder / item.name
                        if not dest.exists():
                            item.rename(dest)
                    # Remove empty source folder
                    if not any(folder.iterdir()):
                        folder.rmdir()
                except Exception as e:
                    logger.error(f"Error consolidating folder: {e}")


def run_guardian():
    """Main guardian loop."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║              Spectre Guardian - Auto-Healer                 ║
╠══════════════════════════════════════════════════════════════╣
║  Monitoring for:                                            ║
║    • Duplicate sites                                        ║
║    • Malformed site IDs                                     ║
║    • Garbage entries                                        ║
║    • Folder inconsistencies                                 ║
║                                                             ║
║  Check interval: {interval:>3} seconds                              ║
╚══════════════════════════════════════════════════════════════╝
    """.format(interval=CHECK_INTERVAL))

    logger.info("Guardian started - monitoring data quality")

    # Initial check
    stats = check_and_heal()
    consolidate_folders()
    logger.info(f"Initial check: {stats}")

    # Main loop
    while True:
        try:
            time.sleep(CHECK_INTERVAL)

            stats = check_and_heal()

            if stats['sites_consolidated'] > 0 or stats['garbage_deleted'] > 0:
                logger.info(f"Healed: {stats['sites_consolidated']} consolidations, "
                          f"{stats['garbage_deleted']} garbage removed, "
                          f"{stats['records_updated']} records updated")
                consolidate_folders()
            else:
                logger.debug(f"Check complete: {stats['sites_checked']} sites OK")

        except KeyboardInterrupt:
            logger.info("Guardian stopped")
            break
        except Exception as e:
            logger.error(f"Guardian error: {e}")
            time.sleep(60)  # Back off on error


if __name__ == "__main__":
    run_guardian()
