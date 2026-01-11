# Deep Code Review: Spectre Inventory Platform

**Reviewer:** Claude Code
**Date:** 2026-01-11
**Branch:** `claude/deep-code-review-1R4qW`
**Scope:** Full backend and frontend codebase review

---

## Executive Summary

Spectre is a well-structured inventory management platform with solid architecture. However, this review identified **23 issues** across security, code quality, and performance categories that should be addressed before production deployment.

| Category | Critical | High | Medium | Low |
|----------|----------|------|--------|-----|
| Security | 2 | 3 | 4 | - |
| Code Quality | - | 2 | 5 | 3 |
| Performance | - | 1 | 2 | 1 |

---

## 1. Security Issues

### 1.1 CRITICAL: SQL Injection in Analysis Module

**File:** `backend/core/analysis.py:183-188`

```python
cursor.execute(f"""
    SELECT id, filename, parsed_data, created_at
    FROM files
    WHERE site_id = ? AND status = ? AND id != ?
    ORDER BY created_at DESC
    LIMIT {COMPARISON_HISTORY_LIMIT}
""", (site, FileStatus.COMPLETED.value, file_id))
```

**Issue:** While `COMPARISON_HISTORY_LIMIT` is a constant, f-string interpolation in SQL is a dangerous pattern. If any similar code uses user input, it becomes exploitable.

**Recommendation:** Use parameterized queries consistently:
```python
cursor.execute("""
    SELECT id, filename, parsed_data, created_at
    FROM files
    WHERE site_id = ? AND status = ? AND id != ?
    ORDER BY created_at DESC
    LIMIT ?
""", (site, FileStatus.COMPLETED.value, file_id, COMPARISON_HISTORY_LIMIT))
```

---

### 1.2 CRITICAL: CORS Allows All Origins

**File:** `backend/api/main.py:68-76`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Issue:** `allow_origins=["*"]` with `allow_credentials=True` is a severe security misconfiguration. This allows any website to make authenticated requests to your API, enabling CSRF attacks.

**Note:** The TODO comment on line 68-69 acknowledges this but it remains unimplemented.

**Recommendation:**
```python
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "http://localhost:8090").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

---

### 1.3 HIGH: Path Traversal Risk in File Operations

**File:** `backend/core/files.py:271-285`

```python
for site_dir in PROCESSED_DIR.iterdir():
    if site_dir.is_dir():
        for date_dir in site_dir.iterdir():
            if date_dir.is_dir():
                for f in date_dir.iterdir():
                    if file_id in f.name or (file_record.get('filename') and file_record['filename'] in f.name):
```

**Issue:** The filename comparison `file_record['filename'] in f.name` could potentially match unintended files if filenames contain path components or special characters.

**Recommendation:** Use strict equality with sanitized filenames:
```python
expected_prefix = f"{file_id}_"
if f.name.startswith(expected_prefix):
    # Safe match
```

---

### 1.4 HIGH: Unauthenticated API Endpoints

**File:** `backend/api/main.py` (entire file)

**Issue:** All API endpoints lack authentication/authorization. Any user can:
- Delete files (`DELETE /api/files/{file_id}`)
- Reset all embeddings (`POST /api/embeddings/reset`)
- Run maintenance cleanup (`POST /api/maintenance/cleanup`)
- Modify site names (`PUT /api/sites/{site_id}`)

**Recommendation:** Implement authentication middleware:
```python
from fastapi.security import OAuth2PasswordBearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    # Validate token
    ...
```

---

### 1.5 HIGH: No Rate Limiting

**File:** `backend/api/main.py` (entire file)

**Issue:** No rate limiting on API endpoints. Vulnerable to:
- DoS attacks via expensive endpoints (`/api/helpdesk/ask`, `/api/analysis/file/{file_id}`)
- Brute force enumeration of file IDs
- Resource exhaustion via repeated embedding generation

**Recommendation:** Add rate limiting with `slowapi`:
```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@app.post("/api/helpdesk/ask")
@limiter.limit("10/minute")
async def helpdesk_ask(...):
    ...
```

---

### 1.6 MEDIUM: Sensitive Data in Error Messages

**File:** `backend/api/main.py:168-169`

```python
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
```

**Issue:** Exception details are exposed to clients, potentially revealing internal paths, database errors, or configuration details.

**Recommendation:** Log the full error server-side, return generic message:
```python
except Exception as e:
    logger.exception(f"Upload failed for file {file.filename}")
    raise HTTPException(status_code=500, detail="Upload failed. Please try again.")
```

---

### 1.7 MEDIUM: Unsafe Filename Handling

**File:** `backend/core/files.py:93`

```python
file_path = file_dir / filename
```

**Issue:** While the extension is validated, the filename itself could contain path traversal characters (`../`) or special characters that cause filesystem issues.

**Recommendation:** Sanitize filenames:
```python
import re
safe_filename = re.sub(r'[^\w\s\-.]', '_', filename)
safe_filename = safe_filename.strip()
file_path = file_dir / safe_filename
```

---

### 1.8 MEDIUM: Hardcoded Ollama URL

**Files:** `backend/core/embeddings.py:37`, `backend/core/analysis.py:22`

```python
OLLAMA_URL = "http://localhost:11434"
```

**Issue:** Hardcoded service URLs make configuration changes difficult and could leak internal architecture.

**Recommendation:** Use environment variables:
```python
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
```

---

### 1.9 MEDIUM: Missing Input Validation

**File:** `backend/api/main.py:605-634`

```python
@app.post("/api/memory/note")
def create_memory_note(
    content: str = Form(...),
    title: str = Form(""),
    tags: Optional[str] = Form(None)
):
```

**Issue:** No validation on content length, title format, or tag count. Users could submit extremely large content or malformed data.

**Recommendation:** Add Pydantic validation:
```python
class NoteCreate(BaseModel):
    content: str = Field(..., max_length=50000)
    title: str = Field("", max_length=200)
    tags: Optional[str] = Field(None, max_length=500)
```

---

## 2. Code Quality Issues

### 2.1 HIGH: Database Connection Not Thread-Safe

**File:** `backend/core/database.py:55-67`

```python
@contextmanager
def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

**Issue:** Each call creates a new connection. With concurrent API requests and background workers, this can lead to:
- Connection pool exhaustion
- Database lock contention (`database is locked` errors)
- Performance degradation

**Recommendation:** Use connection pooling or WAL mode:
```python
# Enable WAL mode for better concurrency
def init_db():
    with get_db() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
```

---

### 2.2 HIGH: Missing Database Transaction Boundaries

**File:** `backend/core/worker.py:495-541`

```python
def recover_stuck_jobs():
    from .database import get_db_connection  # This function doesn't exist!
    try:
        with get_db_connection() as conn:
```

**Issue:** References `get_db_connection` which doesn't exist in `database.py`. This will cause a runtime `ImportError`.

**Recommendation:** Fix the import to use the correct function:
```python
from .database import get_db
```

---

### 2.3 MEDIUM: Inconsistent Error Handling Pattern

**Files:** Various

Some functions return `None` on error, others return `{"error": ...}`, and others raise exceptions. This inconsistency makes error handling unpredictable.

**Examples:**
- `embed_text()` returns `None` on failure
- `process_parse_job()` returns `{"error": "..."}` on failure
- `parse_excel_file()` raises `ValueError` on failure

**Recommendation:** Standardize on one pattern (preferably exceptions for critical failures, Result types for expected failures).

---

### 2.4 MEDIUM: Code Duplication in History Endpoints

**File:** `backend/api/main.py:1257-1421`

The functions `get_site_movers()` and `get_site_anomalies()` have nearly identical file fetching and parsing logic (30+ lines duplicated).

**Recommendation:** Extract common logic:
```python
def _get_site_items(site_id: str, file_record: dict) -> dict:
    """Extract items from a file record."""
    # Shared parsing logic
    ...
```

---

### 2.5 MEDIUM: Magic Numbers and Strings

**File:** `backend/core/analysis.py:25-30`

```python
VALUE_CHANGE_ALERT_THRESHOLD = 20.0
ROW_COUNT_ALERT_THRESHOLD = 10
SITE_SUMMARY_FILE_LIMIT = 10
COMPARISON_HISTORY_LIMIT = 5
ANALYSIS_ROWS_LIMIT = 50
```

While constants are defined, many other magic numbers exist throughout:
- `backend/core/embeddings.py:41`: `MAX_CHUNK_SIZE = 500` - Why 500?
- `backend/api/main.py:176`: `limit: int = Query(100, le=500)` - Why these limits?

**Recommendation:** Document the reasoning for these values and consider making them configurable.

---

### 2.6 MEDIUM: Missing Type Hints

**File:** `backend/core/engine.py` (various functions)

```python
def col_index(cell_ref):  # Missing return type
def get_cell_value(c, shared_strings):  # Missing types
def parse_data_sheet(zf, sheet_path, shared_strings):  # Missing types
```

**Recommendation:** Add comprehensive type hints for better IDE support and documentation:
```python
def col_index(cell_ref: str) -> int:
def get_cell_value(c: ET.Element, shared_strings: List[str]) -> str:
```

---

### 2.7 MEDIUM: Logging Inconsistency

**Files:** Various

Some modules use `logging.getLogger(__name__)`, others use `print()`:
- `backend/core/embeddings.py`: Uses `logger`
- `backend/core/analysis.py:69`: Uses `print()`
- `backend/api/main.py:988-990`: Uses `print()`

**Recommendation:** Standardize on logging module throughout.

---

### 2.8 LOW: Long Functions

**File:** `backend/api/main.py`

The `_init_purchase_match()` function (lines 953-1002) is 50 lines. The `run_purchase_match()` endpoint (lines 1063-1160) is nearly 100 lines.

**Recommendation:** Break into smaller, focused functions.

---

### 2.9 LOW: Dead/Unused Imports

**File:** `backend/core/engine.py:4-5`

```python
import shutil  # Not used in the module
```

**Recommendation:** Remove unused imports.

---

### 2.10 LOW: Missing Docstrings

**File:** `backend/core/engine.py:68-76`

```python
def col_index(cell_ref):
    col = ""
    for ch in cell_ref:
        if ch.isalpha(): col += ch
        else: break
    idx = 0
    for c in col:
        idx = idx * 26 + (ord(c.upper()) - 64)
    return idx
```

No docstring explaining what this function does (converts Excel column letter to index).

---

## 3. Performance Issues

### 3.1 HIGH: N+1 Query Pattern

**File:** `backend/api/main.py:700-736`

```python
for s in scores:
    trend = get_score_trend(s["site_id"])  # One query per site
    if s.get("file_id"):
        file_record = get_file(s["file_id"])  # Another query per site
```

**Issue:** For 100 sites, this executes 200+ database queries.

**Recommendation:** Batch fetch:
```python
site_ids = [s["site_id"] for s in scores]
trends = get_score_trends_batch(site_ids)  # Single query
file_ids = [s.get("file_id") for s in scores if s.get("file_id")]
files = get_files_batch(file_ids)  # Single query
```

---

### 3.2 MEDIUM: Synchronous Embedding Generation

**File:** `backend/core/embeddings.py:55-74`

```python
def embed_text(text: str) -> Optional[List[float]]:
    response = requests.post(
        f"{OLLAMA_URL}/api/embeddings",
        json={...},
        timeout=30
    )
```

**Issue:** Blocking HTTP call for each chunk. For documents with 100 chunks, this takes 100 sequential network calls.

**Recommendation:** Use async HTTP client with batching:
```python
async def embed_batch_async(texts: List[str]) -> List[List[float]]:
    async with aiohttp.ClientSession() as session:
        tasks = [embed_single(session, text) for text in texts]
        return await asyncio.gather(*tasks)
```

---

### 3.3 MEDIUM: Large JSON in Database

**File:** `backend/core/database.py:88`

```python
parsed_data TEXT,  -- JSON blob of extracted data
```

**Issue:** Storing potentially large JSON blobs (megabytes) in SQLite TEXT columns. Reading file records always loads this data.

**Recommendation:** Either:
1. Store parsed data in separate files
2. Add a `parsed_data_path` column instead
3. Lazy-load parsed_data only when needed

---

### 3.4 LOW: Repeated Collection Initialization

**File:** `backend/core/embeddings.py:45-52`

```python
def get_collection(name: str = DEFAULT_COLLECTION, force_fresh: bool = False):
    return get_named_collection(name, create=True)
```

Called repeatedly without caching. ChromaDB handles this internally but adds overhead.

---

## 4. Architectural Concerns

### 4.1 Worker Import Issue

**File:** `backend/core/worker.py:500`

```python
from .database import get_db_connection
```

This import will fail at runtime - `get_db_connection` doesn't exist. Should be `get_db`.

---

### 4.2 Global State for Purchase Match

**File:** `backend/api/main.py:944-951`

```python
_purchase_match_state = {
    "config": None,
    "ips_index": None,
    ...
}
```

**Issue:** Global mutable state is problematic for testing and can cause issues with multiple workers.

**Recommendation:** Use dependency injection or a proper service layer.

---

### 4.3 Missing Health Check Depth

**File:** `backend/api/main.py:90-92`

```python
@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": "2.0.0"}
```

**Issue:** Doesn't verify dependencies (database, Ollama, ChromaDB).

**Recommendation:**
```python
@app.get("/api/health")
def health_check():
    checks = {
        "database": check_database(),
        "ollama": check_ollama_available(),
        "chromadb": check_chromadb(),
    }
    all_healthy = all(checks.values())
    return {
        "status": "ok" if all_healthy else "degraded",
        "checks": checks,
        "version": "2.0.0"
    }
```

---

## 5. Positive Observations

The codebase has several strengths:

1. **Good Separation of Concerns:** Clear module boundaries (database, files, embeddings, analysis)

2. **SQL Injection Prevention:** `ALLOWED_FILE_COLUMNS` and `ALLOWED_JOB_COLUMNS` whitelists in `database.py:44-51`

3. **File Type Validation:** Proper extension and MIME type checking in `files.py:30-37`

4. **Filename Sanitization:** `sanitize_filename()` function in `main.py:83-88`

5. **Graceful Degradation:** ChromaDB import with fallback (`embeddings.py:17-23`)

6. **Job Recovery:** `recover_stuck_jobs()` handles server restarts gracefully

7. **Documentation:** Good inline comments and docstrings in most modules

---

## 6. Recommendations Summary

### Immediate (Before Production)

1. Fix CORS configuration - restrict origins
2. Add authentication to all endpoints
3. Fix the `get_db_connection` import error in `worker.py`
4. Add rate limiting to expensive endpoints
5. Remove sensitive data from error responses

### Short-term

6. Enable SQLite WAL mode for concurrency
7. Use environment variables for all service URLs
8. Add input validation with Pydantic models
9. Implement batch queries to eliminate N+1 patterns
10. Add comprehensive health checks

### Long-term

11. Consider async HTTP client for Ollama calls
12. Implement connection pooling
13. Extract parsed_data storage to files
14. Add request/response logging
15. Set up error monitoring (Sentry or similar)

---

## Appendix: Files Reviewed

| File | Lines | Status |
|------|-------|--------|
| `backend/api/main.py` | 1,776 | Reviewed |
| `backend/core/database.py` | 875 | Reviewed |
| `backend/core/worker.py` | 623 | Reviewed |
| `backend/core/engine.py` | 597 | Reviewed |
| `backend/core/embeddings.py` | 558 | Reviewed |
| `backend/core/files.py` | 392 | Reviewed |
| `backend/core/analysis.py` | 397 | Reviewed |

**Total Lines Reviewed:** ~5,218

---

*Report generated by Claude Code on 2026-01-11*
