"""
Help Desk API router.
"""
from fastapi import APIRouter, HTTPException, Form
import requests

from backend.core.config import settings
from backend.core.embeddings import search as rag_search
from backend.core.corpus import get_corpus_stats, ingest_training_corpus

router = APIRouter(prefix="/api/helpdesk", tags=["Help Desk"])


@router.post("/ask")
def helpdesk_ask(
    question: str = Form(...),
    include_sources: bool = Form(True)
):
    """
    Ask a question to the Help Desk RAG system.
    Searches training corpus and synthesizes an answer.
    """
    results = rag_search(
        query=question,
        limit=5,
        collection_name="culinart_bible"
    )

    if not results:
        return {
            "answer": "I couldn't find relevant information in the training materials for your question.",
            "sources": [],
            "confidence": "low"
        }

    context_parts = []
    sources = []
    for r in results:
        context_parts.append(r["text"])
        source_file = r.get("metadata", {}).get("source_file", "")
        if source_file and source_file not in sources:
            sources.append(source_file)

    context = "\n\n".join(context_parts)

    try:
        prompt = f"""Based on the following training materials, answer this question:

QUESTION: {question}

RELEVANT TRAINING MATERIALS:
{context}

Instructions:
- Answer based ONLY on the provided materials
- Be concise and practical
- If the materials don't fully answer the question, say so
- Use bullet points for lists
- Reference specific documents when relevant

ANSWER:"""

        response = requests.post(
            f"{settings.OLLAMA_URL}/api/chat",
            json={
                "model": settings.LLM_MODEL,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant answering questions about food service operations, safety, and HR policies based on company training materials."},
                    {"role": "user", "content": prompt}
                ],
                "stream": False,
                "options": {"temperature": 0.3}
            },
            timeout=60
        )

        if response.ok:
            data = response.json()
            answer = data.get("message", {}).get("content", "").strip()
        else:
            answer = "Unable to generate answer. Please try again."

    except Exception as e:
        answer = f"Error generating answer: {str(e)}"

    result = {
        "answer": answer,
        "confidence": "high" if len(results) >= 3 else "medium" if len(results) >= 1 else "low"
    }

    if include_sources:
        result["sources"] = sources
        result["source_snippets"] = [
            {"file": r.get("metadata", {}).get("source_file", ""), "text": r["text"][:200]}
            for r in results[:3]
        ]

    return result


@router.post("/search")
def helpdesk_search(
    query: str = Form(...),
    limit: int = Form(10)
):
    """
    Search training corpus without LLM synthesis.
    Returns raw search results for browsing.
    """
    results = rag_search(
        query=query,
        limit=limit,
        collection_name="culinart_bible"
    )

    formatted = []
    for r in results:
        formatted.append({
            "text": r["text"],
            "source_file": r.get("metadata", {}).get("source_file", ""),
            "score": r.get("score", 0),
            "chunk_index": r.get("metadata", {}).get("chunk_index", 0)
        })

    return {
        "results": formatted,
        "count": len(formatted),
        "query": query
    }


@router.get("/corpus/stats")
def helpdesk_corpus_stats():
    """Get stats about the training corpus."""
    return get_corpus_stats()


@router.post("/corpus/ingest")
def helpdesk_ingest_corpus():
    """
    Re-ingest the training corpus.
    Use after adding new training files.
    """
    result = ingest_training_corpus(clear_existing=True)
    return result
