import hashlib
import json
import re
import shutil
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import pdfplumber

NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

# -----------------
# Utility Functions
# -----------------

def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def slugify(text: str) -> str:
    if not text: return ""
    t = text.lower().strip()
    t = re.sub(r"[^a-z0-9\s_-]+", "", t)
    t = t.replace("-", "_")
    t = re.sub(r"\s+", "_", t)
    t = re.sub(r"_+", "_", t)
    return t[:40]

def date_from_filename_or_mtime(path: Path) -> datetime:
    name = path.stem
    m = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{2,4})", name)
    if m:
        mm, dd, yy = m.groups()
        if len(yy) == 2: yy = "20" + yy
        try:
            return datetime(int(yy), int(mm), int(dd))
        except ValueError:
            pass
    return datetime.fromtimestamp(path.stat().st_mtime)

def norm_item(text: str) -> str:
    if not text: return ""
    t = text.lower().strip()
    t = re.sub(r"[^a-z0-9\s]+", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t

def to_float(val):
    if val == "" or val is None: return None
    if isinstance(val, (int, float)): return float(val)
    try:
        cleaned = str(val).replace(",", "").replace("$", "")
        return float(cleaned)
    except Exception:
        return None

# -----------------
# Excel Parsing
# -----------------

def col_index(cell_ref):
    col = ""
    for ch in cell_ref:
        if ch.isalpha(): col += ch
        else: break
    idx = 0
    for c in col:
        idx = idx * 26 + (ord(c.upper()) - 64)
    return idx

def read_shared_strings(zf):
    try:
        data = zf.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    root = ET.fromstring(data)
    strings = []
    for si in root.findall(f"{{{NS_MAIN}}}si"):
        texts = [t.text or "" for t in si.findall(f".//{{{NS_MAIN}}}t")]
        strings.append("".join(texts))
    return strings

def read_workbook_sheets(zf):
    wb = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    id_to_target = {}
    for rel in rels.findall(f"{{{REL_NS}}}Relationship"):
        id_to_target[rel.attrib["Id"]] = rel.attrib["Target"]
    sheets = []
    for sh in wb.findall(f"{{{NS_MAIN}}}sheets/{{{NS_MAIN}}}sheet"):
        name = sh.attrib.get("name")
        rid = sh.attrib.get(f"{{{REL_NS}}}id") # Note: slight simplification from original namespace usage
        if not rid: rid = sh.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            
        target = id_to_target.get(rid, "")
        if target and not target.startswith("xl/"): target = "xl/" + target
        sheets.append((name, target))
    return sheets

def get_cell_value(c, shared_strings):
    ctype = c.attrib.get("t")
    v = c.find(f"{{{NS_MAIN}}}v")
    if v is None and ctype == "inlineStr":
        t = c.find(f"{{{NS_MAIN}}}is/{{{NS_MAIN}}}t")
        val = (t.text or "") if t is not None else ""
    elif v is None:
        val = ""
    else:
        val = v.text or ""
        if ctype == "s":
            try: val = shared_strings[int(val)]
            except: pass
    if isinstance(val, str): val = val.strip()
    return val

def parse_data_sheet(zf, sheet_path, shared_strings):
    data = zf.read(sheet_path)
    root = ET.fromstring(data)
    sheet_data = root.find(f"{{{NS_MAIN}}}sheetData")
    if sheet_data is None: return None
    rows = list(sheet_data.findall(f"{{{NS_MAIN}}}row"))
    
    header_row_idx = None
    for row in rows:
        r_idx = int(row.attrib.get("r", "0"))
        values = []
        str_count = 0
        num_count = 0
        for c in row.findall(f"{{{NS_MAIN}}}c"):
            val = get_cell_value(c, shared_strings)
            if val != "":
                values.append(val)
                if isinstance(val, str) and not val.replace(".", "", 1).isdigit():
                    str_count += 1
                else:
                    num_count += 1
        if len(values) >= 3 and str_count >= num_count:
            header_row_idx = r_idx
            break
            
    if header_row_idx is None: return None
    
    headers = {}
    data_rows = []
    for row in rows:
        r_idx = int(row.attrib.get("r", "0"))
        row_cells = {}
        for c in row.findall(f"{{{NS_MAIN}}}c"):
            cref = c.attrib.get("r")
            if not cref: continue
            val = get_cell_value(c, shared_strings)
            row_cells[col_index(cref)] = val
            
        if r_idx == header_row_idx:
            for idx, val in row_cells.items():
                if isinstance(val, str) and val: headers[idx] = val
        elif r_idx > header_row_idx:
            if row_cells: data_rows.append(row_cells)
            
    return headers, data_rows

# -----------------
# Core Logic
# -----------------

def collect_site_metrics(site_dir: Path):
    files = sorted(site_dir.rglob("*.xlsx"))
    header_keywords = {
        "last inventory qty": ["last inventory qty", "last inv", "last count"],
        "inv count": ["inv count", "inventory count", "count"],
        "price type": ["price type", "pricing basis", "valuation basis"],
        "grouped by": ["grouped by"],
        "sales amount": ["sales amount", "sales", "revenue"],
        "generated date": ["generated date", "run date"],
        "generated by": ["generated by", "run by", "user"],
        "close inventory confirmation": ["close inventory confirmation", "close inventory"],
        "initial inventory": ["initial inventory", "beginning inventory"],
        "ending inventory": ["ending inventory", "end inventory"],
    }

    header_presence = defaultdict(set)
    file_summaries = []
    item_series = defaultdict(dict)

    for p in files:
        try:
            with zipfile.ZipFile(p, "r") as zf:
                shared = read_shared_strings(zf)
                sheets = read_workbook_sheets(zf)
                
                # Check for headers in first few rows of any sheet
                for name, target in sheets:
                    try: data = zf.read(target)
                    except: continue
                    root_xml = ET.fromstring(data)
                    sheet_data = root_xml.find(f"{{{NS_MAIN}}}sheetData")
                    if sheet_data is None: continue
                    rows = sheet_data.findall(f"{{{NS_MAIN}}}row")[:15]
                    for row in rows:
                        for c in row.findall(f"{{{NS_MAIN}}}c"):
                            val = get_cell_value(c, shared)
                            if not isinstance(val, str) or not val: continue
                            low = val.lower().strip()
                            for key, terms in header_keywords.items():
                                if any(t in low for t in terms):
                                    header_presence[key].add(str(p.relative_to(site_dir)))

                data_sheet = next((s for s in sheets if s[0].startswith("Data for ")), None)
                if not data_sheet: continue
                parsed = parse_data_sheet(zf, data_sheet[1], shared)
                if not parsed: continue
                headers, data_rows = parsed
        except Exception:
            # logging.error(f"Failed to parse {p}")
            continue

        header_lookup = {v.strip(): k for k, v in headers.items()}
        idx_item = header_lookup.get("Item Description")
        idx_qty = header_lookup.get("Quantity")
        idx_total = header_lookup.get("Total Price")

        totals = []
        for row in data_rows:
            item = row.get(idx_item, "") if idx_item else ""
            item_key = norm_item(item)
            qty = to_float(row.get(idx_qty)) if idx_qty else None
            total = to_float(row.get(idx_total)) if idx_total else None

            if total is not None: totals.append(total)

            if item_key:
                entry = item_series[item_key].setdefault(str(p.relative_to(site_dir)), {
                    "item": item,
                    "qty_sum": 0.0,
                    "total_sum": 0.0,
                })
                if qty is not None: entry["qty_sum"] += qty
                if total is not None: entry["total_sum"] += total

        file_summaries.append({
            "path": str(p.relative_to(site_dir)),
            "total_sum": sum(totals) if totals else 0.0,
            "mtime": p.stat().st_mtime,
        })

    # Calculate Drifts
    ordered_paths = [f["path"] for f in sorted(file_summaries, key=lambda x: x["mtime"])]
    qty_drifts = []
    total_drifts = []

    for item_key, per_file in item_series.items():
        for i in range(1, len(ordered_paths)):
            prev_path = ordered_paths[i - 1]
            curr_path = ordered_paths[i]
            if prev_path in per_file and curr_path in per_file:
                prev = per_file[prev_path]
                curr = per_file[curr_path]
                
                # Qty Drift
                if prev["qty_sum"] and curr["qty_sum"]:
                    ratio = curr["qty_sum"] / prev["qty_sum"]
                    if (ratio > 2 or ratio < 0.5) and abs(curr["qty_sum"] - prev["qty_sum"]) > 10:
                        qty_drifts.append({
                            "item": curr["item"],
                            "prev": prev_path, "curr": curr_path,
                            "prev_qty": prev["qty_sum"], "curr_qty": curr["qty_sum"],
                            "ratio": ratio
                        })
                # Value Drift
                if prev["total_sum"] and curr["total_sum"]:
                    ratio = curr["total_sum"] / prev["total_sum"]
                    if (ratio > 2 or ratio < 0.5) and abs(curr["total_sum"] - prev["total_sum"]) > 500:
                        total_drifts.append({
                            "item": curr["item"],
                            "prev": prev_path, "curr": curr_path,
                            "prev_total": prev["total_sum"], "curr_total": curr["total_sum"],
                            "ratio": ratio
                        })

    qty_drifts.sort(key=lambda x: abs(x["curr_qty"] - x["prev_qty"]), reverse=True)
    total_drifts.sort(key=lambda x: abs(x["curr_total"] - x["prev_total"]), reverse=True)

    # Latest Stats
    if file_summaries:
        latest = max(file_summaries, key=lambda x: x["mtime"])
        latest_total = latest["total_sum"]
        latest_date = datetime.fromtimestamp(latest["mtime"]).strftime("%Y-%m-%d")
        
        prev_files = sorted([f for f in file_summaries if f["path"] != latest["path"]], key=lambda x: x["mtime"])
        prev_total = prev_files[-1]["total_sum"] if prev_files else 0.0
        delta_pct = ((latest_total - prev_total) / prev_total * 100) if prev_total else 0.0
    else:
        latest_total = 0.0
        delta_pct = 0.0
        latest_date = datetime.now().strftime("%Y-%m-%d")

    missing_fields = [k for k in header_keywords.keys() if not header_presence.get(k)]
    
    return {
        "file_summaries": file_summaries,
        "qty_drifts": qty_drifts,
        "total_drifts": total_drifts,
        "latest_total": latest_total,
        "delta_pct": delta_pct,
        "latest_date": latest_date,
        "missing_fields": missing_fields,
    }


def extract_site_from_sheet(zf, sheet_path, shared_strings) -> str:
    """
    Extract site name from early rows of a sheet.
    Looks for site name patterns in rows 1-5.

    Examples:
        "PSEG - NHQ (673) (COMPASS)" -> "pseg_nhq"
        "Lockhead Martin, Bldg 100 (COMPASS)" -> "lockhead_martin_bldg_100"
    """
    try:
        data = zf.read(sheet_path)
        root = ET.fromstring(data)
        sheet_data = root.find(f"{{{NS_MAIN}}}sheetData")
        if sheet_data is None:
            return None

        # Check first 5 rows for site name
        rows = sheet_data.findall(f"{{{NS_MAIN}}}row")[:5]
        for row in rows:
            for c in row.findall(f"{{{NS_MAIN}}}c"):
                val = get_cell_value(c, shared_strings)
                if not isinstance(val, str) or not val:
                    continue

                # Skip generic headers
                val_lower = val.lower()
                if "inventory" in val_lower or "report" in val_lower:
                    continue
                if "property" in val_lower or "proprietary" in val_lower:
                    continue
                if "current" in val_lower or "preferred" in val_lower:
                    continue
                if "printed by" in val_lower:
                    continue

                # Match pattern with (COMPASS) at end - extract everything before it
                # e.g. "Lockhead Martin, Bldg 100 (COMPASS)" or "PSEG - NHQ (673) (COMPASS)"
                match = re.match(r'^(.+?)\s*\(COMPASS\)\s*$', val, re.IGNORECASE)
                if match:
                    site_name = match.group(1).strip()
                    # Remove trailing (number) if present
                    site_name = re.sub(r'\s*\(\d+\)\s*$', '', site_name)
                    site_id = slugify(site_name)
                    if site_id and len(site_id) >= 2:
                        return site_id

                # Also try pattern with just (number) - e.g. "PSEG - NHQ (673)"
                match = re.match(r'^([A-Za-z0-9\s\-,]+)\s*\(\d+\)', val)
                if match:
                    site_name = match.group(1).strip()
                    site_id = slugify(site_name)
                    if site_id and len(site_id) >= 2:
                        return site_id
    except Exception:
        pass
    return None


def parse_excel_file(file_path: str) -> dict:
    """
    Parse an Excel file and return structured data for embedding.

    Returns:
        dict with 'headers', 'rows', 'metadata'
    """
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if p.suffix.lower() not in ('.xlsx', '.xls'):
        raise ValueError(f"Unsupported file type: {p.suffix}")

    result = {
        "headers": [],
        "rows": [],
        "metadata": {
            "filename": p.name,
            "file_size": p.stat().st_size,
            "parsed_at": datetime.now().isoformat()
        }
    }

    try:
        with zipfile.ZipFile(p, "r") as zf:
            shared = read_shared_strings(zf)
            sheets = read_workbook_sheets(zf)

            # Try to find a data sheet
            data_sheet = None
            for name, target in sheets:
                if name.lower().startswith("data"):
                    data_sheet = (name, target)
                    break

            # Fall back to first sheet
            if not data_sheet and sheets:
                data_sheet = sheets[0]

            if not data_sheet:
                return result

            # Extract site name from the data sheet header rows
            site_id = extract_site_from_sheet(zf, data_sheet[1], shared)
            if site_id:
                result["metadata"]["site_id"] = site_id

            parsed = parse_data_sheet(zf, data_sheet[1], shared)
            if not parsed:
                return result

            headers_dict, data_rows = parsed

            # Convert headers to list
            max_col = max(headers_dict.keys()) if headers_dict else 0
            headers = []
            for i in range(1, max_col + 1):
                headers.append(headers_dict.get(i, f"Column_{i}"))
            result["headers"] = headers

            # Convert rows to list of dicts
            for row_data in data_rows:
                row = {}
                for col_idx, value in row_data.items():
                    header = headers_dict.get(col_idx, f"Column_{col_idx}")
                    row[header] = value
                if row:  # Skip empty rows
                    result["rows"].append(row)

            result["metadata"]["sheet_name"] = data_sheet[0]
            result["metadata"]["row_count"] = len(result["rows"])
            result["metadata"]["column_count"] = len(headers)

    except zipfile.BadZipFile:
        raise ValueError(f"Invalid Excel file: {file_path}")
    except Exception as e:
        raise ValueError(f"Failed to parse file: {str(e)}")

    return result


def parse_csv_file(file_path: str) -> dict:
    """
    Parse a CSV file and return structured data for embedding.
    """
    import csv

    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    result = {
        "headers": [],
        "rows": [],
        "metadata": {
            "filename": p.name,
            "file_size": p.stat().st_size,
            "parsed_at": datetime.now().isoformat()
        }
    }

    try:
        with open(p, 'r', newline='', encoding='utf-8-sig') as f:
            # Try to detect delimiter
            sample = f.read(4096)
            f.seek(0)

            try:
                dialect = csv.Sniffer().sniff(sample)
            except csv.Error:
                dialect = csv.excel

            reader = csv.DictReader(f, dialect=dialect)
            result["headers"] = reader.fieldnames or []

            for row in reader:
                result["rows"].append(dict(row))

            result["metadata"]["row_count"] = len(result["rows"])
            result["metadata"]["column_count"] = len(result["headers"])

    except Exception as e:
        raise ValueError(f"Failed to parse CSV: {str(e)}")

    return result


def parse_pdf_file(file_path: str) -> dict:
    """
    Parse a PDF file and return structured data for embedding.
    Extracts both text content and tables from all pages.

    Returns:
        dict with 'headers', 'rows', 'metadata', 'text_content'
    """
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if p.suffix.lower() != '.pdf':
        raise ValueError(f"Unsupported file type: {p.suffix}")

    result = {
        "headers": [],
        "rows": [],
        "text_content": [],
        "metadata": {
            "filename": p.name,
            "file_size": p.stat().st_size,
            "parsed_at": datetime.now().isoformat(),
            "file_type": "pdf"
        }
    }

    try:
        with pdfplumber.open(p) as pdf:
            result["metadata"]["page_count"] = len(pdf.pages)
            all_tables = []
            all_text = []

            for page_num, page in enumerate(pdf.pages, 1):
                # Extract text from the page
                text = page.extract_text()
                if text:
                    all_text.append({
                        "page": page_num,
                        "content": text.strip()
                    })

                # Extract tables from the page
                tables = page.extract_tables()
                for table_idx, table in enumerate(tables):
                    if not table or len(table) < 2:
                        continue

                    # First row is typically headers
                    headers = [str(cell).strip() if cell else f"Column_{i}"
                              for i, cell in enumerate(table[0])]

                    # Track headers (use first table's headers as primary)
                    if not result["headers"]:
                        result["headers"] = headers

                    # Convert remaining rows to dicts
                    for row in table[1:]:
                        if not row or all(cell is None or str(cell).strip() == "" for cell in row):
                            continue
                        row_dict = {}
                        for i, cell in enumerate(row):
                            header = headers[i] if i < len(headers) else f"Column_{i}"
                            row_dict[header] = str(cell).strip() if cell else ""
                        result["rows"].append(row_dict)

            result["text_content"] = all_text
            result["metadata"]["row_count"] = len(result["rows"])
            result["metadata"]["column_count"] = len(result["headers"])
            result["metadata"]["text_blocks"] = len(all_text)

    except Exception as e:
        raise ValueError(f"Failed to parse PDF: {str(e)}")

    return result


def parse_file(file_path: str) -> dict:
    """
    Universal file parser - routes to appropriate parser based on file type.

    Returns:
        dict with 'headers', 'rows', 'metadata' (and 'text_content' for PDFs)
    """
    p = Path(file_path)
    suffix = p.suffix.lower()

    if suffix in ('.xlsx', '.xls'):
        return parse_excel_file(file_path)
    elif suffix == '.csv':
        return parse_csv_file(file_path)
    elif suffix == '.pdf':
        return parse_pdf_file(file_path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")
