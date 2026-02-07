"""
Corpus management for training documents.

Handles loading and caching text from PDF, DOCX, PPTX, XLSX files
in the Training folder. Used by the helpdesk to provide context to Claude.

Embedding pipeline has been removed — text is loaded directly into
Claude's context window instead.
"""
import logging
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from .parsers import (
    extract_text,
    extract_text_from_pdf as parse_pdf,
    extract_text_from_docx as parse_docx,
    extract_text_from_pptx as parse_pptx,
    extract_text_from_excel as parse_xlsx,
)

logger = logging.getLogger(__name__)

# Training corpus location
TRAINING_DIR = Path(__file__).parent.parent.parent / "Training"

# Cache for parsed document text
_corpus_cache: Optional[List[Dict[str, Any]]] = None

# Re-export for backwards compatibility
parse_file = extract_text

__all__ = [
    "parse_pdf",
    "parse_docx",
    "parse_pptx",
    "parse_xlsx",
    "parse_file",
    "load_corpus",
    "get_corpus_stats",
    "get_corpus_text",
]


def load_corpus(force_reload: bool = False) -> List[Dict[str, Any]]:
    """
    Load and cache all training documents as text.

    Returns list of dicts: [{"file": "filename.pdf", "text": "...content..."}, ...]
    """
    global _corpus_cache

    if _corpus_cache is not None and not force_reload:
        return _corpus_cache

    if not TRAINING_DIR.exists():
        logger.warning(f"Training directory not found: {TRAINING_DIR}")
        _corpus_cache = []
        return _corpus_cache

    supported_extensions = {'.pdf', '.docx', '.pptx', '.xlsx', '.txt'}
    files = [
        f for f in TRAINING_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in supported_extensions
    ]

    docs = []
    for file_path in sorted(files):
        try:
            if file_path.suffix.lower() == '.txt':
                content = file_path.read_text(errors='replace')
            else:
                content = extract_text(file_path)

            if content and content.strip():
                docs.append({
                    "file": file_path.name,
                    "text": content.strip(),
                    "size": len(content),
                })
                logger.info(f"Loaded training doc: {file_path.name} ({len(content)} chars)")
            else:
                logger.warning(f"Empty or unparseable: {file_path.name}")
        except Exception as e:
            logger.error(f"Failed to parse {file_path.name}: {e}")

    _corpus_cache = docs
    logger.info(f"Corpus loaded: {len(docs)} documents, {sum(d['size'] for d in docs)} total chars")
    return _corpus_cache


def get_corpus_text(max_chars: Optional[int] = None) -> str:
    """
    Get all corpus text concatenated, optionally truncated.

    Args:
        max_chars: Maximum total characters to return. None = no limit.

    Returns:
        Combined text from all training documents.
    """
    docs = load_corpus()
    parts = []
    total = 0

    for doc in docs:
        header = f"\n--- {doc['file']} ---\n"
        text = doc["text"]

        if max_chars is not None:
            remaining = max_chars - total
            if remaining <= 0:
                break
            if len(header) + len(text) > remaining:
                text = text[:remaining - len(header)]

        parts.append(header + text)
        total += len(header) + len(text)

    return "\n".join(parts)


def get_corpus_stats() -> Dict[str, Any]:
    """Get statistics about the training corpus."""
    docs = load_corpus()
    return {
        "available": True,
        "document_count": len(docs),
        "total_chars": sum(d["size"] for d in docs),
        "files": [{"file": d["file"], "size": d["size"]} for d in docs],
    }
