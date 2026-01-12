"""
Background job worker using APScheduler.
Processes files asynchronously and runs scheduled tasks.
"""
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
import json
import uuid

from .naming import extract_site_from_filename

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from .database import (
    get_next_job, update_job_status, get_file, update_file_status, update_file,
    create_job, JobStatus, JobType, FileStatus,
    save_unit_score, list_unit_scores, save_score_snapshot,
    get_all_site_ids_with_scores, list_files
)
from .files import INBOX_DIR, move_to_processed, move_to_failed
from .engine import parse_excel_file, parse_file
from .embeddings import embed_document
from .analysis import (
    analyze_document, compare_with_previous, save_analysis_result,
    check_ollama_available
)
from .flag_checker import calculate_unit_score

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: Optional[BackgroundScheduler] = None


def process_parse_job(job: dict) -> dict:
    """Process a file parsing job."""
    file_id = job.get("file_id")
    if not file_id:
        return {"error": "No file_id in job"}

    file_record = get_file(file_id)
    if not file_record:
        return {"error": f"File {file_id} not found"}

    # Get file path
    file_path = Path(file_record.get("current_path", ""))
    if not file_path.exists():
        # Check inbox
        inbox_path = INBOX_DIR / file_id
        if inbox_path.exists():
            for f in inbox_path.iterdir():
                if f.suffix.lower() in ('.xlsx', '.xls', '.csv', '.pdf'):
                    file_path = f
                    break

    if not file_path.exists():
        return {"error": f"File not found at {file_path}"}

    # Update status to processing
    update_file_status(file_id, FileStatus.PROCESSING)

    try:
        # Parse the file (supports Excel, CSV, PDF)
        parsed_data = parse_file(str(file_path))

        # Determine site_id priority:
        # 1. Already set in file record (from upload)
        # 2. Extracted from Excel content (metadata.site_id)
        # 3. Extracted from filename
        # 4. Default to "unknown"
        site_id = file_record.get("site_id")
        if not site_id:
            # Check if parser extracted site from Excel content
            site_id = parsed_data.get("metadata", {}).get("site_id")
            if site_id:
                update_file(file_id, site_id=site_id)
                logger.info(f"Extracted site_id '{site_id}' from Excel content")
            else:
                # Fall back to filename extraction
                filename = file_record.get("filename", "")
                site_id = extract_site_from_filename(filename)
                if site_id:
                    update_file(file_id, site_id=site_id)
                    logger.info(f"Extracted site_id '{site_id}' from filename '{filename}'")
                else:
                    site_id = "unknown"
                    logger.warning(f"Could not extract site_id for file '{filename}'")

        # Move to processed
        move_to_processed(file_id, site_id, parsed_data)

        # Queue scoring job first (fast, shows data on dashboard quickly)
        score_job_id = str(uuid.uuid4())
        create_job(score_job_id, JobType.SCORE, file_id, priority=1)

        # Queue embedding job (slower, lower priority)
        embed_job_id = str(uuid.uuid4())
        create_job(embed_job_id, JobType.EMBED, file_id, priority=-1)

        return {
            "success": True,
            "rows_parsed": len(parsed_data.get("rows", [])),
            "headers": parsed_data.get("headers", [])
        }

    except Exception as e:
        logger.error(f"Failed to parse file {file_id}: {e}")
        move_to_failed(file_id, str(e))
        return {"error": str(e)}


def process_embed_job(job: dict) -> dict:
    """Process an embedding job."""
    file_id = job.get("file_id")
    if not file_id:
        return {"error": "No file_id in job"}

    file_record = get_file(file_id)
    if not file_record:
        return {"error": f"File {file_id} not found"}

    try:
        # Get parsed data
        parsed_data = file_record.get("parsed_data")
        if isinstance(parsed_data, str):
            try:
                parsed_data = json.loads(parsed_data)
            except json.JSONDecodeError as e:
                return {"error": f"Invalid JSON in parsed_data: {e}"}

        if not parsed_data:
            return {"error": "No parsed data available"}

        # Generate embeddings with date metadata - inventory files go to inventory collection
        result = embed_document(
            file_id=file_id,
            parsed_data=parsed_data,
            site_id=file_record.get("site_id"),
            filename=file_record.get("filename"),
            file_date=file_record.get("created_at"),
            collection_name="inventory"
        )

        # Queue analysis job if Ollama is available (scoring already done after parse)
        if check_ollama_available():
            analyze_job_id = str(uuid.uuid4())
            create_job(analyze_job_id, JobType.ANALYZE, file_id, priority=-2)
            logger.info(f"Queued analysis job for file {file_id}")

        return result

    except Exception as e:
        logger.error(f"Failed to embed file {file_id}: {e}")
        return {"error": str(e)}


def process_analyze_job(job: dict) -> dict:
    """Process an analysis job - runs AI analysis on documents."""
    file_id = job.get("file_id")
    if not file_id:
        return {"error": "No file_id in job"}

    file_record = get_file(file_id)
    if not file_record:
        return {"error": f"File {file_id} not found"}

    results = {}

    try:
        # Run document analysis
        analysis = analyze_document(file_id)
        if analysis:
            save_analysis_result(file_id, "document_analysis", analysis)
            results["document_analysis"] = {
                "risk_score": analysis.get("risk_score", 0),
                "anomaly_count": len(analysis.get("anomalies", []))
            }
            logger.info(f"Document analysis complete for {file_id}: risk={analysis.get('risk_score', 0)}")

        # Run comparison with previous files
        site_id = file_record.get("site_id")
        if site_id:
            comparison = compare_with_previous(file_id, site_id)
            if comparison and comparison.get("alerts"):
                save_analysis_result(file_id, "comparison", comparison)
                results["comparison"] = {
                    "value_change_pct": comparison.get("value_change_pct", 0),
                    "alerts": comparison.get("alerts", [])
                }
                logger.info(f"Comparison analysis complete for {file_id}: alerts={comparison.get('alerts')}")

        return {"success": True, **results}

    except Exception as e:
        logger.error(f"Failed to analyze file {file_id}: {e}")
        return {"error": str(e)}


def process_score_job(job: dict) -> dict:
    """Process a scoring job - calculates health score for a file's site."""
    file_id = job.get("file_id")
    if not file_id:
        return {"error": "No file_id in job"}

    file_record = get_file(file_id)
    if not file_record:
        return {"error": f"File {file_id} not found"}

    site_id = file_record.get("site_id")
    if not site_id:
        return {"error": "No site_id for file"}

    try:
        # Get parsed data
        parsed_data = file_record.get("parsed_data")
        if isinstance(parsed_data, str):
            try:
                parsed_data = json.loads(parsed_data)
            except json.JSONDecodeError as e:
                return {"error": f"Invalid JSON in parsed_data: {e}"}

        if not parsed_data:
            return {"error": "No parsed data available"}

        rows = parsed_data.get("rows", [])
        if not rows:
            return {"error": "No rows in parsed data"}

        # Calculate score
        score_result = calculate_unit_score(rows)

        # Save to database
        score_id = str(uuid.uuid4())
        save_unit_score(
            score_id=score_id,
            site_id=site_id,
            score=score_result["score"],
            status=score_result["status"],
            item_flag_count=score_result["summary"]["flagged_items"],
            room_flag_count=0,
            flagged_items=score_result["item_flags"],
            flagged_rooms=[],
            room_totals={},
            total_value=score_result["summary"]["total_value"],
            item_count=score_result["summary"]["item_count"],
            file_id=file_id
        )

        logger.info(f"Scored site {site_id}: score={score_result['score']}, status={score_result['status']}")

        return {
            "success": True,
            "site_id": site_id,
            "score": score_result["score"],
            "status": score_result["status"],
            "flagged_items": score_result["summary"]["flagged_items"]
        }

    except Exception as e:
        logger.error(f"Failed to score file {file_id}: {e}")
        return {"error": str(e)}


def process_job(job: dict) -> dict:
    """Process a single job based on its type."""
    job_type = job.get("job_type")

    if job_type == JobType.PARSE.value:
        return process_parse_job(job)
    elif job_type == JobType.EMBED.value:
        return process_embed_job(job)
    elif job_type == JobType.ANALYZE.value:
        return process_analyze_job(job)
    elif job_type == JobType.SCORE.value:
        return process_score_job(job)
    else:
        return {"error": f"Unknown job type: {job_type}"}


def run_job_worker():
    """
    Check for pending jobs and process them.
    Called periodically by the scheduler.
    """
    job = get_next_job()
    if not job:
        return

    job_id = job["id"]
    logger.info(f"Processing job {job_id} ({job['job_type']})")

    # Mark as running
    update_job_status(job_id, JobStatus.RUNNING)

    try:
        result = process_job(job)

        if result.get("error"):
            update_job_status(job_id, JobStatus.FAILED, error_message=result["error"])
            logger.error(f"Job {job_id} failed: {result['error']}")
        else:
            update_job_status(job_id, JobStatus.COMPLETED, result=result)
            logger.info(f"Job {job_id} completed successfully")

    except Exception as e:
        update_job_status(job_id, JobStatus.FAILED, error_message=str(e))
        logger.exception(f"Job {job_id} failed with exception")


def weekly_score_refresh():
    """
    Weekly job to snapshot current scores and re-score all sites.
    Runs every Sunday at 2 AM by default.
    """
    logger.info("Starting weekly score refresh...")

    # Get current date for snapshot
    snapshot_date = datetime.utcnow().strftime("%Y-%m-%d")

    # Get all current scores and save as snapshots
    current_scores = list_unit_scores(limit=1000)
    for score in current_scores:
        try:
            snapshot_id = str(uuid.uuid4())
            save_score_snapshot(
                snapshot_id=snapshot_id,
                site_id=score["site_id"],
                score=score["score"],
                status=score["status"],
                item_flag_count=score["item_flag_count"],
                room_flag_count=0,
                total_value=score["total_value"],
                snapshot_date=snapshot_date
            )
            logger.info(f"Saved score snapshot for {score['site_id']}")
        except Exception as e:
            logger.error(f"Failed to save snapshot for {score['site_id']}: {e}")

    # Re-score all sites using their latest files
    sites_rescored = 0
    completed_files = list_files(status=FileStatus.COMPLETED, limit=1000)

    # Group by site_id and get latest file per site
    latest_by_site = {}
    for f in completed_files:
        site_id = f.get("site_id")
        if not site_id:
            continue
        if site_id not in latest_by_site:
            latest_by_site[site_id] = f
        else:
            # Compare timestamps, keep latest
            existing_time = latest_by_site[site_id].get("processed_at", "")
            current_time = f.get("processed_at", "")
            if current_time > existing_time:
                latest_by_site[site_id] = f

    # Queue score jobs for each site's latest file
    for site_id, file_record in latest_by_site.items():
        try:
            score_job_id = str(uuid.uuid4())
            create_job(score_job_id, JobType.SCORE, file_record["id"], priority=0)
            sites_rescored += 1
            logger.info(f"Queued refresh score job for {site_id}")
        except Exception as e:
            logger.error(f"Failed to queue refresh for {site_id}: {e}")

    logger.info(f"Weekly refresh complete: {len(current_scores)} snapshots saved, {sites_rescored} sites queued for re-scoring")


def refresh_all_scores():
    """
    Manual trigger to re-score all sites immediately.
    Returns the number of sites queued for re-scoring.
    """
    logger.info("Manual score refresh triggered...")

    completed_files = list_files(status=FileStatus.COMPLETED, limit=1000)

    # Group by site_id and get latest file per site
    latest_by_site = {}
    for f in completed_files:
        site_id = f.get("site_id")
        if not site_id:
            continue
        if site_id not in latest_by_site:
            latest_by_site[site_id] = f
        else:
            existing_time = latest_by_site[site_id].get("processed_at", "")
            current_time = f.get("processed_at", "")
            if current_time > existing_time:
                latest_by_site[site_id] = f

    # Queue score jobs
    sites_queued = 0
    for site_id, file_record in latest_by_site.items():
        try:
            score_job_id = str(uuid.uuid4())
            create_job(score_job_id, JobType.SCORE, file_record["id"], priority=1)  # Higher priority
            sites_queued += 1
        except Exception as e:
            logger.error(f"Failed to queue score for {site_id}: {e}")

    logger.info(f"Manual refresh: {sites_queued} sites queued for scoring")
    return sites_queued


def scan_inbox():
    """
    Scan inbox for new files that haven't been registered.
    Creates database records and jobs for orphaned files.
    """
    from .files import INBOX_DIR
    from .database import create_file

    for file_dir in INBOX_DIR.iterdir():
        if not file_dir.is_dir():
            continue

        file_id = file_dir.name
        existing = get_file(file_id)

        if existing:
            continue

        # Find the file
        metadata_path = file_dir / "metadata.json"
        if metadata_path.exists():
            with open(metadata_path) as f:
                metadata = json.load(f)

            # Create database record
            create_file(
                file_id=file_id,
                filename=metadata.get("filename", "unknown"),
                original_path=str(file_dir),
                file_type=metadata.get("file_type", "unknown"),
                file_size=metadata.get("size", 0),
                site_id=metadata.get("site_id")
            )

            # Create processing job
            job_id = str(uuid.uuid4())
            create_job(job_id, JobType.PARSE, file_id, priority=1)
            logger.info(f"Registered orphaned file: {file_id}")


def recover_stuck_jobs():
    """
    Recover jobs stuck in 'running' state for more than 10 minutes.
    This handles cases where the server restarted while a job was processing.
    """
    from .database import get_db

    try:
        with get_db() as conn:
            # Find jobs stuck in running for more than 10 minutes
            cur = conn.execute("""
                SELECT id, job_type, started_at, attempts
                FROM jobs
                WHERE status = 'running'
                AND started_at < datetime('now', '-10 minutes')
            """)
            stuck_jobs = cur.fetchall()

            for job in stuck_jobs:
                job_id, job_type, started_at, attempts = job
                # Reset to queued if under max attempts, otherwise fail
                if attempts < 3:
                    conn.execute("""
                        UPDATE jobs
                        SET status = 'queued',
                            started_at = NULL,
                            error_message = 'Auto-recovered from stuck state'
                        WHERE id = ?
                    """, (job_id,))
                    logger.warning(f"Recovered stuck job {job_id} ({job_type}) - re-queued")
                else:
                    conn.execute("""
                        UPDATE jobs
                        SET status = 'failed',
                            completed_at = datetime('now'),
                            error_message = 'Max attempts exceeded after stuck recovery'
                        WHERE id = ?
                    """, (job_id,))
                    logger.warning(f"Failed stuck job {job_id} ({job_type}) - max attempts exceeded")

            conn.commit()

            if stuck_jobs:
                logger.info(f"Recovered {len(stuck_jobs)} stuck jobs")

    except Exception as e:
        logger.error(f"Error recovering stuck jobs: {e}")


def start_scheduler():
    """Start the background scheduler."""
    global scheduler

    if scheduler is not None:
        logger.warning("Scheduler already running")
        return

    scheduler = BackgroundScheduler()

    # Job worker - check every 5 seconds
    scheduler.add_job(
        run_job_worker,
        IntervalTrigger(seconds=5),
        id="job_worker",
        name="Process pending jobs",
        replace_existing=True
    )

    # Inbox scanner - check every minute
    scheduler.add_job(
        scan_inbox,
        IntervalTrigger(minutes=1),
        id="inbox_scanner",
        name="Scan inbox for new files",
        replace_existing=True
    )

    # Stuck job recovery - check every 5 minutes
    scheduler.add_job(
        recover_stuck_jobs,
        IntervalTrigger(minutes=5),
        id="stuck_job_recovery",
        name="Recover stuck jobs",
        replace_existing=True
    )

    # Weekly score refresh - Sunday at 2 AM
    scheduler.add_job(
        weekly_score_refresh,
        CronTrigger(day_of_week='sun', hour=2, minute=0),
        id="weekly_score_refresh",
        name="Weekly score snapshot and refresh",
        replace_existing=True
    )

    scheduler.start()
    logger.info("Background scheduler started")


def stop_scheduler():
    """Stop the background scheduler."""
    global scheduler

    if scheduler is not None:
        scheduler.shutdown(wait=False)
        scheduler = None
        logger.info("Background scheduler stopped")


def get_scheduler_status() -> dict:
    """Get scheduler status."""
    if scheduler is None:
        return {"running": False, "jobs": []}

    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": str(job.next_run_time) if job.next_run_time else None
        })

    return {"running": scheduler.running, "jobs": jobs}


# Auto-start when imported as part of the app
def init_worker():
    """Initialize the worker (call from FastAPI startup)."""
    start_scheduler()
