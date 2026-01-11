# Project State & Implementation Plan

> Last updated: 2026-01-04 @ 11:15 AM EST
> Maintainer: Claude Code
> See also: PROJECT_STATUS.md, ARCHITECTURE.md, CHANGELOG.md

---

## MCP Tools

Always use Context7 MCP when I need library/API documentation, code generation, setup or configuration steps without me having to explicitly ask.

---

## STATUS SNAPSHOT

### Current System State
| Metric | Value |
|--------|-------|
| Files Processed | 15 completed, 1 failed |
| Embeddings | 3,370 chunks indexed |
| Jobs | 42 completed, 2 queued |
| Sites | 1 (pseg_nhq) |

### Services Running
- **Frontend**: http://localhost:8090 ✅
- **Backend API**: http://localhost:8000 ✅
- **Ollama**: http://localhost:11434 ✅
- **Background Worker**: Running (5s job cycle) ✅

### What's Working
- ✅ File upload via Inbox page
- ✅ Automatic parsing of Excel files
- ✅ Embedding generation with nomic-embed-text
- ✅ Semantic search across documents
- ✅ AI analysis with anomaly detection
- ✅ Site detail page with drift analysis
- ✅ Dashboard with stats widgets
- ✅ Documents page with file list

### Known Issues
- ⚠️ 1 file failed to process (needs investigation)
- ⚠️ AI analysis jobs still queued (Ollama may be busy)

---

## Recent Changes (2026-01-03)

### Phase 5 Complete - AI Analysis
- [x] AI analysis service (`backend/core/analysis.py`)
- [x] Automatic document analysis after embedding
- [x] Anomaly detection with risk scoring
- [x] Site summary generation
- [x] Comparison with previous files (drift detection)
- [x] Analysis API endpoints
- [x] Dashboard AI Insights widget

### Phase 4 Complete - File Processing Pipeline
- [x] `/data` directory structure (inbox, processed, failed, embeddings, exports)
- [x] SQLite database for file/job tracking (`data/spectre.db`)
- [x] File lifecycle management (upload → process → archive)
- [x] Background job worker with APScheduler
- [x] ChromaDB vector database for embeddings
- [x] Ollama nomic-embed-text integration
- [x] New API endpoints for files, jobs, search, embeddings

### Frontend Updates
- [x] Inbox page with real file upload
- [x] Documents page with processing status
- [x] Search page with semantic search
- [x] Site page fixed to match API data format
- [x] Dashboard stats widgets (files, jobs, embeddings, worker)

### Import Script
- [x] Created `backend/scripts/import_existing.py`
- [x] Imported 15 existing Excel files from `sorted/by_site/`

---

## Project Overview

**Spectre** - Inventory operations dashboard with AI-powered analysis

| Component | Tech | Port |
|-----------|------|------|
| Frontend | React + Vite + TailwindCSS | 8090 (nginx) |
| Backend API | FastAPI (Python) | 8000 |
| AI (Local) | Ollama | 11434 |
| Database | IndexedDB (browser) + filesystem |

---

## Current Architecture

```
/home/joseph-loftus/Documents/Inventory  docs/
├── frontend/               # React SPA
│   ├── src/
│   │   ├── components/     # UI components (shadcn/ui)
│   │   ├── hooks/          # useChat, useOllama, useNotes, etc.
│   │   ├── lib/
│   │   │   ├── db/         # Dexie IndexedDB wrapper
│   │   │   ├── api.ts      # Backend API client
│   │   │   └── ollama.ts   # Ollama/Claude client
│   │   └── pages/          # Route pages
│   └── dist/               # Built assets (served by nginx)
├── backend/
│   ├── api/main.py         # FastAPI routes
│   └── core/engine.py      # Excel parsing & metrics
├── sorted/by_site/         # Inventory files organized by site
├── nginx/                  # Nginx config (spectre.conf)
└── CLAUDE.md               # This file
```

---

## Current State Assessment

### Working Features
- [x] Dashboard with KPIs, site carousel, health matrix
- [x] Ollama/Claude AI chat with streaming
- [x] Chat sessions with history (IndexedDB)
- [x] Memory system (save/view/delete memories)
- [x] Notes with voice recording
- [x] Basic Excel parsing for inventory metrics
- [x] Auto-reconnection to Ollama on restart

### Incomplete/Stubbed Features
- [ ] **File upload processing** - UI exists, but files aren't parsed with AI
- [ ] **Documents page** - placeholder only
- [ ] **Embedding-based search** - not implemented
- [ ] **Background processing** - all synchronous
- [ ] **Permanent file storage** - no organized pipeline

### Known Issues
- Memory importance hardcoded to 4 (should be selectable)
- Only top 10 memories loaded into context
- No vector search for relevant memories
- Inbox file processing is simulated (setTimeout)

---

## Ollama Models Available

```
granite4:3b
granite3.1-moe:latest
nomic-embed-text:v1.5      <- EMBEDDING MODEL
qwen3-vl:4b                <- VISION MODEL
olmo-3:7b
llama3.2:latest
qwen3-vl:latest
```

---

## Implementation Plan: File Processing Pipeline

### Phase 1: Storage Infrastructure

**Goal:** Organized file storage with clear lifecycle stages

```
/data/                      # New root for all data
├── inbox/                  # Raw uploads awaiting processing
│   └── {uuid}/
│       ├── original.xlsx
│       └── metadata.json
├── processed/              # Successfully parsed files
│   └── {site}/
│       └── {date}/
│           ├── parsed.json     # Extracted data
│           └── original.xlsx   # Archive
├── embeddings/             # Vector store
│   └── chroma/             # ChromaDB persistence
└── failed/                 # Files that failed processing
    └── {uuid}/
        ├── original.xlsx
        ├── error.log
        └── metadata.json
```

**Tasks:**
1. Create directory structure
2. Add storage config to backend
3. Create file lifecycle state machine
4. Add file move/archive utilities

---

### Phase 2: Background Job System

**Goal:** Process files asynchronously without blocking UI

**Options evaluated:**
| Option | Pros | Cons |
|--------|------|------|
| Celery + Redis | Battle-tested, powerful | Heavy, needs Redis |
| Dramatiq | Lighter than Celery | Still needs broker |
| RQ (Redis Queue) | Simple | Needs Redis |
| APScheduler | No broker needed | In-process only |
| **Simple file-based queue** | Zero deps, easy | Limited scaling |

**Recommendation:** Start with **APScheduler** for simplicity, migrate to Celery if needed.

**Tasks:**
1. Add APScheduler to backend
2. Create job queue table (or file-based)
3. Implement worker that polls for new files
4. Add job status API endpoints
5. Show processing status in frontend

---

### Phase 3: Document Parsing Pipeline

**Goal:** Extract structured data from Excel/PDF files

```
Upload → Validate → Parse → Extract → Transform → Store
```

**Parsing strategies by file type:**

| Type | Parser | Output |
|------|--------|--------|
| Excel (.xlsx) | openpyxl / current engine.py | JSON rows |
| CSV | pandas | JSON rows |
| PDF | PyMuPDF + pdfplumber | Text + tables |

**Tasks:**
1. Enhance engine.py with better header detection
2. Add PDF parsing capability
3. Create unified document schema
4. Store parsed data in SQLite or JSON files
5. Add parsing error handling & retry logic

---

### Phase 4: Embedding Pipeline

**Goal:** Enable semantic search across documents

**Architecture:**
```
Parsed Doc → Chunk → Embed (nomic-embed-text) → Store (ChromaDB)
```

**Chunking strategy:**
- Split by rows for tabular data
- Split by paragraphs for text
- Overlap chunks for context continuity
- Max 512 tokens per chunk (nomic-embed-text limit)

**Tasks:**
1. Install ChromaDB (`pip install chromadb`)
2. Create embedding service using Ollama API
3. Implement document chunker
4. Build ingestion pipeline: parse → chunk → embed → store
5. Create search API endpoint
6. Add search UI to frontend

**Embedding API (Ollama):**
```python
import requests

def embed(text: str) -> list[float]:
    resp = requests.post('http://localhost:11434/api/embeddings', json={
        'model': 'nomic-embed-text:v1.5',
        'prompt': text
    })
    return resp.json()['embedding']
```

---

### Phase 5: Background AI Analysis

**Goal:** Automatic insights without user interaction

**Scheduled jobs:**
| Job | Frequency | Action |
|-----|-----------|--------|
| New file scan | Every 5 min | Check inbox, queue processing |
| Anomaly detection | Daily | Compare latest vs historical |
| Summary generation | Weekly | Generate site summaries |
| Memory extraction | Per chat | Extract key facts from conversations |

**Tasks:**
1. Create scheduled job definitions
2. Implement anomaly detector using embeddings
3. Add auto-summary generation
4. Create notification system for alerts
5. Build admin UI for job management

---

### Phase 6: UI Polish (OpenWebUI-inspired)

**Goal:** Modern, polished chat interface

**Improvements:**
- [ ] Message markdown rendering
- [ ] Code syntax highlighting
- [ ] File attachment in chat
- [ ] Model selector in chat header
- [ ] Conversation search
- [ ] Export chat as PDF/markdown
- [ ] Dark/light theme toggle
- [ ] Mobile-responsive chat
- [ ] Typing indicators
- [ ] Message reactions/feedback

---

## API Endpoints (Current)

```
GET  /api/inventory/summary     # All sites overview
GET  /api/inventory/{site}      # Single site metrics
GET  /api/health                # Health check
```

## API Endpoints (Planned)

```
# File Management
POST /api/files/upload          # Upload new file
GET  /api/files                 # List all files
GET  /api/files/{id}            # Get file details
GET  /api/files/{id}/status     # Processing status

# Search
POST /api/search                # Semantic search
GET  /api/search/similar/{id}   # Find similar documents

# Jobs
GET  /api/jobs                  # List background jobs
GET  /api/jobs/{id}             # Job status
POST /api/jobs/{id}/retry       # Retry failed job

# Analysis
GET  /api/analysis/anomalies    # Recent anomalies
GET  /api/analysis/trends       # Trend analysis
POST /api/analysis/ask          # Ask question about data
```

---

## Environment & Services

**Systemd services:**
```bash
# Ollama (user service)
~/.config/systemd/user/ollama.service
systemctl --user status ollama

# Start script with CORS
~/.local/bin/ollama-serve.sh
```

**Nginx config:**
```
/home/joseph-loftus/Documents/Inventory  docs/nginx/spectre.conf
```

**Key environment variables:**
```bash
OLLAMA_ORIGINS="*"          # Allow all origins
OLLAMA_HOST="0.0.0.0"       # Listen on all interfaces
```

---

## Next Steps (Priority Order)

1. **Create `/data` directory structure** (Phase 1)
2. **Add SQLite for file/job tracking** (Phase 1)
3. **Implement APScheduler** (Phase 2)
4. **Create file processing worker** (Phase 2)
5. **Add ChromaDB + embedding pipeline** (Phase 4)
6. **Build search API** (Phase 4)
7. **UI improvements** (Phase 6)

---

## Commands Reference

```bash
# Build frontend
cd frontend && npm run build

# Restart nginx
kill -HUP $(cat nginx/logs/nginx.pid)

# Check Ollama
curl http://localhost:11434/api/tags

# Restart Ollama
systemctl --user restart ollama

# Test embedding
curl -X POST http://localhost:11434/api/embeddings \
  -d '{"model":"nomic-embed-text:v1.5","prompt":"test"}'
```

---

## Dependencies to Add

**Python (backend):**
```
chromadb>=0.4.0
apscheduler>=3.10.0
python-multipart>=0.0.6
aiofiles>=23.0.0
```

**Node (frontend):**
```
react-markdown
remark-gfm
prism-react-renderer
```
