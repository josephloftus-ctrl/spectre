"""
CLI entry point for Purchase Match Diagnostic.

Usage:
    python -m nebula.purchase_match --ips file1.xlsx file2.xlsx --unit PSEG_HQ
    python -m nebula.purchase_match --ips *.xlsx --unit PSEG_HQ --output-csv results.csv
"""

import argparse
import sys
from pathlib import Path

from .config import load_config
from .canon_loader import load_canon
from .index import build_index
from .adapters import MockInventoryAdapter
from .matcher import match_inventory
from .report import format_console, export_csv, generate_report_filename


def main():
    parser = argparse.ArgumentParser(
        prog="purchase_match",
        description="Purchase Match Diagnostic - Compare inventory against purchase history",
    )

    parser.add_argument(
        "--ips",
        nargs="+",
        required=True,
        metavar="FILE",
        help="OrderMaestro IPS export files (XLSX)",
    )

    parser.add_argument(
        "--unit",
        required=True,
        help="Unit to validate (e.g., PSEG_HQ)",
    )

    parser.add_argument(
        "--inventory",
        required=True,
        metavar="FILE",
        help="Inventory data file (CSV or JSON)",
    )

    parser.add_argument(
        "--config",
        default=None,
        metavar="FILE",
        help="Unit-vendor config file (default: module's unit_vendor_config.json)",
    )

    parser.add_argument(
        "--output-csv",
        metavar="FILE",
        help="Output CSV file path",
    )

    parser.add_argument(
        "--show-clean",
        action="store_true",
        help="Include CLEAN items in console output",
    )

    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress console output (only output CSV)",
    )

    args = parser.parse_args()

    # Resolve config path
    if args.config:
        config_path = Path(args.config)
    else:
        config_path = Path(__file__).parent / "unit_vendor_config.json"

    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    # Verify IPS files exist
    ips_files = []
    for pattern in args.ips:
        path = Path(pattern)
        if path.exists():
            ips_files.append(path)
        else:
            # Try glob expansion
            expanded = list(Path(".").glob(pattern))
            if expanded:
                ips_files.extend(expanded)
            else:
                print(f"Error: IPS file not found: {pattern}", file=sys.stderr)
                sys.exit(1)

    if not ips_files:
        print("Error: No IPS files found", file=sys.stderr)
        sys.exit(1)

    # Verify inventory file exists
    inventory_path = Path(args.inventory)
    if not inventory_path.exists():
        print(f"Error: Inventory file not found: {inventory_path}", file=sys.stderr)
        sys.exit(1)

    try:
        # Load configuration
        config = load_config(config_path)

        # Load and index purchase canon
        if not args.quiet:
            print(f"Loading {len(ips_files)} IPS file(s)...")
        records = load_canon(ips_files, config)
        index = build_index(records)
        if not args.quiet:
            print(f"Indexed {index.record_count} purchase records")

        # Load inventory
        if not args.quiet:
            print(f"Loading inventory from {inventory_path}...")
        adapter = MockInventoryAdapter(inventory_path)
        inventory = adapter.get_inventory_for_unit(args.unit)

        if not inventory:
            print(f"Warning: No inventory items found for unit {args.unit}", file=sys.stderr)
            sys.exit(0)

        if not args.quiet:
            print(f"Matching {len(inventory)} inventory items...")

        # Run matcher
        results = match_inventory(inventory, index, config)

        # Output console report
        if not args.quiet:
            report = format_console(results, show_clean=args.show_clean)
            print(report)

        # Output CSV if requested
        if args.output_csv:
            output_path = Path(args.output_csv)
            with open(output_path, "w", newline="") as f:
                export_csv(results, output=f)
            if not args.quiet:
                print(f"\nCSV exported to: {output_path}")

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
