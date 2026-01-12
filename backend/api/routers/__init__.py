"""
API Routers package.

Each module contains a FastAPI router for a specific domain.
"""

from .inventory import router as inventory_router
from .files import router as files_router
from .jobs import router as jobs_router, stats_router, maintenance_router, worker_router
from .search import router as search_router
from .collections import router as collections_router
from .analysis import router as analysis_router
from .scores import router as scores_router
from .sites import router as sites_router
from .cart import router as cart_router
from .catalog import router as catalog_router
from .counting import router as counting_router
from .locations import router as locations_router
from .snapshots import router as snapshots_router
from .export import router as export_router
from .purchase_match import router as purchase_match_router
from .standup import router as standup_router
from .helpdesk import router as helpdesk_router
from .memory import router as memory_router
from .templates import router as templates_router
from .history import router as history_router

__all__ = [
    "inventory_router",
    "files_router",
    "jobs_router",
    "stats_router",
    "maintenance_router",
    "worker_router",
    "search_router",
    "collections_router",
    "analysis_router",
    "scores_router",
    "sites_router",
    "cart_router",
    "catalog_router",
    "counting_router",
    "locations_router",
    "snapshots_router",
    "export_router",
    "purchase_match_router",
    "standup_router",
    "helpdesk_router",
    "memory_router",
    "templates_router",
    "history_router",
]
