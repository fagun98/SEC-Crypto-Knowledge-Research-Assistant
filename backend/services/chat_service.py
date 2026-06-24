from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

from backend.core.config import get_settings
from backend.schemas.chat import ChatRequest, ChatResponse, Source


def _source_from_agent(item: dict[str, Any]) -> Source:
    score = item.get("score") or item.get("raw_score")
    try:
        normalized_score = float(score) if score is not None else None
    except (TypeError, ValueError):
        normalized_score = None
    return Source(
        title=str(item.get("title") or "SEC source"),
        url=item.get("url") or item.get("source_url") or item.get("document_url") or None,
        score=normalized_score,
        snippet=item.get("snippet") or item.get("text") or None,
    )


def _run_chat(request: ChatRequest) -> ChatResponse:
    # Imported lazily so the health and report endpoints do not initialize model clients.
    from langgraph_agent import run_chat_turn

    answer = run_chat_turn(
        request.message.strip(),
        history=[message.model_dump() for message in request.history],
    )
    debug = answer.retrieval_debug or {}
    settings = get_settings()
    return ChatResponse(
        answer=answer.html,
        session_id=request.session_id or str(uuid4()),
        sources=[_source_from_agent(item) for item in (answer.sources or [])],
        metadata={
            "model": debug.get("answer_model") or settings.openai_llm_model,
            "retrieval_mode": "hybrid_rag",
            "retrieval": debug,
            **({"warning": answer.error} if answer.error else {}),
        },
    )


async def chat(request: ChatRequest) -> ChatResponse:
    return await asyncio.to_thread(_run_chat, request)
