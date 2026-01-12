"""
AI Analysis Service - Background document analysis using Ollama

Provides:
- Anomaly detection for inventory data
- Auto-summary generation
- Key insights extraction
"""

import json
from datetime import datetime
from typing import Optional

from backend.core.database import (
    get_db, get_file, FileStatus
)
from backend.core.engine import parse_excel_file, parse_csv_file
from backend.core import llm

# Alert thresholds for change detection
VALUE_CHANGE_ALERT_THRESHOLD = 20.0   # Percent change to trigger value alert
ROW_COUNT_ALERT_THRESHOLD = 10        # Row count change to trigger alert
SITE_SUMMARY_FILE_LIMIT = 10          # Max files to consider for site summary
COMPARISON_HISTORY_LIMIT = 5          # Max previous files to compare against
ANALYSIS_ROWS_LIMIT = 50              # Max rows to send for AI analysis


def check_ollama_available() -> bool:
    """Check if Ollama is running and model is available."""
    return llm.check_available()


def generate_completion(prompt: str, system: str = None, max_tokens: int = 1000) -> Optional[str]:
    """Generate a completion using Ollama."""
    return llm.generate(prompt, system=system, max_tokens=max_tokens)


def analyze_document(file_id: str) -> Optional[dict]:
    """
    Analyze a processed document for anomalies and insights.

    Returns dict with:
    - summary: Brief document summary
    - anomalies: List of detected anomalies
    - insights: Key observations
    - risk_score: 0-100 risk assessment
    """
    file_record = get_file(file_id)
    if not file_record or file_record['status'] != FileStatus.COMPLETED.value:
        return None

    # Get parsed data
    parsed_data = file_record.get('parsed_data')
    if not parsed_data:
        return None

    try:
        data = json.loads(parsed_data)
    except json.JSONDecodeError:
        return None

    # Prepare data summary for LLM
    headers = data.get('headers', [])
    rows = data.get('rows', [])[:ANALYSIS_ROWS_LIMIT]  # Limit rows for analysis
    metadata = data.get('metadata', {})

    data_summary = f"""
Document: {metadata.get('filename', 'Unknown')}
Columns: {', '.join(headers[:10])}
Total Rows: {metadata.get('row_count', len(rows))}

Sample Data (first 10 rows):
"""
    for i, row in enumerate(rows[:10]):
        row_str = " | ".join(str(v)[:30] for v in row.values())
        data_summary += f"{i+1}. {row_str}\n"

    # Generate analysis
    system_prompt = """You are an inventory data analyst. Analyze the provided data and identify:
1. Any anomalies or unusual patterns
2. Key insights about the inventory
3. Potential issues or risks

Be concise and factual. Focus on actionable observations."""

    analysis_prompt = f"""Analyze this inventory document:

{data_summary}

Provide your analysis in this JSON format:
{{
    "summary": "Brief 1-2 sentence summary of the document",
    "anomalies": ["anomaly 1", "anomaly 2"],
    "insights": ["insight 1", "insight 2"],
    "risk_score": 0-100,
    "risk_factors": ["factor 1", "factor 2"]
}}

Only output valid JSON, nothing else."""

    response = generate_completion(analysis_prompt, system_prompt)
    if not response:
        return None

    # Parse JSON response
    try:
        # Try to extract JSON from response
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            analysis = json.loads(response[json_start:json_end])
            analysis['file_id'] = file_id
            analysis['analyzed_at'] = datetime.now().isoformat()
            return analysis
    except json.JSONDecodeError:
        pass

    # Fallback if JSON parsing fails
    return {
        'file_id': file_id,
        'summary': response[:200],
        'anomalies': [],
        'insights': [],
        'risk_score': 0,
        'risk_factors': [],
        'analyzed_at': datetime.now().isoformat(),
        'raw_response': response
    }


def compare_with_previous(file_id: str, site_id: str = None) -> Optional[dict]:
    """
    Compare a document with previous versions to detect drift.

    Returns comparison results including value changes and anomalies.
    """
    file_record = get_file(file_id)
    if not file_record:
        return None

    # Get previous files for same site
    site = site_id or file_record.get('site_id')
    if not site:
        return None

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, filename, parsed_data, created_at
            FROM files
            WHERE site_id = ? AND status = ? AND id != ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (site, FileStatus.COMPLETED.value, file_id, COMPARISON_HISTORY_LIMIT))
        previous_files = cursor.fetchall()

    if not previous_files:
        return {'message': 'No previous files for comparison'}

    # Compare with most recent previous file
    prev = previous_files[0]
    try:
        current_data = json.loads(file_record.get('parsed_data', '{}'))
        previous_data = json.loads(prev[2] or '{}')
    except json.JSONDecodeError:
        return None

    current_rows = current_data.get('rows', [])
    previous_rows = previous_data.get('rows', [])

    # Simple comparison metrics
    comparison = {
        'file_id': file_id,
        'compared_with': prev[0],
        'compared_filename': prev[1],
        'current_row_count': len(current_rows),
        'previous_row_count': len(previous_rows),
        'row_count_change': len(current_rows) - len(previous_rows),
        'compared_at': datetime.now().isoformat()
    }

    # Calculate value changes if Total Price column exists
    def sum_totals(rows):
        total = 0
        for row in rows:
            for key, val in row.items():
                if 'total' in key.lower() or 'price' in key.lower():
                    try:
                        cleaned = str(val).replace('$', '').replace(',', '')
                        total += float(cleaned)
                    except (ValueError, TypeError):
                        pass
        return total

    current_total = sum_totals(current_rows)
    previous_total = sum_totals(previous_rows)

    if previous_total > 0:
        pct_change = ((current_total - previous_total) / previous_total) * 100
    else:
        pct_change = 0

    comparison['current_value'] = current_total
    comparison['previous_value'] = previous_total
    comparison['value_change'] = current_total - previous_total
    comparison['value_change_pct'] = round(pct_change, 2)

    # Flag significant changes
    comparison['alerts'] = []
    if abs(pct_change) > VALUE_CHANGE_ALERT_THRESHOLD:
        comparison['alerts'].append(f"Significant value change: {pct_change:+.1f}%")
    if abs(comparison['row_count_change']) > ROW_COUNT_ALERT_THRESHOLD:
        comparison['alerts'].append(f"Row count changed by {comparison['row_count_change']}")

    return comparison


def generate_site_summary(site_id: str) -> Optional[dict]:
    """
    Generate a summary report for a site based on all its documents.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT id, filename, parsed_data, created_at
            FROM files
            WHERE site_id = ? AND status = ?
            ORDER BY created_at DESC
            LIMIT {SITE_SUMMARY_FILE_LIMIT}
        """, (site_id, FileStatus.COMPLETED.value))
        files = cursor.fetchall()

    if not files:
        return None

    # Gather data from files
    file_summaries = []
    for f in files:
        try:
            data = json.loads(f[2] or '{}')
            rows = data.get('rows', [])

            # Calculate totals
            total = 0
            for row in rows:
                for key, val in row.items():
                    if 'total' in key.lower():
                        try:
                            cleaned = str(val).replace('$', '').replace(',', '')
                            total += float(cleaned)
                        except (ValueError, TypeError):
                            pass

            file_summaries.append({
                'filename': f[1],
                'date': f[3],
                'row_count': len(rows),
                'total_value': total
            })
        except json.JSONDecodeError:
            continue

    if not file_summaries:
        return None

    # Generate LLM summary
    summary_text = f"Site: {site_id}\nRecent Documents:\n"
    for fs in file_summaries:
        summary_text += f"- {fs['filename']}: {fs['row_count']} items, ${fs['total_value']:,.2f}\n"

    system_prompt = "You are an inventory analyst. Provide a brief executive summary of the site's inventory status."

    prompt = f"""Based on this inventory data for site {site_id}:

{summary_text}

Provide a 2-3 sentence executive summary highlighting:
1. Current inventory status
2. Any trends across recent reports
3. Areas needing attention"""

    response = generate_completion(prompt, system_prompt, max_tokens=200)

    return {
        'site_id': site_id,
        'file_count': len(file_summaries),
        'latest_file': file_summaries[0] if file_summaries else None,
        'total_value': sum(f['total_value'] for f in file_summaries),
        'ai_summary': response,
        'generated_at': datetime.now().isoformat()
    }


def save_analysis_result(file_id: str, analysis_type: str, result: dict) -> str:
    """Save analysis result to database."""
    import uuid

    result_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO analysis_results (id, file_id, analysis_type, result, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (result_id, file_id, analysis_type, json.dumps(result), now))

    return result_id


def get_analysis_results(file_id: str = None, analysis_type: str = None, limit: int = 20) -> list:
    """Get analysis results with optional filters."""
    query = "SELECT * FROM analysis_results WHERE 1=1"
    params = []

    if file_id:
        query += " AND file_id = ?"
        params.append(file_id)
    if analysis_type:
        query += " AND analysis_type = ?"
        params.append(analysis_type)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

    # Parse JSON result field
    for r in results:
        try:
            r['result'] = json.loads(r['result'])
        except (json.JSONDecodeError, TypeError):
            pass

    return results


def get_recent_anomalies(limit: int = 10) -> list:
    """Get recent anomalies across all files."""
    results = get_analysis_results(analysis_type='document_analysis', limit=50)

    anomalies = []
    for r in results:
        result_data = r.get('result', {})
        if isinstance(result_data, dict):
            file_anomalies = result_data.get('anomalies', [])
            risk_score = result_data.get('risk_score', 0)

            if file_anomalies or risk_score > 50:
                anomalies.append({
                    'file_id': r['file_id'],
                    'anomalies': file_anomalies,
                    'risk_score': risk_score,
                    'summary': result_data.get('summary', ''),
                    'detected_at': r['created_at']
                })

    return anomalies[:limit]
