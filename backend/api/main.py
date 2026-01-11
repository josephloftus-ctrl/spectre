from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pathlib import Path
from typing import Optional
from urllib.parse import quote
import re
import os
import sys

# Add parent directory to path to allow importing core
sys.path.append(str(Path(__file__).resolve().parents[2]))

from backend.core.engine import collect_site_metrics
from backend.core.database import (
    get_file, list_files, get_job, list_jobs, get_stats,
    FileStatus, JobStatus, JobType, retry_failed_jobs
)
from backend.core.files import (
    save_uploaded_file, move_to_failed, retry_failed_file,
    get_inbox_files, get_processed_files, get_file_content,
    cleanup_old_files
)
from backend.core.embeddings import (
    search, find_similar, get_embedding_stats, delete_file_embeddings,
    reset_collection, search_unified
)
from backend.core.collections import (
    COLLECTIONS, list_collections, get_collection_stats,
    migrate_spectre_to_bible, ensure_data_directories
)
from backend.core.memory import (
    get_today_items, get_upcoming_items, search_memory, embed_note
)
from backend.core.worker import (
    init_worker, stop_scheduler, get_scheduler_status,
    refresh_all_scores
)
from backend.core.database import (
    get_unit_score, list_unit_scores, get_score_history, get_score_trend,
    get_site, get_site_display_name, list_sites, update_site_display_name,
    get_ignored_skus
)
from backend.core.analysis import (
    get_analysis_results, get_recent_anomalies, generate_site_summary,
    analyze_document, save_analysis_result
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


app = FastAPI(title="Spectre Inventory Platform", version="2.0.0", lifespan=lifespan)

# CORS
# TODO: In production, replace "*" with specific allowed origins
# Example: allow_origins=["https://ops-dash.yourdomain.com"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
ROOT_DIR = Path(__file__).resolve().parents[2]
SORTED_DIR = ROOT_DIR / "sorted" / "by_site"


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe use in Content-Disposition header."""
    # Remove path separators and control characters, keep safe chars
    safe = re.sub(r'[^\w\s\-\.]', '_', filename)
    # URL-encode for RFC 5987 compliant header
    return quote(safe, safe='')  # encode everything except alphanumeric

@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": "2.0.0"}

@app.get("/api/inventory/summary")
def get_inventory_summary():
    """
    Returns global stats and list of sites with their health.
    Now reads from unit_scores database table instead of filesystem.
    """
    # Get all unit scores from database
    scores = list_unit_scores(limit=500)

    if not scores:
        return {"sites": [], "global_value": 0, "active_sites": 0, "total_issues": 0}

    site_summaries = []
    global_value = 0.0
    total_issues = 0

    for score in scores:
        site_summaries.append({
            "site": score["site_id"],
            "latest_total": score["total_value"],
            "delta_pct": 0,  # TODO: Calculate from score history
            "issue_count": score["item_flag_count"],
            "last_updated": score["created_at"]
        })

        global_value += score["total_value"]
        total_issues += score["item_flag_count"]

    return {
        "global_value": global_value,
        "active_sites": len(scores),
        "total_issues": total_issues,
        "sites": site_summaries
    }

@app.get("/api/inventory/sites/{site_id}")
def get_site_detail(site_id: str):
    """
    Get site details. Now reads from unit_scores database.
    """
    score = get_unit_score(site_id)
    if not score:
        raise HTTPException(status_code=404, detail="Site not found")

    return {
        "site": site_id,
        "latest_total": score["total_value"],
        "delta_pct": 0,
        "latest_date": score["created_at"],
        "total_drifts": [],
        "qty_drifts": [],
        "file_summaries": []
    }


# ============== File Management API ==============

@app.post("/api/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    site_id: Optional[str] = Form(None)
):
    """Upload a new file for processing."""
    try:
        content = await file.read()
        file_record = save_uploaded_file(
            file_content=content,
            filename=file.filename,
            site_id=site_id,
            content_type=file.content_type
        )
        return {"success": True, "file": file_record}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.get("/api/files")
def get_files(
    status: Optional[str] = Query(None),
    site_id: Optional[str] = Query(None),
    limit: int = Query(100, le=500)
):
    """List files with optional filters."""
    file_status = FileStatus(status) if status else None
    files = list_files(status=file_status, site_id=site_id, limit=limit)
    return {"files": files, "count": len(files)}


@app.get("/api/files/{file_id}")
def get_file_detail(file_id: str):
    """Get file details by ID."""
    file_record = get_file(file_id)
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")
    return file_record


@app.get("/api/files/{file_id}/download")
def download_file(file_id: str):
    """Download a file."""
    try:
        content, filename = get_file_content(file_id)
        safe_filename = sanitize_filename(filename)
        return Response(
            content=content,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}"
            }
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")


@app.post("/api/files/{file_id}/retry")
def retry_file(file_id: str):
    """Retry processing a failed file."""
    try:
        file_record = retry_failed_file(file_id)
        return {"success": True, "file": file_record}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")


# ============== Job Management API ==============

@app.get("/api/jobs")
def get_jobs(
    status: Optional[str] = Query(None),
    job_type: Optional[str] = Query(None),
    limit: int = Query(100, le=500)
):
    """List jobs with optional filters."""
    job_status = JobStatus(status) if status else None
    jtype = JobType(job_type) if job_type else None
    jobs = list_jobs(status=job_status, job_type=jtype, limit=limit)
    return {"jobs": jobs, "count": len(jobs)}


@app.get("/api/jobs/{job_id}")
def get_job_detail(job_id: str):
    """Get job details by ID."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.post("/api/jobs/retry-failed")
def retry_all_failed_jobs():
    """Re-queue all failed jobs that haven't exceeded max attempts."""
    count = retry_failed_jobs()
    return {"success": True, "requeued_count": count}


# ============== Stats API ==============

@app.get("/api/stats")
def get_system_stats():
    """Get system statistics."""
    stats = get_stats()
    return stats


@app.get("/api/stats/inbox")
def get_inbox_stats():
    """Get inbox file list."""
    files = get_inbox_files()
    return {"files": files, "count": len(files)}


@app.get("/api/stats/processed")
def get_processed_stats(site_id: Optional[str] = Query(None)):
    """Get processed files list."""
    files = get_processed_files(site_id)
    return {"files": files, "count": len(files)}


@app.post("/api/maintenance/cleanup")
def run_cleanup(days: int = Query(30, ge=1, le=365)):
    """Delete old failed files."""
    deleted = cleanup_old_files(days)
    return {"success": True, "deleted_count": deleted}


# ============== Search API ==============

@app.post("/api/search")
def search_documents(
    query: str = Form(...),
    limit: int = Form(10),
    file_id: Optional[str] = Form(None),
    site_id: Optional[str] = Form(None),
    date_from: Optional[str] = Form(None),
    date_to: Optional[str] = Form(None),
    sort_by: str = Form("relevance")  # relevance, date_desc, date_asc, site
):
    """
    Semantic search across documents with date awareness.
    - Default: sorted by relevance, includes all dates
    - site_id: Filter to specific site
    - date_from/date_to: ISO date strings (YYYY-MM-DD) for filtering
    - sort_by: 'relevance' (default), 'date_desc', 'date_asc', 'site'
    """
    results = search(
        query,
        limit=limit,
        file_id=file_id,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        site_id=site_id
    )
    return {"results": results, "count": len(results), "query": query}


@app.get("/api/search/similar/{file_id}")
def get_similar_documents(
    file_id: str,
    chunk: int = Query(0),
    limit: int = Query(5)
):
    """Find documents similar to a specific file chunk."""
    results = find_similar(file_id, chunk_index=chunk, limit=limit)
    return {"results": results, "count": len(results), "file_id": file_id}


@app.delete("/api/embeddings/{file_id}")
def remove_file_embeddings(file_id: str):
    """Delete all embeddings for a file."""
    count = delete_file_embeddings(file_id)
    return {"success": True, "deleted_count": count}


@app.get("/api/embeddings/stats")
def embedding_statistics():
    """Get embedding system statistics."""
    return get_embedding_stats()


@app.post("/api/embeddings/reset")
def reset_embeddings():
    """
    Reset the embedding collection. Required when changing embedding models.
    WARNING: This deletes all existing embeddings. Re-embedding is needed after.
    """
    result = reset_collection()
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Reset failed"))
    return result


@app.post("/api/embeddings/reindex")
def reindex_all_embeddings():
    """
    Queue re-embedding jobs for all completed files.
    Use after resetting embeddings or changing models.
    """
    from backend.core.database import create_job, JobType
    import uuid

    # Get all completed files
    files = list_files(status=FileStatus.COMPLETED, limit=500)

    queued = 0
    for f in files:
        job_id = str(uuid.uuid4())
        create_job(job_id, JobType.EMBED, f["id"], priority=1)
        queued += 1

    return {
        "success": True,
        "message": f"Queued {queued} files for re-embedding",
        "queued_count": queued
    }


# ============== Collections API ==============

@app.get("/api/collections")
def get_collections():
    """
    List all available collections with their stats.
    Collections: culinart_bible, food_knowledge, living_memory
    """
    collections = list_collections()
    return {"collections": collections, "count": len(collections)}


@app.get("/api/collections/{name}")
def get_collection_details(name: str):
    """Get detailed stats for a specific collection."""
    if name not in COLLECTIONS:
        raise HTTPException(status_code=404, detail=f"Collection '{name}' not found")
    stats = get_collection_stats(name)
    return stats


@app.post("/api/collections/migrate")
def migrate_collections():
    """
    Migrate existing spectre_documents to culinart_bible.
    Run this once to rename the old collection.
    """
    result = migrate_spectre_to_bible()
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Migration failed"))
    return result


@app.post("/api/collections/init")
def initialize_collections():
    """Initialize collection directories and ensure all collections exist."""
    ensure_data_directories()
    # Touch each collection to create it
    collections = list_collections()
    return {
        "success": True,
        "message": "Collections initialized",
        "collections": collections
    }


@app.post("/api/search/unified")
def unified_search(
    query: str = Form(...),
    limit: int = Form(10),
    collections: Optional[str] = Form(None),  # Comma-separated collection names
    date_from: Optional[str] = Form(None),
    date_to: Optional[str] = Form(None),
    site_id: Optional[str] = Form(None)
):
    """
    Search across multiple collections.
    - collections: comma-separated list (e.g., "culinart_bible,living_memory") or empty for all
    """
    # Parse collections parameter
    collection_list = None
    if collections:
        collection_list = [c.strip() for c in collections.split(",") if c.strip()]

    results = search_unified(
        query=query,
        limit=limit,
        collections=collection_list,
        date_from=date_from,
        date_to=date_to,
        site_id=site_id
    )
    return {"results": results, "count": len(results), "query": query}


@app.post("/api/search/{collection_name}")
def search_collection(
    collection_name: str,
    query: str = Form(...),
    limit: int = Form(10),
    file_id: Optional[str] = Form(None),
    site_id: Optional[str] = Form(None),
    date_from: Optional[str] = Form(None),
    date_to: Optional[str] = Form(None),
    sort_by: str = Form("relevance")
):
    """Search within a specific collection."""
    if collection_name not in COLLECTIONS:
        raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' not found")

    results = search(
        query,
        limit=limit,
        file_id=file_id,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        site_id=site_id,
        collection_name=collection_name
    )
    return {"results": results, "count": len(results), "collection": collection_name}


# ============== Day At A Glance API ==============

@app.get("/api/glance")
def day_at_a_glance(date: Optional[str] = Query(None)):
    """
    Get Day At A Glance data for a specific date.
    Returns schedules, notes, people working, and tags for the day.

    Args:
        date: ISO date string (YYYY-MM-DD), defaults to today
    """
    items = get_today_items(date)
    if items.get("error"):
        raise HTTPException(status_code=500, detail=items["error"])
    return items


@app.get("/api/glance/upcoming")
def upcoming_glance(days: int = Query(7, le=30)):
    """Get Day At A Glance data for the upcoming days."""
    items = get_upcoming_items(days)
    return {"days": items, "count": len(items)}


@app.get("/api/glance/briefing")
def ai_briefing(date: Optional[str] = Query(None)):
    """
    Generate an AI-powered morning briefing.
    Combines schedule, notes, and insights into a summary.
    """
    from datetime import datetime as dt

    target_date = date or dt.now().strftime('%Y-%m-%d')

    # Get today's items from living memory
    today_items = get_today_items(target_date)

    # Get recent anomalies from analysis
    anomalies = get_recent_anomalies(limit=5)

    # Build briefing context
    briefing = {
        "date": target_date,
        "schedule_count": len(today_items.get("schedules", [])),
        "note_count": len(today_items.get("notes", [])),
        "people_working": today_items.get("people_working", []),
        "tags": today_items.get("tags", []),
        "recent_anomalies": anomalies[:3] if anomalies else [],
        "summary": None
    }

    # Generate AI summary if Ollama is available
    try:
        import requests
        OLLAMA_URL = "http://localhost:11434"

        # Build prompt
        prompt_parts = [f"Today is {target_date}. Give a brief morning briefing."]

        if briefing["people_working"]:
            prompt_parts.append(f"Staff working: {', '.join(briefing['people_working'])}")

        if briefing["schedule_count"]:
            prompt_parts.append(f"There are {briefing['schedule_count']} schedule entries.")

        if briefing["note_count"]:
            prompt_parts.append(f"There are {briefing['note_count']} notes to review.")

        if briefing["recent_anomalies"]:
            anomaly_texts = [a.get("summary", "Issue detected") for a in briefing["recent_anomalies"]]
            prompt_parts.append(f"Recent issues: {'; '.join(anomaly_texts)}")

        prompt = " ".join(prompt_parts) + " Keep it under 100 words."

        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": "llama3.2:latest",
                "prompt": prompt,
                "stream": False
            },
            timeout=30
        )

        if response.ok:
            data = response.json()
            briefing["summary"] = data.get("response", "").strip()

    except Exception as e:
        briefing["summary"] = f"Unable to generate AI summary: {str(e)}"

    return briefing


@app.post("/api/memory/note")
def create_memory_note(
    content: str = Form(...),
    title: str = Form(""),
    tags: Optional[str] = Form(None)  # Comma-separated tags
):
    """
    Create a quick note in living memory.
    Notes are automatically embedded and searchable.
    """
    import uuid

    note_id = str(uuid.uuid4())
    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    result = embed_note(
        file_id=note_id,
        content=content,
        title=title,
        tags=tag_list
    )

    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])

    return {
        "success": True,
        "note_id": note_id,
        "title": title,
        "metadata": result.get("metadata", {})
    }


# ============== Worker API ==============

@app.get("/api/worker/status")
def worker_status():
    """Get background worker status."""
    return get_scheduler_status()


# ============== Analysis API ==============

@app.get("/api/analysis/results")
def list_analysis_results(
    file_id: Optional[str] = Query(None),
    analysis_type: Optional[str] = Query(None),
    limit: int = Query(20, le=100)
):
    """Get analysis results with optional filters."""
    results = get_analysis_results(file_id=file_id, analysis_type=analysis_type, limit=limit)
    return {"results": results, "count": len(results)}


@app.get("/api/analysis/anomalies")
def list_anomalies(limit: int = Query(10, le=50)):
    """Get recent anomalies detected across all files."""
    anomalies = get_recent_anomalies(limit=limit)
    return {"anomalies": anomalies, "count": len(anomalies)}


@app.get("/api/analysis/file/{file_id}")
def get_file_analysis(file_id: str):
    """Get all analysis results for a specific file."""
    results = get_analysis_results(file_id=file_id)
    if not results:
        raise HTTPException(status_code=404, detail="No analysis found for file")
    return {"file_id": file_id, "analyses": results}


@app.post("/api/analysis/file/{file_id}")
def trigger_file_analysis(file_id: str):
    """Manually trigger analysis for a file."""
    file_record = get_file(file_id)
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    analysis = analyze_document(file_id)
    if not analysis:
        raise HTTPException(status_code=400, detail="Analysis failed - file may not be processed yet")

    result_id = save_analysis_result(file_id, "document_analysis", analysis)
    return {"success": True, "result_id": result_id, "analysis": analysis}


@app.get("/api/analysis/site/{site_id}/summary")
def get_site_analysis_summary(site_id: str):
    """Generate an AI summary for a site."""
    summary = generate_site_summary(site_id)
    if not summary:
        raise HTTPException(status_code=404, detail="No data found for site")
    return summary


# ============== Scores API ==============

@app.get("/api/scores")
def get_all_scores(
    status: Optional[str] = Query(None),
    limit: int = Query(100, le=500)
):
    """
    Get all unit scores, sorted by score descending (worst first).
    Returns status indicators, not raw scores.
    Now includes file attribution info.
    """
    scores = list_unit_scores(status=status, limit=limit)

    # Add trend indicators and file info
    units = []
    for s in scores:
        trend = get_score_trend(s["site_id"])

        # Get source file info if available
        source_file = None
        if s.get("file_id"):
            file_record = get_file(s["file_id"])
            if file_record:
                source_file = {
                    "id": file_record["id"],
                    "filename": file_record["filename"],
                    "processed_at": file_record.get("processed_at")
                }

        units.append({
            "site_id": s["site_id"],
            "status": s["status"],
            "item_flags": s["item_flag_count"],
            "total_value": s["total_value"],
            "last_scored": s["created_at"],
            "trend": trend,  # 'up' (worse), 'down' (better), 'stable', or None
            "source_file": source_file
        })

    return {
        "units": units,
        "count": len(units)
    }


@app.get("/api/scores/{site_id}")
def get_site_score(site_id: str):
    """
    Get score details for a specific site.
    Includes flagged items for drill-down.
    """
    score = get_unit_score(site_id)
    if not score:
        raise HTTPException(status_code=404, detail="No score found for site")

    trend = get_score_trend(site_id)

    return {
        "site_id": site_id,
        "status": score["status"],
        "item_flags": score["item_flag_count"],
        "total_value": score["total_value"],
        "item_count": score["item_count"],
        "last_scored": score["created_at"],
        "trend": trend,
        "flagged_items": score["flagged_items"]
    }


@app.get("/api/scores/{site_id}/items")
def get_site_flagged_items(site_id: str):
    """Get just the flagged items for a site (for drill-down)."""
    score = get_unit_score(site_id)
    if not score:
        raise HTTPException(status_code=404, detail="No score found for site")

    return {
        "site_id": site_id,
        "items": score["flagged_items"],
        "count": score["item_flag_count"]
    }


@app.get("/api/scores/{site_id}/history")
def get_site_score_history(
    site_id: str,
    limit: int = Query(12, le=52)
):
    """Get weekly score history for trend analysis."""
    history = get_score_history(site_id, limit=limit)
    return {
        "site_id": site_id,
        "history": history,
        "count": len(history)
    }


@app.post("/api/scores/refresh")
def trigger_score_refresh():
    """Manually trigger a re-score of all sites."""
    count = refresh_all_scores()
    return {
        "success": True,
        "message": f"Queued {count} sites for re-scoring"
    }


@app.post("/api/scores/snapshot")
def create_score_snapshot():
    """
    Manually create a score history snapshot for all sites.
    Use this to immediately capture current scores for week-over-week comparison
    instead of waiting for the Sunday 2 AM automatic snapshot.
    """
    from backend.core.database import list_unit_scores, save_score_snapshot
    from datetime import datetime
    import uuid

    snapshot_date = datetime.utcnow().strftime("%Y-%m-%d")
    current_scores = list_unit_scores(limit=1000)

    snapshots_created = 0
    for score in current_scores:
        snapshot_id = str(uuid.uuid4())
        save_score_snapshot(
            snapshot_id=snapshot_id,
            site_id=score["site_id"],
            score=score["score"],
            status=score["status"],
            item_flag_count=score["item_flag_count"],
            room_flag_count=score.get("room_flag_count", 0),
            total_value=score.get("total_value", 0),
            snapshot_date=snapshot_date
        )
        snapshots_created += 1

    return {
        "success": True,
        "message": f"Created {snapshots_created} score snapshots for {snapshot_date}",
        "snapshot_date": snapshot_date,
        "count": snapshots_created
    }


@app.get("/api/scores/{site_id}/files")
def get_site_scored_files(site_id: str):
    """
    Get all files that have been processed for a specific site.
    Shows which files contributed to scoring and when.
    """
    # Get files for this site
    files = list_files(site_id=site_id, limit=50)

    # Get the current score to identify the "active" file
    current_score = get_unit_score(site_id)
    active_file_id = current_score["file_id"] if current_score else None

    file_list = []
    for f in files:
        file_list.append({
            "id": f["id"],
            "filename": f["filename"],
            "status": f["status"],
            "processed_at": f.get("processed_at"),
            "created_at": f["created_at"],
            "is_active_score": f["id"] == active_file_id
        })

    return {
        "site_id": site_id,
        "files": file_list,
        "active_file_id": active_file_id,
        "count": len(file_list)
    }


# ============== Sites API ==============

@app.get("/api/sites")
def get_all_sites():
    """
    List all sites with their display names.
    Auto-formats site_id if no custom name is set.
    """
    sites = list_sites()
    return {
        "sites": sites,
        "count": len(sites)
    }


@app.get("/api/sites/{site_id}")
def get_site_detail_by_id(site_id: str):
    """Get site details including display name."""
    site = get_site(site_id)
    if not site:
        # Return auto-formatted name for sites not in DB
        from backend.core.database import auto_format_site_name
        return {
            "site_id": site_id,
            "display_name": auto_format_site_name(site_id),
            "is_custom": False
        }
    return {
        "site_id": site["site_id"],
        "display_name": site["display_name"],
        "is_custom": site["is_custom"],
        "created_at": site.get("created_at"),
        "updated_at": site.get("updated_at")
    }


@app.put("/api/sites/{site_id}")
def update_site_name(
    site_id: str,
    display_name: Optional[str] = Form(None)
):
    """
    Update the display name for a site.
    Pass display_name=None or empty string to reset to auto-formatted name.
    """
    site = update_site_display_name(site_id, display_name if display_name else None)
    return {
        "success": True,
        "site": site
    }


# ============== Purchase Match API ==============

# Import purchase match module
from nebula.purchase_match import (
    load_config, load_canon, build_index,
    match_inventory, summarize_results,
    format_console, export_csv,
    MatchFlag
)
from nebula.purchase_match.parsed_adapter import ParsedFileInventoryAdapter

# Import MOG loader and embeddings
from nebula.purchase_match.mog import load_mog_directory
from nebula.purchase_match.mog_embeddings import MOGEmbeddingIndex, build_mog_embeddings
from nebula.purchase_match.matcher import set_embedding_index

# Global state for purchase match (loaded on first use)
_purchase_match_state = {
    "config": None,
    "ips_index": None,
    "mog_index": None,
    "mog_embedding_index": None,
    "adapter": None,
    "initialized": False,
}

def _init_purchase_match():
    """Initialize purchase match components if not already done."""
    if _purchase_match_state["initialized"]:
        return True

    try:
        # Paths
        config_path = ROOT_DIR / "nebula" / "purchase_match" / "unit_vendor_config.json"
        ips_dir = ROOT_DIR / "Invoice Purchasing Summaries"
        mog_dir = ROOT_DIR / "FULL MOGS"
        data_dir = ROOT_DIR / "data" / "processed"

        # Load config
        _purchase_match_state["config"] = load_config(config_path)

        # Load IPS files (purchase history)
        if ips_dir.exists():
            ips_files = list(ips_dir.glob("*.xlsx"))
            if ips_files:
                records = load_canon(ips_files, _purchase_match_state["config"])
                _purchase_match_state["ips_index"] = build_index(records)
                # Keep legacy alias
                _purchase_match_state["index"] = _purchase_match_state["ips_index"]

        # Load MOG files (vendor catalogs)
        if mog_dir.exists():
            _purchase_match_state["mog_index"] = load_mog_directory(mog_dir)

            # Build embedding index for semantic matching (runs in background if needed)
            if _purchase_match_state["mog_index"]:
                try:
                    embedding_index = MOGEmbeddingIndex()
                    if embedding_index.build_index(_purchase_match_state["mog_index"]):
                        _purchase_match_state["mog_embedding_index"] = embedding_index
                        set_embedding_index(embedding_index)
                        print(f"MOG embedding index ready for semantic matching")
                except Exception as e:
                    print(f"Warning: Could not build embedding index: {e}")

        # Create adapter for inventory data
        if data_dir.exists():
            _purchase_match_state["adapter"] = ParsedFileInventoryAdapter(
                data_dir, _purchase_match_state["config"]
            )

        _purchase_match_state["initialized"] = True
        return True
    except Exception as e:
        print(f"Warning: Failed to initialize purchase match: {e}")
        return False


@app.get("/api/purchase-match/status")
def purchase_match_status():
    """Get purchase match system status."""
    _init_purchase_match()

    ips_index = _purchase_match_state.get("ips_index")
    mog_index = _purchase_match_state.get("mog_index")
    embedding_index = _purchase_match_state.get("mog_embedding_index")
    adapter = _purchase_match_state.get("adapter")

    return {
        "initialized": _purchase_match_state["initialized"],
        "ips_loaded": ips_index is not None,
        "ips_record_count": ips_index.record_count if ips_index else 0,
        "mog_loaded": mog_index is not None,
        "mog_item_count": mog_index.total_items if mog_index else 0,
        "mog_vendors": mog_index.vendors if mog_index else [],
        "embedding_ready": embedding_index is not None and embedding_index.is_ready,
        "inventory_loaded": adapter is not None,
        "available_units": adapter.get_all_units() if adapter else [],
        # Legacy
        "canon_loaded": ips_index is not None,
        "canon_record_count": ips_index.record_count if ips_index else 0,
    }


@app.get("/api/purchase-match/units")
def purchase_match_units():
    """Get list of units available for matching."""
    _init_purchase_match()

    adapter = _purchase_match_state.get("adapter")
    if not adapter:
        raise HTTPException(status_code=503, detail="Inventory adapter not initialized")

    return {"units": adapter.get_all_units()}


@app.get("/api/purchase-match/run/{unit}")
def run_purchase_match(unit: str, include_clean: bool = Query(False)):
    """
    Run purchase match diagnostic for a unit.

    Combines IPS (purchases) + MOG (catalogs) + Inventory for robust analysis.
    Returns items grouped by status with full details and light suggestions.
    """
    _init_purchase_match()

    config = _purchase_match_state.get("config")
    ips_index = _purchase_match_state.get("ips_index")
    mog_index = _purchase_match_state.get("mog_index")
    adapter = _purchase_match_state.get("adapter")

    if not config or not ips_index:
        raise HTTPException(status_code=503, detail="Purchase data not loaded. Upload IPS files first.")

    if not adapter:
        raise HTTPException(status_code=503, detail="Inventory adapter not initialized")

    # Get inventory for unit
    inventory = adapter.get_inventory_for_unit(unit)
    if not inventory:
        raise HTTPException(status_code=404, detail=f"No inventory found for unit: {unit}")

    # Get ignored SKUs for this unit
    ignored_skus = get_ignored_skus(unit)

    # Run matcher with all data sources
    results = match_inventory(
        inventory, ips_index, config,
        mog_index=mog_index,
        ignored_skus=ignored_skus
    )
    summary = summarize_results(results)

    # Group results by new flag types
    likely_typos = []  # SKU not found, but similar item exists
    orderable = []     # Valid SKU in catalog, just not purchased
    unknown = []       # Not in IPS or MOG - needs investigation
    ignored = []
    clean = []

    for r in results:
        # Base item info
        item = {
            "sku": r.inventory_item.sku,
            "description": r.inventory_item.description,
            "quantity": float(r.inventory_item.quantity),
            "price": float(r.inventory_item.price) if r.inventory_item.price else None,
            "vendor": r.inventory_item.vendor,
            "reason": r.reason,
        }

        if r.flag == MatchFlag.LIKELY_TYPO and r.suggested_sku:
            # Full suggestion details - displayed lightly
            item["suggestion"] = {
                "sku": r.suggested_sku.sku,
                "description": r.suggested_sku.description,
                "vendor": r.suggested_sku.vendor,
                "price": float(r.suggested_sku.price) if r.suggested_sku.price else None,
                "similarity": round(r.suggested_sku.similarity * 100),  # As percentage
            }
            likely_typos.append(item)

        elif r.flag == MatchFlag.ORDERABLE and r.mog_match:
            # Show catalog info
            item["catalog"] = {
                "vendor": r.mog_match.vendor,
                "description": r.mog_match.description,
                "price": float(r.mog_match.price) if r.mog_match.price else None,
            }
            orderable.append(item)

        elif r.flag == MatchFlag.UNKNOWN:
            unknown.append(item)

        elif r.flag == MatchFlag.IGNORED:
            ignored.append(item)

        elif r.flag == MatchFlag.CLEAN:
            if include_clean:
                clean.append(item)

    return {
        "unit": unit,
        "summary": summary,
        # New categories
        "likely_typos": likely_typos,
        "orderable": orderable,
        "unknown": unknown,
        "ignored": ignored,
        "clean": clean if include_clean else None,
        # Legacy compatibility
        "mismatches": likely_typos,
        "orphans": unknown,
    }


@app.get("/api/purchase-match/report/{unit}")
def purchase_match_report(unit: str):
    """Get formatted text report for a unit."""
    _init_purchase_match()

    config = _purchase_match_state.get("config")
    index = _purchase_match_state.get("index")
    adapter = _purchase_match_state.get("adapter")

    if not config or not index or not adapter:
        raise HTTPException(status_code=503, detail="Purchase match not initialized")

    inventory = adapter.get_inventory_for_unit(unit)
    if not inventory:
        raise HTTPException(status_code=404, detail=f"No inventory found for unit: {unit}")

    results = match_inventory(inventory, index, config)
    report = format_console(results)

    return Response(content=report, media_type="text/plain")


@app.post("/api/purchase-match/reload")
def reload_purchase_match():
    """Reload purchase match data (IPS files and inventory)."""
    _purchase_match_state["initialized"] = False
    success = _init_purchase_match()

    if not success:
        raise HTTPException(status_code=500, detail="Failed to reload purchase match data")

    return purchase_match_status()


# ============== History API ==============

@app.get("/api/history/{site_id}")
def get_site_history(
    site_id: str,
    days: int = Query(30, le=90)
):
    """
    Get historical data for a site.
    Returns score history plus computed metrics.
    """
    from backend.core.database import get_score_history, get_unit_score

    # Get history
    # Estimate weeks from days (roughly)
    weeks = max(1, days // 7)
    history = get_score_history(site_id, limit=weeks)

    # Get current score
    current = get_unit_score(site_id)

    if not current and not history:
        raise HTTPException(status_code=404, detail="No data found for site")

    # Compute trends if we have history
    value_trend = None
    count_trend = None

    if len(history) >= 2:
        latest = history[0]
        previous = history[1]

        if previous.get("total_value", 0) > 0:
            value_change = latest.get("total_value", 0) - previous.get("total_value", 0)
            value_pct = (value_change / previous["total_value"]) * 100
            value_trend = {
                "change": value_change,
                "percent": round(value_pct, 1),
                "direction": "up" if value_change > 0 else "down" if value_change < 0 else "stable"
            }

        prev_count = previous.get("item_flag_count", 0)
        curr_count = latest.get("item_flag_count", 0)
        count_change = curr_count - prev_count
        count_trend = {
            "change": count_change,
            "direction": "up" if count_change > 0 else "down" if count_change < 0 else "stable"
        }

    return {
        "site_id": site_id,
        "current": current,
        "history": history,
        "trends": {
            "value": value_trend,
            "flags": count_trend
        }
    }


@app.get("/api/history/{site_id}/movers")
def get_site_movers(
    site_id: str,
    limit: int = Query(10, le=50)
):
    """
    Get items with biggest quantity changes between latest and previous file.
    """
    from backend.core.database import list_files, FileStatus
    import json

    # Get latest two files for this site
    files = list_files(status=FileStatus.COMPLETED, site_id=site_id, limit=2)

    if len(files) < 2:
        return {
            "site_id": site_id,
            "movers": [],
            "message": "Need at least 2 files to compare"
        }

    # Parse the data from both files
    def get_items(file_record):
        parsed = file_record.get("parsed_data")
        if isinstance(parsed, str):
            parsed = json.loads(parsed)
        if not parsed:
            return {}

        items = {}
        for row in parsed.get("rows", []):
            sku = row.get("Dist #") or row.get("Item Number") or row.get("SKU")
            qty = row.get("Quantity", 0)
            desc = row.get("Item Description") or row.get("Description") or ""
            if sku:
                try:
                    items[str(sku)] = {
                        "quantity": float(qty) if qty else 0,
                        "description": str(desc)[:50]
                    }
                except (ValueError, TypeError):
                    pass
        return items

    latest_items = get_items(files[0])
    previous_items = get_items(files[1])

    # Calculate changes
    movers = []
    all_skus = set(latest_items.keys()) | set(previous_items.keys())

    for sku in all_skus:
        latest = latest_items.get(sku, {})
        previous = previous_items.get(sku, {})

        latest_qty = latest.get("quantity", 0)
        previous_qty = previous.get("quantity", 0)
        change = latest_qty - previous_qty

        if change != 0:
            movers.append({
                "sku": sku,
                "description": latest.get("description") or previous.get("description", ""),
                "previous_qty": previous_qty,
                "current_qty": latest_qty,
                "change": change,
                "direction": "up" if change > 0 else "down"
            })

    # Sort by absolute change, take top N
    movers.sort(key=lambda x: abs(x["change"]), reverse=True)

    return {
        "site_id": site_id,
        "movers": movers[:limit],
        "latest_file": files[0].get("filename"),
        "previous_file": files[1].get("filename")
    }


@app.get("/api/history/{site_id}/anomalies")
def get_site_anomalies(
    site_id: str,
    limit: int = Query(20, le=100)
):
    """
    Get items that appeared or vanished between latest and previous file.
    """
    from backend.core.database import list_files, FileStatus
    import json

    # Get latest two files for this site
    files = list_files(status=FileStatus.COMPLETED, site_id=site_id, limit=2)

    if len(files) < 2:
        return {
            "site_id": site_id,
            "appeared": [],
            "vanished": [],
            "message": "Need at least 2 files to compare"
        }

    # Parse the data from both files
    def get_items(file_record):
        parsed = file_record.get("parsed_data")
        if isinstance(parsed, str):
            parsed = json.loads(parsed)
        if not parsed:
            return {}

        items = {}
        for row in parsed.get("rows", []):
            sku = row.get("Dist #") or row.get("Item Number") or row.get("SKU")
            qty = row.get("Quantity", 0)
            desc = row.get("Item Description") or row.get("Description") or ""
            price = row.get("Unit Price") or row.get("Price") or 0
            if sku:
                try:
                    items[str(sku)] = {
                        "quantity": float(qty) if qty else 0,
                        "description": str(desc)[:50],
                        "price": float(price) if price else 0
                    }
                except (ValueError, TypeError):
                    pass
        return items

    latest_items = get_items(files[0])
    previous_items = get_items(files[1])

    # Find appeared (in latest but not previous)
    appeared = []
    for sku, data in latest_items.items():
        if sku not in previous_items:
            appeared.append({
                "sku": sku,
                "description": data["description"],
                "quantity": data["quantity"],
                "price": data["price"]
            })

    # Find vanished (in previous but not latest)
    vanished = []
    for sku, data in previous_items.items():
        if sku not in latest_items:
            vanished.append({
                "sku": sku,
                "description": data["description"],
                "quantity": data["quantity"],
                "price": data["price"]
            })

    # Sort by quantity (biggest items first)
    appeared.sort(key=lambda x: x["quantity"], reverse=True)
    vanished.sort(key=lambda x: x["quantity"], reverse=True)

    return {
        "site_id": site_id,
        "appeared": appeared[:limit],
        "vanished": vanished[:limit],
        "appeared_count": len(appeared),
        "vanished_count": len(vanished),
        "latest_file": files[0].get("filename"),
        "previous_file": files[1].get("filename")
    }


# ============== Ignore List API (Purchase Match) ==============

from backend.core.database import (
    add_ignored_item, remove_ignored_item, list_ignored_items, get_ignored_skus
)
from pydantic import BaseModel


class IgnoreItemRequest(BaseModel):
    sku: str
    reason: Optional[str] = None
    notes: Optional[str] = None


@app.get("/api/purchase-match/{site_id}/ignored")
def get_ignored_items(site_id: str):
    """List all ignored items for a site."""
    items = list_ignored_items(site_id)
    return {
        "site_id": site_id,
        "items": items,
        "count": len(items)
    }


@app.post("/api/purchase-match/{site_id}/ignore")
def add_item_to_ignore_list(site_id: str, request: IgnoreItemRequest):
    """Add an item to the site's ignore list."""
    item = add_ignored_item(
        site_id=site_id,
        sku=request.sku,
        reason=request.reason,
        notes=request.notes
    )
    return {
        "success": True,
        "item": item
    }


@app.delete("/api/purchase-match/{site_id}/ignore/{sku}")
def remove_item_from_ignore_list(site_id: str, sku: str):
    """Remove an item from the site's ignore list."""
    removed = remove_ignored_item(site_id, sku)
    if not removed:
        raise HTTPException(status_code=404, detail="Item not found in ignore list")
    return {
        "success": True,
        "message": f"Removed {sku} from ignore list"
    }


# ============== Templates API ==============

TEMPLATES_DIR = ROOT_DIR / "Templates"

# Map site IDs to template filenames
TEMPLATE_MAP = {
    "pseg_nhq": "PSEG NHQ Inventory Template.xlsx",
    "pseg_hq": "PSEG NHQ Inventory Template.xlsx",
    "pseg_salem": "PSEG Salem InventoryTemplate.xlsx",
    "hope_creek": "Hope Creek InventoryTemplate.xlsx",
    "pseg_hope_creek": "Hope Creek InventoryTemplate.xlsx",
    "lm100": "LM100 Inventory Template.xlsx",
    "lockheed": "LM100 Inventory Template.xlsx",
    "lmd": "LMD Inventory Template.xlsx",
    "lockheed_bldg_d": "LMD Inventory Template.xlsx",
    "blank": "EmptyInventoryTemplate.xlsx",
    "cart": "CartTemplate.xlsx",
}

@app.get("/api/templates")
def list_templates():
    """List all available count sheet templates."""
    templates = []
    if TEMPLATES_DIR.exists():
        for f in TEMPLATES_DIR.glob("*.xlsx"):
            templates.append({
                "filename": f.name,
                "size_kb": round(f.stat().st_size / 1024, 1),
                "modified": f.stat().st_mtime
            })
    return {
        "templates": sorted(templates, key=lambda x: x["filename"]),
        "directory": str(TEMPLATES_DIR)
    }


@app.get("/api/templates/{site_id}/download")
def download_template(
    site_id: str,
    sort_by: Optional[str] = Query(None, description="Sort by: description, sku, category, vendor, price")
):
    """Download a count sheet template for a specific site, optionally sorted."""
    # Normalize site_id
    site_key = site_id.lower().replace("-", "_").replace(" ", "_")

    # Look up template filename
    template_name = TEMPLATE_MAP.get(site_key)
    if not template_name:
        # Try to find a matching template by partial name
        for f in TEMPLATES_DIR.glob("*.xlsx"):
            if site_key in f.name.lower().replace(" ", "_"):
                template_name = f.name
                break

    if not template_name:
        raise HTTPException(
            status_code=404,
            detail=f"No template found for site: {site_id}. Available: {list(TEMPLATE_MAP.keys())}"
        )

    template_path = TEMPLATES_DIR / template_name
    if not template_path.exists():
        raise HTTPException(status_code=404, detail=f"Template file not found: {template_name}")

    # If sorting requested, use sheet_writer
    if sort_by:
        try:
            from nebula.purchase_match.sheet_writer import generate_sorted_template
            content = generate_sorted_template(template_path, sort_by)
            if not content:
                raise HTTPException(status_code=500, detail="Failed to generate sorted template")
        except ImportError:
            # Fallback to unsorted
            with open(template_path, "rb") as f:
                content = f.read()
    else:
        # Return original template
        with open(template_path, "rb") as f:
            content = f.read()

    safe_name = sanitize_filename(template_name)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=\"{safe_name}\"; filename*=UTF-8''{safe_name}"
        }
    )


# ============== Standup API ==============

from backend.core.standup import (
    get_or_generate_standup, prebake_standup, reroll_section,
    list_cached_standups, get_cached_standup
)

@app.get("/api/standup")
def get_standup(date: Optional[str] = Query(None)):
    """
    Get daily standup content (Safety Moment, DEI Moment, Manager Prompt).
    Returns cached content if available, generates fresh if not.
    """
    content = get_or_generate_standup(date)
    return content


@app.get("/api/standup/cached")
def get_standup_cached_only(date: Optional[str] = Query(None)):
    """Get cached standup content only (returns null if not pre-baked)."""
    content = get_cached_standup(date)
    if not content:
        return {"available": False, "date": date}
    content["available"] = True
    return content


@app.post("/api/standup/prebake")
def prebake_standup_content(date: Optional[str] = Form(None)):
    """
    Pre-generate and cache standup content for a date.
    Use this for overnight pre-baking of next day's content.
    """
    result = prebake_standup(date)
    return result


@app.post("/api/standup/reroll/{section}")
def reroll_standup_section(
    section: str,
    topic: Optional[str] = Form(None)
):
    """
    Regenerate a specific standup section.

    Args:
        section: 'safety', 'dei', or 'manager'
        topic: Optional topic hint to focus the content
    """
    if section not in ['safety', 'dei', 'manager']:
        raise HTTPException(status_code=400, detail="Invalid section. Use: safety, dei, manager")

    result = reroll_section(section, topic)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])

    return {"success": True, "section": section, "content": result}


@app.get("/api/standup/history")
def get_standup_history():
    """List all cached standup dates."""
    cached = list_cached_standups()
    return {"cached": cached, "count": len(cached)}


# ============== Help Desk API ==============

from backend.core.embeddings import search as rag_search

@app.post("/api/helpdesk/ask")
def helpdesk_ask(
    question: str = Form(...),
    include_sources: bool = Form(True)
):
    """
    Ask a question to the Help Desk RAG system.
    Searches training corpus and synthesizes an answer.
    """
    # Search training corpus
    results = rag_search(
        query=question,
        limit=5,
        collection_name="culinart_bible"
    )

    if not results:
        return {
            "answer": "I couldn't find relevant information in the training materials for your question.",
            "sources": [],
            "confidence": "low"
        }

    # Build context from search results
    context_parts = []
    sources = []
    for r in results:
        context_parts.append(r["text"])
        source_file = r.get("metadata", {}).get("source_file", "")
        if source_file and source_file not in sources:
            sources.append(source_file)

    context = "\n\n".join(context_parts)

    # Generate answer with LLM
    try:
        import requests
        OLLAMA_URL = "http://localhost:11434"

        prompt = f"""Based on the following training materials, answer this question:

QUESTION: {question}

RELEVANT TRAINING MATERIALS:
{context}

Instructions:
- Answer based ONLY on the provided materials
- Be concise and practical
- If the materials don't fully answer the question, say so
- Use bullet points for lists
- Reference specific documents when relevant

ANSWER:"""

        response = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": "granite4:3b",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant answering questions about food service operations, safety, and HR policies based on company training materials."},
                    {"role": "user", "content": prompt}
                ],
                "stream": False,
                "options": {"temperature": 0.3}
            },
            timeout=60
        )

        if response.ok:
            data = response.json()
            answer = data.get("message", {}).get("content", "").strip()
        else:
            answer = "Unable to generate answer. Please try again."

    except Exception as e:
        answer = f"Error generating answer: {str(e)}"

    result = {
        "answer": answer,
        "confidence": "high" if len(results) >= 3 else "medium" if len(results) >= 1 else "low"
    }

    if include_sources:
        result["sources"] = sources
        result["source_snippets"] = [
            {"file": r.get("metadata", {}).get("source_file", ""), "text": r["text"][:200]}
            for r in results[:3]
        ]

    return result


@app.post("/api/helpdesk/search")
def helpdesk_search(
    query: str = Form(...),
    limit: int = Form(10)
):
    """
    Search training corpus without LLM synthesis.
    Returns raw search results for browsing.
    """
    results = rag_search(
        query=query,
        limit=limit,
        collection_name="culinart_bible"
    )

    formatted = []
    for r in results:
        formatted.append({
            "text": r["text"],
            "source_file": r.get("metadata", {}).get("source_file", ""),
            "score": r.get("score", 0),
            "chunk_index": r.get("metadata", {}).get("chunk_index", 0)
        })

    return {
        "results": formatted,
        "count": len(formatted),
        "query": query
    }


@app.get("/api/helpdesk/corpus/stats")
def helpdesk_corpus_stats():
    """Get stats about the training corpus."""
    from backend.core.corpus import get_corpus_stats
    return get_corpus_stats()


@app.post("/api/helpdesk/corpus/ingest")
def helpdesk_ingest_corpus():
    """
    Re-ingest the training corpus.
    Use after adding new training files.
    """
    from backend.core.corpus import ingest_training_corpus
    result = ingest_training_corpus(clear_existing=True)
    return result
