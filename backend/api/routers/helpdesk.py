"""
Help Desk API router.

Uses training corpus text loaded directly into Claude's context window
instead of embedding-based RAG search.
"""
from fastapi import APIRouter, HTTPException, Form

from backend.core import llm
from backend.core.corpus import load_corpus, get_corpus_stats, get_corpus_text

router = APIRouter(prefix="/api/helpdesk", tags=["Help Desk"])


@router.post("/ask")
def helpdesk_ask(
    question: str = Form(...),
    include_sources: bool = Form(True)
):
    """
    Ask a question using training materials as context.
    Loads relevant corpus text into Claude's context window.
    """
    docs = load_corpus()
    if not docs:
        return {
            "answer": "No training materials are available. Please add documents to the Training/ directory.",
            "sources": [],
            "confidence": "low"
        }

    # Build context from corpus — use keyword relevance to pick best docs
    question_lower = question.lower()
    question_words = set(question_lower.split())

    # Score each doc by keyword overlap with the question
    scored_docs = []
    for doc in docs:
        doc_lower = doc["text"].lower()
        overlap = sum(1 for w in question_words if w in doc_lower and len(w) > 3)
        scored_docs.append((overlap, doc))

    # Sort by relevance (highest overlap first), take top docs that fit context
    scored_docs.sort(key=lambda x: x[0], reverse=True)

    context_parts = []
    sources = []
    total_chars = 0
    max_context_chars = 100_000  # ~25K tokens, leaving room for prompt + response

    for _, doc in scored_docs:
        if total_chars + doc["size"] > max_context_chars:
            # If this doc would exceed budget, try truncating it
            remaining = max_context_chars - total_chars
            if remaining > 500:
                context_parts.append(f"--- {doc['file']} (truncated) ---\n{doc['text'][:remaining]}")
                sources.append(doc["file"])
            break
        context_parts.append(f"--- {doc['file']} ---\n{doc['text']}")
        sources.append(doc["file"])
        total_chars += doc["size"]

    context = "\n\n".join(context_parts)

    try:
        system = "You are a helpful assistant answering questions about food service operations, safety, and HR policies based on company training materials."

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

        answer = llm.chat(prompt, system=system, temperature=0.3)

        if not answer:
            answer = "Unable to generate answer. Please try again."

    except Exception as e:
        answer = f"Error generating answer: {str(e)}"

    result = {
        "answer": answer,
        "confidence": "high" if len(sources) >= 3 else "medium" if len(sources) >= 1 else "low"
    }

    if include_sources:
        result["sources"] = sources[:5]
        result["source_snippets"] = [
            {"file": doc["file"], "text": doc["text"][:200]}
            for _, doc in scored_docs[:3]
            if doc["file"] in sources
        ]

    return result


@router.post("/search")
def helpdesk_search(
    query: str = Form(...),
    limit: int = Form(10)
):
    """
    Search training corpus by keyword matching.
    Returns matching document snippets.
    """
    docs = load_corpus()
    query_lower = query.lower()
    query_words = [w for w in query_lower.split() if len(w) > 2]

    results = []
    for doc in docs:
        doc_lower = doc["text"].lower()
        if not any(w in doc_lower for w in query_words):
            continue

        # Find the best matching snippet
        best_pos = 0
        best_score = 0
        for i in range(0, len(doc_lower), 100):
            chunk = doc_lower[i:i+500]
            score = sum(1 for w in query_words if w in chunk)
            if score > best_score:
                best_score = score
                best_pos = i

        snippet = doc["text"][best_pos:best_pos+500]

        results.append({
            "text": snippet,
            "source_file": doc["file"],
            "score": best_score / max(len(query_words), 1),
            "chunk_index": 0,
        })

    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)

    return {
        "results": results[:limit],
        "count": len(results[:limit]),
        "query": query
    }


@router.get("/corpus/stats")
def helpdesk_corpus_stats():
    """Get stats about the training corpus."""
    return get_corpus_stats()
