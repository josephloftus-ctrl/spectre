"""Parsing services for cycle menus and promo PDFs."""

import re
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..utils.pdf import extract_text_from_pdf


# === Keyword Extraction ===

STOP_WORDS = {
    'with', 'and', 'the', 'in', 'on', 'of', 'a', 'an', 'style',
    'inspired', 'classic', 'traditional', 'homemade', 'fresh',
    'served', 'topped', 'made', 'house'
}


def extract_keywords(name: str) -> list[str]:
    """Extract keywords from a recipe/item name."""
    name = name.lower()
    words = re.findall(r'[a-z]+', name)
    return [w for w in words if w not in STOP_WORDS and len(w) > 2]


# === Cycle Menu Parsing ===

def parse_cycle_menu(xlsx_path: Path, unit_config: dict) -> list[dict]:
    """Parse MenuWorks Week at a Glance xlsx export."""
    xlsx_path = Path(xlsx_path)

    with zipfile.ZipFile(xlsx_path) as z:
        ss_xml = z.read('xl/sharedStrings.xml')
        strings = _parse_shared_strings(ss_xml)

        ws_xml = z.read('xl/worksheets/sheet1.xml')
        rows = _parse_worksheet(ws_xml, strings)

    return _extract_menu_items(rows, unit_config)


def _parse_shared_strings(xml_content: bytes) -> list[str]:
    """Extract shared strings from xlsx."""
    root = ET.fromstring(xml_content)
    ns = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

    strings = []
    for si in root.findall('main:si', ns):
        texts = si.findall('.//main:t', ns)
        value = ''.join(t.text or '' for t in texts)
        strings.append(value)

    return strings


def _parse_worksheet(xml_content: bytes, strings: list[str]) -> dict[int, dict[str, str]]:
    """Parse worksheet into row -> column -> value dict."""
    root = ET.fromstring(xml_content)
    ns = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

    rows = {}
    for row in root.findall('.//main:row', ns):
        row_num = int(row.get('r'))
        rows[row_num] = {}

        for cell in row.findall('main:c', ns):
            ref = cell.get('r')
            col = re.match(r'([A-Z]+)', ref).group(1)
            cell_type = cell.get('t')
            value_el = cell.find('main:v', ns)

            if value_el is not None and value_el.text:
                if cell_type == 's':
                    value = strings[int(value_el.text)]
                else:
                    value = value_el.text
            else:
                value = ''

            rows[row_num][col] = value

    return rows


def _extract_menu_items(rows: dict, unit_config: dict) -> list[dict]:
    """Extract structured menu items from parsed rows."""
    items = []
    day_columns = ['B', 'E', 'F', 'G', 'H']

    current_week = None
    current_dates = {}
    current_station = None
    current_meal = None

    for row_num in sorted(rows.keys()):
        row = rows[row_num]

        # Check for week header
        for col, val in row.items():
            if val and val.startswith('Week '):
                match = re.search(r'Week (\d+)', val)
                if match:
                    current_week = int(match.group(1))

        # Check for day headers
        for col in day_columns:
            val = row.get(col, '')
            if val and re.match(r'\w+day \(\d{2}/\d{2}/\d{4}\)', val):
                match = re.match(r'(\w+day) \((\d{2}/\d{2}/\d{4})\)', val)
                if match:
                    day_name = match.group(1)
                    date_str = match.group(2)
                    dt = datetime.strptime(date_str, '%m/%d/%Y')
                    current_dates[col] = {
                        'date': dt.strftime('%Y-%m-%d'),
                        'day_of_week': day_name
                    }

        # Check for station header
        col_a = row.get('A', '')
        if col_a and ' : ' in col_a:
            parts = col_a.split(' : ', 1)
            current_meal = parts[0].strip()
            current_station = parts[1].strip()

        # Extract items from day columns
        if current_station and current_dates:
            for col in day_columns:
                val = row.get(col, '').strip()
                date_info = current_dates.get(col)

                if not val or val == 'end' or not date_info:
                    continue
                if re.match(r'\w+day \(\d{2}/\d{2}/\d{4}\)', val):
                    continue

                station_group = _get_station_group(current_station, unit_config)

                items.append({
                    'date': date_info['date'],
                    'day_of_week': date_info['day_of_week'],
                    'week_number': current_week,
                    'meal': current_meal,
                    'station': current_station,
                    'station_group': station_group,
                    'item_name': val,
                    'keywords': extract_keywords(val)
                })

    return items


def _get_station_group(station: str, unit_config: dict) -> Optional[str]:
    """Map station name to group using unit config."""
    station_lower = station.lower()

    for group, stations in unit_config.get('station_groups', {}).items():
        for s in stations:
            if s.lower() == station_lower or station_lower in s.lower():
                return group

    return None


# === Promo PDF Parsing ===

THEME_PATTERNS = [
    (r'super.?bowl', 'super-bowl'),
    (r'mardi.?gras', 'mardi-gras'),
    (r'valentine', 'valentines'),
    (r'fish.?friday', 'fish-friday'),
    (r'black.?history', 'black-history-month'),
    (r'heart.?healthy', 'heart-healthy'),
]


def extract_theme_from_filename(filename: str) -> str:
    """Extract theme identifier from filename."""
    filename_lower = filename.lower()

    for pattern, theme_id in THEME_PATTERNS:
        if re.search(pattern, filename_lower):
            return theme_id

    name = re.sub(r'\.pdf$', '', filename, flags=re.IGNORECASE)
    name = re.sub(r'Recipe(s)?(\s+Packet)?', '', name, flags=re.IGNORECASE)
    return name.strip().lower().replace(' ', '-') or 'unknown'


def parse_promo_pdf(pdf_path: Path, themes_config: dict, month: str) -> list[dict]:
    """Parse a promo PDF and extract recipes."""
    text = extract_text_from_pdf(pdf_path)
    theme = extract_theme_from_filename(pdf_path.name)
    theme_info = _get_theme_info(theme, themes_config, month)

    return _parse_promo_text(text, theme, theme_info)


def _get_theme_info(theme: str, themes_config: dict, month: str) -> dict:
    """Get theme dates and info from config."""
    month_themes = themes_config.get(month, {})
    theme_config = month_themes.get(theme, {})

    return {
        'dates': theme_config.get('dates', []),
        'window': theme_config.get('window', 0),
        'all_month': theme_config.get('all_month', False),
    }


def _parse_promo_text(text: str, theme: str, theme_info: dict) -> list[dict]:
    """Parse promo text into recipe records."""
    recipes = []
    lines = text.split('\n')

    current = None

    for line in lines:
        if not line.strip() or _is_header_line(line):
            continue

        parsed = _parse_line(line)

        if parsed['has_ref'] and parsed['has_name'] and parsed['has_cost']:
            # Complete entry
            if current and current.get('master_ref'):
                recipes.append(_finalize_recipe(current, theme, theme_info))

            current = {
                'master_ref': parsed['ref'],
                'name': parsed['name'],
                'station': parsed['station'],
                'calories': parsed['calories'],
                'cost': parsed['cost'],
                'dietary': parsed['dietary'],
            }
            recipes.append(_finalize_recipe(current, theme, theme_info))
            current = None

        elif parsed['has_ref'] and not parsed['has_cost']:
            # Ref-only or ref+name line
            if current and not current.get('master_ref'):
                current['master_ref'] = parsed['ref']
                if parsed['name']:
                    current['name'] = (current.get('name', '') + ' ' + parsed['name']).strip()
                recipes.append(_finalize_recipe(current, theme, theme_info))
                current = None
            elif parsed['has_name']:
                current = {
                    'master_ref': parsed['ref'],
                    'name': parsed['name'],
                    'station': parsed['station'],
                    'calories': parsed['calories'],
                    'cost': parsed['cost'],
                    'dietary': parsed['dietary'],
                }

        elif parsed['has_cost']:
            # New entry starting with cost
            if current and current.get('master_ref'):
                recipes.append(_finalize_recipe(current, theme, theme_info))

            current = {
                'master_ref': None,
                'name': parsed['name'] or '',
                'station': parsed['station'] or '',
                'calories': parsed['calories'],
                'cost': parsed['cost'],
                'dietary': parsed['dietary'],
            }

        elif current is not None:
            # Continuation
            if parsed['name']:
                current['name'] = (current.get('name', '') + ' ' + parsed['name']).strip()
            if parsed['station'] and not current.get('station'):
                current['station'] = parsed['station']

    if current and current.get('master_ref') and current.get('name'):
        recipes.append(_finalize_recipe(current, theme, theme_info))

    return recipes


def _is_header_line(line: str) -> bool:
    """Check if line is a header."""
    if 'Master' in line and 'Reference' in line:
        return True
    if 'Recipe Name' in line and 'Station' in line:
        return True
    if 'Cost Per' in line or 'Serving' in line:
        return True
    if 'Copyright' in line:
        return True
    return False


def _parse_line(line: str) -> dict:
    """Parse a single line for recipe data."""
    result = {
        'has_ref': False,
        'ref': None,
        'has_name': False,
        'name': None,
        'station': None,
        'calories': None,
        'cost': None,
        'dietary': [],
        'has_cost': False,
    }

    # Extract cost
    cost_match = re.search(r'\$(\d+\.\d{2})', line)
    if cost_match:
        result['cost'] = float(cost_match.group(1))
        result['has_cost'] = True
        line = line[:cost_match.start()] + ' ' * len(cost_match.group(0)) + line[cost_match.end():]

    # Extract dietary
    if re.search(r'\sVG(?:\s|$)', line):
        result['dietary'] = ['VG']
        line = re.sub(r'\sVG(?:\s|$)', '  ', line)
    elif re.search(r'\sV(?:\s|$)', line):
        result['dietary'] = ['V']
        line = re.sub(r'\sV(?:\s|$)', '  ', line)

    # Extract calories
    cal_match = re.search(r'(?<!\d)(\d{2,4})(?!\d)', line[60:]) if len(line) > 60 else None
    if cal_match:
        cal_val = int(cal_match.group(1))
        if 50 <= cal_val <= 2000:
            result['calories'] = cal_val

    # Extract master ref
    ref_match = re.match(r'^\s*(\d{5,6}(?:\.\d+)?)\s+', line)
    if ref_match:
        result['has_ref'] = True
        result['ref'] = ref_match.group(1)
        line = line[ref_match.end():]
    else:
        ref_only = re.match(r'^\s*(\d{5,6}(?:\.\d+)?)\s*$', line)
        if ref_only:
            result['has_ref'] = True
            result['ref'] = ref_only.group(1)
            return result

    # Extract name (remaining text)
    name_part = ' '.join(line.split()).strip()
    name_part = re.sub(r'^\d{5,6}(?:\.\d+)?\s*', '', name_part)

    if len(name_part) > 2:
        result['name'] = name_part
        result['has_name'] = True

    return result


def _finalize_recipe(entry: dict, theme: str, theme_info: dict) -> dict:
    """Finalize recipe into standard format."""
    name = ' '.join((entry.get('name') or '').split())
    station = entry.get('station', '')

    return {
        'master_ref': entry.get('master_ref'),
        'name': name,
        'station': station or None,
        'station_groups': _get_promo_station_groups(station),
        'calories': entry.get('calories'),
        'cost': entry.get('cost'),
        'dietary': entry.get('dietary', []),
        'theme': theme,
        'theme_dates': theme_info.get('dates', []),
        'theme_window': theme_info.get('window', 0),
        'theme_all_month': theme_info.get('all_month', False),
        'keywords': extract_keywords(name),
    }


def _get_promo_station_groups(station: str) -> list[str]:
    """Map station string to groups."""
    if not station:
        return []

    station_lower = station.lower()
    groups = []

    mappings = {
        'grill': ['grill', 'city grill', 'hot chute'],
        'entree': ['chef', 'table', 'action'],
        'soup': ['soup', 'kettle'],
        'deli': ['deli'],
        'breakfast': ['breakfast', 'wakin', 'buffet'],
        'dessert': ['dessert', 'sweet'],
        'salad': ['salad'],
    }

    for group, keywords in mappings.items():
        if any(kw in station_lower for kw in keywords):
            groups.append(group)

    return groups or ['unknown']
