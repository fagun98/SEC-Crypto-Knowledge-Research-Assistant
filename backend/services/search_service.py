from __future__ import annotations

import asyncio

from backend.schemas.search import SearchRequest, SearchResponse, SearchResult


def _search(request: SearchRequest) -> SearchResponse:
    from search_handler import search_pinecone

    raw = search_pinecone(
        query=request.query.strip(),
        alpha=request.alpha,
        top_k=request.top_k,
        score_threshold=request.score_threshold,
    )
    if raw and raw[0].get("error"):
        raise RuntimeError("The knowledge search service is currently unavailable.")

    results = [
        SearchResult(
            title=str(item.get("title") or "Untitled document"),
            url=item.get("url") or None,
            score=float(item.get("raw_score") or item.get("score") or 0.0),
            snippet=str(item.get("snippet") or ""),
            metadata=item.get("metadata") or {},
        )
        for item in raw
    ]
    return SearchResponse(query=request.query.strip(), results=results)


async def search(request: SearchRequest) -> SearchResponse:
    return await asyncio.to_thread(_search, request)
