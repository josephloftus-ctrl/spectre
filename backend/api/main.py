"""
Spectre Inventory Platform - FastAPI Application

This is the main entry point for the API. All endpoint logic has been
moved to domain-specific routers in the routers/ directory.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import sys

# Add parent directory to path to allow importing core
sys.path.append(str(Path(__file__).resolve().parents[2]))

from backend.core.config import settings
from backend.core.worker import init_worker, stop_scheduler

# Import all routers
from backend.api.routers import (
    inventory_router,
    files_router,
    jobs_router,
    stats_router,
    maintenance_router,
    worker_router,
    search_router,
    collections_router,
    analysis_router,
    scores_router,
    sites_router,
    cart_router,
    catalog_router,
    counting_router,
    locations_router,
    snapshots_router,
    export_router,
    purchase_match_router,
    standup_router,
    helpdesk_router,
    memory_router,
    templates_router,
    history_router,
    rooms_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown."""
    # Startup
    try:
        init_worker()
    except Exception as e:
        print(f"Warning: Failed to start worker: {e}")

    yield  # Application runs here

    # Shutdown
    stop_scheduler()


app = FastAPI(
    title="Spectre Inventory Platform",
    version="2.0.0",
    description="AI-powered inventory management and analysis platform",
    lifespan=lifespan
)

# CORS - Use centralized settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)

# ============== Include all routers ==============

# Core endpoints
app.include_router(inventory_router)
app.include_router(files_router)
app.include_router(jobs_router)
app.include_router(stats_router)
app.include_router(maintenance_router)
app.include_router(worker_router)

# Search and analysis
app.include_router(search_router)
app.include_router(collections_router)
app.include_router(analysis_router)

# Data management
app.include_router(scores_router)
app.include_router(sites_router)
app.include_router(cart_router)
app.include_router(catalog_router)

# Count sessions and locations
app.include_router(counting_router)
app.include_router(locations_router)
app.include_router(rooms_router)
app.include_router(snapshots_router)

# Export and utilities
app.include_router(export_router)
app.include_router(templates_router)

# Purchase match and integrations
app.include_router(purchase_match_router)

# AI-powered features
app.include_router(standup_router)
app.include_router(helpdesk_router)
app.include_router(memory_router)

# History tracking
app.include_router(history_router)


# ============== Health Check ==============

@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "2.0.0"}
