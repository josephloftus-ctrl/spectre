# Spectre

**AI-powered food service inventory management system**

Spectre is a modern inventory operations dashboard that combines document management, semantic search, and AI-powered analysis for food service operations. Built with a local-first approach using Ollama for privacy-focused AI capabilities.

---

## Features

### AI Assistant
- **Chat** - Natural language interface for inventory questions and analysis
- **Daily Standup** - AI-generated safety moments, DEI moments, and manager prompts
- **Help Desk** - Search training materials with confidence-scored answers

### Document Management
- **File Upload** - Drag-and-drop Excel, PDF, and CSV files
- **Folder Sync** - Connect OneDrive folders for automatic imports
- **Processing Pipeline** - Automatic parsing, embedding, and indexing

### Semantic Search
- **Natural Language Queries** - Ask questions like "What items had the highest value drift?"
- **Collection Filtering** - Search across knowledge base, food knowledge, or living memory
- **Date Range Filtering** - Find documents from specific time periods

### Inventory Analytics
- **Site Health Matrix** - At-a-glance status across all locations
- **Drift Detection** - Automatic anomaly detection with risk scoring
- **Trend Analysis** - Historical comparison and forecasting

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, Vite, TailwindCSS, shadcn/ui |
| Backend | FastAPI (Python), APScheduler |
| AI | Ollama (granite4:3b), nomic-embed-text |
| Vector DB | ChromaDB |
| Database | SQLite |
| Proxy | Nginx |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│  React + Vite + TailwindCSS (port 8090 via nginx)           │
├─────────────────────────────────────────────────────────────┤
│                        Backend API                           │
│  FastAPI + APScheduler (port 8000)                          │
├──────────────────────┬──────────────────────────────────────┤
│      SQLite          │           ChromaDB                    │
│  (files, jobs)       │      (embeddings)                    │
├──────────────────────┴──────────────────────────────────────┤
│                         Ollama                               │
│  granite4:3b (chat) + nomic-embed-text (embeddings)         │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.10+
- [Ollama](https://ollama.ai)

### 1. Install Ollama Models

```bash
ollama pull granite4:3b
ollama pull nomic-embed-text:v1.5
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000
```

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run build
```

### 4. Start Nginx

```bash
cd nginx
nginx -c $(pwd)/spectre.conf
```

### 5. Open the App

Navigate to http://localhost:8090

---

## Project Structure

```
spectre/
├── frontend/               # React SPA
│   ├── src/
│   │   ├── components/     # UI components (shadcn/ui)
│   │   ├── hooks/          # React hooks
│   │   ├── lib/            # API client, utilities
│   │   └── pages/          # Route pages
│   └── dist/               # Built assets
├── backend/
│   ├── api/main.py         # FastAPI routes
│   └── core/               # Business logic
│       ├── engine.py       # Excel parsing
│       ├── embeddings.py   # Vector embeddings
│       ├── analysis.py     # AI analysis
│       └── standup.py      # Daily standup generation
├── data/                   # Runtime data
│   ├── inbox/              # Uploaded files
│   ├── processed/          # Parsed files
│   ├── embeddings/         # ChromaDB persistence
│   └── spectre.db          # SQLite database
└── nginx/                  # Nginx configuration
```

---

## Pages

| Route | Description |
|-------|-------------|
| `/` | Dashboard with KPIs, site carousel, health matrix |
| `/inventory` | Tabbed view: Health, History, Purchase Match |
| `/documents` | File upload and processing status |
| `/assistant` | AI chat, daily standup, help desk |
| `/search` | Semantic search and collection management |
| `/notes` | Note taking with voice recording |
| `/settings` | System configuration and status |

---

## API Endpoints

### Files
- `POST /api/files/upload` - Upload a file
- `GET /api/files` - List all files
- `POST /api/files/{id}/retry` - Retry failed processing

### Search
- `POST /api/search/unified` - Search across all collections
- `POST /api/search/collection/{name}` - Search specific collection

### AI
- `GET /api/standup` - Get daily standup content
- `POST /api/standup/reroll/{section}` - Regenerate a section
- `POST /api/helpdesk/ask` - Ask the help desk

### System
- `GET /api/stats` - System statistics
- `GET /api/health` - Health check
- `GET /api/worker/status` - Background worker status

---

## Environment

The app runs entirely locally with no external API dependencies:

- **AI**: Ollama runs on localhost:11434
- **Backend**: FastAPI on localhost:8000
- **Frontend**: Nginx serves on localhost:8090
- **Data**: SQLite + ChromaDB stored in `/data`

---

## Development

### Frontend Dev Server

```bash
cd frontend
npm run dev
```

### Backend with Auto-reload

```bash
cd backend
uvicorn api.main:app --reload
```

### Check Ollama

```bash
curl http://localhost:11434/api/tags
```

---

## License

MIT

---

## Contributing

Contributions welcome! Please read the contributing guidelines before submitting PRs.
