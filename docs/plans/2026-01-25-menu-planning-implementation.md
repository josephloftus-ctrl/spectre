# Menu Planning Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate Menu Planning Project into Spectre as a consolidated backend module with modern tech stack.

**Architecture:** Consolidated module at `/backend/core/menu_planning/` with SQLAlchemy 2.0 ORM, Pydantic v2 models, pdfplumber for PDF parsing, and polars for data processing. Separate `menu_planning.db` database.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 + aiosqlite, Pydantic v2, pdfplumber, polars, PyYAML

---

## Task 1: Add Dependencies

**Files:**
- Modify: `backend/requirements.txt`

**Step 1: Add new dependencies to requirements.txt**

Add these lines to `backend/requirements.txt`:

```
# Menu Planning
pdfplumber>=0.10.0
polars>=0.20.0
sqlalchemy[asyncio]>=2.0.0
aiosqlite>=0.19.0
pyyaml>=6.0
```

**Step 2: Install dependencies**

Run: `cd backend && source venv/bin/activate && pip install pdfplumber polars "sqlalchemy[asyncio]" aiosqlite pyyaml`

**Step 3: Verify installation**

Run: `python -c "import pdfplumber, polars, sqlalchemy, aiosqlite, yaml; print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add backend/requirements.txt
git commit -m "feat(menu-planning): add dependencies for menu planning module"
```

---

## Task 2: Create Module Structure

**Files:**
- Create: `backend/core/menu_planning/__init__.py`
- Create: `backend/core/menu_planning/config/themes.yaml`
- Create: `backend/core/menu_planning/config/keywords.yaml`

**Step 1: Create directory structure**

Run: `mkdir -p backend/core/menu_planning/{services,utils,config}`

**Step 2: Create __init__.py**

```python
"""
Menu Planning Module

Provides menu replacement recommendations by analyzing cycle menus
against promotional recipe packets.
"""

__version__ = "0.1.0"
```

**Step 3: Create themes.yaml**

```yaml
# Theme definitions by month
# Each theme has dates, window (days before valid), and keywords

2026-02:
  super-bowl:
    name: "Super Bowl"
    dates: ["2026-02-08", "2026-02-09"]
    window: 1
    keywords: ["super bowl", "game day", "tailgate", "football"]

  mardi-gras:
    name: "Mardi Gras"
    dates: ["2026-02-17"]
    window: 3
    keywords: ["mardi gras", "cajun", "creole", "new orleans"]

  valentines:
    name: "Valentine's Day"
    dates: ["2026-02-14"]
    window: 1
    keywords: ["valentine", "heart", "love"]

  fish-friday:
    name: "Fish Friday"
    dates: ["2026-02-06", "2026-02-13", "2026-02-20", "2026-02-27"]
    window: 0
    keywords: ["fish", "seafood", "cod", "shrimp", "salmon"]

  black-history-month:
    name: "Black History Month"
    dates: ["2026-02-03", "2026-02-10", "2026-02-17", "2026-02-24"]
    window: 1
    keywords: ["black history", "soul food", "southern"]

  heart-healthy:
    name: "Wellness - Heart Healthy"
    dates: ["2026-02-04", "2026-02-11", "2026-02-18", "2026-02-25"]
    window: 1
    keywords: ["wellness", "heart healthy", "healthy"]
```

**Step 4: Create keywords.yaml**

```yaml
# Ingredient family definitions for collision detection

families:
  mexican:
    - nachos
    - taco
    - burrito
    - quesadilla
    - carnitas
    - birria

  cajun:
    - cajun
    - creole
    - gumbo
    - jambalaya
    - andouille

  buffalo:
    - buffalo
    - hot wing
    - nashville hot

  bbq:
    - bbq
    - pulled pork
    - brisket
    - smoked

  asian:
    - teriyaki
    - kung pao
    - stir fry
    - fried rice

  seafood:
    - shrimp
    - cod
    - fish
    - salmon
```

**Step 5: Commit**

```bash
git add backend/core/menu_planning/
git commit -m "feat(menu-planning): create module structure with config files"
```

---

## Task 3: Database Schema

**Files:**
- Create: `backend/core/menu_planning/database.py`
- Create: `backend/core/menu_planning/schemas.py`

**Step 1: Create database.py**

```python
"""Database connection and session management for menu planning."""

from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

# Database path
DB_PATH = Path(__file__).parent.parent.parent.parent / "data" / "menu_planning.db"


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


# Engine and session factory
engine = create_async_engine(
    f"sqlite+aiosqlite:///{DB_PATH}",
    echo=False,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    """Create all tables."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    """Get a database session."""
    async with async_session() as session:
        yield session
```

**Step 2: Create schemas.py**

```python
"""SQLAlchemy ORM models for menu planning."""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Integer, Text, DateTime, Date, Numeric, JSON, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from .database import Base


class ProcessingStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class Unit(Base):
    """Unit configuration."""
    __tablename__ = "units"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    station_groups: Mapped[dict] = mapped_column(JSON, default=dict)
    active_stations: Mapped[list] = mapped_column(JSON, default=list)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    cycle_menus: Mapped[list["CycleMenu"]] = relationship(back_populates="unit")


class CycleMenu(Base):
    """Uploaded cycle menu."""
    __tablename__ = "cycle_menus"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    unit_id: Mapped[str] = mapped_column(String(50), ForeignKey("units.id"))
    month: Mapped[str] = mapped_column(String(7))  # YYYY-MM
    filename: Mapped[str] = mapped_column(String(255))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus), default=ProcessingStatus.PENDING
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    unit: Mapped["Unit"] = relationship(back_populates="cycle_menus")
    items: Mapped[list["CycleMenuItem"]] = relationship(back_populates="cycle_menu", cascade="all, delete-orphan")


class CycleMenuItem(Base):
    """Parsed menu item from cycle menu."""
    __tablename__ = "cycle_menu_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cycle_menu_id: Mapped[int] = mapped_column(Integer, ForeignKey("cycle_menus.id"))
    date: Mapped[date] = mapped_column(Date)
    day_of_week: Mapped[str] = mapped_column(String(20))
    week_number: Mapped[int] = mapped_column(Integer)
    meal: Mapped[str] = mapped_column(String(50))
    station: Mapped[str] = mapped_column(String(100))
    station_group: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    item_name: Mapped[str] = mapped_column(String(255))
    keywords: Mapped[list] = mapped_column(JSON, default=list)

    cycle_menu: Mapped["CycleMenu"] = relationship(back_populates="items")


class PromoPacket(Base):
    """Uploaded promotional recipe packet."""
    __tablename__ = "promo_packets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    month: Mapped[str] = mapped_column(String(7))
    theme: Mapped[str] = mapped_column(String(100))
    filename: Mapped[str] = mapped_column(String(255))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus), default=ProcessingStatus.PENDING
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    recipes: Mapped[list["PromoRecipe"]] = relationship(back_populates="packet", cascade="all, delete-orphan")


class PromoRecipe(Base):
    """Parsed recipe from promo packet."""
    __tablename__ = "promo_recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    packet_id: Mapped[int] = mapped_column(Integer, ForeignKey("promo_packets.id"))
    master_ref: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(255))
    station: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    station_groups: Mapped[list] = mapped_column(JSON, default=list)
    calories: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    dietary: Mapped[list] = mapped_column(JSON, default=list)
    theme: Mapped[str] = mapped_column(String(100))
    theme_dates: Mapped[list] = mapped_column(JSON, default=list)
    theme_window: Mapped[int] = mapped_column(Integer, default=0)
    theme_all_month: Mapped[bool] = mapped_column(default=False)
    keywords: Mapped[list] = mapped_column(JSON, default=list)

    packet: Mapped["PromoPacket"] = relationship(back_populates="recipes")


class Recommendation(Base):
    """Generated recommendation run."""
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cycle_menu_id: Mapped[int] = mapped_column(Integer, ForeignKey("cycle_menus.id"))
    run_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    config_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    results: Mapped[list] = mapped_column(JSON, default=list)
    flags: Mapped[dict] = mapped_column(JSON, default=dict)
```

**Step 3: Test schema creation**

Run: `cd backend && source venv/bin/activate && python -c "from core.menu_planning.schemas import *; print('Schema OK')"`

**Step 4: Commit**

```bash
git add backend/core/menu_planning/database.py backend/core/menu_planning/schemas.py
git commit -m "feat(menu-planning): add SQLAlchemy ORM schemas"
```

---

## Task 4: Pydantic Models

**Files:**
- Create: `backend/core/menu_planning/models.py`

**Step 1: Create models.py with request/response models**

```python
"""Pydantic v2 models for API request/response validation."""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


# === Unit Models ===

class UnitCreate(BaseModel):
    id: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    station_groups: dict[str, list[str]] = Field(default_factory=dict)
    active_stations: list[str] = Field(default_factory=list)
    settings: dict = Field(default_factory=dict)


class UnitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    station_groups: dict[str, list[str]]
    active_stations: list[str]
    settings: dict
    created_at: datetime


# === Cycle Menu Models ===

class CycleMenuItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date
    day_of_week: str
    week_number: int
    meal: str
    station: str
    station_group: Optional[str]
    item_name: str
    keywords: list[str]


class CycleMenuResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    unit_id: str
    month: str
    filename: str
    uploaded_at: datetime
    status: str
    error_message: Optional[str]
    items: list[CycleMenuItemResponse] = []


class CycleMenuListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    unit_id: str
    month: str
    filename: str
    uploaded_at: datetime
    status: str
    item_count: int = 0


# === Promo Models ===

class PromoRecipeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    master_ref: str
    name: str
    station: Optional[str]
    station_groups: list[str]
    calories: Optional[int]
    cost: Optional[Decimal]
    dietary: list[str]
    theme: str
    keywords: list[str]


class PromoPacketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    month: str
    theme: str
    filename: str
    uploaded_at: datetime
    status: str
    error_message: Optional[str]
    recipes: list[PromoRecipeResponse] = []


# === Recommendation Models ===

class ScoreBreakdown(BaseModel):
    date_relevance: int = 0
    station_fit: int = 0
    keyword_fit: int = 0
    cost_delta: int = 0
    dietary_value: int = 0
    variety_bonus: int = 0
    total: int = 0


class RecommendationItem(BaseModel):
    date: date
    day_of_week: str
    current_item: dict
    promo_recipe: dict
    scores: ScoreBreakdown
    total_score: int
    why: str = ""


class FlagsReport(BaseModel):
    theme_collisions: list[dict] = []
    weekday_repeats: list[dict] = []
    ingredient_collisions: list[dict] = []
    total_flags: int = 0


class RecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cycle_menu_id: int
    run_at: datetime
    config_snapshot: dict
    results: list[RecommendationItem]
    flags: FlagsReport


class GenerateRequest(BaseModel):
    unit_id: str
    month: str
    min_score: int = Field(default=50, ge=0, le=100)
    max_per_day: int = Field(default=5, ge=1, le=20)


# === Theme Models ===

class ThemeConfig(BaseModel):
    name: str
    dates: list[str] = []
    window: int = 0
    all_month: bool = False
    keywords: list[str] = []


class ThemesResponse(BaseModel):
    themes: dict[str, dict[str, ThemeConfig]]
```

**Step 2: Test model creation**

Run: `cd backend && source venv/bin/activate && python -c "from core.menu_planning.models import *; print('Models OK')"`

**Step 3: Commit**

```bash
git add backend/core/menu_planning/models.py
git commit -m "feat(menu-planning): add Pydantic v2 request/response models"
```

---

## Task 5: PDF Parsing Service

**Files:**
- Create: `backend/core/menu_planning/utils/pdf.py`
- Create: `backend/core/menu_planning/services/parsing.py`

**Step 1: Create pdf.py utility**

```python
"""PDF text extraction using pdfplumber."""

import pdfplumber
from pathlib import Path


def extract_text_from_pdf(pdf_path: Path | str) -> str:
    """Extract text from PDF maintaining layout."""
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text(layout=True)
            if text:
                text_parts.append(text)

    return "\n".join(text_parts)


def extract_tables_from_pdf(pdf_path: Path | str) -> list[list[list[str]]]:
    """Extract tables from PDF as list of tables, each table is list of rows."""
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    all_tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            all_tables.extend(tables or [])

    return all_tables
```

**Step 2: Create parsing.py service**

```python
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
```

**Step 3: Test parsing**

Run: `cd backend && source venv/bin/activate && python -c "from core.menu_planning.services.parsing import extract_keywords; print(extract_keywords('Buffalo Chicken Sandwich'))"`
Expected: `['buffalo', 'chicken', 'sandwich']`

**Step 4: Commit**

```bash
git add backend/core/menu_planning/utils/ backend/core/menu_planning/services/parsing.py
git commit -m "feat(menu-planning): add PDF and Excel parsing services"
```

---

## Task 6: Scoring Service

**Files:**
- Create: `backend/core/menu_planning/services/scoring.py`

**Step 1: Create scoring.py**

```python
"""
Scoring algorithm for menu replacement recommendations.

Factors (total 100 points):
- Date relevance: 25 points
- Station fit: 25 points
- Keyword fit: 20 points
- Cost delta: 15 points
- Dietary value: 10 points
- Variety bonus: 5 points
"""

from collections import Counter, defaultdict
from datetime import datetime, timedelta


def score_replacement(
    menu_item: dict,
    promo_recipe: dict,
    date: str,
    unit_config: dict,
    context: dict
) -> dict:
    """Score a potential menu item replacement."""
    scores = {
        'date_relevance': _score_date_relevance(promo_recipe, date),
        'station_fit': _score_station_fit(menu_item, promo_recipe),
        'keyword_fit': _score_keyword_fit(menu_item, promo_recipe),
        'cost_delta': _score_cost_delta(promo_recipe),
        'dietary_value': _score_dietary_value(promo_recipe, context),
        'variety_bonus': _score_variety_bonus(promo_recipe, context),
    }

    scores['total'] = sum(scores.values())
    scores['passes_threshold'] = scores['total'] >= 50

    return scores


def _score_date_relevance(promo_recipe: dict, date: str) -> int:
    """Score based on theme date alignment."""
    if promo_recipe.get('theme_all_month'):
        return 15

    theme_dates = promo_recipe.get('theme_dates', [])
    window = promo_recipe.get('theme_window', 0)

    if not theme_dates:
        return 0

    target_date = datetime.strptime(date, '%Y-%m-%d').date()
    min_dist = float('inf')

    for theme_date_str in theme_dates:
        theme_date = datetime.strptime(theme_date_str, '%Y-%m-%d').date()
        window_start = theme_date - timedelta(days=window)
        window_end = theme_date

        if window_start <= target_date <= window_end:
            return 25

        if target_date < window_start:
            dist = (window_start - target_date).days
        else:
            dist = (target_date - window_end).days

        min_dist = min(min_dist, dist)

    if min_dist <= 1:
        return 18
    elif min_dist <= 3:
        return 10
    return 0


def _score_station_fit(menu_item: dict, promo_recipe: dict) -> int:
    """Score based on station compatibility."""
    menu_group = menu_item.get('station_group')
    promo_groups = promo_recipe.get('station_groups', [])

    if not menu_group or not promo_groups:
        return 0

    strict_stations = {'dessert', 'soup', 'breakfast', 'salad'}

    if menu_group in strict_stations:
        return 25 if menu_group in promo_groups else 0

    if menu_group in promo_groups:
        return 25

    compatible_pairs = [
        ('grill', 'entree'),
        ('entree', 'grill'),
        ('deli', 'grill'),
        ('grill', 'deli'),
    ]

    for promo_group in promo_groups:
        if (menu_group, promo_group) in compatible_pairs:
            return 15

    return 0


def _score_keyword_fit(menu_item: dict, promo_recipe: dict) -> int:
    """Score based on keyword overlap."""
    menu_keywords = set(menu_item.get('keywords', []))
    promo_keywords = set(promo_recipe.get('keywords', []))

    if not menu_keywords or not promo_keywords:
        return 0

    overlap = len(menu_keywords & promo_keywords)

    if overlap >= 3:
        return 20
    elif overlap == 2:
        return 15
    elif overlap == 1:
        return 8
    return 0


def _score_cost_delta(promo_recipe: dict) -> int:
    """Score based on cost."""
    cost = promo_recipe.get('cost')

    if cost is None:
        return 7

    if cost <= 1.50:
        return 15
    elif cost <= 2.00:
        return 12
    elif cost <= 2.50:
        return 10
    elif cost <= 3.00:
        return 5
    return 0


def _score_dietary_value(promo_recipe: dict, context: dict) -> int:
    """Score based on dietary contribution."""
    dietary = promo_recipe.get('dietary', [])
    day_dietary = context.get('day_dietary', set())

    if not dietary:
        return 3

    for tag in dietary:
        if tag not in day_dietary:
            return 10

    return 3


def _score_variety_bonus(promo_recipe: dict, context: dict) -> int:
    """Score based on usage frequency."""
    used_promos = context.get('used_promos', {})
    master_ref = promo_recipe.get('master_ref')

    usage_count = used_promos.get(master_ref, 0)

    if usage_count == 0:
        return 5
    elif usage_count == 1:
        return 2
    return 0


def generate_recommendations(
    cycle_menu: list[dict],
    promo_recipes: list[dict],
    unit_config: dict,
    month: str
) -> list[dict]:
    """Generate all recommendations for a month."""
    recommendations = []

    menu_by_date = defaultdict(list)
    for item in cycle_menu:
        menu_by_date[item['date']].append(item)

    used_promos = Counter()
    day_dietary = defaultdict(set)

    for date in sorted(menu_by_date.keys()):
        items = menu_by_date[date]
        day_recs = []

        for menu_item in items:
            for promo in promo_recipes:
                context = {
                    'used_promos': used_promos,
                    'day_dietary': day_dietary[date],
                }

                scores = score_replacement(menu_item, promo, date, unit_config, context)

                if scores['passes_threshold']:
                    day_recs.append({
                        'date': date,
                        'day_of_week': menu_item.get('day_of_week'),
                        'week_number': menu_item.get('week_number'),
                        'current_item': menu_item,
                        'promo_recipe': promo,
                        'scores': scores,
                        'total_score': scores['total'],
                    })

        day_recs.sort(key=lambda x: -x['total_score'])

        seen_stations = set()
        for rec in day_recs:
            station = rec['current_item'].get('station_group')
            if station not in seen_stations or rec['total_score'] >= 70:
                recommendations.append(rec)
                seen_stations.add(station)
                used_promos[rec['promo_recipe']['master_ref']] += 1
                for tag in rec['promo_recipe'].get('dietary', []):
                    day_dietary[date].add(tag)

    return recommendations
```

**Step 2: Test scoring**

Run: `cd backend && source venv/bin/activate && python -c "from core.menu_planning.services.scoring import _score_keyword_fit; print(_score_keyword_fit({'keywords': ['buffalo', 'chicken']}, {'keywords': ['buffalo', 'wings', 'chicken']}))"`
Expected: `15`

**Step 3: Commit**

```bash
git add backend/core/menu_planning/services/scoring.py
git commit -m "feat(menu-planning): add scoring service with 6-factor algorithm"
```

---

## Task 7: Guardrails Service

**Files:**
- Create: `backend/core/menu_planning/services/guardrails.py`

**Step 1: Create guardrails.py**

```python
"""Guardrails for recommendation quality control."""

import yaml
from collections import defaultdict
from pathlib import Path


def load_keyword_families(config_path: Path = None) -> dict:
    """Load ingredient family definitions."""
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "keywords.yaml"

    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f)
            return config.get('families', {})
    return {}


def detect_theme_collisions(recommendations: list[dict]) -> list[dict]:
    """Flag multiple conflicting themes on same day."""
    event_themes = {'super-bowl', 'mardi-gras', 'valentines', 'fish-friday'}

    by_date = defaultdict(list)
    for rec in recommendations:
        by_date[rec['date']].append(rec)

    flags = []
    for date, recs in by_date.items():
        day_themes = set()
        for rec in recs:
            theme = rec['promo_recipe'].get('theme')
            if theme in event_themes:
                day_themes.add(theme)

        if len(day_themes) > 1:
            flags.append({
                'type': 'theme_collision',
                'date': date,
                'themes': list(day_themes),
                'message': f"Multiple event themes on {date}: {', '.join(day_themes)}"
            })

    return flags


def detect_weekday_repeats(recommendations: list[dict]) -> list[dict]:
    """Flag same theme on same weekday in consecutive weeks."""
    by_weekday_theme = defaultdict(list)

    for rec in recommendations:
        day = rec.get('day_of_week')
        theme = rec['promo_recipe'].get('theme')
        week = rec.get('week_number')

        if day and theme and week:
            by_weekday_theme[(day, theme)].append((week, rec))

    flags = []
    for (day, theme), week_recs in by_weekday_theme.items():
        week_recs.sort(key=lambda x: x[0])

        for i in range(len(week_recs) - 1):
            week1, _ = week_recs[i]
            week2, _ = week_recs[i + 1]

            if week2 - week1 == 1:
                flags.append({
                    'type': 'weekday_repeat',
                    'day_of_week': day,
                    'theme': theme,
                    'weeks': [week1, week2],
                    'message': f"Theme '{theme}' on {day} in consecutive weeks"
                })

    return flags


def detect_ingredient_collisions(
    recommendations: list[dict],
    keyword_families: dict = None
) -> list[dict]:
    """Flag recipes sharing ingredient families in same week."""
    if keyword_families is None:
        keyword_families = load_keyword_families()

    keyword_to_family = {}
    for family, keywords in keyword_families.items():
        for kw in keywords:
            keyword_to_family[kw.lower()] = family

    by_week = defaultdict(list)
    for rec in recommendations:
        week = rec.get('week_number')
        if week:
            by_week[week].append(rec)

    flags = []
    for week, recs in by_week.items():
        recipe_families = defaultdict(list)

        for rec in recs:
            recipe_name = rec['promo_recipe'].get('name', '')
            recipe_keywords = rec['promo_recipe'].get('keywords', [])
            master_ref = rec['promo_recipe'].get('master_ref')

            for kw in recipe_keywords:
                kw_lower = kw.lower()
                if kw_lower in keyword_to_family:
                    family = keyword_to_family[kw_lower]
                    recipe_families[family].append((master_ref, recipe_name))

        for family, recipes in recipe_families.items():
            unique_refs = set(r[0] for r in recipes)
            if len(unique_refs) > 1:
                flags.append({
                    'type': 'ingredient_collision',
                    'week': week,
                    'family': family,
                    'recipes': list(set(recipes)),
                    'message': f"Week {week}: Multiple '{family}' items"
                })

    return flags


def apply_guardrail_penalties(recommendations: list[dict]) -> list[dict]:
    """Apply score penalties for guardrail violations."""
    weekday_themes = defaultdict(lambda: defaultdict(int))

    for rec in sorted(recommendations, key=lambda x: (x.get('week_number', 0), x['date'])):
        day = rec.get('day_of_week')
        theme = rec['promo_recipe'].get('theme')

        if day and theme:
            prior_uses = weekday_themes[day][theme]
            if prior_uses > 0:
                rec['scores']['weekday_repeat_penalty'] = -20
                rec['scores']['total'] += -20
                rec['total_score'] = rec['scores']['total']

            weekday_themes[day][theme] += 1

    return recommendations


def filter_recommendations(
    recommendations: list[dict],
    max_per_day: int = 5,
    max_per_station_per_day: int = 2,
    min_score: int = 50
) -> list[dict]:
    """Filter and limit recommendations."""
    filtered = [r for r in recommendations if r['total_score'] >= min_score]

    by_date = defaultdict(list)
    for rec in filtered:
        by_date[rec['date']].append(rec)

    result = []
    for date, recs in by_date.items():
        recs.sort(key=lambda x: -x['total_score'])

        station_counts = defaultdict(int)
        day_count = 0

        for rec in recs:
            station = rec['current_item'].get('station_group', 'unknown')

            if day_count >= max_per_day:
                break
            if station_counts[station] >= max_per_station_per_day:
                continue

            result.append(rec)
            station_counts[station] += 1
            day_count += 1

    return result


def generate_flags_report(recommendations: list[dict]) -> dict:
    """Generate comprehensive flags report."""
    theme_collisions = detect_theme_collisions(recommendations)
    weekday_repeats = detect_weekday_repeats(recommendations)
    ingredient_collisions = detect_ingredient_collisions(recommendations)

    return {
        'theme_collisions': theme_collisions,
        'weekday_repeats': weekday_repeats,
        'ingredient_collisions': ingredient_collisions,
        'total_flags': len(theme_collisions) + len(weekday_repeats) + len(ingredient_collisions)
    }
```

**Step 2: Test guardrails**

Run: `cd backend && source venv/bin/activate && python -c "from core.menu_planning.services.guardrails import load_keyword_families; print(len(load_keyword_families()))"`
Expected: A number > 0 (count of families)

**Step 3: Commit**

```bash
git add backend/core/menu_planning/services/guardrails.py
git commit -m "feat(menu-planning): add guardrails service for quality control"
```

---

## Task 8: Output Service

**Files:**
- Create: `backend/core/menu_planning/services/output.py`

**Step 1: Create output.py**

```python
"""Output generation for recommendations."""

from collections import defaultdict
from datetime import datetime


THEME_DISPLAY = {
    'super-bowl': ('Super Bowl', '🏈'),
    'mardi-gras': ('Mardi Gras', '🎭'),
    'valentines': ("Valentine's Day", '❤️'),
    'fish-friday': ('Fish Friday', '🐟'),
    'black-history-month': ('Black History Month', '✊'),
    'heart-healthy': ('Heart Healthy', '💚'),
}

FLAVOR_KEYWORDS = {
    'spicy': {'spicy', 'hot', 'buffalo', 'nashville', 'cajun'},
    'comfort': {'mac', 'cheese', 'melt', 'grilled', 'fried'},
    'hearty': {'beef', 'pork', 'brisket', 'pulled', 'bbq'},
    'light': {'salad', 'grilled', 'fresh', 'veggie'},
    'indulgent': {'bacon', 'cheese', 'loaded', 'stuffed'},
}


def generate_why(rec: dict) -> str:
    """Generate plain-English explanation for recommendation."""
    parts = []
    scores = rec.get('scores', {})

    keyword_score = scores.get('keyword_fit', 0)
    if keyword_score >= 15:
        menu_kw = set(k.lower() for k in rec['current_item'].get('keywords', []))
        promo_kw = set(k.lower() for k in rec['promo_recipe'].get('keywords', []))
        shared = menu_kw & promo_kw

        flavor = None
        for f, words in FLAVOR_KEYWORDS.items():
            if shared & words:
                flavor = f
                break

        if flavor == 'spicy':
            parts.append("Both are spicy favorites")
        elif flavor == 'comfort':
            parts.append("Both are comfort food")
        elif flavor == 'hearty':
            parts.append("Both are hearty and filling")
        elif shared:
            sample = list(shared)[:2]
            parts.append(f"Similar style ({', '.join(sample)})")

    station_score = scores.get('station_fit', 0)
    if station_score >= 25:
        parts.append("Same station")
    elif station_score >= 15:
        parts.append("Compatible station")

    date_score = scores.get('date_relevance', 0)
    if date_score >= 25:
        parts.append("Perfect timing for theme")
    elif date_score >= 15:
        parts.append("Good timing")

    dietary_score = scores.get('dietary_value', 0)
    if dietary_score >= 10:
        dietary = rec['promo_recipe'].get('dietary', [])
        if dietary:
            parts.append(f"Adds {'/'.join(dietary)} option")

    return ". ".join(parts) + "." if parts else "Good overall fit."


def select_tiers(theme_recs: list[dict]) -> tuple[list[dict], list[dict]]:
    """Select top picks and also-consider items."""
    seen_refs = {}
    for rec in sorted(theme_recs, key=lambda x: -x['total_score']):
        ref = rec['promo_recipe']['master_ref']
        if ref not in seen_refs:
            seen_refs[ref] = rec

    unique_recs = list(seen_refs.values())

    top_picks = []
    seen_stations = set()
    for rec in unique_recs:
        station = rec['current_item'].get('station_group', 'unknown')
        if station not in seen_stations and len(top_picks) < 2:
            if rec['total_score'] >= 70 or len(top_picks) == 0:
                top_picks.append(rec)
                seen_stations.add(station)

    if not top_picks and unique_recs:
        top_picks = [unique_recs[0]]

    top_refs = {r['promo_recipe']['master_ref'] for r in top_picks}
    also_consider = [
        r for r in unique_recs
        if r['promo_recipe']['master_ref'] not in top_refs
        and r['total_score'] >= 55
    ][:3]

    return top_picks, also_consider


def generate_calendar_markdown(
    recommendations: list[dict],
    unit_config: dict,
    month: str
) -> str:
    """Generate markdown calendar output."""
    lines = []
    DIVIDER = "═" * 65

    month_dt = datetime.strptime(month + '-01', '%Y-%m-%d')
    month_name = month_dt.strftime('%B %Y')
    unit_name = unit_config.get('name', unit_config.get('unit_id', 'Unknown'))

    lines.append(DIVIDER)
    lines.append(f"  {month_name} Menu Recommendations")
    lines.append(f"  {unit_name}")
    lines.append(DIVIDER)
    lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    by_theme = defaultdict(list)
    for rec in recommendations:
        theme = rec['promo_recipe'].get('theme', 'other')
        by_theme[theme].append(rec)

    def theme_sort_key(theme):
        recs = by_theme[theme]
        dates = [r['date'] for r in recs]
        return min(dates) if dates else '9999'

    for theme in sorted(by_theme.keys(), key=theme_sort_key):
        theme_recs = by_theme[theme]

        if theme in THEME_DISPLAY:
            theme_name, emoji = THEME_DISPLAY[theme]
        else:
            theme_name = theme.replace('-', ' ').title()
            emoji = '📋'

        dates = sorted(set(r['date'] for r in theme_recs))
        date_strs = []
        for d in dates[:4]:
            dt = datetime.strptime(d, '%Y-%m-%d')
            date_strs.append(dt.strftime('%a %b %d'))
        dates_display = ', '.join(date_strs)

        lines.append("")
        lines.append(DIVIDER)
        lines.append(f"  {emoji} {theme_name.upper()}")
        lines.append(f"  Feature on: {dates_display}")
        lines.append(DIVIDER)

        top_picks, also_consider = select_tiers(theme_recs)

        if top_picks:
            lines.append("")
            lines.append("  TOP PICK")
            lines.append("")

            for rec in top_picks:
                promo = rec['promo_recipe']
                current = rec['current_item']

                lines.append(f"  {promo.get('name', '')[:50]}")
                lines.append(f"    → replaces {current.get('item_name', '')[:35]}")
                lines.append("  " + "─" * 61)
                lines.append(f"  Why: {generate_why(rec)}")

                details = []
                if promo.get('cost'):
                    details.append(f"${promo['cost']:.2f}")
                if promo.get('station'):
                    details.append(promo['station'][:20])
                if promo.get('master_ref'):
                    details.append(f"#{promo['master_ref']}")
                lines.append(f"  {' | '.join(details)}")
                lines.append("")

        if also_consider:
            lines.append("")
            lines.append("  ALSO CONSIDER")
            lines.append("")

            for rec in also_consider:
                promo = rec['promo_recipe']
                current = rec['current_item']

                lines.append(f"  • {promo.get('name', '')[:40]}")
                lines.append(f"    → replaces {current.get('item_name', '')[:25]}")

                why = generate_why(rec).split('.')[0] + '.'
                cost_str = f"${promo['cost']:.2f}" if promo.get('cost') else ""
                lines.append(f"    {why} {cost_str} | #{promo.get('master_ref', '')}")
                lines.append("")

        lines.append("─" * 65)

    return '\n'.join(lines)


def generate_flags_markdown(flags: dict) -> str:
    """Generate flags markdown output."""
    lines = []

    lines.append("# Needs Review")
    lines.append("")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    total = flags.get('total_flags', 0)
    if total == 0:
        lines.append("No flags - all recommendations look good!")
        return '\n'.join(lines)

    lines.append(f"**Total flags:** {total}")
    lines.append("")

    if flags.get('theme_collisions'):
        lines.append("## Theme Collisions")
        lines.append("")
        for flag in flags['theme_collisions']:
            lines.append(f"- **{flag['date']}:** {', '.join(flag['themes'])}")
        lines.append("")

    if flags.get('weekday_repeats'):
        lines.append("## Weekday Repeats")
        lines.append("")
        for flag in flags['weekday_repeats']:
            lines.append(f"- **{flag['day_of_week']}:** '{flag['theme']}' in weeks {flag['weeks']}")
        lines.append("")

    if flags.get('ingredient_collisions'):
        lines.append("## Ingredient Family Collisions")
        lines.append("")
        for flag in flags['ingredient_collisions']:
            lines.append(f"### Week {flag['week']}: {flag['family'].title()}")
            for ref, name in flag['recipes']:
                lines.append(f"- {name} ({ref})")
            lines.append("")

    return '\n'.join(lines)
```

**Step 2: Test output**

Run: `cd backend && source venv/bin/activate && python -c "from core.menu_planning.services.output import generate_why; print(generate_why({'scores': {'keyword_fit': 20, 'station_fit': 25, 'date_relevance': 25}, 'current_item': {'keywords': ['buffalo']}, 'promo_recipe': {'keywords': ['buffalo', 'hot'], 'dietary': []}}))"`

**Step 3: Commit**

```bash
git add backend/core/menu_planning/services/output.py
git commit -m "feat(menu-planning): add output service for markdown generation"
```

---

## Task 9: Services __init__.py

**Files:**
- Create: `backend/core/menu_planning/services/__init__.py`

**Step 1: Create services/__init__.py**

```python
"""Menu planning services."""

from .parsing import (
    parse_cycle_menu,
    parse_promo_pdf,
    extract_keywords,
    extract_theme_from_filename,
)
from .scoring import (
    score_replacement,
    generate_recommendations,
)
from .guardrails import (
    apply_guardrail_penalties,
    filter_recommendations,
    generate_flags_report,
)
from .output import (
    generate_why,
    generate_calendar_markdown,
    generate_flags_markdown,
)

__all__ = [
    'parse_cycle_menu',
    'parse_promo_pdf',
    'extract_keywords',
    'extract_theme_from_filename',
    'score_replacement',
    'generate_recommendations',
    'apply_guardrail_penalties',
    'filter_recommendations',
    'generate_flags_report',
    'generate_why',
    'generate_calendar_markdown',
    'generate_flags_markdown',
]
```

**Step 2: Commit**

```bash
git add backend/core/menu_planning/services/__init__.py
git commit -m "feat(menu-planning): add services module exports"
```

---

## Task 10: API Router

**Files:**
- Create: `backend/core/menu_planning/router.py`

**Step 1: Create router.py**

```python
"""FastAPI router for menu planning endpoints."""

import yaml
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .database import get_session, init_db
from .schemas import (
    Unit, CycleMenu, CycleMenuItem, PromoPacket, PromoRecipe,
    Recommendation, ProcessingStatus
)
from .models import (
    UnitCreate, UnitResponse, CycleMenuResponse, CycleMenuListResponse,
    PromoPacketResponse, RecommendationResponse, GenerateRequest, ThemesResponse
)
from .services import (
    parse_cycle_menu, parse_promo_pdf, extract_theme_from_filename,
    generate_recommendations, apply_guardrail_penalties,
    filter_recommendations, generate_flags_report,
    generate_calendar_markdown, generate_flags_markdown, generate_why
)

router = APIRouter(prefix="/menu-planning", tags=["menu-planning"])

CONFIG_PATH = Path(__file__).parent / "config"
UPLOAD_PATH = Path(__file__).parent.parent.parent.parent / "data" / "menu_planning_uploads"


@router.on_event("startup")
async def startup():
    """Initialize database on startup."""
    await init_db()
    UPLOAD_PATH.mkdir(parents=True, exist_ok=True)


# === Units ===

@router.get("/units", response_model=list[UnitResponse])
async def list_units(session: AsyncSession = Depends(get_session)):
    """List all units."""
    result = await session.execute(select(Unit))
    return result.scalars().all()


@router.post("/units", response_model=UnitResponse)
async def create_unit(unit: UnitCreate, session: AsyncSession = Depends(get_session)):
    """Create a new unit."""
    db_unit = Unit(**unit.model_dump())
    session.add(db_unit)
    await session.commit()
    await session.refresh(db_unit)
    return db_unit


@router.get("/units/{unit_id}", response_model=UnitResponse)
async def get_unit(unit_id: str, session: AsyncSession = Depends(get_session)):
    """Get a unit by ID."""
    result = await session.execute(select(Unit).where(Unit.id == unit_id))
    unit = result.scalar_one_or_none()
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    return unit


@router.put("/units/{unit_id}", response_model=UnitResponse)
async def update_unit(unit_id: str, unit: UnitCreate, session: AsyncSession = Depends(get_session)):
    """Update a unit."""
    result = await session.execute(select(Unit).where(Unit.id == unit_id))
    db_unit = result.scalar_one_or_none()
    if not db_unit:
        raise HTTPException(status_code=404, detail="Unit not found")

    for key, value in unit.model_dump().items():
        setattr(db_unit, key, value)

    await session.commit()
    await session.refresh(db_unit)
    return db_unit


# === Themes ===

@router.get("/themes", response_model=ThemesResponse)
async def get_themes():
    """Get theme definitions."""
    themes_path = CONFIG_PATH / "themes.yaml"
    if themes_path.exists():
        with open(themes_path) as f:
            themes = yaml.safe_load(f) or {}
    else:
        themes = {}
    return ThemesResponse(themes=themes)


@router.put("/themes")
async def update_themes(themes: dict):
    """Update theme definitions."""
    themes_path = CONFIG_PATH / "themes.yaml"
    with open(themes_path, 'w') as f:
        yaml.dump(themes, f)
    return {"status": "ok"}


# === Cycle Menus ===

@router.post("/cycle-menus/upload")
async def upload_cycle_menu(
    unit_id: str,
    month: str,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    session: AsyncSession = Depends(get_session)
):
    """Upload a cycle menu xlsx file."""
    # Verify unit exists
    result = await session.execute(select(Unit).where(Unit.id == unit_id))
    unit = result.scalar_one_or_none()
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")

    # Save file
    file_path = UPLOAD_PATH / f"{unit_id}_{month}_{file.filename}"
    content = await file.read()
    file_path.write_bytes(content)

    # Create record
    cycle_menu = CycleMenu(
        unit_id=unit_id,
        month=month,
        filename=file.filename,
        status=ProcessingStatus.PENDING
    )
    session.add(cycle_menu)
    await session.commit()
    await session.refresh(cycle_menu)

    # Process in background
    if background_tasks:
        background_tasks.add_task(
            process_cycle_menu,
            cycle_menu.id,
            file_path,
            unit.station_groups
        )

    return {"id": cycle_menu.id, "status": "processing"}


async def process_cycle_menu(menu_id: int, file_path: Path, station_groups: dict):
    """Background task to process cycle menu."""
    from .database import async_session

    async with async_session() as session:
        result = await session.execute(select(CycleMenu).where(CycleMenu.id == menu_id))
        menu = result.scalar_one()

        try:
            menu.status = ProcessingStatus.PROCESSING
            await session.commit()

            items = parse_cycle_menu(file_path, {'station_groups': station_groups})

            for item in items:
                db_item = CycleMenuItem(
                    cycle_menu_id=menu_id,
                    date=item['date'],
                    day_of_week=item['day_of_week'],
                    week_number=item['week_number'],
                    meal=item['meal'],
                    station=item['station'],
                    station_group=item['station_group'],
                    item_name=item['item_name'],
                    keywords=item['keywords']
                )
                session.add(db_item)

            menu.status = ProcessingStatus.COMPLETED
            await session.commit()

        except Exception as e:
            menu.status = ProcessingStatus.ERROR
            menu.error_message = str(e)
            await session.commit()


@router.get("/cycle-menus", response_model=list[CycleMenuListResponse])
async def list_cycle_menus(
    unit_id: Optional[str] = None,
    month: Optional[str] = None,
    session: AsyncSession = Depends(get_session)
):
    """List cycle menus."""
    query = select(CycleMenu)
    if unit_id:
        query = query.where(CycleMenu.unit_id == unit_id)
    if month:
        query = query.where(CycleMenu.month == month)

    result = await session.execute(query.options(selectinload(CycleMenu.items)))
    menus = result.scalars().all()

    return [
        CycleMenuListResponse(
            id=m.id,
            unit_id=m.unit_id,
            month=m.month,
            filename=m.filename,
            uploaded_at=m.uploaded_at,
            status=m.status.value,
            item_count=len(m.items)
        )
        for m in menus
    ]


@router.get("/cycle-menus/{menu_id}", response_model=CycleMenuResponse)
async def get_cycle_menu(menu_id: int, session: AsyncSession = Depends(get_session)):
    """Get a cycle menu with items."""
    result = await session.execute(
        select(CycleMenu)
        .where(CycleMenu.id == menu_id)
        .options(selectinload(CycleMenu.items))
    )
    menu = result.scalar_one_or_none()
    if not menu:
        raise HTTPException(status_code=404, detail="Cycle menu not found")

    return CycleMenuResponse(
        id=menu.id,
        unit_id=menu.unit_id,
        month=menu.month,
        filename=menu.filename,
        uploaded_at=menu.uploaded_at,
        status=menu.status.value,
        error_message=menu.error_message,
        items=[CycleMenuResponse.model_fields['items'].annotation.__args__[0].model_validate(i) for i in menu.items]
    )


@router.delete("/cycle-menus/{menu_id}")
async def delete_cycle_menu(menu_id: int, session: AsyncSession = Depends(get_session)):
    """Delete a cycle menu."""
    result = await session.execute(select(CycleMenu).where(CycleMenu.id == menu_id))
    menu = result.scalar_one_or_none()
    if not menu:
        raise HTTPException(status_code=404, detail="Cycle menu not found")

    await session.delete(menu)
    await session.commit()
    return {"status": "deleted"}


# === Promos ===

@router.post("/promos/upload")
async def upload_promo(
    month: str,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    session: AsyncSession = Depends(get_session)
):
    """Upload a promo PDF."""
    theme = extract_theme_from_filename(file.filename)

    file_path = UPLOAD_PATH / f"promo_{month}_{file.filename}"
    content = await file.read()
    file_path.write_bytes(content)

    packet = PromoPacket(
        month=month,
        theme=theme,
        filename=file.filename,
        status=ProcessingStatus.PENDING
    )
    session.add(packet)
    await session.commit()
    await session.refresh(packet)

    if background_tasks:
        background_tasks.add_task(process_promo_packet, packet.id, file_path, month)

    return {"id": packet.id, "theme": theme, "status": "processing"}


async def process_promo_packet(packet_id: int, file_path: Path, month: str):
    """Background task to process promo PDF."""
    from .database import async_session

    async with async_session() as session:
        result = await session.execute(select(PromoPacket).where(PromoPacket.id == packet_id))
        packet = result.scalar_one()

        try:
            packet.status = ProcessingStatus.PROCESSING
            await session.commit()

            themes_path = CONFIG_PATH / "themes.yaml"
            themes_config = {}
            if themes_path.exists():
                with open(themes_path) as f:
                    themes_config = yaml.safe_load(f) or {}

            recipes = parse_promo_pdf(file_path, themes_config, month)

            for recipe in recipes:
                db_recipe = PromoRecipe(
                    packet_id=packet_id,
                    master_ref=recipe['master_ref'],
                    name=recipe['name'],
                    station=recipe['station'],
                    station_groups=recipe['station_groups'],
                    calories=recipe['calories'],
                    cost=recipe['cost'],
                    dietary=recipe['dietary'],
                    theme=recipe['theme'],
                    theme_dates=recipe['theme_dates'],
                    theme_window=recipe['theme_window'],
                    theme_all_month=recipe['theme_all_month'],
                    keywords=recipe['keywords']
                )
                session.add(db_recipe)

            packet.status = ProcessingStatus.COMPLETED
            await session.commit()

        except Exception as e:
            packet.status = ProcessingStatus.ERROR
            packet.error_message = str(e)
            await session.commit()


@router.get("/promos", response_model=list[PromoPacketResponse])
async def list_promos(
    month: Optional[str] = None,
    theme: Optional[str] = None,
    session: AsyncSession = Depends(get_session)
):
    """List promo packets."""
    query = select(PromoPacket)
    if month:
        query = query.where(PromoPacket.month == month)
    if theme:
        query = query.where(PromoPacket.theme == theme)

    result = await session.execute(query.options(selectinload(PromoPacket.recipes)))
    return result.scalars().all()


@router.get("/promos/{packet_id}", response_model=PromoPacketResponse)
async def get_promo(packet_id: int, session: AsyncSession = Depends(get_session)):
    """Get a promo packet with recipes."""
    result = await session.execute(
        select(PromoPacket)
        .where(PromoPacket.id == packet_id)
        .options(selectinload(PromoPacket.recipes))
    )
    packet = result.scalar_one_or_none()
    if not packet:
        raise HTTPException(status_code=404, detail="Promo packet not found")
    return packet


@router.delete("/promos/{packet_id}")
async def delete_promo(packet_id: int, session: AsyncSession = Depends(get_session)):
    """Delete a promo packet."""
    result = await session.execute(select(PromoPacket).where(PromoPacket.id == packet_id))
    packet = result.scalar_one_or_none()
    if not packet:
        raise HTTPException(status_code=404, detail="Promo packet not found")

    await session.delete(packet)
    await session.commit()
    return {"status": "deleted"}


# === Recommendations ===

@router.post("/recommendations/generate")
async def generate_recs(
    request: GenerateRequest,
    session: AsyncSession = Depends(get_session)
):
    """Generate recommendations for a unit and month."""
    # Get unit
    result = await session.execute(select(Unit).where(Unit.id == request.unit_id))
    unit = result.scalar_one_or_none()
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")

    # Get cycle menu
    result = await session.execute(
        select(CycleMenu)
        .where(CycleMenu.unit_id == request.unit_id)
        .where(CycleMenu.month == request.month)
        .where(CycleMenu.status == ProcessingStatus.COMPLETED)
        .options(selectinload(CycleMenu.items))
    )
    menu = result.scalar_one_or_none()
    if not menu:
        raise HTTPException(status_code=404, detail="No completed cycle menu found")

    # Get promos
    result = await session.execute(
        select(PromoPacket)
        .where(PromoPacket.month == request.month)
        .where(PromoPacket.status == ProcessingStatus.COMPLETED)
        .options(selectinload(PromoPacket.recipes))
    )
    packets = result.scalars().all()

    if not packets:
        raise HTTPException(status_code=404, detail="No completed promo packets found")

    # Convert to dicts
    cycle_items = [
        {
            'date': str(i.date),
            'day_of_week': i.day_of_week,
            'week_number': i.week_number,
            'meal': i.meal,
            'station': i.station,
            'station_group': i.station_group,
            'item_name': i.item_name,
            'keywords': i.keywords
        }
        for i in menu.items
    ]

    promo_recipes = []
    for p in packets:
        for r in p.recipes:
            promo_recipes.append({
                'master_ref': r.master_ref,
                'name': r.name,
                'station': r.station,
                'station_groups': r.station_groups,
                'calories': r.calories,
                'cost': float(r.cost) if r.cost else None,
                'dietary': r.dietary,
                'theme': r.theme,
                'theme_dates': r.theme_dates,
                'theme_window': r.theme_window,
                'theme_all_month': r.theme_all_month,
                'keywords': r.keywords
            })

    unit_config = {
        'unit_id': unit.id,
        'name': unit.name,
        'station_groups': unit.station_groups
    }

    # Generate
    recs = generate_recommendations(cycle_items, promo_recipes, unit_config, request.month)
    recs = apply_guardrail_penalties(recs)
    filtered = filter_recommendations(recs, max_per_day=request.max_per_day, min_score=request.min_score)
    flags = generate_flags_report(filtered)

    # Add why to each rec
    for rec in filtered:
        rec['why'] = generate_why(rec)

    # Save
    db_rec = Recommendation(
        cycle_menu_id=menu.id,
        config_snapshot={'min_score': request.min_score, 'max_per_day': request.max_per_day},
        results=filtered,
        flags=flags
    )
    session.add(db_rec)
    await session.commit()
    await session.refresh(db_rec)

    return {"id": db_rec.id, "count": len(filtered), "flags": flags['total_flags']}


@router.get("/recommendations", response_model=list[dict])
async def list_recommendations(session: AsyncSession = Depends(get_session)):
    """List recommendation runs."""
    result = await session.execute(select(Recommendation))
    recs = result.scalars().all()
    return [
        {
            'id': r.id,
            'cycle_menu_id': r.cycle_menu_id,
            'run_at': r.run_at,
            'result_count': len(r.results),
            'flag_count': r.flags.get('total_flags', 0)
        }
        for r in recs
    ]


@router.get("/recommendations/{rec_id}")
async def get_recommendation(rec_id: int, session: AsyncSession = Depends(get_session)):
    """Get recommendation details."""
    result = await session.execute(select(Recommendation).where(Recommendation.id == rec_id))
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    return {
        'id': rec.id,
        'cycle_menu_id': rec.cycle_menu_id,
        'run_at': rec.run_at,
        'config_snapshot': rec.config_snapshot,
        'results': rec.results,
        'flags': rec.flags
    }


@router.get("/recommendations/{rec_id}/export")
async def export_recommendation(rec_id: int, session: AsyncSession = Depends(get_session)):
    """Export recommendation as markdown."""
    result = await session.execute(
        select(Recommendation)
        .where(Recommendation.id == rec_id)
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    # Get unit info
    result = await session.execute(
        select(CycleMenu).where(CycleMenu.id == rec.cycle_menu_id)
    )
    menu = result.scalar_one()

    result = await session.execute(select(Unit).where(Unit.id == menu.unit_id))
    unit = result.scalar_one()

    unit_config = {'unit_id': unit.id, 'name': unit.name}

    calendar_md = generate_calendar_markdown(rec.results, unit_config, menu.month)
    flags_md = generate_flags_markdown(rec.flags)

    return {
        'calendar': calendar_md,
        'flags': flags_md
    }
```

**Step 2: Commit**

```bash
git add backend/core/menu_planning/router.py
git commit -m "feat(menu-planning): add FastAPI router with all endpoints"
```

---

## Task 11: Register Router

**Files:**
- Modify: `backend/api/main.py`

**Step 1: Add menu planning router import and registration**

Find the router imports section in `backend/api/main.py` and add:

```python
from backend.core.menu_planning.router import router as menu_planning_router
```

Find where routers are registered (app.include_router calls) and add:

```python
app.include_router(menu_planning_router, prefix="/api")
```

**Step 2: Test import**

Run: `cd backend && source venv/bin/activate && python -c "from api.main import app; print([r.path for r in app.routes if 'menu' in r.path])"`

**Step 3: Commit**

```bash
git add backend/api/main.py
git commit -m "feat(menu-planning): register menu planning router in main app"
```

---

## Task 12: Create utils __init__.py

**Files:**
- Create: `backend/core/menu_planning/utils/__init__.py`

**Step 1: Create utils/__init__.py**

```python
"""Menu planning utilities."""

from .pdf import extract_text_from_pdf, extract_tables_from_pdf

__all__ = ['extract_text_from_pdf', 'extract_tables_from_pdf']
```

**Step 2: Commit**

```bash
git add backend/core/menu_planning/utils/__init__.py
git commit -m "feat(menu-planning): add utils module exports"
```

---

## Task 13: Integration Test

**Files:**
- Create: `backend/core/menu_planning/tests/__init__.py`
- Create: `backend/core/menu_planning/tests/test_scoring.py`

**Step 1: Create test directory**

Run: `mkdir -p backend/core/menu_planning/tests`

**Step 2: Create test_scoring.py**

```python
"""Tests for scoring service."""

import pytest
from ..services.scoring import (
    score_replacement,
    _score_keyword_fit,
    _score_station_fit,
    _score_date_relevance,
)


def test_keyword_fit_strong_match():
    """3+ shared keywords = 20 points."""
    menu = {'keywords': ['buffalo', 'chicken', 'sandwich', 'spicy']}
    promo = {'keywords': ['buffalo', 'chicken', 'wings', 'spicy']}
    assert _score_keyword_fit(menu, promo) == 20


def test_keyword_fit_good_match():
    """2 shared keywords = 15 points."""
    menu = {'keywords': ['buffalo', 'chicken']}
    promo = {'keywords': ['buffalo', 'wings', 'chicken']}
    assert _score_keyword_fit(menu, promo) == 15


def test_keyword_fit_weak_match():
    """1 shared keyword = 8 points."""
    menu = {'keywords': ['chicken']}
    promo = {'keywords': ['chicken', 'teriyaki']}
    assert _score_keyword_fit(menu, promo) == 8


def test_keyword_fit_no_match():
    """0 shared keywords = 0 points."""
    menu = {'keywords': ['beef']}
    promo = {'keywords': ['chicken']}
    assert _score_keyword_fit(menu, promo) == 0


def test_station_fit_exact_match():
    """Same station group = 25 points."""
    menu = {'station_group': 'grill'}
    promo = {'station_groups': ['grill', 'entree']}
    assert _score_station_fit(menu, promo) == 25


def test_station_fit_compatible():
    """Compatible groups = 15 points."""
    menu = {'station_group': 'grill'}
    promo = {'station_groups': ['entree']}
    assert _score_station_fit(menu, promo) == 15


def test_station_fit_strict_mismatch():
    """Strict stations don't cross-match."""
    menu = {'station_group': 'soup'}
    promo = {'station_groups': ['grill']}
    assert _score_station_fit(menu, promo) == 0


def test_date_relevance_direct_hit():
    """Within theme window = 25 points."""
    promo = {'theme_dates': ['2026-02-08'], 'theme_window': 1}
    assert _score_date_relevance(promo, '2026-02-08') == 25
    assert _score_date_relevance(promo, '2026-02-07') == 25  # Within window


def test_date_relevance_near():
    """±1 day from window = 18 points."""
    promo = {'theme_dates': ['2026-02-08'], 'theme_window': 0}
    assert _score_date_relevance(promo, '2026-02-09') == 18


def test_date_relevance_far():
    """±3 days = 10 points."""
    promo = {'theme_dates': ['2026-02-08'], 'theme_window': 0}
    assert _score_date_relevance(promo, '2026-02-11') == 10


def test_date_relevance_outside():
    """Outside window = 0 points."""
    promo = {'theme_dates': ['2026-02-08'], 'theme_window': 0}
    assert _score_date_relevance(promo, '2026-02-20') == 0


def test_date_relevance_all_month():
    """All-month themes = 15 points."""
    promo = {'theme_all_month': True}
    assert _score_date_relevance(promo, '2026-02-15') == 15
```

**Step 3: Run tests**

Run: `cd backend && source venv/bin/activate && python -m pytest core/menu_planning/tests/test_scoring.py -v`
Expected: All tests pass

**Step 4: Commit**

```bash
git add backend/core/menu_planning/tests/
git commit -m "test(menu-planning): add scoring service tests"
```

---

## Summary

This plan creates a complete menu planning integration with:

1. **Dependencies** - pdfplumber, polars, SQLAlchemy 2.0, aiosqlite
2. **Module structure** - Consolidated under `/backend/core/menu_planning/`
3. **Database** - SQLAlchemy ORM with async support, separate `menu_planning.db`
4. **Models** - Pydantic v2 for request/response validation
5. **Services** - Parsing, scoring, guardrails, output generation
6. **Router** - Full CRUD for units, cycle menus, promos, recommendations
7. **Tests** - Basic scoring tests

**Total tasks:** 13
**Estimated commits:** 13
