#!/usr/bin/env python3
import hashlib
import json
import math
import re
import shutil
import sys
import time
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

# New imports
import argparse
import threading
import logging
from http.server import HTTPServer, SimpleHTTPRequestHandler



NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def sha256_path(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def slugify(text):
    t = text.lower().strip()
    t = re.sub(r"[^a-z0-9\s_-]+", "", t)
    t = t.replace("-", "_")
    t = re.sub(r"\s+", "_", t)
    t = re.sub(r"_+", "_", t)
    return t[:40] if len(t) > 40 else t


def date_from_filename_or_mtime(path):
    name = path.stem
    m = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{2,4})", name)
    if m:
        mm, dd, yy = m.groups()
        if len(yy) == 2:
            yy = "20" + yy
        try:
            return datetime(int(yy), int(mm), int(dd))
        except ValueError:
            pass
    return datetime.fromtimestamp(path.stat().st_mtime)


def load_site_aliases(root_dir):
    alias_path = root_dir / "config" / "site_aliases.json"
    if not alias_path.exists():
        return {}
    try:
        data = json.loads(alias_path.read_text())
    except Exception:
        return {}
    normalized = {}
    for k, v in data.items():
        if isinstance(k, str) and isinstance(v, str):
            normalized[k.lower().strip()] = slugify(v)
    return normalized


def tokenize(text):
    return [t for t in re.split(r"[^a-z0-9]+", text.lower()) if t]


def detect_site(path, existing_sites, alias_map):
    name = path.stem.lower()
    for alias, canonical in alias_map.items():
        if alias in name:
            return canonical
    name_tokens = tokenize(name)
    best = None
    best_score = 0
    for site in existing_sites:
        site_tokens = site.split("_")
        score = sum(1 for t in site_tokens if t in name_tokens)
        if score > best_score:
            best = site
            best_score = score
    if best_score >= 2:
        return best
    alpha_tokens = [t for t in name_tokens if t.isalpha()]
    if len(alpha_tokens) >= 2:
        return f"{alpha_tokens[0]}_{alpha_tokens[1]}"
    if len(alpha_tokens) == 1:
        return alpha_tokens[0]
    return "unspecified_site"


def build_target(path, sorted_root, site):
    dt = date_from_filename_or_mtime(path)
    yyyy_mm = dt.strftime("%Y-%m")
    yyyy_mm_dd = dt.strftime("%Y-%m-%d")
    doc_type = "exports"
    source = "unknown"
    descriptor = slugify(path.stem)
    dest_dir = sorted_root / site / yyyy_mm / doc_type
    dest_dir.mkdir(parents=True, exist_ok=True)
    base = f"{yyyy_mm_dd}_{site}_{doc_type}_{source}_{descriptor}_v"
    ext = path.suffix.lower()
    version = 1
    while True:
        candidate = dest_dir / f"{base}{version}{ext}"
        if not candidate.exists():
            return candidate
        if sha256_path(candidate) == sha256_path(path):
            return None
        version += 1


def dedupe_sorted(sorted_root, archive_dups):
    archive_dups.mkdir(parents=True, exist_ok=True)
    files = sorted(sorted_root.rglob("*.xlsx"))
    hash_groups = defaultdict(list)
    for p in files:
        hash_groups[sha256_path(p)].append(p)
    moved = []
    for items in hash_groups.values():
        if len(items) <= 1:
            continue
        items_sorted = sorted(items)
        for dup in items_sorted[1:]:
            target = archive_dups / dup.name
            if target.exists():
                base = dup.stem
                ext = dup.suffix
                i = 2
                while True:
                    alt = archive_dups / f"{base}_dup{i}{ext}"
                    if not alt.exists():
                        target = alt
                        break
                    i += 1
            shutil.move(str(dup), str(target))
            moved.append((dup, target))
    return moved


def col_index(cell_ref):
    col = ""
    for ch in cell_ref:
        if ch.isalpha():
            col += ch
        else:
            break
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
        rid = sh.attrib.get(
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        )
        target = id_to_target.get(rid, "")
        if target and not target.startswith("xl/"):
            target = "xl/" + target
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
            try:
                val = shared_strings[int(val)]
            except Exception:
                pass
    if isinstance(val, str):
        val = val.strip()
    return val


def parse_data_sheet(zf, sheet_path, shared_strings, max_rows_scan=20000):
    data = zf.read(sheet_path)
    root = ET.fromstring(data)
    sheet_data = root.find(f"{{{NS_MAIN}}}sheetData")
    if sheet_data is None:
        return None
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
                if isinstance(val, str) and not val.replace(".", "", 1).replace("-", "", 1).isdigit():
                    str_count += 1
                else:
                    num_count += 1
        if len(values) >= 3 and str_count >= num_count:
            header_row_idx = r_idx
            break
    if header_row_idx is None:
        return None
    headers = {}
    data_rows = []
    for row in rows:
        r_idx = int(row.attrib.get("r", "0"))
        row_cells = {}
        for c in row.findall(f"{{{NS_MAIN}}}c"):
            cref = c.attrib.get("r")
            if not cref:
                continue
            val = get_cell_value(c, shared_strings)
            row_cells[col_index(cref)] = val
        if r_idx == header_row_idx:
            for idx, val in row_cells.items():
                if isinstance(val, str) and val:
                    headers[idx] = val
            continue
        if r_idx > header_row_idx:
            if row_cells:
                data_rows.append(row_cells)
    return headers, data_rows


def to_float(val):
    if val == "" or val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    try:
        cleaned = str(val).replace(",", "").replace("$", "")
        return float(cleaned)
    except Exception:
        return None


def norm_item(text):
    if not text:
        return ""
    t = text.lower().strip()
    t = re.sub(r"[^a-z0-9\s]+", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t


def collect_site_metrics(site_dir):
    files = sorted(site_dir.rglob("*.xlsx"))
    header_keywords = {
        "last inventory qty": ["last inventory qty", "last inv", "last count"],
        "inv count": ["inv count", "inventory count", "count"],
        "price type": ["price type", "pricing basis", "valuation basis"],
        "grouped by": ["grouped by"],
        "sales amount": ["sales amount", "sales", "revenue"],
        "generated date": ["generated date", "run date", "report date"],
        "generated by": ["generated by", "run by", "user"],
        "close inventory confirmation": ["close inventory confirmation", "close inventory", "closeout"],
        "initial inventory": ["initial inventory", "beginning inventory"],
        "ending inventory": ["ending inventory", "end inventory"],
    }

    header_presence = defaultdict(set)
    file_summaries = []
    item_series = defaultdict(dict)

    for p in files:
        with zipfile.ZipFile(p, "r") as zf:
            shared = read_shared_strings(zf)
            sheets = read_workbook_sheets(zf)
            for name, target in sheets:
                try:
                    data = zf.read(target)
                except KeyError:
                    continue
                root_xml = ET.fromstring(data)
                sheet_data = root_xml.find(f"{{{NS_MAIN}}}sheetData")
                if sheet_data is None:
                    continue
                rows = sheet_data.findall(f"{{{NS_MAIN}}}row")[:15]
                for row in rows:
                    for c in row.findall(f"{{{NS_MAIN}}}c"):
                        val = get_cell_value(c, shared)
                        if not isinstance(val, str) or not val:
                            continue
                        low = val.lower().strip()
                        for key, terms in header_keywords.items():
                            if any(t in low for t in terms):
                                header_presence[key].add(str(p.relative_to(site_dir)))

            data_sheet = next((s for s in sheets if s[0].startswith("Data for ")), None)
            if not data_sheet:
                continue
            parsed = parse_data_sheet(zf, data_sheet[1], shared)
            if not parsed:
                continue
            headers, data_rows = parsed

        header_lookup = {v.strip(): k for k, v in headers.items()}
        idx_item = header_lookup.get("Item Description")
        idx_qty = header_lookup.get("Quantity")
        idx_total = header_lookup.get("Total Price")

        qty_counter = Counter()
        qtys = []
        totals = []

        for row in data_rows:
            item = row.get(idx_item, "") if idx_item else ""
            item_key = norm_item(item)
            qty = to_float(row.get(idx_qty)) if idx_qty else None
            total = to_float(row.get(idx_total)) if idx_total else None

            if qty is not None:
                qtys.append(qty)
                qty_counter[qty] += 1
            if total is not None:
                totals.append(total)

            if item_key:
                entry = item_series[item_key].setdefault(str(p.relative_to(site_dir)), {
                    "item": item,
                    "qty_sum": 0.0,
                    "total_sum": 0.0,
                })
                if qty is not None:
                    entry["qty_sum"] += qty
                if total is not None:
                    entry["total_sum"] += total

        estimated_flag = False
        top_qty = None
        top_qty_pct = 0.0
        if qty_counter:
            top_qty, top_qty_count = qty_counter.most_common(1)[0]
            top_qty_pct = top_qty_count / max(1, len(qtys))
            if top_qty_pct >= 0.2 and len(qtys) >= 50:
                estimated_flag = True

        file_summaries.append({
            "path": str(p.relative_to(site_dir)),
            "rows": len(data_rows),
            "total_sum": sum(totals) if totals else 0.0,
            "top_qty": top_qty,
            "top_qty_pct": top_qty_pct,
            "estimated_flag": estimated_flag,
            "mtime": p.stat().st_mtime,
        })

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
                if prev["qty_sum"] and curr["qty_sum"]:
                    ratio = curr["qty_sum"] / prev["qty_sum"] if prev["qty_sum"] else None
                    if ratio and (ratio > 2 or ratio < 0.5) and abs(curr["qty_sum"] - prev["qty_sum"]) > 10:
                        qty_drifts.append({
                            "item": curr["item"],
                            "prev": prev_path,
                            "curr": curr_path,
                            "prev_qty": prev["qty_sum"],
                            "curr_qty": curr["qty_sum"],
                            "ratio": ratio,
                        })
                if prev["total_sum"] and curr["total_sum"]:
                    ratio = curr["total_sum"] / prev["total_sum"] if prev["total_sum"] else None
                    if ratio and (ratio > 2 or ratio < 0.5) and abs(curr["total_sum"] - prev["total_sum"]) > 500:
                        total_drifts.append({
                            "item": curr["item"],
                            "prev": prev_path,
                            "curr": curr_path,
                            "prev_total": prev["total_sum"],
                            "curr_total": curr["total_sum"],
                            "ratio": ratio,
                        })

    qty_drifts.sort(key=lambda x: abs(x["curr_qty"] - x["prev_qty"]), reverse=True)
    total_drifts.sort(key=lambda x: abs(x["curr_total"] - x["prev_total"]), reverse=True)

    if file_summaries:
        latest = max(file_summaries, key=lambda x: x["mtime"])
        latest_total = latest["total_sum"]
        latest_date = datetime.fromtimestamp(latest["mtime"]).strftime("%Y-%m-%d")
        prev_files = sorted(
            [f for f in file_summaries if f["path"] != latest["path"]],
            key=lambda x: x["mtime"],
        )
        prev_total = prev_files[-1]["total_sum"] if prev_files else 0.0
        delta_pct = ((latest_total - prev_total) / prev_total * 100) if prev_total else 0.0
    else:
        latest_total = 0.0
        prev_total = 0.0
        delta_pct = 0.0
        latest_date = datetime.now().strftime("%Y-%m-%d")

    missing_fields = [k for k in header_keywords.keys() if not header_presence.get(k)]
    flagged_lines = len(qty_drifts) + len(total_drifts)

    return {
        "header_keywords": header_keywords,
        "header_presence": header_presence,
        "file_summaries": file_summaries,
        "qty_drifts": qty_drifts,
        "total_drifts": total_drifts,
        "latest_total": latest_total,
        "delta_pct": delta_pct,
        "latest_date": latest_date,
        "flagged_lines": flagged_lines,
        "missing_fields": missing_fields,
    }


def parse_date_label(path_str):
    """
    Extracts a readable date label from a filename (e.g. 'Dec 30').
    Falls back to 'Unknown' if no date found.
    """
    m = re.search(r"20(\d{2})[-_](\d{1,2})[-_](\d{1,2})", path_str)
    if m:
        yy, mm, dd = m.groups()
        try:
            dt = datetime(int("20" + yy), int(mm), int(dd))
            return dt.strftime("%b %d")
        except ValueError:
            pass
    return "Unknown"


def generate_sparkline(values, width=120, height=40, color="#06b6d4"):
    """
    Generates an SVG sparkline string for a list of values.
    """
    if not values or len(values) < 2:
        return ""
    
    clean_vals = [v for v in values if v is not None]
    if len(clean_vals) < 2:
        return ""

    min_v, max_v = min(clean_vals), max(clean_vals)
    rng = max_v - min_v if max_v != min_v else 1.0
    
    points = []
    step = width / (len(clean_vals) - 1)
    
    for i, v in enumerate(clean_vals):
        x = i * step
        # SVG y=0 is top, so we flip the y coordinate
        y = height - ((v - min_v) / rng * (height - 4)) - 2 # 2px padding
        points.append(f"{x:.1f},{y:.1f}")
        
    pts = " ".join(points)
    return f'<svg width="{width}" height="{height}" fill="none" class="sparkline"><polyline points="{pts}" stroke="{color}" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round" /></svg>'


def generate_bar_chart(items, width="100%", height=160):
    """
    Generates a horizontal bar chart SVG.
    items: list of dicts {'label': str, 'value': float, 'color': str}
    """
    if not items:
        return ""
    
    # Config
    bar_height = 20
    gap = 12
    margin_left = 120 # Space for labels
    
    # Calc max value for scaling
    max_val = max(abs(i['value']) for i in items) if items else 1.0
    
    svg_height = len(items) * (bar_height + gap)
    content = ""
    
    for i, item in enumerate(items):
        y = i * (bar_height + gap)
        val_width = (abs(item['value']) / max_val) * (100 - 30) # leave 30% buffer
        
        # Label
        content += f'<text x="{margin_left - 10}" y="{y + 14}" text-anchor="end" fill="var(--text-secondary)" font-size="12" font-family="var(--font-mono)">{item["label"]}</text>'
        
        # Bar Bg
        content += f'<rect x="{margin_left}" y="{y}" width="100%" height="{bar_height}" fill="rgba(255,255,255,0.05)" rx="4" />'
        
        # Value Bar
        content += f'<rect x="{margin_left}" y="{y}" width="{val_width}%" height="{bar_height}" fill="{item["color"]}" rx="4"><animate attributeName="width" from="0" to="{val_width}%" dur="0.8s" fill="freeze" /></rect>'
        
        # Value Text
        content += f'<text x="{margin_left + 5}" y="{y + 14}" fill="white" font-size="11" font-weight="600" style="mix-blend-mode: difference;">{item["val_str"]}</text>'
        
    return f'<svg width="{width}" height="{svg_height}" style="overflow:visible">{content}</svg>'




def build_audit_report(root_dir, report_path):
    sorted_by_site = root_dir / "sorted" / "by_site"
    sites = sorted([p.name for p in sorted_by_site.iterdir() if p.is_dir()])
    site_reports = []

    for site in sites:
        site_dir = sorted_by_site / site
        metrics = collect_site_metrics(site_dir)
        
        # Calculate Confidence Score
        # Based on presence of 10 key fields. Each missing field drops score by 10%.
        missing_count = len(metrics["missing_fields"])
        confidence_score = max(0, 100 - (missing_count * 10))
        
        # Prepare Sparkline Data (chronological total values)
        # Sort files by mtime and extract total_sum
        sorted_files = sorted(metrics["file_summaries"], key=lambda x: x["mtime"])
        spark_values = [f["total_sum"] for f in sorted_files[-10:]] # Last 10 points
        sparkline_svg = generate_sparkline(spark_values, color="#F43F5E" if metrics["delta_pct"] < 0 else "#2DD4BF")

        site_reports.append({
            "site": site,
            "site_dir": site_dir,
            "confidence_score": confidence_score,
            "sparkline_svg": sparkline_svg,
            **metrics,
        })

    # Global Stats
    total_sites = len(site_reports)
    total_files = sum(len(s["file_summaries"]) for s in site_reports)
    total_value = sum(s["latest_total"] for s in site_reports)
    total_issues = sum(len(s["total_drifts"]) + len(s["qty_drifts"]) for s in site_reports)
    report_date = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Icons (feather/heroicons style)
    icons = {
        "globe": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>',
        "box": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>',
        "check_circle": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--success)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>',
        "alert": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--danger)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>',
        "menu": '<svg width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>',
        "x": '<svg width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>',
        "trending": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline><polyline points="17 6 23 6 23 12"></polyline></svg>',
        "activity": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>',
        "arrow_up": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="19" x2="12" y2="5"></line><polyline points="5 12 12 5 19 12"></polyline></svg>',
        "arrow_down": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><polyline points="19 12 12 19 5 12"></polyline></svg>',
    }

    # Calculate global max delta for bar scaling
    all_abs_deltas = []
    for s in site_reports:
        for d in s["total_drifts"]:
            all_abs_deltas.append(abs(d["curr_total"] - d["prev_total"]))
        for d in s["qty_drifts"]:
             # For qty drifts, we might want a different scale or just value?
             # Let's stick to value impact if possible, or qty magnitude
             pass 
    global_max_delta = max(all_abs_deltas) if all_abs_deltas else 1.0

    # HTML Generator
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0" />
  <title>Inventory Integrity Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&family=Outfit:wght@500;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-main: #0f172a; --bg-sidebar: #1e293b; --bg-card: #1e293b;
      --border: #334155; --text-primary: #f8fafc; --text-secondary: #94a3b8;
      --primary: #3b82f6; --success: #2dd4bf; --warning: #fbbf24; --danger: #f43f5e;
      --font-head: 'Outfit', sans-serif; --font-body: 'Inter', sans-serif; --font-mono: 'JetBrains Mono', monospace;
    }}
    * {{ box-sizing: border-box; -webkit-tap-highlight-color: transparent; }}
    body {{
      margin: 0; background: var(--bg-main); color: var(--text-primary);
      font-family: var(--font-body); display: flex; height: 100vh; overflow: hidden;
    }}
    
    /* Sidebar */
    .sidebar {{
      width: 260px; background: rgba(30, 41, 59, 0.7); border-right: 1px solid var(--border);
      display: flex; flex-direction: column; flex-shrink: 0; z-index: 50;
      backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
      transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }}
    .logo {{
      padding: 24px; font-family: var(--font-head); font-size: 20px; font-weight: 700;
      letter-spacing: -0.5px; color: var(--text-primary); border-bottom: 1px solid var(--border);
      display: flex; justify-content: space-between; align-items: center;
    }}
    .close-btn {{ display: none; cursor: pointer; color: var(--text-secondary); }}
    .nav {{ flex: 1; padding: 16px; overflow-y: auto; }}
    .nav-group {{ font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; color: var(--text-secondary); margin: 24px 12px 8px; }}
    .nav-item {{
      display: flex; align-items: center; gap: 12px;
      padding: 10px 12px; margin-bottom: 2px; border-radius: 8px; cursor: pointer;
      color: var(--text-secondary); font-size: 14px; font-weight: 500; transition: .2s;
    }}
    .nav-item svg {{ opacity: 0.7; transition: .2s; }}
    .nav-item:hover {{ background: rgba(255,255,255,0.05); color: var(--text-primary); }}
    .nav-item:hover svg {{ opacity: 1; }}
    .nav-item.active {{ background: rgba(59, 130, 246, 0.15); color: #60a5fa; }}
    .nav-item.active svg {{ opacity: 1; stroke: #60a5fa; }}
    .nav-label {{ white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 1; }}
    .nav-badge {{ 
      background: var(--danger); color: white; padding: 2px 6px; border-radius: 4px; 
      font-size: 11px; font-family: var(--font-mono); 
    }}

    /* Main Content */
    .main {{ flex: 1; display: flex; flex-direction: column; overflow: hidden; position: relative; }}
    .header {{
      height: 60px; border-bottom: 1px solid var(--border); display: flex; align-items: center;
      padding: 0 24px; gap: 16px; background: rgba(15, 23, 42, 0.8);
      backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
      flex-shrink: 0; z-index: 10;
    }}
    .menu-btn {{ 
      display: none; cursor: pointer; padding: 8px; margin-left: -8px; border-radius: 6px;
      color: var(--text-secondary); 
    }}
    .header-title {{ font-family: var(--font-head); font-size: 20px; font-weight: 600; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    .header-meta {{ font-size: 13px; color: var(--text-secondary); margin-left: auto; display: flex; align-items: center; gap: 6px; background: rgba(255,255,255,0.03); padding: 4px 10px; border-radius: 99px; border: 1px solid var(--border); }}

    .content-area {{ flex: 1; overflow-y: auto; padding: 32px; scroll-behavior: smooth; }}
    .tab-view {{ display: none; animation: fadeIn 0.4s cubic-bezier(0.16, 1, 0.3, 1); }}
    .tab-view.active {{ display: block; }}
    @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}

    /* Cards & Stats */
    .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 20px; margin-bottom: 32px; }}
    .card {{ 
      background: var(--bg-card); border: 1px solid var(--border); border-radius: 16px; 
      padding: 24px; margin-bottom: 24px; 
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
      transition: transform 0.2s, box-shadow 0.2s;
    }}
    .card:hover {{ transform: translateY(-1px); box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.2); border-color: rgba(255,255,255,0.1); }}
    
    .stat-label {{ color: var(--text-secondary); font-size: 13px; font-weight: 500; margin-bottom: 8px; display: flex; align-items: center; gap: 8px; }}
    .stat-value {{ font-family: var(--font-head); font-size: 32px; font-weight: 600; color: var(--text-primary); letter-spacing: -0.5px; }}
    .stat-spark {{ margin-top: 16px; opacity: 0.9; height: 48px; mask-image: linear-gradient(to right, transparent, black 10%, black 90%, transparent); }}

    /* Layouts */
    .bento-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 24px; margin-bottom: 24px; }}
    .bento-col {{ display: flex; flex-direction: column; gap: 24px; }}
    
    .heatmap-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 8px; }}
    .heatmap-item {{ 
      background: rgba(30,30,50,0.5); aspect-ratio: 1; border-radius: 8px; border: 1px solid var(--border);
      display: flex; flex-direction: column; align-items: center; justify-content: center;
      transition: .2s; cursor: pointer; position: relative; overflow: hidden;
    }}
    .heatmap-item:hover {{ transform: scale(1.05); z-index: 10; border-color: var(--primary); box-shadow: 0 4px 12px rgba(0,0,0,0.3); }}
    .heatmap-val {{ font-weight: 700; font-size: 16px; z-index: 2; }}
    .heatmap-lbl {{ font-size: 11px; color: rgba(255,255,255,0.7); z-index: 2; text-align: center; padding: 0 4px; }}
    .heatmap-bg {{ position: absolute; inset: 0; opacity: 0.2; z-index: 1; }}

    /* Variance Stream & Impact Bars */
    .drift-stream {{ display: flex; flex-direction: column; gap: 12px; }}
    .drift-card {{
      position: relative; background: rgba(30, 41, 59, 0.4); border: 1px solid var(--border);
      border-radius: 12px; overflow: hidden; padding: 16px;
      display: flex; align-items: center; gap: 16px;
      transition: transform 0.2s, background 0.2s;
    }}
    .drift-card:hover {{ background: rgba(30, 41, 59, 0.8); transform: scale(1.01); }}
    
    .impact-bar {{
      position: absolute; top: 0; bottom: 0; left: 0; z-index: 0;
      opacity: 0.15; transition: width 0.5s ease;
      background: linear-gradient(90deg, var(--danger), transparent);
    }}
    .drift-content {{ position: relative; z-index: 1; flex: 1; display: flex; align-items: center; justify-content: space-between; }}
    
    .drift-icon {{
      width: 40px; height: 40px; border-radius: 10px; background: rgba(15, 23, 42, 0.5);
      border: 1px solid var(--border); display: flex; align-items: center; justify-content: center;
      color: var(--text-secondary); flex-shrink: 0;
    }}
    .drift-info {{ flex: 1; margin-left: 12px; min-width: 0; }}
    .drift-title {{ font-weight: 600; font-size: 15px; color: var(--text-primary); margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    .drift-meta {{ font-size: 12px; color: var(--text-secondary); display: flex; gap: 12px; align-items: center; }}
    .drift-tag {{ font-family: var(--font-mono); font-size: 11px; padding: 2px 6px; border-radius: 4px; background: rgba(0,0,0,0.3); }}

    .drift-values {{ text-align: right; }}
    .drift-val-main {{ font-family: var(--font-head); font-size: 18px; font-weight: 700; color: var(--text-primary); }}
    .drift-val-sub {{ font-size: 12px; font-weight: 500; margin-top: 2px; }}
    
    /* Tables fallback (still used for detailed generic lists if needed) */
    .table-responsive {{ overflow-x: auto; -webkit-overflow-scrolling: touch; margin: 0 -24px; padding: 0 24px; }}
    table {{ width: 100%; border-collapse: separate; border-spacing: 0; font-size: 14px; min-width: 650px; }}
    th {{ text-align: left; color: var(--text-secondary); padding: 16px; border-bottom: 1px solid var(--border); font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; background: rgba(30, 41, 59, 0.3); }}
    td {{ padding: 16px; border-bottom: 1px solid var(--border); color: var(--text-primary); vertical-align: middle; transition: background 0.1s; }}
    tr:hover td {{ background: rgba(255,255,255,0.02); }}
    tr:last-child td {{ border-bottom: none; }}
    
    .cell-mono {{ font-family: var(--font-mono); font-size: 13px; letter-spacing: -0.5px; }}
    .pill {{ padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px; white-space: nowrap; }}
    .pill.high {{ background: rgba(244, 63, 94, 0.15); color: var(--danger); border: 1px solid rgba(244, 63, 94, 0.2); }}
    .pill.med {{ background: rgba(251, 191, 36, 0.15); color: var(--warning); border: 1px solid rgba(251, 191, 36, 0.2); }}

    /* Confidence Ring */
    .confidence-wrapper {{ display: flex; align-items: center; gap: 20px; margin-bottom: 32px; padding: 20px; background: rgba(255,255,255,0.02); border-radius: 12px; border: 1px solid var(--border); }}
    .ring-container {{ position: relative; width: 72px; height: 72px; flex-shrink: 0; }}
    .ring-bg {{ fill: none; stroke: var(--border); stroke-width: 6; }}
    .ring-val {{ fill: none; stroke: var(--success); stroke-width: 6; stroke-linecap: round; transform: rotate(-90deg); transform-origin: 50% 50%; transition: 1s ease; }}
    .ring-text {{ position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-family: var(--font-head); font-size: 16px; font-weight: 700; }}

    /* Mobile Overlay */
    .overlay {{ 
      position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 40; 
      opacity: 0; pointer-events: none; transition: opacity 0.3s; backdrop-filter: blur(4px);
    }}

    @media (max-width: 768px) {{
      .sidebar {{ position: fixed; inset: 0 right auto 0 0; transform: translateX(-100%); width: 280px; box-shadow: 20px 0 50px rgba(0,0,0,0.5); }}
      .sidebar.open {{ transform: translateX(0); }}
      .overlay.open {{ opacity: 1; pointer-events: auto; }}
      .menu-btn {{ display: block; }}
      .close-btn {{ display: block; }}
      .content-area {{ padding: 20px; }}
      .stats-grid {{ grid-template-columns: 1fr; }}
      .header {{ padding: 0 16px; }}
      .header-meta {{ display: none; }} 
      .card {{ padding: 16px; }}
      td, th {{ padding: 16px 12px; }} 
    }}

  </style>
</head>
<body>
  <div class="overlay" onclick="toggleSidebar()"></div>
  
  <div class="sidebar" id="sidebar">
    <div class="logo">
      Inventory Watch
      <div class="close-btn" onclick="toggleSidebar()">
        {icons['x']}
      </div>
    </div>
    <div class="nav">
      <div class="nav-item active" onclick="showTab('dashboard')">
        {icons['globe']}
        <span class="nav-label">Global Overview</span>
      </div>
      
      <div class="nav-group">Locations</div>
"""

    for s in site_reports:
        issues = len(s["total_drifts"]) + len(s["qty_drifts"])
        badge = f'<span class="nav-badge">{issues}</span>' if issues > 0 else ""
        html += f"""      <div class="nav-item" onclick="showTab('site-{s['site']}')">
        {icons['box']}
        <span class="nav-label">{s['site']}</span>
        {badge}
      </div>
"""

    html += f"""    </div>
  </div>

  <div class="main">
    <div class="header">
      <div class="menu-btn" onclick="toggleSidebar()">
        {icons['menu']}
      </div>
      <div class="header-title" id="pageTitle">Global Overview</div>
      <div class="header-meta">{icons['activity']} Updated {report_date}</div>
    </div>
    
    <div class="content-area">
      <!-- DASHBOARD TAB -->
      <div id="dashboard" class="tab-view active">
        
        <!-- Top Stats Row -->
        <div class="stats-grid">
          <div class="card">
            <div class="stat-label">Total Inventory Value</div>
            <div class="stat-value">${total_value:,.2f}</div>
          </div>
          <div class="card">
            <div class="stat-label">Active Sites</div>
            <div class="stat-value">{total_sites}</div>
          </div>
          <div class="card">
            <div class="stat-label">Total Drift Alerts</div>
            <div class="stat-value" style="color: {'var(--danger)' if total_issues > 0 else 'var(--text-primary)'}">{total_issues}</div>
          </div>
        </div>

"""
    # -------------------------
    # DATA PREP FOR WIDGETS
    # -------------------------
    
    # 1. Site Health Matrix HTML
    heatmap_html = ""
    for s in site_reports:
        # Determine color/health
        h_val = s['delta_pct']
        h_color = "var(--success)"
        if h_val < -5: h_color = "var(--danger)"
        elif h_val < 0: h_color = "var(--warning)"
        
        # Determine size/opacity by relation to total value? 
        # Or just simple color scale? Let's do color scale for drift.
        
        heatmap_html += f"""            <div class="heatmap-item" onclick="showTab('site-{s['site']}')">
              <div class="heatmap-bg" style="background:{h_color}"></div>
              <div class="heatmap-val" style="color:{h_color}">{h_val:+.1f}%</div>
              <div class="heatmap-lbl">{s['site']}</div>
            </div>
"""

    # 2. Top Movers Chart Data
    # Global top variances
    all_drifts = []
    for s in site_reports:
        for d in s["total_drifts"]:
            d["site"] = s["site"]
            d["abs_delta"] = abs(d["curr_total"] - d["prev_total"])
            all_drifts.append(d)
    all_drifts.sort(key=lambda x: x["abs_delta"], reverse=True)
    
    chart_items = []
    for d in all_drifts[:5]:
        delta = d["curr_total"] - d["prev_total"]
        color = "var(--danger)" if delta < 0 else "var(--success)"
        chart_items.append({
            "label": d["item"],
            "value": delta,
            "val_str": f"${delta:+.0f}",
            "color": color
        })
    
    top_movers_chart = generate_bar_chart(chart_items)


    html += f"""        <!-- Bento Grid Middle Row -->
        <div class="bento-grid">
            <div class="bento-col">
                <h3>Site Health Matrix</h3>
                <div class="card" style="padding:12px; height:100%">
                    <div class="heatmap-grid">
                        {heatmap_html}
                    </div>
                </div>
            </div>
            
            <div class="bento-col">
                <h3>Top Movers (Variance)</h3>
                <div class="card" style="display:flex; align-items:center;">
                    {top_movers_chart}
                </div>
            </div>
        </div>

        <h3 style="margin-top:0">Recent Critical Alerts</h3>
        <div class="drift-stream">
"""
    
    var_danger = "var(--danger)"
    
    # Render Stream (Top 10 still, maybe reduce visual weight?)
    for d in all_drifts[:10]:
        change_label = f"{parse_date_label(d['prev'])} → {parse_date_label(d['curr'])}"
        delta = d["curr_total"] - d["prev_total"]
        pct_width = min(100, (abs(delta) / global_max_delta) * 100)
        color = "var(--danger)" if delta < 0 else "var(--success)"
        icon = icons["arrow_down"] if delta < 0 else icons["arrow_up"]
        
        html += f"""          <div class="drift-card">
            <div class="impact-bar" style="width: {pct_width}%; background: linear-gradient(90deg, {color}, transparent);"></div>
            <div class="drift-content">
                <div style="display:flex; align-items:center;">
                    <div class="drift-icon" style="color:{color}">{icon}</div>
                    <div class="drift-info">
                        <div class="drift-title">{d['item']}</div>
                        <div class="drift-meta">
                            <span class="drift-tag">{d['site']}</span>
                            <span>{change_label}</span>
                        </div>
                    </div>
                </div>
                <div class="drift-values">
                    <div class="drift-val-main" style="color: {color}">{delta:+.2f}</div>
                </div>
            </div>
          </div>
"""
    html += """        </div>
      </div>
"""

    # SITE TABS
    for s in site_reports:
        # Confidence ring calc
        c_score = s["confidence_score"]
        c_dash = 2 * 3.14159 * 24 # r=24
        c_offset = c_dash - (c_score / 100 * c_dash)
        c_color = "var(--success)" if c_score > 80 else "var(--warning)"
        if c_score < 50: c_color = "var(--danger)"
        
        # Local Max for bars
        local_max = 1.0
        if s["total_drifts"]:
             local_max = max(abs(d["curr_total"] - d["prev_total"]) for d in s["total_drifts"])

        html += f"""      <div id="site-{s['site']}" class="tab-view">
        <div class="confidence-wrapper">
           <div class="ring-container">
             <svg width="60" height="60" viewBox="0 0 60 60">
               <circle cx="30" cy="30" r="24" class="ring-bg" />
               <circle cx="30" cy="30" r="24" class="ring-val" stroke="{c_color}" stroke-dasharray="{c_dash}" stroke-dashoffset="{c_offset}" />
             </svg>
             <div class="ring-text">{c_score}%</div>
           </div>
           <div>
             <div style="font-weight:600; font-size:16px;">Data Verification Score</div>
             <div style="color:var(--text-secondary); font-size:13px;">Based on {len(s['missing_fields'])} missing required columns</div>
           </div>
        </div>

        <div class="stats-grid">
           <div class="card">
             <div class="stat-label">Site Value</div>
             <div class="stat-value">${s['latest_total']:,.2f}</div>
             <div class="stat-spark">{s['sparkline_svg']}</div>
           </div>
           <div class="card">
             <div class="stat-label">Value Change</div>
             <div class="stat-value" style="color:{'var(--success)' if s['delta_pct'] >= 0 else 'var(--danger)'}">{s['delta_pct']:+.1f}%</div>
           </div>
        </div>

        <h3>Drift Analysis</h3>
        <div class="drift-stream">
"""
        # Site specific drifts
        local_drifts = s["total_drifts"] + s["qty_drifts"]
        
        if not local_drifts:
             html += """<div style="padding:24px; text-align:center; color:var(--text-secondary); border:1px dashed var(--border); border-radius:12px;">No significant anomalies detected.</div>"""

        for d in local_drifts[:20]: 
            is_price = "prev_total" in d
            item = d["item"]
            window = f"{parse_date_label(d['prev'])} → {parse_date_label(d['curr'])}"
            
            if is_price:
                 delta = d["curr_total"] - d["prev_total"]
                 val_str = f"${delta:+.2f}"
                 color = "var(--danger)" if delta < 0 else "var(--success)"
                 icon = icons["arrow_down"] if delta < 0 else icons["arrow_up"]
                 sub_lbl = "Price Swing"
                 # Bar calc
                 abs_d = abs(delta)
                 pct_width = min(100, (abs_d / local_max) * 100) if local_max > 0 else 0
            else:
                 delta = d["curr_qty"] - d["prev_qty"]
                 val_str = f"{delta:+.1f}"
                 color = "var(--warning)"
                 icon = icons["box"]
                 sub_lbl = "Qty Drift"
                 pct_width = 0 # No bar for qty yet or make it yellow?
                 
                 
            html += f"""          <div class="drift-card">
                <div class="impact-bar" style="width: {pct_width}%; background: linear-gradient(90deg, {color}, transparent);"></div>
                <div class="drift-content">
                    <div style="display:flex; align-items:center;">
                        <div class="drift-icon" style="color:{color}">{icon}</div>
                        <div class="drift-info">
                            <div class="drift-title">{item}</div>
                            <div class="drift-meta">
                                <span>{window}</span>
                            </div>
                        </div>
                    </div>
                    <div class="drift-values">
                        <div class="drift-val-main" style="color: {color}">{val_str}</div>
                        <div class="drift-val-sub">{sub_lbl}</div>
                    </div>
                </div>
              </div>
"""
        html += """        </div>
      </div>
"""

    html += """    </div>
  </div>

  <script>
    function toggleSidebar() {
      document.getElementById('sidebar').classList.toggle('open');
      document.querySelector('.overlay').classList.toggle('open');
    }

    function showTab(id) {
      // Hide all tabs
      document.querySelectorAll('.tab-view').forEach(el => el.classList.remove('active'));
      document.getElementById(id).classList.add('active');
      
      // Update sidebar
      document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
      
      // Find the nav item that matches, simplified logic
      // In a real app we'd map IDs to nav items better
      document.querySelectorAll('.nav-item').forEach(item => {
         if(item.onclick.toString().includes(id)) item.classList.add('active');
      });
      
      // Update Title
      const title = id === 'dashboard' ? 'Global Overview' : 'Site Detail: ' + id.replace('site-', '');
      document.getElementById('pageTitle').innerText = title;
      
      // Close sidebar on mobile after selection
      if (window.innerWidth <= 768) {
        toggleSidebar();
      }
    }
  </script>
</body>
</html>
"""
    report_path.write_text(html)


def is_file_stable(path, debounce_seconds=5):
    """Checks if a file has stopped being modified for a given duration."""
    if not path.exists():
        return False
    now = time.time()
    return (now - path.stat().st_mtime) >= debounce_seconds


def process_inbox(inbox_dir, sorted_root, archive_root, archive_dups, root_dir, alias_map):
    moved = []
    skipped = []
    existing_sites = [p.name for p in (sorted_root / "by_site").iterdir() if (p / "by_site").is_dir()]

    for path in sorted(inbox_dir.glob("*.xlsx")):
        site = detect_site(path, existing_sites, alias_map)
        target = build_target(path, sorted_root / "by_site", site)
        if target is None:
            skipped.append(path)
            continue
        archive_target = archive_root / "originals" / path.name
        archive_target.parent.mkdir(parents=True, exist_ok=True) # Ensure parent dir exists
        if not archive_target.exists():
            shutil.copy2(path, archive_target)
        shutil.move(str(path), str(target))
        moved.append((path, target))

    if moved:
        dedupe_sorted(sorted_root / "by_site", archive_dups)
        build_audit_report(root_dir, root_dir / "inventory_audit_report.html")

    return moved, skipped




# --- Observability (Stolen from Suu-AI) ---
def configure_logging(level="INFO", log_file=None):
    """Configures structured logging."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
        force=True
    )

logger = logging.getLogger("InventoryWatch")

def start_server(root_dir, port=8000):
    """Starts a simple HTTP server in a daemon thread."""
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(root_dir), **kwargs)
        
        # Squelch logs to keep console clean
        def log_message(self, format, *args):
            pass

    server = HTTPServer(('0.0.0.0', port), Handler)
    logger.info(f"🚀 Dashboard live at http://localhost:{port}/inventory_audit_report.html")
    logger.info(f"   (Also accessible via Tailscale IP on port {port})")
    server.serve_forever()

def main():
    root = Path(__file__).resolve().parents[1]
    inbox_dir = root / "inbox"
    
    # CLI Args
    parser = argparse.ArgumentParser()
    parser.add_argument("--regenerate", action="store_true", help="Regenerate report from existing files")
    parser.add_argument("--serve", action="store_true", help="Start a web server to view the report")
    parser.add_argument("--log-level", default="INFO", help="Set logging level")
    args = parser.parse_args()

    # Setup Logging
    configure_logging(level=args.log_level, log_file=root / "inventory_watch.log")

    # Setup directories
    sorted_root = root / "sorted"
    archive_root = root / "archive"
    archive_dups = root / "archive_duplicates"
    
    for d in [inbox_dir, sorted_root, archive_root, archive_dups]:
        d.mkdir(parents=True, exist_ok=True)

    # Aliases
    alias_map = load_site_aliases(root)
    
    # Mode: Regenerate only
    if args.regenerate:
        logger.info("Regenerating audit report from existing data...")
        build_audit_report(root, root / "inventory_audit_report.html")
        logger.info(f"Report written to {root / 'inventory_audit_report.html'}")
        return

    # Mode: Serve
    if args.serve:
        # Check if report exists, if not build it first
        if not (root / "inventory_audit_report.html").exists():
             build_audit_report(root, root / "inventory_audit_report.html")
        
        start_server(root)
        return

    # Mode: Watch (Default)
    server_thread = threading.Thread(target=start_server, args=(root,), daemon=True)
    server_thread.start()

    debounce_seconds = 5
    poll_seconds = 5
    
    logger.info(f"Monitoring {inbox_dir} for new .xlsx files...")
    logger.info("Press Ctrl+C to stop.")

    while True:
        # 1) Check inbox
        ready = []
        for p in inbox_dir.glob("*.xlsx"):
            if is_file_stable(p, debounce_seconds):
                ready.append(p)
        
        if ready:
            process_inbox(inbox_dir, sorted_root, archive_root, archive_dups, root, alias_map)
        
        time.sleep(poll_seconds)

if __name__ == "__main__":
    main()
