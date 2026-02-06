"""
Corpus ingestion for the knowledge RAG database.

Handles PDF, DOCX, PPTX, XLSX files from the Training folder.
Separate from inventory processing pipeline.

File parsing has been consolidated into parsers.py.
"""
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Import text extraction from consolidated parsers module
from .parsers import (
    extract_text,
    extract_text_from_pdf as parse_pdf,
    extract_text_from_docx as parse_docx,
    extract_text_from_pptx as parse_pptx,
    extract_text_from_excel as parse_xlsx,
)
from .embeddings import embed_text, chunk_text
from .collections import get_collection

logger = logging.getLogger(__name__)

# Training corpus location
TRAINING_DIR = Path(__file__).parent.parent.parent / "Training"
# Note: "knowledge_base" was empty, using "training_corpus" which has 1333 ingested documents
KNOWLEDGE_COLLECTION = "training_corpus"

# Re-export for backwards compatibility
parse_file = extract_text

__all__ = [
    "parse_pdf",
    "parse_docx",
    "parse_pptx",
    "parse_xlsx",
    "parse_file",
    "ingest_file",
    "ingest_training_corpus",
    "get_corpus_stats",
]


def ingest_file(
    file_path: Path,
    collection_name: str = KNOWLEDGE_COLLECTION
) -> Dict[str, Any]:
    """
    Ingest a single file into the knowledge RAG database.

    Args:
        file_path: Path to the file to ingest
        collection_name: ChromaDB collection to store in

    Returns:
        Dict with success status and chunk count
    """
    collection = get_collection(collection_name)
    if not collection:
        return {"success": False, "error": "Collection not available"}

    # Parse the file using consolidated parser
    content = extract_text(file_path)
    if not content:
        return {"success": False, "error": "Could not parse file"}

    # Create chunks
    chunks = chunk_text(content, max_size=500, overlap=50)

    # Generate embeddings and store
    embedded_count = 0
    file_id = file_path.stem  # Use filename without extension as ID

    for i, chunk in enumerate(chunks):
        chunk_id = f"knowledge_{file_id}_{i}"

        embedding = embed_text(chunk)
        if not embedding:
            continue

        try:
            collection.upsert(
                ids=[chunk_id],
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[{
                    "source_file": file_path.name,
                    "source_type": "knowledge_corpus",
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "ingested_at": datetime.now().isoformat(),
                    "collection": collection_name
                }]
            )
            embedded_count += 1
        except Exception as e:
            logger.error(f"Failed to store chunk {chunk_id}: {e}")

    return {
        "success": True,
        "file": file_path.name,
        "chunks_created": embedded_count,
        "total_chunks": len(chunks)
    }


def ingest_training_corpus(clear_existing: bool = True) -> Dict[str, Any]:
    """
    Ingest all files from the Training folder into the knowledge RAG.

    Args:
        clear_existing: If True, clear existing knowledge data first

    Returns:
        Summary of ingestion results
    """
    if not TRAINING_DIR.exists():
        return {"success": False, "error": f"Training directory not found: {TRAINING_DIR}"}

    collection = get_collection(KNOWLEDGE_COLLECTION)
    if not collection:
        return {"success": False, "error": "Collection not available"}

    # Clear existing knowledge data if requested
    if clear_existing:
        try:
            # Get all IDs that start with "knowledge_"
            existing = collection.get(where={"source_type": "knowledge_corpus"})
            if existing and existing.get('ids'):
                collection.delete(ids=existing['ids'])
                logger.info(f"Cleared {len(existing['ids'])} existing knowledge chunks")
        except Exception as e:
            logger.warning(f"Could not clear existing data: {e}")

    # Find all supported files
    supported_extensions = {'.pdf', '.docx', '.pptx', '.xlsx'}
    files = [
        f for f in TRAINING_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in supported_extensions
    ]

    results = {
        "success": True,
        "files_processed": 0,
        "files_failed": 0,
        "total_chunks": 0,
        "details": []
    }

    for file_path in files:
        logger.info(f"Ingesting: {file_path.name}")
        result = ingest_file(file_path)

        if result.get("success"):
            results["files_processed"] += 1
            results["total_chunks"] += result.get("chunks_created", 0)
        else:
            results["files_failed"] += 1

        results["details"].append(result)

    return results


def get_corpus_stats() -> Dict[str, Any]:
    """Get statistics about the knowledge corpus."""
    collection = get_collection(KNOWLEDGE_COLLECTION)
    if not collection:
        return {"available": False}

    try:
        # Get all knowledge corpus entries
        existing = collection.get(where={"source_type": "knowledge_corpus"})

        # Count unique source files
        source_files = set()
        if existing and existing.get('metadatas'):
            for meta in existing['metadatas']:
                if meta.get('source_file'):
                    source_files.add(meta['source_file'])

        return {
            "available": True,
            "collection": KNOWLEDGE_COLLECTION,
            "total_chunks": len(existing.get('ids', [])) if existing else 0,
            "source_files": list(source_files),
            "file_count": len(source_files)
        }
    except Exception as e:
        logger.error(f"Error getting corpus stats: {e}")
        return {"available": False, "error": str(e)}
