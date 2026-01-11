# SPEC-007: Purchase Match Diagnostic
# Siloed module - no imports from other Nebula components

from .models import PurchaseRecord, InventoryRecord, MatchResult, MatchFlag
from .config import load_config, get_approved_vendors, normalize_vendor, Config
from .canon_loader import load_canon
from .index import build_index, CanonIndex
from .adapters import InventoryAdapter, MockInventoryAdapter, InMemoryInventoryAdapter
from .matcher import match_inventory, summarize_results
from .report import format_console, export_csv

__version__ = "1.0.0"

__all__ = [
    # Models
    "PurchaseRecord",
    "InventoryRecord",
    "MatchResult",
    "MatchFlag",
    # Config
    "Config",
    "load_config",
    "get_approved_vendors",
    "normalize_vendor",
    # Canon
    "load_canon",
    "build_index",
    "CanonIndex",
    # Adapters
    "InventoryAdapter",
    "MockInventoryAdapter",
    "InMemoryInventoryAdapter",
    # Matcher
    "match_inventory",
    "summarize_results",
    # Report
    "format_console",
    "export_csv",
]
