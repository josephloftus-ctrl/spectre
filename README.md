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
- **Site Health Scoring** - Comprehensive health scores combining item and room-level flags
- **Purchase Match Integration** - SKU validation against vendor catalogs with typo detection
- **Room-Level Metrics** - Track inventory by location (walk-in, freezer, dry storage)
- **Drift Detection** - Automatic anomaly detection with risk scoring
- **Trend Analysis** - Historical comparison and forecasting

### Quick Actions (FAB)
- **Quick Note** - Inline note capture with voice recording support
- **Count Session** - Start inventory counts quickly
- **Shopping Cart** - Quick access to order building

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
│   ├── api/
│   │   ├── main.py         # FastAPI app setup
│   │   ├── models.py       # Pydantic request/response models
│   │   └── routers/        # Modular API routers
│   │       ├── inventory.py
│   │       ├── scores.py
│   │       ├── files.py
│   │       ├── search.py
│   │       └── ...
│   └── core/               # Business logic
│       ├── database.py     # SQLite operations
│       ├── worker.py       # Background job processor
│       ├── flag_checker.py # Health scoring system
│       ├── engine.py       # Excel parsing
│       ├── embeddings.py   # Vector embeddings
│       └── analysis.py     # AI analysis
├── data/                   # Runtime data
│   ├── inbox/              # Uploaded files
│   ├── processed/          # Parsed files by site
│   ├── embeddings/         # ChromaDB persistence
│   └── spectre.db          # SQLite database
└── nginx/                  # Nginx configuration
```

---

## Pages

| Route | Description |
|-------|-------------|
| `/` | Dashboard with site health scores, sorted by urgency |
| `/site/:id` | Site detail with room breakdown, flagged items |
| `/inbox` | File upload and processing status |
| `/documents` | Document list and management |
| `/assistant` | AI chat, daily standup, help desk |
| `/search` | Semantic search across all collections |
| `/purchase-match` | SKU validation and catalog matching |
| `/cart` | Shopping cart for order building |
| `/count` | Inventory count sessions |
| `/notes` | Note taking with voice recording |
| `/settings` | System configuration and status |

---

## API Endpoints

### Inventory
- `GET /api/inventory/summary` - Global stats with site health scores
- `GET /api/inventory/sites/{id}` - Site detail with room breakdown
- `GET /api/inventory/sites/{id}/items` - Normalized inventory items

### Scores
- `GET /api/scores` - List all unit scores
- `GET /api/scores/{site_id}` - Site health score detail
- `POST /api/scores/refresh` - Re-score all sites

### Files
- `POST /api/files/upload` - Upload a file
- `GET /api/files` - List all files
- `POST /api/files/{id}/retry` - Retry failed processing

### Search
- `POST /api/search/unified` - Search across all collections
- `POST /api/search/{collection}` - Search specific collection

### Purchase Match
- `GET /api/purchase-match/status` - System status
- `GET /api/purchase-match/run/{unit}` - Run SKU validation

### AI
- `GET /api/standup` - Get daily standup content
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
