# Spectre - Project Instructions

> AI-powered inventory operations dashboard
> See also: README.md, CHANGELOG.md, CODE_REVIEW.md

---

## Quick Reference

| Component | Tech | Port |
|-----------|------|------|
| Frontend | React + Vite + TailwindCSS | 8090 (nginx) |
| Backend | FastAPI (Python) | 8000 |
| AI | Claude API (Haiku for chat, Sonnet for analysis) | via Anthropic API |
| Database | SQLite | - |

---

## Development Commands

```bash
# Start backend
cd backend && uvicorn api.main:app --reload --port 8000

# Build frontend
cd frontend && npm run build

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
│       ├── hooks/      # useChat, useAI, useNotes, etc.
│       ├── lib/        # API client (api.ts), AI proxy (ai.ts), DB, utilities
│       └── pages/      # Route pages
├── backend/
│   ├── api/main.py     # FastAPI routes
│   └── core/           # Business logic modules
│       ├── llm.py      # Claude API client (chat, generate, stream)
│       ├── corpus.py   # Training doc loader (text stuffed into context)
│       └── config.py   # Centralized settings
├── data/               # Runtime data
│   ├── inbox/          # Uploaded files
│   ├── processed/      # Parsed files by site
│   └── spectre.db      # SQLite database
└── nginx/              # Nginx configuration
```

---

## AI Architecture

All AI calls route through the backend proxy (`/api/ai/claude/*`). The frontend never calls Claude directly.

| Model | Config Key | Purpose |
|-------|-----------|---------|
| `claude-haiku-4-5-20251001` | `CLAUDE_CHAT_MODEL` | Chat, helpdesk, general queries |
| `claude-sonnet-4-5-20250929` | `CLAUDE_ANALYSIS_MODEL` | Inventory analysis, anomaly detection |

Training documents from `Training/` directory are loaded into memory and stuffed into Claude's context window for helpdesk queries (no embeddings/RAG).

Environment: Set `CLAUDE_API_KEY` in backend environment.

---

## Recent Completions

- Migrated from Ollama to Claude API (all AI through backend proxy)
- Removed ChromaDB/embeddings pipeline (context-stuffing approach)
- Markdown rendering with syntax highlighting (Prism)
- Dark/light theme toggle
- CORS restricted to allowed origins via `settings.ALLOWED_ORIGINS`
- Centralized configuration (`backend/core/config.py`)
- Room-based inventory categorization
- Plugin system for client-specific configurations
- Template-filling export for OrderMaestro compatibility
