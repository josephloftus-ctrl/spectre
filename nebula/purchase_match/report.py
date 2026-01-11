"""
Report Generator - Format results for human consumption.

Produces console output and CSV export for match results.
"""

import csv
import io
from datetime import datetime
from typing import TextIO

from .models import MatchResult, MatchFlag
from .matcher import group_results_by_unit, sort_results_for_report, summarize_results


def format_console(results: list[MatchResult], show_clean: bool = False) -> str:
    """
    Format results for console display.

    Groups by unit, sorts by flag type (SKU_MISMATCH first).
    Uses box-drawing characters for visual hierarchy.

    Args:
        results: Match results to format
        show_clean: Whether to include CLEAN items (default False)

    Returns:
        Formatted string for console output
    """
    if not results:
        return "No inventory items to report.\n"

    lines = []
    grouped = group_results_by_unit(results)

    for unit, unit_results in sorted(grouped.items()):
        sorted_results = sort_results_for_report(unit_results)

        # Filter out CLEAN if not requested
        if not show_clean:
            sorted_results = [r for r in sorted_results if r.flag != MatchFlag.CLEAN]

        if not sorted_results:
            continue

        # Unit header
        lines.append(f"\nUNIT: {unit}")
        lines.append("=" * 70)

        # Separate by flag type
        mismatches = [r for r in sorted_results if r.flag == MatchFlag.SKU_MISMATCH]
        orphans = [r for r in sorted_results if r.flag == MatchFlag.ORPHAN]
        clean = [r for r in sorted_results if r.flag == MatchFlag.CLEAN] if show_clean else []

        if mismatches:
            lines.append(f"\nSKU MISMATCHES ({len(mismatches)}) - Quick fixes, likely miscoded")
            lines.append("-" * 70)
            lines.append(f"{'INVENTORY SKU':<15} {'DESCRIPTION':<25} {'PRICE':>10} {'SUGGESTED SKU':<15}")
            lines.append("-" * 70)
            for r in mismatches:
                inv = r.inventory_item
                sugg = r.suggested_match
                price_str = f"${inv.price}" if inv.price else "N/A"
                sugg_str = f"{sugg.sku} ({sugg.description[:20]})" if sugg else ""
                lines.append(f"{inv.sku:<15} {inv.description[:25]:<25} {price_str:>10} -> {sugg_str}")

        if orphans:
            lines.append(f"\nORPHANS ({len(orphans)}) - Needs investigation")
            lines.append("-" * 70)
            lines.append(f"{'INVENTORY SKU':<15} {'DESCRIPTION':<25} {'PRICE':>10} {'REASON':<20}")
            lines.append("-" * 70)
            for r in orphans:
                inv = r.inventory_item
                price_str = f"${inv.price}" if inv.price else "N/A"
                reason_short = r.reason[:40] if r.reason else "Unknown"
                lines.append(f"{inv.sku:<15} {inv.description[:25]:<25} {price_str:>10} {reason_short}")

        if clean:
            lines.append(f"\nCLEAN ({len(clean)})")
            lines.append("-" * 70)
            for r in clean:
                inv = r.inventory_item
                lines.append(f"{inv.sku:<15} {inv.description[:40]}")

    # Summary
    summary = summarize_results(results)
    lines.append("\n" + "=" * 70)
    lines.append("SUMMARY")
    lines.append(f"  Total items:    {summary['total']}")
    lines.append(f"  Clean:          {summary['clean']}")
    lines.append(f"  SKU Mismatches: {summary['sku_mismatch']}")
    lines.append(f"  Orphans:        {summary['orphan']}")
    lines.append(f"  Actionable:     {summary['actionable']}")
    lines.append("=" * 70)

    return "\n".join(lines)


def export_csv(
    results: list[MatchResult],
    output: TextIO | None = None,
    include_clean: bool = True,
) -> str:
    """
    Export results to CSV format.

    Args:
        results: Match results to export
        output: Optional file handle to write to
        include_clean: Whether to include CLEAN items (default True)

    Returns:
        CSV string (also writes to output if provided)
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    # Header
    writer.writerow([
        "unit",
        "flag",
        "inventory_sku",
        "inventory_desc",
        "inventory_price",
        "inventory_vendor",
        "inventory_quantity",
        "suggested_sku",
        "suggested_desc",
        "suggested_price",
        "suggested_vendor",
        "reason",
    ])

    # Data rows
    for result in results:
        if not include_clean and result.flag == MatchFlag.CLEAN:
            continue

        inv = result.inventory_item
        sugg = result.suggested_match

        writer.writerow([
            inv.unit,
            result.flag.value,
            inv.sku,
            inv.description,
            str(inv.price) if inv.price else "",
            inv.vendor or "",
            str(inv.quantity),
            sugg.sku if sugg else "",
            sugg.description if sugg else "",
            str(sugg.price) if sugg else "",
            sugg.vendor if sugg else "",
            result.reason,
        ])

    csv_content = buffer.getvalue()

    if output:
        output.write(csv_content)

    return csv_content


def generate_report_filename(unit: str | None = None, extension: str = "csv") -> str:
    """
    Generate a filename for the report.

    Args:
        unit: Optional unit name to include
        extension: File extension (default "csv")

    Returns:
        Filename like "purchase_match_PSEG_HQ_2026-01-08.csv"
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    if unit:
        return f"purchase_match_{unit}_{date_str}.{extension}"
    return f"purchase_match_{date_str}.{extension}"
