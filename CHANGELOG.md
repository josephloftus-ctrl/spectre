# Changelog

All notable changes to the Spectre Inventory Platform.

---

## [2026-01-04] - Documentation Update

### Added
- `PROJECT_STATUS.md` - Current system state and quick reference
- `ARCHITECTURE.md` - Full system architecture documentation
- `CHANGELOG.md` - This file

### Changed
- Moved `Suu-AI` and `lylp all` to `/Documents/other_projects/`

---

## [2026-01-03] - Phase 5 Complete

### Added
- AI analysis service (`backend/core/analysis.py`)
- Automatic document analysis after embedding
- Anomaly detection with risk scoring
- Site summary generation via AI
- Drift detection (comparison with previous files)
- Analysis API endpoints:
  - `GET /api/analysis/results`
  - `GET /api/analysis/anomalies`
  - `GET /api/analysis/file/{file_id}`
  - `POST /api/analysis/file/{file_id}`
  - `GET /api/analysis/site/{site_id}/summary`
- Dashboard AI Insights widget

### Changed
- Site page updated to match API data format
- Dashboard now shows real stats from API

---

## [2026-01-02] - Phase 4 Complete

### Added
- ChromaDB vector database integration
- Ollama nomic-embed-text embedding model
- Document chunking for embeddings
- Semantic search API (`POST /api/search`)
- Similar documents API (`GET /api/search/similar/{file_id}`)
- Embedding statistics endpoint
- Search page in frontend with semantic search UI

### Changed
- Background worker now processes embedding jobs

---

## [2026-01-01] - Phase 2-3 Complete

### Added
- APScheduler background job system
- Job queue with retry logic (max 3 attempts)
- File processing worker (5-second polling)
- Enhanced Excel parsing with header detection
- Job management API endpoints
- Worker status API endpoint
- Documents page with processing status indicators

---

## [2025-12-31] - Phase 1 Complete

### Added
- `/data` directory structure:
  - `inbox/` - Raw uploads
  - `processed/` - Successfully parsed files
  - `failed/` - Processing failures
  - `embeddings/` - Vector store
  - `exports/` - Generated reports
- SQLite database (`spectre.db`)
- File lifecycle management (upload → process → archive)
- File management API endpoints:
  - `POST /api/files/upload`
  - `GET /api/files`
  - `GET /api/files/{id}`
  - `GET /api/files/{id}/download`
  - `POST /api/files/{id}/retry`
- System stats API (`GET /api/stats`)
- Import script for existing files (`backend/scripts/import_existing.py`)

### Changed
- Inbox page now has real file upload functionality
- Dashboard widgets show live data

---

## [2025-12-30] - Initial Setup

### Added
- React + Vite + TailwindCSS frontend
- FastAPI backend
- shadcn/ui component library
- Basic dashboard with KPIs and site carousel
- Ollama integration for AI chat
- Chat sessions with IndexedDB history
- Memory system (save/view/delete)
- Notes with voice recording
- Basic Excel parsing for inventory metrics
- Nginx configuration for serving frontend

### Infrastructure
- Frontend served at port 8090 (nginx)
- Backend API at port 8000
- Ollama at port 11434

---

## Roadmap

### Phase 6: UI Polish (Upcoming)
- [ ] Message markdown rendering
- [ ] Code syntax highlighting
- [ ] File attachment in chat
- [ ] Model selector in chat header
- [ ] Conversation search
- [ ] Export chat as PDF/markdown
- [ ] Dark/light theme toggle
- [ ] Mobile-responsive improvements
- [ ] Typing indicators
- [ ] Message reactions/feedback

### Future Considerations
- [ ] User authentication
- [ ] Multi-tenant support
- [ ] PDF document parsing
- [ ] Scheduled report generation
- [ ] Email notifications for anomalies
- [ ] Celery migration for heavier workloads
