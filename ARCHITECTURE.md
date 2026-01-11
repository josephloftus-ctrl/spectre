# Spectre - System Architecture

> Inventory Operations Dashboard with AI-Powered Analysis

---

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                           NGINX (Port 8090)                         │
│                    Static files + Reverse proxy                     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          │                         │                         │
          ▼                         ▼                         ▼
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│    Frontend     │      │    Backend API   │      │     Ollama      │
│  React + Vite   │ ──▶  │     FastAPI      │ ──▶  │   LLM Server    │
│   Port: 8090    │      │    Port: 8000    │      │   Port: 11434   │
└─────────────────┘      └─────────────────┘      └─────────────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          │                         │                         │
          ▼                         ▼                         ▼
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│    SQLite       │      │    ChromaDB     │      │   File System   │
│   spectre.db    │      │   Embeddings    │      │  /data folders  │
└─────────────────┘      └─────────────────┘      └─────────────────┘
```

---

## Component Details

### Frontend (React + Vite + TailwindCSS)

**Location:** `frontend/`

**Tech Stack:**
- React 18 with TypeScript
- Vite build tool
- TailwindCSS + shadcn/ui components
- Dexie (IndexedDB wrapper) for client-side storage

**Key Directories:**
```
frontend/src/
├── components/     # UI components (shadcn/ui)
├── hooks/          # Custom React hooks
│   ├── useChat.ts
│   ├── useOllama.ts
│   ├── useNotes.ts
│   └── useMemory.ts
├── lib/
│   ├── db/         # Dexie IndexedDB wrapper
│   ├── api.ts      # Backend API client
│   └── ollama.ts   # Ollama client
└── pages/          # Route pages
```

**Pages:**
- Dashboard - KPIs, site carousel, health matrix
- Inbox - File upload interface
- Documents - File list and status
- Search - Semantic search
- Site Detail - Per-site drill-down
- Chat - AI conversation interface

---

### Backend API (FastAPI)

**Location:** `backend/`

**Tech Stack:**
- FastAPI (Python)
- APScheduler for background jobs
- openpyxl for Excel parsing
- SQLite for metadata

**Key Modules:**
```
backend/
├── api/
│   └── main.py         # FastAPI routes (345 lines)
├── core/
│   ├── engine.py       # Excel parsing & metrics
│   ├── database.py     # SQLite operations
│   ├── files.py        # File lifecycle management
│   ├── embeddings.py   # ChromaDB operations
│   ├── worker.py       # APScheduler background jobs
│   └── analysis.py     # AI analysis service
├── scripts/
│   └── import_existing.py
└── requirements.txt
```

---

### AI Layer (Ollama)

**Location:** Local service

**Available Models:**
| Model | Purpose |
|-------|---------|
| nomic-embed-text:v1.5 | Embeddings (768 dim) |
| qwen3-vl:4b | Vision (document analysis) |
| llama3.2:latest | Chat/reasoning |
| granite4:3b | Fast inference |

**Integration Points:**
1. **Embeddings** - Document chunks → vectors
2. **Chat** - User conversations
3. **Analysis** - Anomaly detection, summaries

---

### Data Storage

#### SQLite (`data/spectre.db`)

**Tables:**
- `files` - File metadata and processing status
- `jobs` - Background job queue
- `analysis_results` - AI analysis outputs

**File Status Flow:**
```
uploaded → processing → processed
                    ↘ failed
```

**Job Status Flow:**
```
queued → running → completed
              ↘ failed (retry up to 3x)
```

#### ChromaDB (`data/embeddings/chroma/`)

- Collection: `spectre_docs`
- Embedding model: nomic-embed-text (768 dimensions)
- Metadata: file_id, chunk_index, site_id, date

#### File System (`data/`)

```
data/
├── inbox/           # Raw uploads
│   └── {uuid}/
│       ├── original.xlsx
│       └── metadata.json
├── processed/       # Successfully parsed
│   └── {site}/
│       └── {date}/
│           ├── parsed.json
│           └── original.xlsx
├── failed/          # Processing failures
│   └── {uuid}/
│       ├── original.xlsx
│       ├── error.log
│       └── metadata.json
├── embeddings/      # ChromaDB persistence
│   └── chroma/
└── exports/         # Generated reports
```

---

## Data Flow

### File Upload Flow

```
1. User uploads file via frontend
         │
         ▼
2. POST /api/files/upload
         │
         ▼
3. Save to data/inbox/{uuid}/
         │
         ▼
4. Create file record in SQLite (status: uploaded)
         │
         ▼
5. Background worker picks up file
         │
         ▼
6. Parse Excel → Extract rows → JSON
         │
         ├─── Success ─────────────────────────┐
         │                                      │
         ▼                                      ▼
7a. Move to data/failed/           7b. Move to data/processed/{site}/
         │                                      │
         ▼                                      ▼
8a. Update status: failed          8b. Update status: processed
                                               │
                                               ▼
                                   9. Create embedding job
                                               │
                                               ▼
                                   10. Chunk document → Embed → ChromaDB
                                               │
                                               ▼
                                   11. Create analysis job
                                               │
                                               ▼
                                   12. AI analyzes document
                                               │
                                               ▼
                                   13. Store analysis results
```

### Search Flow

```
1. User enters query
         │
         ▼
2. POST /api/search (query text)
         │
         ▼
3. Embed query via Ollama
         │
         ▼
4. Query ChromaDB for similar vectors
         │
         ▼
5. Return ranked results with metadata
```

---

## Background Worker

**Implementation:** APScheduler (in-process)

**Jobs:**
| Job | Interval | Action |
|-----|----------|--------|
| process_inbox | 5 sec | Check inbox, process new files |
| embed_documents | 5 sec | Generate embeddings for processed files |
| analyze_documents | 5 sec | Run AI analysis on embedded files |
| cleanup | Daily | Remove old failed files |

**Job Processing:**
```python
# Simplified worker loop
while job = get_next_queued_job():
    try:
        execute(job)
        mark_completed(job)
    except Exception as e:
        if job.attempts < 3:
            mark_failed_retry(job)
        else:
            mark_failed_final(job)
```

---

## Configuration

### Environment Variables

```bash
# Ollama
OLLAMA_ORIGINS="*"
OLLAMA_HOST="0.0.0.0"

# Paths (hardcoded in code)
ROOT_DIR=/home/joseph-loftus/Documents/Inventory  docs
DATA_DIR=$ROOT_DIR/data
SORTED_DIR=$ROOT_DIR/sorted/by_site
```

### Nginx (`nginx/spectre.conf`)

```nginx
server {
    listen 8090;
    root frontend/dist;

    location /api/ {
        proxy_pass http://localhost:8000;
    }
}
```

---

## Security Considerations

- CORS: Currently allows all origins (`*`)
- Auth: None implemented
- File validation: Basic extension check only
- SQL injection: Using parameterized queries
- Path traversal: UUID-based file storage

---

## Performance Notes

- SQLite: Single writer, suitable for current scale
- ChromaDB: In-process, persisted to disk
- Ollama: GPU-accelerated if available
- File processing: Sequential (one at a time)

---

## Dependencies

### Python (`backend/requirements.txt`)
```
fastapi
uvicorn
python-multipart
openpyxl
chromadb>=0.4.0
apscheduler>=3.10.0
aiofiles
requests
```

### Node (`frontend/package.json`)
```
react
react-dom
vite
tailwindcss
@radix-ui/*
lucide-react
dexie
```
