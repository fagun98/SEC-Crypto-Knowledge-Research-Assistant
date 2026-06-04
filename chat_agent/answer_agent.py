from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from chat_agent.env import load_dotenv_env, setup_openai_api_key

load_dotenv_env()

from langchain_core.messages import HumanMessage, SystemMessage  # noqa: E402

from chat_agent.data_collector import RetrievalContext
from chat_agent.types import RetrievedChunk
from utils import get_brain_model, get_llm


@dataclass
class ChatAnswer:
    html: str
    sources: List[Dict[str, Any]] = field(default_factory=list)
    retrieval_debug: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


def _classification_summary(classification: Dict[str, Any]) -> str:
    norm = classification.get("normalized") or {}
    parts = [
        f"domain_primary={norm.get('domain_primary', '')}",
        f"subdomain={norm.get('subdomain', [])}",
        f"lifecycle_stage={norm.get('lifecycle_stage', '')}",
        f"durability_tier={norm.get('durability_tier', '')}",
    ]
    return "; ".join(parts)


def _chunks_for_prompt(chunks: List[RetrievedChunk]) -> str:
    payloads = [c.context_payload() for c in chunks]
    return json.dumps(payloads, ensure_ascii=False, indent=2)


def _sources_from_chunks(chunks: List[RetrievedChunk]) -> List[Dict[str, Any]]:
    sources: List[Dict[str, Any]] = []
    seen_urls: set[str] = set()
    for ch in chunks:
        meta = ch.metadata
        url = meta.get("source_url") or meta.get("document_url") or ""
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        sources.append(
            {
                "id": ch.id,
                "title": meta.get("title") or "Source",
                "source_url": url,
                "domain_primary": meta.get("domain_primary"),
                "lifecycle_stage": meta.get("lifecycle_stage"),
                "durability_tier": meta.get("durability_tier"),
            }
        )
    return sources


SYSTEM_PROMPT = """
You are a SEC and crypto regulatory research assistant for Crypto Regulatory Insight (CRI).

Answer the user's question using ONLY the provided knowledge-base chunks. If the chunks do not contain enough evidence, say so clearly in HTML.

Output requirements:
- Return a valid HTML fragment only (no markdown). Use tags such as <article>, <h2>, <p>, <ul>, <li>.
- For each substantive claim, cite the source with an inline link: <a href="SOURCE_URL">Title or short label</a>.
- When citing staff guidance (durability T4) or informal sources (T5), include a brief caveat in <em> tags near that citation.
- Include domain/lifecycle context where helpful (e.g. domain CU, lifecycle INTPR).
- Do not invent URLs or facts not supported by the chunks.
- End with a <section class="sources"><h3>Sources</h3><ul>...</ul></section> listing all cited documents with links."""


def generate_answer(
    query: str,
    retrieval: RetrievalContext,
    *,
    history: Optional[List[Dict[str, str]]] = None,
) -> ChatAnswer:
    """Generate an HTML answer from ranked retrieval context."""
    chunks = retrieval.ranked_chunks
    debug = retrieval.to_debug_dict()

    if not chunks:
        return ChatAnswer(
            html=(
                "<article><p>I could not find relevant documents in the knowledge base "
                "for this question. Try rephrasing or broadening your query.</p></article>"
            ),
            sources=[],
            retrieval_debug=debug,
        )

    history_text = ""
    if history:
        lines = []
        for turn in history[-6:]:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            if content:
                lines.append(f"{role}: {content[:1500]}")
        if lines:
            history_text = "\n\nPrior conversation:\n" + "\n".join(lines)

    user_content = f"""User question:
{query}

Query classification (for framing): {_classification_summary(retrieval.classification)}
{history_text}

Knowledge-base chunks (JSON):
{_chunks_for_prompt(chunks)}

Produce the HTML answer now."""

    try:
        setup_openai_api_key()
        llm = get_llm(temperature=0.2)
        response = llm.invoke(
            [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_content)]
        )
        html = (response.content or "").strip()
        if not html.startswith("<"):
            html = f"<article>{html}</article>"
    except Exception as e:
        return ChatAnswer(
            html=f"<article><p>Error generating answer: {e}</p></article>",
            sources=_sources_from_chunks(chunks),
            retrieval_debug=debug,
            error=str(e),
        )

    debug["answer_model"] = get_brain_model()
    return ChatAnswer(
        html=html,
        sources=_sources_from_chunks(chunks),
        retrieval_debug=debug,
    )
