"""
XLSX Export Module - OrderMaestro Compatible Exports

Generates Excel files in OrderMaestro-compatible format for:
- Inventory counts
- Shopping carts
- Modified inventory data

OrderMaestro Format:
- Header rows start around row 8-9
- Key columns: Item Description, Dist #, Quantity, UOM, Unit Price, Total Price, GL Codes
- Site info in early rows
"""

from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


# OrderMaestro standard columns (in order)
ORDERMAESTRO_COLUMNS = [
    "Dist #",           # SKU / Item number
    "Item Description",
    "Quantity",
    "UOM",
    "Unit Price",
    "Total Price",
    "GL Codes",
]

# Shopping cart export columns
CART_COLUMNS = [
    "Dist #",
    "Item Description",
    "Order Qty",
    "UOM",
    "Unit Price",
    "Extended Price",
    "Vendor",
    "Notes",
]

# Styles
HEADER_FONT = Font(bold=True, size=11)
HEADER_FILL = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
HEADER_ALIGNMENT = Alignment(horizontal="center", vertical="center", wrap_text=True)
THIN_BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin")
)
CURRENCY_FORMAT = '"$"#,##0.00'
NUMBER_FORMAT = '#,##0.00'


def create_ordermaestro_workbook(
    site_name: str,
    items: List[Dict[str, Any]],
    title: str = "Inventory Valuation",
    include_totals: bool = True
) -> BytesIO:
    """
    Create an OrderMaestro-compatible inventory workbook.

    Args:
        site_name: Name of the site (e.g., "PSEG NHQ")
        items: List of inventory items with keys: sku, description, quantity, uom, unit_price, total_price, location
        title: Report title
        include_totals: Whether to include a totals row

    Returns:
        BytesIO buffer containing the Excel file
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Data for {site_name[:28]}"  # Sheet name max 31 chars

    # Row 1-2: Report header
    ws.merge_cells('A1:G1')
    ws['A1'] = title
    ws['A1'].font = Font(bold=True, size=14)
    ws['A1'].alignment = Alignment(horizontal="center")

    # Row 3: Site name with (COMPASS) suffix for compatibility
    ws.merge_cells('A3:G3')
    ws['A3'] = f"{site_name} (COMPASS)"
    ws['A3'].font = Font(bold=True, size=12)
    ws['A3'].alignment = Alignment(horizontal="center")

    # Row 4: Generated date
    ws.merge_cells('A4:G4')
    ws['A4'] = f"Generated: {datetime.now().strftime('%m/%d/%Y %I:%M %p')}"
    ws['A4'].font = Font(size=10, italic=True)
    ws['A4'].alignment = Alignment(horizontal="center")

    # Row 6: Empty row

    # Row 8: Headers (OrderMaestro typically has headers around row 8-9)
    header_row = 8
    for col_idx, header in enumerate(ORDERMAESTRO_COLUMNS, 1):
        cell = ws.cell(row=header_row, column=col_idx, value=header)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = HEADER_ALIGNMENT
        cell.border = THIN_BORDER

    # Data rows
    current_row = header_row + 1
    total_value = 0.0

    for item in items:
        sku = item.get("sku", "")
        description = item.get("description", "")
        quantity = item.get("quantity", 0)
        uom = item.get("uom", "EA")
        unit_price = item.get("unit_price") or 0
        total_price = item.get("total_price")
        location = item.get("location", "")

        # Calculate total if not provided
        if total_price is None:
            total_price = quantity * unit_price

        total_value += total_price

        # Format location as GL Code
        gl_code = location
        if location and "->" not in location:
            gl_code = f"Locations->{location}"

        row_data = [sku, description, quantity, uom, unit_price, total_price, gl_code]

        for col_idx, value in enumerate(row_data, 1):
            cell = ws.cell(row=current_row, column=col_idx, value=value)
            cell.border = THIN_BORDER

            # Format currency columns
            if col_idx in (5, 6):  # Unit Price, Total Price
                cell.number_format = CURRENCY_FORMAT
            elif col_idx == 3:  # Quantity
                cell.number_format = NUMBER_FORMAT

        current_row += 1

    # Totals row
    if include_totals:
        current_row += 1  # Blank row
        ws.cell(row=current_row, column=1, value="TOTAL").font = Font(bold=True)
        ws.cell(row=current_row, column=3, value=sum(i.get("quantity", 0) for i in items)).number_format = NUMBER_FORMAT
        total_cell = ws.cell(row=current_row, column=6, value=total_value)
        total_cell.number_format = CURRENCY_FORMAT
        total_cell.font = Font(bold=True)

    # Adjust column widths
    column_widths = [15, 45, 12, 8, 12, 14, 35]
    for col_idx, width in enumerate(column_widths, 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    # Save to buffer
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def create_cart_workbook(
    site_name: str,
    items: List[Dict[str, Any]],
    title: str = "Shopping Cart / Order Form"
) -> BytesIO:
    """
    Create a shopping cart export workbook.

    Args:
        site_name: Name of the site
        items: List of cart items with keys: sku, description, quantity, uom, unit_price, vendor, notes

    Returns:
        BytesIO buffer containing the Excel file
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Cart"

    # Header section
    ws.merge_cells('A1:H1')
    ws['A1'] = title
    ws['A1'].font = Font(bold=True, size=14)
    ws['A1'].alignment = Alignment(horizontal="center")

    ws.merge_cells('A3:H3')
    ws['A3'] = f"Site: {site_name}"
    ws['A3'].font = Font(bold=True, size=12)

    ws.merge_cells('A4:H4')
    ws['A4'] = f"Date: {datetime.now().strftime('%m/%d/%Y')}"
    ws['A4'].font = Font(size=10)

    # Column headers
    header_row = 6
    for col_idx, header in enumerate(CART_COLUMNS, 1):
        cell = ws.cell(row=header_row, column=col_idx, value=header)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = HEADER_ALIGNMENT
        cell.border = THIN_BORDER

    # Data rows
    current_row = header_row + 1
    total_value = 0.0

    for item in items:
        sku = item.get("sku", "")
        description = item.get("description", "")
        quantity = item.get("quantity", 1)
        uom = item.get("uom", "EA")
        unit_price = item.get("unit_price") or 0
        extended = quantity * unit_price
        vendor = item.get("vendor", "")
        notes = item.get("notes", "")

        total_value += extended

        row_data = [sku, description, quantity, uom, unit_price, extended, vendor, notes]

        for col_idx, value in enumerate(row_data, 1):
            cell = ws.cell(row=current_row, column=col_idx, value=value)
            cell.border = THIN_BORDER

            if col_idx in (5, 6):  # Unit Price, Extended
                cell.number_format = CURRENCY_FORMAT
            elif col_idx == 3:  # Quantity
                cell.number_format = NUMBER_FORMAT

        current_row += 1

    # Totals
    current_row += 1
    ws.cell(row=current_row, column=1, value="TOTAL").font = Font(bold=True)
    ws.cell(row=current_row, column=3, value=len(items)).font = Font(bold=True)
    total_cell = ws.cell(row=current_row, column=6, value=total_value)
    total_cell.number_format = CURRENCY_FORMAT
    total_cell.font = Font(bold=True)

    # Column widths
    column_widths = [15, 40, 10, 8, 12, 14, 15, 30]
    for col_idx, width in enumerate(column_widths, 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def create_count_sheet_workbook(
    site_name: str,
    items: List[Dict[str, Any]],
    session_name: Optional[str] = None,
    include_variances: bool = False
) -> BytesIO:
    """
    Create a count sheet export workbook.

    Args:
        site_name: Name of the site
        items: List of count items with keys: sku, description, counted_qty, expected_qty, uom, unit_price, location
        session_name: Optional name for the count session
        include_variances: Whether to include variance columns

    Returns:
        BytesIO buffer containing the Excel file
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Data for {site_name[:28]}"

    # Define columns based on variance flag
    if include_variances:
        columns = ["Dist #", "Item Description", "Expected Qty", "Counted Qty", "Variance", "UOM", "Unit Price", "Total Value", "GL Codes"]
    else:
        columns = ORDERMAESTRO_COLUMNS

    # Header section
    ws.merge_cells(f'A1:{get_column_letter(len(columns))}1')
    title = session_name or f"Inventory Count - {datetime.now().strftime('%m/%d/%Y')}"
    ws['A1'] = title
    ws['A1'].font = Font(bold=True, size=14)
    ws['A1'].alignment = Alignment(horizontal="center")

    ws.merge_cells(f'A3:{get_column_letter(len(columns))}3')
    ws['A3'] = f"{site_name} (COMPASS)"
    ws['A3'].font = Font(bold=True, size=12)
    ws['A3'].alignment = Alignment(horizontal="center")

    ws.merge_cells(f'A4:{get_column_letter(len(columns))}4')
    ws['A4'] = f"Generated: {datetime.now().strftime('%m/%d/%Y %I:%M %p')}"
    ws['A4'].font = Font(size=10, italic=True)
    ws['A4'].alignment = Alignment(horizontal="center")

    # Column headers
    header_row = 8
    for col_idx, header in enumerate(columns, 1):
        cell = ws.cell(row=header_row, column=col_idx, value=header)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = HEADER_ALIGNMENT
        cell.border = THIN_BORDER

    # Data rows
    current_row = header_row + 1
    total_value = 0.0
    total_variance = 0.0

    # Group items by location for easier counting
    items_sorted = sorted(items, key=lambda x: (x.get("location", ""), x.get("sku", "")))

    for item in items_sorted:
        sku = item.get("sku", "")
        description = item.get("description", "")
        counted_qty = item.get("counted_qty", 0)
        expected_qty = item.get("expected_qty")
        uom = item.get("uom", "EA")
        unit_price = item.get("unit_price") or 0
        location = item.get("location", "")

        item_value = counted_qty * unit_price
        total_value += item_value

        gl_code = location
        if location and "->" not in location:
            gl_code = f"Locations->{location}"

        if include_variances:
            variance = (counted_qty - expected_qty) if expected_qty is not None else 0
            total_variance += variance * unit_price
            row_data = [sku, description, expected_qty or "", counted_qty, variance if expected_qty else "", uom, unit_price, item_value, gl_code]
        else:
            row_data = [sku, description, counted_qty, uom, unit_price, item_value, gl_code]

        for col_idx, value in enumerate(row_data, 1):
            cell = ws.cell(row=current_row, column=col_idx, value=value)
            cell.border = THIN_BORDER

            # Currency formatting
            if include_variances:
                if col_idx in (7, 8):
                    cell.number_format = CURRENCY_FORMAT
                elif col_idx in (3, 4, 5):
                    cell.number_format = NUMBER_FORMAT
                    # Highlight variances
                    if col_idx == 5 and isinstance(value, (int, float)) and value != 0:
                        if value > 0:
                            cell.fill = PatternFill(start_color="E6F3E6", end_color="E6F3E6", fill_type="solid")
                        else:
                            cell.fill = PatternFill(start_color="F3E6E6", end_color="F3E6E6", fill_type="solid")
            else:
                if col_idx in (5, 6):
                    cell.number_format = CURRENCY_FORMAT
                elif col_idx == 3:
                    cell.number_format = NUMBER_FORMAT

        current_row += 1

    # Totals row
    current_row += 1
    ws.cell(row=current_row, column=1, value="TOTAL").font = Font(bold=True)

    if include_variances:
        ws.cell(row=current_row, column=4, value=sum(i.get("counted_qty", 0) for i in items)).number_format = NUMBER_FORMAT
        ws.cell(row=current_row, column=5, value=total_variance).number_format = CURRENCY_FORMAT
        total_cell = ws.cell(row=current_row, column=8, value=total_value)
    else:
        ws.cell(row=current_row, column=3, value=sum(i.get("counted_qty", 0) for i in items)).number_format = NUMBER_FORMAT
        total_cell = ws.cell(row=current_row, column=6, value=total_value)

    total_cell.number_format = CURRENCY_FORMAT
    total_cell.font = Font(bold=True)

    # Column widths
    if include_variances:
        column_widths = [15, 40, 12, 12, 12, 8, 12, 14, 35]
    else:
        column_widths = [15, 45, 12, 8, 12, 14, 35]

    for col_idx, width in enumerate(column_widths, 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def create_modified_inventory_workbook(
    site_name: str,
    items: List[Dict[str, Any]],
    modifications: List[Dict[str, Any]],
    title: str = "Modified Inventory"
) -> BytesIO:
    """
    Create an inventory export with AI-assisted modifications applied.

    Args:
        site_name: Name of the site
        items: Original inventory items
        modifications: List of modifications to apply (sku, field_name, old_value, new_value)
        title: Report title

    Returns:
        BytesIO buffer containing the Excel file
    """
    # Apply modifications to items
    modified_items = []
    mod_lookup = {}

    # Build lookup for modifications by SKU
    for mod in modifications:
        sku = mod.get("sku", "")
        if sku not in mod_lookup:
            mod_lookup[sku] = []
        mod_lookup[sku].append(mod)

    # Apply modifications
    for item in items:
        modified_item = dict(item)
        sku = item.get("sku", "")

        if sku in mod_lookup:
            for mod in mod_lookup[sku]:
                field = mod.get("field_name", "")
                new_value = mod.get("new_value")

                if field == "sku":
                    modified_item["sku"] = new_value
                elif field == "description":
                    modified_item["description"] = new_value
                elif field == "quantity":
                    try:
                        modified_item["quantity"] = float(new_value)
                    except (ValueError, TypeError):
                        pass
                elif field == "uom":
                    modified_item["uom"] = new_value
                elif field == "unit_price":
                    try:
                        modified_item["unit_price"] = float(new_value)
                    except (ValueError, TypeError):
                        pass

        modified_items.append(modified_item)

    # Use the standard OrderMaestro format
    return create_ordermaestro_workbook(
        site_name=site_name,
        items=modified_items,
        title=title,
        include_totals=True
    )


def export_inventory_from_db(site_id: str, include_modifications: bool = False) -> BytesIO:
    """
    Export inventory data from database for a site.

    Args:
        site_id: Site identifier
        include_modifications: Whether to apply pending modifications

    Returns:
        BytesIO buffer containing the Excel file
    """
    from backend.core.database import (
        get_site_display_name, get_unit_score, list_inventory_modifications
    )

    site_name = get_site_display_name(site_id)
    score_data = get_unit_score(site_id)

    if not score_data:
        # Return empty workbook
        return create_ordermaestro_workbook(
            site_name=site_name,
            items=[],
            title="Inventory Export (No Data)"
        )

    # The flagged items contain the issue items, but we need full inventory
    # For now, use the flagged items as a sample
    items = []
    for flagged in score_data.get("flagged_items", []):
        items.append({
            "sku": "",  # SKU not stored in flags
            "description": flagged.get("item", ""),
            "quantity": flagged.get("qty", 0),
            "uom": flagged.get("uom", ""),
            "unit_price": 0,
            "total_price": flagged.get("total", 0),
            "location": flagged.get("location", "")
        })

    if include_modifications:
        modifications = list_inventory_modifications(site_id, applied=False)
        return create_modified_inventory_workbook(
            site_name=site_name,
            items=items,
            modifications=modifications,
            title=f"Modified Inventory - {site_name}"
        )

    return create_ordermaestro_workbook(
        site_name=site_name,
        items=items,
        title=f"Inventory Valuation - {site_name}"
    )


def export_cart_from_db(site_id: str) -> BytesIO:
    """
    Export shopping cart data from database for a site.

    Args:
        site_id: Site identifier

    Returns:
        BytesIO buffer containing the Excel file
    """
    from backend.core.database import get_site_display_name, list_cart_items

    site_name = get_site_display_name(site_id)
    cart_items = list_cart_items(site_id)

    return create_cart_workbook(
        site_name=site_name,
        items=cart_items,
        title=f"Order Form - {site_name}"
    )


def export_count_session_from_db(session_id: str) -> BytesIO:
    """
    Export a count session from database.

    Args:
        session_id: Count session identifier

    Returns:
        BytesIO buffer containing the Excel file
    """
    from backend.core.database import (
        get_count_session, get_site_display_name, list_count_items
    )

    session = get_count_session(session_id)
    if not session:
        raise ValueError(f"Count session not found: {session_id}")

    site_name = get_site_display_name(session["site_id"])
    items = list_count_items(session_id)

    # Check if we have expected quantities for variance calculation
    has_expected = any(item.get("expected_qty") is not None for item in items)

    return create_count_sheet_workbook(
        site_name=site_name,
        items=items,
        session_name=session.get("name"),
        include_variances=has_expected
    )
