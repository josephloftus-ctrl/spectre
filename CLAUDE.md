# Spectre - Project Instructions

> AI-powered inventory operations dashboard
> See also: README.md, CHANGELOG.md, CODE_REVIEW.md

---

## Quick Reference

| Component | Tech | Port |
|-----------|------|------|
| Frontend | React + Vite + TailwindCSS | 8090 (nginx) |
| Backend | FastAPI (Python) | 8000 |
| AI | Ollama (granite4:3b, nomic-embed-text) | 11434 |
| Database | SQLite + ChromaDB | - |

---

## Development Commands

```bash
# Start backend
cd backend && uvicorn api.main:app --reload --port 8000

# Build frontend
cd frontend && npm run build

# Check Ollama
curl http://localhost:11434/api/tags

# Restart nginx
kill -HUP $(cat nginx/logs/nginx.pid)
```

---

## Project Structure

```
spectre/
├── frontend/           # React SPA
│   └── src/
│       ├── components/ # UI components (shadcn/ui)
│       ├── hooks/      # useChat, useOllama, useNotes, etc.
│       ├── lib/        # API client, DB, utilities
│       └── pages/      # Route pages
├── backend/
│   ├── api/main.py     # FastAPI routes
│   └── core/           # Business logic modules
├── data/               # Runtime data
│   ├── inbox/          # Uploaded files
│   ├── processed/      # Parsed files by site
│   ├── embeddings/     # ChromaDB vector store
│   └── spectre.db      # SQLite database
└── nginx/              # Nginx configuration
```

---

## Ollama Models

| Model | Purpose |
|-------|---------|
| `granite4:3b` | Chat/reasoning |
| `nomic-embed-text:v1.5` | Embeddings (768 dim) |
| `qwen3-vl:4b` | Vision/document analysis |

---

## Recent Completions

- Markdown rendering with syntax highlighting (Prism)
- Dark/light theme toggle
- CORS restricted to allowed origins via `settings.ALLOWED_ORIGINS`
- Centralized configuration (`backend/core/config.py`)
- Room-based inventory categorization
- Plugin system for client-specific configurations
- Template-filling export for OrderMaestro compatibility
