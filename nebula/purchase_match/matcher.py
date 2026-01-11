"""
Purchase Matcher - Core comparison engine.

Combines 3 data sources for robust inventory analysis:
1. IPS (Invoice Purchasing Summaries) - What was actually purchased
2. MOG (Master Order Guides) - What's available to order
3. Inventory - What's being counted on-site

Decision Matrix:
| In IPS? | In MOG? | Similar in MOG? | Result |
|---------|---------|-----------------|--------|
| ✓       | -       | -               | CLEAN |
| ✗       | ✓       | -               | ORDERABLE |
| ✗       | ✗       | ✓               | LIKELY_TYPO |
| ✗       | ✗       | ✗               | UNKNOWN |
"""

from typing import Optional, Set, List
import logging
from .models import InventoryRecord, MatchResult, MatchFlag, MOGMatch, PurchaseRecord
from .index import CanonIndex
from .config import Config
from .mog import MOGIndex

logger = logging.getLogger(__name__)

# Minimum similarity score to suggest a typo correction
MIN_SIMILARITY_THRESHOLD = 0.3
MIN_EMBEDDING_SIMILARITY = 50  # Percentage for embedding-based matches

# Global embedding index reference
_embedding_index = None


def set_embedding_index(index):
    """Set the embedding index for semantic matching."""
    global _embedding_index
    _embedding_index = index
    logger.info("Embedding index set for semantic matching")


def match_inventory(
    inventory: list[InventoryRecord],
    ips_index: CanonIndex,
    config: Config,
    mog_index: Optional[MOGIndex] = None,
    ignored_skus: Optional[Set[str]] = None,
) -> list[MatchResult]:
    """
    Match inventory items against IPS purchases and MOG catalogs.

    Args:
        inventory: Items to validate
        ips_index: Indexed purchase history (IPS)
        config: Unit-vendor configuration
        mog_index: Indexed vendor catalogs (MOG) - optional but recommended
        ignored_skus: Set of SKUs to mark as IGNORED

    Returns:
        List of MatchResult for each inventory item
    """
    results = []
    ignored = ignored_skus or set()

    for item in inventory:
        result = _match_single_item(item, ips_index, mog_index, ignored)
        results.append(result)

    return results


def _match_single_item(
    item: InventoryRecord,
    ips_index: CanonIndex,
    mog_index: Optional[MOGIndex],
    ignored_skus: Set[str],
) -> MatchResult:
    """
    Match a single inventory item using all available data sources.

    Logic flow:
    1. Check ignore list first
    2. Check IPS (was it purchased?)
    3. Check MOG (is it orderable?)
    4. Search MOG by description (is it a typo?)
    5. Unknown - needs investigation
    """
    sku = item.sku

    # 1. Check ignore list
    if sku in ignored_skus:
        return MatchResult(
            inventory_item=item,
            flag=MatchFlag.IGNORED,
            reason="On site ignore list"
        )

    # 2. Check IPS - was this SKU purchased?
    ips_match = ips_index.lookup_sku(sku)
    if ips_match is not None:
        return MatchResult(
            inventory_item=item,
            flag=MatchFlag.CLEAN,
            reason="SKU found in purchase history",
            ips_match=ips_match
        )

    # 3. Check MOG - is this SKU in the vendor catalogs?
    if mog_index is not None:
        mog_item = mog_index.lookup_sku(sku)
        if mog_item is not None:
            return MatchResult(
                inventory_item=item,
                flag=MatchFlag.ORDERABLE,
                reason=f"Valid SKU in {mog_item.vendor} catalog, not recently purchased",
                mog_match=MOGMatch(
                    sku=mog_item.sku,
                    description=mog_item.description,
                    vendor=mog_item.vendor,
                    price=mog_item.price
                )
            )

        # 4. Search by description - is this a typo?
        if item.description:
            # Try embedding-based search first (more accurate)
            if _embedding_index and _embedding_index.is_ready:
                similar = _embedding_index.find_similar(item.description, limit=3)
                if similar and similar[0]["similarity"] >= MIN_EMBEDDING_SIMILARITY:
                    best = similar[0]
                    return MatchResult(
                        inventory_item=item,
                        flag=MatchFlag.LIKELY_TYPO,
                        reason=f"SKU not found, but description matches {best['vendor']} item (semantic)",
                        suggested_sku=MOGMatch(
                            sku=best["sku"],
                            description=best["description"],
                            vendor=best["vendor"],
                            price=best.get("price"),
                            similarity=best["similarity"] / 100  # Convert to 0-1
                        )
                    )

            # Fallback to word-based matching
            similar_items = mog_index.find_by_description(item.description, limit=3)
            if similar_items:
                best = similar_items[0]
                # Calculate similarity for the best match
                similarity = _calculate_similarity(item.description, best.description)

                if similarity >= MIN_SIMILARITY_THRESHOLD:
                    return MatchResult(
                        inventory_item=item,
                        flag=MatchFlag.LIKELY_TYPO,
                        reason=f"SKU not found, but description matches {best.vendor} item",
                        suggested_sku=MOGMatch(
                            sku=best.sku,
                            description=best.description,
                            vendor=best.vendor,
                            price=best.price,
                            similarity=similarity
                        )
                    )

    # 5. Unknown - not in IPS, not in MOG, no similar items
    return MatchResult(
        inventory_item=item,
        flag=MatchFlag.UNKNOWN,
        reason="SKU not found in purchases or vendor catalogs"
    )


def _calculate_similarity(desc1: str, desc2: str) -> float:
    """
    Calculate similarity between two descriptions.

    Uses Jaccard similarity on normalized word sets.
    Returns 0-1 score.
    """
    import re

    def normalize(s: str) -> set:
        s = s.lower()
        s = re.sub(r'[^\w\s]', ' ', s)
        return set(s.split())

    words1 = normalize(desc1)
    words2 = normalize(desc2)

    if not words1 or not words2:
        return 0.0

    intersection = len(words1 & words2)
    union = len(words1 | words2)

    return intersection / union if union > 0 else 0.0


def group_results_by_unit(results: list[MatchResult]) -> dict[str, list[MatchResult]]:
    """Group match results by unit for reporting."""
    grouped: dict[str, list[MatchResult]] = {}
    for result in results:
        unit = result.inventory_item.unit
        if unit not in grouped:
            grouped[unit] = []
        grouped[unit].append(result)
    return grouped


def sort_results_for_report(results: list[MatchResult]) -> list[MatchResult]:
    """
    Sort results for human consumption.

    Priority order (most actionable first):
    1. LIKELY_TYPO - quick fix available
    2. UNKNOWN - needs investigation
    3. ORDERABLE - valid but not purchased
    4. IGNORED - acknowledged
    5. CLEAN - no action needed
    """
    flag_order = {
        MatchFlag.LIKELY_TYPO: 0,
        MatchFlag.UNKNOWN: 1,
        MatchFlag.ORDERABLE: 2,
        MatchFlag.IGNORED: 3,
        MatchFlag.CLEAN: 4,
    }
    return sorted(results, key=lambda r: flag_order.get(r.flag, 99))


def filter_actionable(results: list[MatchResult]) -> list[MatchResult]:
    """Filter to only actionable results (exclude CLEAN and IGNORED)."""
    return [r for r in results if r.flag not in (MatchFlag.CLEAN, MatchFlag.IGNORED)]


def summarize_results(results: list[MatchResult]) -> dict:
    """Generate summary statistics for results."""
    counts = {
        "total": len(results),
        "clean": 0,
        "orderable": 0,
        "likely_typo": 0,
        "unknown": 0,
        "ignored": 0,
    }

    for result in results:
        if result.flag == MatchFlag.CLEAN:
            counts["clean"] += 1
        elif result.flag == MatchFlag.ORDERABLE:
            counts["orderable"] += 1
        elif result.flag == MatchFlag.LIKELY_TYPO:
            counts["likely_typo"] += 1
        elif result.flag == MatchFlag.UNKNOWN:
            counts["unknown"] += 1
        elif result.flag == MatchFlag.IGNORED:
            counts["ignored"] += 1

    counts["actionable"] = counts["likely_typo"] + counts["unknown"]

    # Legacy compatibility
    counts["sku_mismatch"] = counts["likely_typo"]
    counts["orphan"] = counts["unknown"]

    return counts
