"""
Smoke tests for the 5 most critical API endpoints.

These verify that the endpoints respond correctly with basic happy-path
and error-path scenarios using an in-memory test database.
"""
import json

from tests.conftest import create_file, create_job, create_score, create_score_history


# ============================================================================
# GET /api/inventory/summary
# ============================================================================

class TestInventorySummary:
    """Tests for the inventory summary endpoint."""

    def test_empty_summary(self, client, patch_db):
        """Returns empty summary when no scores exist."""
        resp = client.get("/api/inventory/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["sites"] == []
        assert data["global_value"] == 0
        assert data["active_sites"] == 0
        assert data["total_issues"] == 0

    def test_summary_with_sites(self, client, patch_db):
        """Returns correct aggregation across multiple sites."""
        file_id = create_file(patch_db, site_id="pseg_nhq", inventory_date="2026-01-29")
        create_score(
            patch_db,
            site_id="pseg_nhq",
            score=7,
            status="warning",
            total_value=15000.0,
            item_flag_count=4,
            file_id=file_id,
        )
        create_score(
            patch_db,
            site_id="lockheed_martin_bldg_100",
            score=0,
            status="clean",
            total_value=8000.0,
            item_flag_count=0,
        )

        resp = client.get("/api/inventory/summary")
        assert resp.status_code == 200
        data = resp.json()

        assert data["active_sites"] == 2
        assert data["global_value"] == 23000.0
        assert data["total_issues"] == 4
        assert len(data["sites"]) == 2

        # Check that inventory_date comes through for the linked file
        nhq_site = next(s for s in data["sites"] if s["site"] == "pseg_nhq")
        assert nhq_site["inventory_date"] == "2026-01-29"
        assert nhq_site["health_status"] == "warning"


# ============================================================================
# POST /api/files/upload
# ============================================================================

class TestFileUpload:
    """Tests for the file upload endpoint."""

    def test_upload_no_file(self, client, patch_db):
        """Returns 422 when no file is provided."""
        resp = client.post("/api/files/upload")
        assert resp.status_code == 422

    def test_list_files_empty(self, client, patch_db):
        """Returns empty list when no files exist."""
        resp = client.get("/api/files")
        assert resp.status_code == 200
        data = resp.json()
        assert data["files"] == []
        assert data["count"] == 0

    def test_list_files_with_data(self, client, patch_db):
        """Returns files when they exist in the database."""
        create_file(patch_db, filename="report_a.xlsx", site_id="pseg_nhq")
        create_file(patch_db, filename="report_b.xlsx", site_id="pseg_salem")

        resp = client.get("/api/files")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2

    def test_list_files_filter_by_site(self, client, patch_db):
        """Filters files by site_id query parameter."""
        create_file(patch_db, filename="report_a.xlsx", site_id="pseg_nhq")
        create_file(patch_db, filename="report_b.xlsx", site_id="pseg_salem")

        resp = client.get("/api/files?site_id=pseg_nhq")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["files"][0]["site_id"] == "pseg_nhq"

    def test_get_file_not_found(self, client, patch_db):
        """Returns 404 for nonexistent file."""
        resp = client.get("/api/files/nonexistent-id")
        assert resp.status_code == 404


# ============================================================================
# GET /api/scores
# ============================================================================

class TestScores:
    """Tests for the scores endpoint."""

    def test_empty_scores(self, client, patch_db):
        """Returns empty list when no scores exist."""
        resp = client.get("/api/scores")
        assert resp.status_code == 200
        data = resp.json()
        assert data["units"] == []
        assert data["count"] == 0

    def test_scores_list(self, client, patch_db):
        """Returns scores sorted by severity (worst first)."""
        create_score(patch_db, site_id="pseg_nhq", score=12, status="critical", total_value=20000)
        create_score(patch_db, site_id="pseg_salem", score=3, status="healthy", total_value=8000)

        resp = client.get("/api/scores")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2

        # Worst first
        assert data["units"][0]["site_id"] == "pseg_nhq"
        assert data["units"][0]["status"] == "critical"
        assert data["units"][1]["site_id"] == "pseg_salem"

    def test_score_detail(self, client, patch_db):
        """Returns detailed score for a specific site."""
        flagged = [{"item": "BEEF PATTY", "qty": 15, "uom": "CS", "total": 300, "flags": ["uom_error"], "points": 3, "location": "Freezer"}]
        create_score(
            patch_db,
            site_id="pseg_nhq",
            score=7,
            status="warning",
            flagged_items=flagged,
            item_flag_count=1,
        )

        resp = client.get("/api/scores/pseg_nhq")
        assert resp.status_code == 200
        data = resp.json()
        assert data["site_id"] == "pseg_nhq"
        assert data["status"] == "warning"
        assert len(data["flagged_items"]) == 1
        assert data["flagged_items"][0]["item"] == "BEEF PATTY"

    def test_score_not_found(self, client, patch_db):
        """Returns 404 for site with no score."""
        resp = client.get("/api/scores/nonexistent_site")
        assert resp.status_code == 404

    def test_score_history(self, client, patch_db):
        """Returns score history for a site."""
        create_score(patch_db, site_id="pseg_nhq")
        create_score_history(patch_db, site_id="pseg_nhq", score=5, snapshot_date="2026-01-20")
        create_score_history(patch_db, site_id="pseg_nhq", score=3, snapshot_date="2026-01-13")

        resp = client.get("/api/scores/pseg_nhq/history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2
        # Most recent first
        assert data["history"][0]["snapshot_date"] == "2026-01-20"


# ============================================================================
# POST /api/search
# ============================================================================

class TestSearch:
    """Tests for the search endpoint.

    Note: The search endpoint depends on the purchase match MOG index.
    We test the 503 fallback when MOG is not loaded.
    """

    def test_search_requires_query(self, client, patch_db):
        """Returns 422 when query parameter is missing."""
        resp = client.post("/api/search")
        assert resp.status_code == 422

    def test_search_no_mog_returns_503(self, client, patch_db):
        """Returns 503 when MOG index is not available."""
        from unittest.mock import patch as mock_patch

        with mock_patch("backend.api.routers.search._init_purchase_match"):
            with mock_patch("backend.api.routers.search._purchase_match_state", {"mog_index": None}):
                resp = client.post("/api/search", data={"query": "chicken"})
                assert resp.status_code == 503


# ============================================================================
# GET /api/jobs
# ============================================================================

class TestJobs:
    """Tests for the jobs endpoint."""

    def test_empty_jobs(self, client, patch_db):
        """Returns empty list when no jobs exist."""
        resp = client.get("/api/jobs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["jobs"] == []
        assert data["count"] == 0

    def test_jobs_list(self, client, patch_db):
        """Returns jobs sorted by creation time (newest first)."""
        file_id = create_file(patch_db)
        create_job(patch_db, job_type="parse", file_id=file_id, status="completed")
        create_job(patch_db, job_type="embed", file_id=file_id, status="queued")

        resp = client.get("/api/jobs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2

    def test_jobs_filter_by_status(self, client, patch_db):
        """Filters jobs by status query parameter."""
        file_id = create_file(patch_db)
        create_job(patch_db, job_type="parse", file_id=file_id, status="completed")
        create_job(patch_db, job_type="embed", file_id=file_id, status="queued")

        resp = client.get("/api/jobs?status=queued")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["jobs"][0]["status"] == "queued"

    def test_job_not_found(self, client, patch_db):
        """Returns 404 for nonexistent job."""
        resp = client.get("/api/jobs/nonexistent-id")
        assert resp.status_code == 404


# ============================================================================
# GET /api/health
# ============================================================================

class TestHealthCheck:
    """Tests for the health check endpoint."""

    def test_health(self, client, patch_db):
        """Returns OK status."""
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
