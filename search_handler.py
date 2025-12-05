"""
Search handler for querying Pinecone and formatting results for Streamlit UI.

This module provides a clean interface between the Pinecone backend
and the Streamlit frontend, ensuring results are properly structured.
"""

from typing import Any, Dict, List, Optional

from pinecone_hybrid import get_pinecone_hybrid_db


# Global DB instance (singleton pattern)
_db_instance: Optional[Any] = None


def get_db_instance(score_threshold: float = 0.5):
    """Get or create a singleton PineconeVectorDB instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = get_pinecone_hybrid_db(score_threshold=score_threshold)
    return _db_instance


def search_pinecone(
    query: str,
    alpha: float = 0.5,
    top_k: int = 20,
    score_threshold: float = 0.5,
    include_scores: bool = True,
) -> List[Dict[str, Any]]:
    """
    Search Pinecone with a query and return structured results for Streamlit UI.

    Args:
        query: Search query string.
        alpha: Blend factor between dense (1.0) and sparse (0.0) search. Default 0.5.
        top_k: Maximum number of results to return. Default 20.
        score_threshold: Minimum relevance score threshold. Default 0.5.
        include_scores: Whether to include relevance scores in results. Default True.

    Returns:
        List of structured result dictionaries with keys:
            - title: Document title or identifier
            - snippet: Text content/preview
            - score: Relevance score (0-1)
            - metadata: Full metadata dict from Pinecone (if available)
            - id: Pinecone record ID (if available)

    Example:
        >>> results = search_pinecone("machine learning", alpha=0.7, top_k=10)
        >>> for result in results:
        ...     print(result['title'], result['score'])
    """
    if not query or not query.strip():
        return []

    try:
        db = get_db_instance(score_threshold=score_threshold)
        raw_results = db.fetch(
            query=query.strip(),
            top_k=top_k,
            alpha=alpha,
            include_scores=include_scores,
        )

        structured_results: List[Dict[str, Any]] = []

        for idx, item in enumerate(raw_results, start=1):
            # Extract common metadata fields with fallbacks
            title = (
                item.get("title")
                or item.get("page_title")
                or item.get("name")
                or item.get("document_id")
                or item.get("id")
                or item.get("_id")
                or f"Result {idx}"
            )

            snippet = (
                item.get("text")
                or item.get("document_text", "")[:500] + "..." if len(item.get("document_text", "")) > 500 else item.get("document_text", "")
                or item.get("content")
                or item.get("snippet")
                or item.get("body")
                or item.get("description")
                or str(item.get("metadata", ""))
                or "No content available"
            )

            # Truncate long snippets for UI display
            max_snippet_length = 500
            if isinstance(snippet, str) and len(snippet) > max_snippet_length:
                snippet = snippet[:max_snippet_length] + "..."

            score = item.get("_score", 0.0)
            if score is None:
                score = 0.0

            # Format score as string with 2 decimal places for display
            score_str = f"{score:.2f}"

            source_url = item.get("source_url", "")
            document_url = item.get("document_url", "")

            structured_result: Dict[str, Any] = {
                "title": str(title),
                "snippet": str(snippet),
                "url": document_url or source_url,
                "score": score_str,
                "raw_score": float(score),
                "metadata": {k: v for k, v in item.items() if not k.startswith("_")},
            }

            # Include ID if available
            if "_id" in item:
                structured_result["id"] = item["_id"]
            elif "id" in item:
                structured_result["id"] = item["id"]

            structured_results.append(structured_result)

        return structured_results

    except Exception as e:
        # Return error information in a structured format
        return [
            {
                "title": "Error",
                "snippet": f"Failed to search Pinecone: {str(e)}",
                "score": "0.00",
                "raw_score": 0.0,
                "metadata": {},
                "error": True,
            }
        ]


def format_results_for_display(
    results: List[Dict[str, Any]], max_results: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Format search results for Streamlit display.

    Args:
        results: List of structured result dictionaries from search_pinecone().
        max_results: Maximum number of results to return. If None, returns all.

    Returns:
        Formatted list of results ready for UI display.
    """
    if max_results:
        results = results[:max_results]

    return results

