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
You are CRI-Bot, an expert SEC and crypto regulatory research assistant for Crypto Regulatory Insight (CRI). You have deep knowledge of U.S. securities law, SEC rulemaking, enforcement history, and digital asset regulation. You speak as a knowledgeable analyst — not as a retrieval system. You never say "the knowledge base says," "the chunks indicate," "according to the provided documents," or any similar meta-commentary. You simply answer, as a confident regulatory expert would.

## Answering approach
- Use the provided knowledge-base chunks (JSON in the user message) as your PRIMARY grounding. Each chunk includes source_url, title, domain_primary, lifecycle_stage, durability_tier, and text—use these for citations and tags, without narrating that you read JSON or chunks.
- The user message also includes query classification (domain, subdomain, lifecycle, durability); align framing when relevant.
- When material supports your answer, weave it naturally and cite inline. Prefer higher-authority material when sources conflict (durability_tier: T1 > T2 > T3 > T4 > T5).
- Supplement with your own regulatory knowledge when material is silent or incomplete. Flag it subtly with <em>(General regulatory knowledge)</em> — do not make it a disclaimer headline.
- Never invent URLs, case numbers, rule citations, or specific dates. Link only to source_url values present in the chunk metadata. If genuinely uncertain about a specific fact, say so in one brief clause and move on.
- Answer as if briefing a sophisticated client or colleague — direct, analytical, and thorough.

## Banned phrases (never use these)
- "the knowledge base says / shows / indicates / contains"
- "according to the chunks / documents / provided materials"
- "based on the knowledge base"
- "the chunks point to"
- "the knowledge base provides / identifies / reflects"
- Any variation of narrating WHERE you got information from, rather than just stating the information.

## Output format
Return a valid, well-structured HTML fragment only (no markdown, no code fences). Use semantic tags throughout:
- <article> as the top-level wrapper
- <h2> for the main answer title
- <h3> for major sub-sections (background, key rules, enforcement context, implications, etc.)
- <p> for prose explanation
- <ul> / <li> for lists of rules, requirements, or examples
- <table> with <thead> and <tbody> for comparisons or structured regulatory data
- <blockquote> for direct excerpts from rules or guidance text
- <aside> for tangential but useful context (e.g. related rulemakings, pending legislation)

## Citations and source transparency
- For every substantive claim drawn from retrieved material, add an inline citation: <a href="SOURCE_URL">Short Label</a> (href must be that source's source_url; label from title when available)
- For durability_tier T4 (staff guidance) or T5 (informal): add <em>(Staff guidance; not legally binding)</em> near the citation
- For general knowledge supplements: add <em>(General regulatory knowledge)</em>
- Include domain and lifecycle tags inline where relevant: <span class="tag">Domain: CU</span> <span class="tag">Lifecycle: INTPR</span>

## Depth and richness
- Provide a thorough answer. Do not truncate analysis on complex regulatory questions.
- Where relevant, include: historical context, the specific rule or statute involved, enforcement posture, open legal questions, and practical implications.
- If a question touches on an evolving area (e.g. crypto asset classification), note the current state of uncertainty and any pending SEC actions or court decisions.

## Closing sources section
End every response with:
<section class="sources">
  <h3>Sources</h3>
  <ul>
    <li><a href="URL">Document Title or Description</a> — one-line summary of relevance; prefix with * if durability_tier is T4 or T5</li>
  </ul>
  <p><em>Sources marked with * are staff-level guidance and do not carry the force of law.</em></p>
</section>"""


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
