from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from chat_agent.env import load_dotenv_env, setup_openai_api_key
from chat_agent.models import get_rerank_model
from chat_agent.types import RetrievedChunk
from utils import get_env_int

load_dotenv_env()

from openai import OpenAI  # noqa: E402

RERANK_SNIPPET_CHARS = 800


def _strip_code_fence(text: str) -> str:
    s = (text or "").strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", s, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return s


def _extract_json_array(text: str) -> List[Dict[str, Any]]:
    s = _strip_code_fence(text)
    start = s.find("[")
    end = s.rfind("]")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON array found in rerank response.")
    parsed = json.loads(s[start : end + 1])
    if not isinstance(parsed, list):
        raise ValueError("Rerank response is not a JSON array.")
    return parsed


def _chunk_summary(chunk: RetrievedChunk) -> Dict[str, Any]:
    meta = chunk.metadata
    text = chunk.text or meta.get("document_text") or meta.get("text") or ""
    if len(text) > RERANK_SNIPPET_CHARS:
        text = text[:RERANK_SNIPPET_CHARS] + "…"
    return {
        "id": chunk.id,
        "title": meta.get("title") or "Untitled",
        "source_url": meta.get("source_url") or meta.get("document_url") or "",
        "domain_primary": meta.get("domain_primary") or "",
        "lifecycle_stage": meta.get("lifecycle_stage") or "",
        "durability_tier": meta.get("durability_tier") or "",
        "snippet": text,
        "pinecone_score": chunk.pinecone_score,
    }


def _build_rerank_prompt(query: str, summaries: List[Dict[str, Any]]) -> str:
    payload = json.dumps(summaries, ensure_ascii=False, indent=2)
    return f"""You are a SEC and crypto regulatory research assistant reranking knowledge-base chunks.

User question:
{query}

Candidate chunks (JSON):
{payload}

Return ONLY a JSON array ordered from most to least relevant. Each element:
{{"id": "<chunk id>", "relevance_score": <0.0-1.0>, "rationale": "<one short sentence>"}}

Rules:
- Score by how well the chunk helps answer the user's question (SEC/financial regulatory focus).
- Penalize off-topic chunks even if keyword overlap is high.
- When relevance is similar, prefer higher authority (T1 > T2 > T3 > T4 > T5 durability_tier).
- Include every candidate id exactly once.
- No markdown, no extra text."""


def rerank_chunks(
    query: str,
    chunks: List[RetrievedChunk],
    *,
    top_k: Optional[int] = None,
    client: Optional[OpenAI] = None,
) -> tuple[List[RetrievedChunk], List[Dict[str, Any]]]:
    """
    LLM rerank merged chunks. Returns (ranked_chunks, rerank_debug_rows).
    """
    if not chunks:
        return [], []

    k = top_k if top_k is not None else get_env_int("CHAT_RERANK_TOP_K", 8)
    k = max(5, min(10, k))

    by_id = {c.id: c for c in chunks}
    summaries = [_chunk_summary(c) for c in chunks]

    model = get_rerank_model()
    api_key = setup_openai_api_key()
    c = client or OpenAI(api_key=api_key)
    resp = c.responses.create(
        model=model,
        input=_build_rerank_prompt(query, summaries),
        text={"format": {"type": "text"}},
        max_output_tokens=2000,
    )
    raw = (resp.output_text or "").strip()

    debug_rows: List[Dict[str, Any]] = []
    try:
        ranked_specs = _extract_json_array(raw)
    except (ValueError, json.JSONDecodeError):
        fallback = sorted(chunks, key=lambda x: x.pinecone_score, reverse=True)[:k]
        return fallback, [{"error": "rerank_parse_failed", "fallback": True}]

    seen: set[str] = set()
    ranked: List[RetrievedChunk] = []
    for item in ranked_specs:
        if not isinstance(item, dict):
            continue
        cid = str(item.get("id") or "").strip()
        if not cid or cid in seen or cid not in by_id:
            continue
        seen.add(cid)
        chunk = by_id[cid]
        ranked.append(chunk)
        debug_rows.append(
            {
                "id": cid,
                "relevance_score": item.get("relevance_score"),
                "rationale": item.get("rationale"),
            }
        )
        if len(ranked) >= k:
            break

    if len(ranked) < k:
        for ch in sorted(chunks, key=lambda x: x.pinecone_score, reverse=True):
            if ch.id not in seen:
                ranked.append(ch)
                seen.add(ch.id)
            if len(ranked) >= k:
                break

    return ranked[:k], debug_rows
