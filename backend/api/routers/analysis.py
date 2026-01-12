"""
Analysis API router.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from backend.core.database import get_file
from backend.core.analysis import (
    get_analysis_results, get_recent_anomalies, generate_site_summary,
    analyze_document, save_analysis_result
)

router = APIRouter(prefix="/api/analysis", tags=["Analysis"])


@router.get("/results")
def list_analysis_results(
    file_id: Optional[str] = Query(None),
    analysis_type: Optional[str] = Query(None),
    limit: int = Query(20, le=100)
):
    """Get analysis results with optional filters."""
    results = get_analysis_results(file_id=file_id, analysis_type=analysis_type, limit=limit)
    return {"results": results, "count": len(results)}


@router.get("/anomalies")
def list_anomalies(limit: int = Query(10, le=50)):
    """Get recent anomalies detected across all files."""
    anomalies = get_recent_anomalies(limit=limit)
    return {"anomalies": anomalies, "count": len(anomalies)}


@router.get("/file/{file_id}")
def get_file_analysis(file_id: str):
    """Get all analysis results for a specific file."""
    results = get_analysis_results(file_id=file_id)
    if not results:
        raise HTTPException(status_code=404, detail="No analysis found for file")
    return {"file_id": file_id, "analyses": results}


@router.post("/file/{file_id}")
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


@router.get("/site/{site_id}/summary")
def get_site_analysis_summary(site_id: str):
    """Generate an AI summary for a site."""
    summary = generate_site_summary(site_id)
    if not summary:
        raise HTTPException(status_code=404, detail="No data found for site")
    return summary
