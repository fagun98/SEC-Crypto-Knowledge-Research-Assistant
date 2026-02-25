"""
SEC Q&A Chat Agent (v3, single‑query, topic‑driven).

This module implements a *single‑turn* SEC question–answering pipeline
that is intended for experimentation and workflow evaluation.

Compared to ``chat_agent_v2``, this version:

* Assumes **one standalone user query** (no multi‑turn chat history).
* Uses an LLM to expand the query into a small set of **SEC‑focused topics**.
* Runs hybrid search against the SEC Pinecone index **per topic**.
* Collects the top 20–30 chunks and has an LLM **rate** how well each
  chunk can help answer the question.
* Keeps only the most promising chunks, then asks the LLM to
  **summarise each chunk in a question‑focused way**.
* Sends only these summaries to a final answering agent to generate the
  Markdown answer with a sources section.

The goal is to make this pipeline easy to inspect and rate before
integrating into a more complex agent or UI.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Tuple

from dotenv import load_dotenv
from openai import OpenAI

from crypto_ingest import (
    hybrid_search,
    fetch_url,
    extract_text_from_html,
    extract_text_from_pdf,
    is_pdf_url,
)

load_dotenv()

client = OpenAI()

# Optional callback for emitting progress updates to the UI.
ProgressCallback = Callable[[Dict[str, Any]], None]

# Logger for pipeline checkpoints and errors.
logger = logging.getLogger("sec_chat_agent")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(name)s - %(message)s"
    )
    _handler.setFormatter(_formatter)
    logger.addHandler(_handler)
logger.setLevel(logging.INFO)

# Approximate $ per 1M tokens for cost logging.  Keep in sync with v2.
MODEL_COST_PER_1M: Dict[str, Tuple[float, float]] = {
    "gpt-5-mini": (0.25, 2.00),
    "gpt-5.2": (1.75, 14.00),
}


def _estimate_tokens_and_cost(
    response: object,
    model: str,
    input_str: str,
    output_str: str,
    *,
    step_name: str = "call",
) -> Tuple[int, int, float]:
    """Estimate token counts and cost for an OpenAI API call."""
    in_tok = out_tok = 0
    usage = getattr(response, "usage", None)
    if usage is not None:
        in_tok = (
            getattr(usage, "input_tokens", None)
            or getattr(usage, "prompt_tokens", None)
            or 0
        )
        out_tok = (
            getattr(usage, "output_tokens", None)
            or getattr(usage, "completion_tokens", None)
            or 0
        )
    if in_tok == 0 and input_str:
        # Roughly 1 token ≈ 4 characters.
        in_tok = max(1, len(input_str) // 4)
    if out_tok == 0 and output_str:
        out_tok = max(1, len(output_str) // 4)
    price = MODEL_COST_PER_1M.get(model, (0.20, 0.80))
    cost = (in_tok * price[0] + out_tok * price[1]) / 1_000_000
    logger.info(
        "  [%s] Tokens: %s in, %s out | Est. cost: $%.4f",
        step_name,
        f"{in_tok:,}",
        f"{out_tok:,}",
        cost,
    )
    return in_tok, out_tok, cost


@dataclass
class RetrievedChunk:
    source_url: str
    content: str


def _generate_sec_topics(query: str, *, max_topics: int = 8) -> List[str]:
    """
    Use an LLM to generate SEC‑focused search topics for a user query.
    """
    system_prompt = """
You are an assistant that generates focused SEC.gov search topics.

Rules:
- Work only within the domain of the U.S. Securities and Exchange Commission (SEC).
- Focus on SEC regulations, enforcement actions, guidance, rulemakings, staff statements,
  speeches, reports, and official frameworks.
- Ignore non-SEC regulators (e.g., CFTC, ESMA, MAS), foreign laws, or generic crypto commentary.
- Your job is to take the user's question and propose concise topics that are likely to
  appear in SEC.gov documents relevant to answering that question.

Output format:
- Return ONLY valid JSON, with this structure and nothing else:
  {
    "topics": ["topic 1", "topic 2", "..."]
  }
"""

    user_prompt = f"""
User query:
{query}

Instructions:
- Propose between 1 and {max_topics} concise search topics (5–12 words each).
- Each topic should be directly relevant to answering the query using SEC.gov materials.
- Do not mention non-SEC agencies or foreign law.
- Respond with JSON only, no extra commentary.
"""

    full_prompt = system_prompt + "\n\n" + user_prompt
    try:
        # gpt-5-mini is a reasoning model: request text explicitly and allow room for
        # reasoning tokens plus the JSON message so output_text is non-empty.
        resp = client.responses.create(
            model="gpt-5-mini",
            input=full_prompt,
            text={"format": {"type": "text"}},
            max_output_tokens=1024,
        )
        raw_text = resp.output_text or ""
        text = raw_text.strip()
        _estimate_tokens_and_cost(
            resp, "gpt-5-mini", full_prompt, text, step_name="v3_topics"
        )
        if not text:
            raise ValueError("Empty response from model for topics.")

        # Be tolerant if the model wraps JSON in extra text.
        start = text.find("{")
        end = text.rfind("}")
        json_str = text[start : end + 1] if start != -1 and end != -1 and end > start else text

        data = json.loads(json_str)
        topics = data.get("topics") or []
        cleaned: List[str] = []
        for t in topics:
            if not isinstance(t, str):
                continue
            tt = t.strip()
            if tt:
                cleaned.append(tt)
        if not cleaned:
            raise ValueError("No valid topics in JSON.")
        logger.info("[v3] Generated topics: %s", cleaned)
        return cleaned[:max_topics]
    except Exception as e:
        logger.warning("[v3] Topic generation failed, falling back to raw query: %s", e)
        return [query]


def _retrieve_sec_chunks_for_topics(
    topics: List[str],
    *,
    top_k_per_topic: int = 10,
    alpha: float = 0.5,
    max_total: int = 30,
) -> List[RetrievedChunk]:
    """
    Retrieve SEC chunks from Pinecone using topic-expanded queries.
    """
    aggregated: List[RetrievedChunk] = []
    seen_keys: set[str] = set()

    for topic in topics:
        if len(aggregated) >= max_total:
            break
        try:
            docs = hybrid_search(query=topic, top_k=top_k_per_topic, alpha=alpha)
        except Exception as e:
            logger.error("[v3] hybrid_search error for topic '%s': %s", topic, e)
            continue

        for doc in docs:
            if len(aggregated) >= max_total:
                break
            url = (doc.get("source_url") or "").strip()
            content = (doc.get("content") or "").strip()
            if not content:
                continue
            key_src = url or "N/A"
            key = hashlib.sha256((key_src + "\n" + content).encode("utf-8")).hexdigest()
            if key in seen_keys:
                continue
            seen_keys.add(key)
            aggregated.append(RetrievedChunk(source_url=key_src, content=content))

    logger.info("[v3] Retrieved %d unique chunk(s) across topics.", len(aggregated))
    return aggregated[:max_total]


def _build_retrieval_queries(query: str, topics: List[str]) -> List[str]:
    """
    Build augmented retrieval queries by appending the full user query to each topic.

    This helps the vector search stay anchored to the specific question while still
    benefiting from topic-focused phrasing.
    """
    retrieval_queries: List[str] = []
    base = query.strip()
    for topic in topics:
        t = topic.strip()
        if not t:
            continue
        retrieval_queries.append(f"{t}. User query: {base}")
    if not retrieval_queries and base:
        retrieval_queries.append(base)
    return retrieval_queries


def _truncate_chunks(
    chunks: List[RetrievedChunk],
    *,
    max_chars_per_chunk: int = 4000,
) -> List[RetrievedChunk]:
    """
    Trim chunk content to a maximum number of characters.
    """
    truncated: List[RetrievedChunk] = []
    for c in chunks:
        content = c.content
        if len(content) > max_chars_per_chunk:
            content = content[:max_chars_per_chunk]
        truncated.append(RetrievedChunk(source_url=c.source_url, content=content))
    return truncated


def _score_chunks_for_question(
    query: str,
    chunks: List[RetrievedChunk],
) -> List[Dict]:
    """
    Ask an LLM to rate how well each chunk can help answer the query.
    """
    if not chunks:
        return []

    indexed_chunks = [
        {
            "index": idx,
            "source_url": c.source_url,
            "content": c.content,
        }
        for idx, c in enumerate(chunks)
    ]
    chunks_json = json.dumps(indexed_chunks)

    system_prompt = """
You are an assistant that rates the relevance of SEC.gov text chunks for answering a specific question.

Rules:
- Consider ONLY whether each chunk likely contains direct or key supporting information needed to answer the user's question.
- Ignore generic boilerplate, navigation text, or content unrelated to the question.
- Work strictly within the SEC context; prefer chunks that clearly relate to SEC laws, rules, enforcement, guidance, or crypto policy.

Relevance labels:
- "high"   : Chunk likely provides core reasoning, definitions, or specific passages needed.
- "medium" : Chunk provides useful supporting context but may not be sufficient on its own.
- "low"    : Chunk is weakly related or mostly irrelevant.

Output format:
- Return ONLY valid JSON with the following structure:
  {
    "ratings": [
      {
        "index": 0,
        "relevance": "high" | "medium" | "low",
        "can_answer": true | false,
        "notes": "short reason"
      },
      ...
    ]
  }
"""

    user_prompt = f"""
User query:
{query}

You are given a list of SEC.gov document chunks as JSON:
{chunks_json}

For each chunk:
- Decide how relevant it is to answering the question.
- Set "can_answer" to true if this chunk, by itself or with a few similar chunks, could reasonably support a direct answer.
- Provide a short one-sentence "notes" explanation.

Respond with JSON only.
"""

    full_prompt = system_prompt + "\n\n" + user_prompt
    default_ratings: List[Dict] = [
        {
            "index": idx,
            "relevance": "medium",
            "can_answer": True,
            "notes": "Default rating (fallback).",
        }
        for idx in range(len(chunks))
    ]

    try:
        resp = client.responses.create(
            model="gpt-5-mini",
            input=full_prompt,
            text={"format": {"type": "text"}},
            max_output_tokens=2000,
        )
        raw_text = resp.output_text or ""
        text = raw_text.strip()
        _estimate_tokens_and_cost(
            resp, "gpt-5-mini", full_prompt, text, step_name="v3_rating"
        )
        if not text:
            raise ValueError("Empty response from model for rating.")
        start = text.find("{")
        end = text.rfind("}")
        json_str = text[start : end + 1] if start != -1 and end != -1 and end >= start else text
        data = json.loads(json_str)
        ratings = data.get("ratings")
        if not isinstance(ratings, list):
            raise ValueError("ratings is not a list")
    except Exception as e:
        logger.warning("[v3] Chunk rating failed, returning default ratings: %s", e)
        ratings = default_ratings

    # Map ratings by index.
    by_index: Dict[int, Dict] = {}
    for r in ratings:
        try:
            idx = int(r.get("index"))
        except Exception:
            continue
        if 0 <= idx < len(chunks):
            by_index[idx] = {
                "index": idx,
                "relevance": r.get("relevance") or "medium",
                "can_answer": bool(r.get("can_answer", False)),
                "notes": r.get("notes") or "",
            }

    scored: List[Dict] = []
    for idx, c in enumerate(chunks):
        r = by_index.get(
            idx,
            {
                "index": idx,
                "relevance": "medium",
                "can_answer": True,
                "notes": "Implicit default rating.",
            },
        )
        scored.append(
            {
                "source_url": c.source_url,
                "content": c.content,
                "relevance": r["relevance"],
                "can_answer": r["can_answer"],
                "notes": r["notes"],
            }
        )

    return scored


def _summarize_relevant_chunks(
    query: str,
    rated_chunks: List[Dict],
    *,
    max_chunks: int = 10,
) -> List[Dict]:
    """
    Summarise the most relevant chunks with respect to the question.
    """
    if not rated_chunks:
        return []

    # Prioritise chunks that can answer, then medium relevance.
    can_answer_chunks = [c for c in rated_chunks if c.get("can_answer")]
    medium_chunks = [
        c for c in rated_chunks if not c.get("can_answer") and c.get("relevance") == "medium"
    ]
    low_chunks = [
        c for c in rated_chunks if c not in can_answer_chunks and c not in medium_chunks
    ]

    ordered: List[Dict] = can_answer_chunks + medium_chunks + low_chunks
    selected = ordered[:max_chunks]

    summaries: List[Dict] = []

    for idx, chunk in enumerate(selected):
        src = chunk.get("source_url", "N/A")
        content = chunk.get("content") or ""

        system_prompt = """
You are an assistant that summarises SEC.gov text specifically to help answer a question.

Rules:
- Use ONLY the provided text; do not add outside knowledge.
- Focus your summary strictly on parts of the text that help answer the question.
- If the text is mostly irrelevant to the question, say that explicitly.
- Keep the summary compact (one short paragraph or 3–6 bullet points).
"""

        user_prompt = f"""
User query:
{query}

Source URL: {src}

Document chunk:
\"\"\"{content}\"\"\"

Instructions:
- Summarise only the information that is helpful for answering the user query.
- If little or nothing in this chunk is relevant, say that clearly.
"""

        full_prompt = system_prompt + "\n\n" + user_prompt

        try:
            resp = client.responses.create(
                model="gpt-5-mini",
                input=full_prompt,
                text={"format": {"type": "text"}},
                max_output_tokens=800,
            )
            raw_text = resp.output_text or ""
            text = raw_text.strip()
            _estimate_tokens_and_cost(
                resp,
                "gpt-5-mini",
                full_prompt,
                text,
                step_name=f"v3_summarize_{idx}",
            )
            summary = text
            if not summary:
                continue
        except Exception as e:
            logger.warning("[v3] Summarisation failed for chunk %d: %s", idx, e)
            continue

        summaries.append(
            {
                "source_url": src,
                "summary": summary,
                "relevance": chunk.get("relevance", "medium"),
                "can_answer": bool(chunk.get("can_answer")),
            }
        )

    logger.info("[v3] Generated %d summaries.", len(summaries))
    return summaries


def _generate_final_answer_from_summaries(
    query: str,
    summaries: List[Dict],
) -> str:
    """
    Use summarised evidence to generate the final SEC answer.
    """
    if not summaries:
        # Log a clear reason when we fall back to the generic \"insufficient material\" message.
        logger.warning(
            "[v3] No document summaries available for final answer; "
            "this usually means full-document fetch or summarisation failed for query: %r",
            query,
        )
        return (
            "I could not find sufficient relevant SEC.gov material in the knowledge base "
            "to answer this question with confidence.\n\n"
            "Sources: (no suitable SEC.gov documents were identified)"
        )

    # Prepare compact JSON for the model.
    context_payload = [
        {
            "source_url": s.get("source_url", ""),
            "summary": (s.get("summary") or "").replace("\n", " "),
        }
        for s in summaries
    ]
    context_json = json.dumps(context_payload)

    system_prompt = """
You are an **SEC Q&A Chat Agent**.

Rules:
- Answer questions ONLY using the summarised SEC.gov snippets provided to you.
- Write in clear, non‑legalistic English.
- Provide concise factual answers strictly based on the summaries. Do NOT offer
  personal interpretations or forecasts unless clearly supported by the summaries.
- Focus on giving a direct, best‑effort answer based on the summaries you have.
- Do NOT mention limitations of the summaries, the underlying SEC.gov materials, or what is or is not covered; simply give the best answer you can.
- At the end of every answer, include a Markdown section titled "Sources" with bullet points:

  Sources:

  - <short description> — <sec.gov URL>
  - ...

- Only cite URLs that appear in the provided summaries.
"""

    user_prompt = f"""
User query:
{query}

You have access to the following summarised SEC.gov evidence (JSON list of objects with
\"source_url\" and \"summary\"):
{context_json}

Instructions:
- Carefully read the summaries and answer the user query as accurately as possible.
- Use only information that is reasonably supported by these summaries.
- When you make factual statements, ensure they can be traced back to at least one summary.
- Give a direct, finished answer; do not mention limitations of the summaries or what is or is not covered by SEC.gov.
- Do NOT say phrases like "not from the SEC.gov materials you provided" or "the provided chunks do not contain...".
- At the end of your answer, add a "Sources" section with bullet points listing the most relevant
  sec.gov URLs you used.
"""

    full_prompt = system_prompt + "\n\n" + user_prompt

    try:
        resp = client.responses.create(
            model="gpt-5.2",
            reasoning={"effort": "medium"},
            input=full_prompt,
            max_output_tokens=10000,
        )
        text = resp.output_text or ""
        _estimate_tokens_and_cost(
            resp, "gpt-5.2", full_prompt, text, step_name="v3_answer"
        )
        answer = text.strip()
        if answer:
            return answer
    except Exception as e:
        logger.error("[v3] Final answer generation failed: %s", e)

    return (
        "I wasn't able to generate an answer from the available SEC summaries.\n\n"
        "Sources: see the SEC URLs included in the retrieved context."
    )


def _group_chunks_by_url(chunks: List[RetrievedChunk]) -> Dict[str, List[str]]:
    """
    Group truncated chunk contents by source_url for document-level reasoning.
    """
    grouped: Dict[str, List[str]] = {}
    for c in chunks:
        url = c.source_url or "N/A"
        grouped.setdefault(url, []).append(c.content)
    return grouped


def _rerank_documents_for_query(
    query: str,
    doc_candidates: Dict[str, List[str]],
    *,
    max_candidates: int = 15,
    top_n: int = 10,
) -> List[str]:
    """
    Ask an LLM to pick the top-N source URLs most likely to answer the query.
    """
    if not doc_candidates:
        return []

    # Build a compact view of candidates: snippet + chunk count.
    items: List[Dict[str, object]] = []
    for url, chunks in list(doc_candidates.items())[:max_candidates]:
        text = " ".join(chunks)[:800]
        items.append(
            {
                "source_url": url,
                "snippet": text,
                "chunk_count": len(chunks),
            }
        )
    items_json = json.dumps(items)

    system_prompt = """
You are an assistant that ranks SEC.gov documents for a specific research question.

Rules:
- Each candidate has a source_url, a short text snippet, and a chunk_count.
- Select the documents that are most likely to contain enough information to answer the question.
- Prefer documents whose snippet clearly discusses the key concepts in the query.
- Work strictly within the SEC context.

Output format:
- Return ONLY valid JSON:
  {
    "top_urls": ["https://www.sec.gov/...", "..."]
  }
"""

    user_prompt = f"""
User query:
{query}

Candidate documents (JSON list):
{items_json}

Instructions:
- Choose up to {top_n} source_url values that look most promising for answering the query.
- Order them from most to least promising.
- Respond with JSON only.
"""

    full_prompt = system_prompt + "\n\n" + user_prompt
    try:
        resp = client.responses.create(
            model="gpt-5-mini",
            input=full_prompt,
            text={"format": {"type": "text"}},
            max_output_tokens=1200,
        )
        raw_text = resp.output_text or ""
        text = raw_text.strip()
        _estimate_tokens_and_cost(
            resp, "gpt-5-mini", full_prompt, text, step_name="v3_rerank_docs"
        )
        if not text:
            raise ValueError("Empty response from model for doc rerank.")
        start = text.find("{")
        end = text.rfind("}")
        json_str = (
            text[start : end + 1]
            if start != -1 and end != -1 and end >= start
            else text
        )
        data = json.loads(json_str)
        urls = data.get("top_urls") or []
        top_urls: List[str] = []
        for u in urls:
            if isinstance(u, str) and u.strip():
                top_urls.append(u.strip())
        if not top_urls:
            raise ValueError("No valid URLs in reranker JSON.")
        # Filter to URLs we actually have candidates for and enforce top_n.
        filtered = [u for u in top_urls if u in doc_candidates]
        return filtered[:top_n] or list(doc_candidates.keys())[:top_n]
    except Exception as e:
        logger.warning(
            "[v3] Document reranking failed, falling back to heuristic: %s", e
        )
        # Heuristic: sort URLs by number of chunks (descending).
        sorted_urls = sorted(
            doc_candidates.items(), key=lambda kv: len(kv[1]), reverse=True
        )
        return [u for u, _ in sorted_urls[:top_n]]


def _fetch_full_document_text(url: str, *, max_chars: int = 60000) -> str:
    """
    Refetch a full SEC document by URL and extract main text.
    """
    resp = fetch_url(url)
    if not resp:
        return ""
    content_type = (resp.headers.get("Content-Type") or "").lower()
    text = ""
    try:
        if "pdf" in content_type or is_pdf_url(url):
            pages = extract_text_from_pdf(url, resp.content)
            text = " ".join(page_text for _, page_text in pages)
        else:
            _, main_text = extract_text_from_html(url, resp.text)
            text = main_text
    except Exception as e:
        logger.warning("[v3] Error extracting full document for %s: %s", url, e)
        return ""
    text = " ".join(text.split())
    if len(text) > max_chars:
        text = text[:max_chars]
    return text


def _summarize_full_documents(
    query: str,
    urls: List[str],
    *,
    max_docs: int = 7,
    progress_cb: ProgressCallback | None = None,
) -> List[Dict]:
    """
    Summarise full SEC documents (by URL) with respect to the question.
    """
    if not urls:
        return []

    summaries: List[Dict] = []
    for idx, url in enumerate(urls[:max_docs]):
        if progress_cb is not None:
            try:
                progress_cb(
                    {
                        "stage": "fetch_doc",
                        "url": url,
                        "current": idx + 1,
                        "total": min(len(urls), max_docs),
                    }
                )
            except Exception:
                pass
        doc_text = _fetch_full_document_text(url)
        if not doc_text:
            logger.warning("[v3] No text extracted for %s (fetch or parse failure).", url)
            continue
        if len(doc_text) < 500:
            logger.info(
                "[v3] Skipping %s: extracted text too short (%d characters).",
                url,
                len(doc_text),
            )
            continue

        system_prompt = """
You are an assistant that summarises full SEC.gov documents specifically to help answer a question.

Rules:
- Use ONLY the provided document text; do not add outside knowledge.
- Focus your summary strictly on parts of the document that help answer the question.
- If the document is mostly irrelevant to the question, say that explicitly.
- Keep the summary focused and structured, but cover all key points relevant to the query.
"""

        user_prompt = f"""
User query:
{query}

Source URL: {url}

Full document text:
\"\"\"{doc_text}\"\"\"

Instructions:
- Summarise only the information that is helpful for answering the user query.
- If little or nothing in this document is relevant, say that clearly.
"""

        full_prompt = system_prompt + "\n\n" + user_prompt
        try:
            resp = client.responses.create(
                model="gpt-5-mini",
                input=full_prompt,
                text={"format": {"type": "text"}},
                max_output_tokens=1200,
            )
            raw_text = resp.output_text or ""
            text = raw_text.strip()
            _estimate_tokens_and_cost(
                resp,
                "gpt-5-mini",
                full_prompt,
                text,
                step_name=f"v3_doc_summarize_{idx}",
            )
            summary = text
            if not summary:
                continue
        except Exception as e:
            logger.error("[v3] Full-document summarisation failed for %s: %s", url, e)
            continue

        summaries.append(
            {
                "source_url": url,
                "summary": summary,
                "doc_length": len(doc_text),
            }
        )
        if progress_cb is not None:
            try:
                progress_cb(
                    {
                        "stage": "doc_summarized",
                        "url": url,
                        "current": idx + 1,
                        "total": min(len(urls), max_docs),
                    }
                )
            except Exception:
                pass

    logger.info("[v3] Generated %d full-document summaries.", len(summaries))
    return summaries


def run_sec_query_experiment_v3(
    query: str,
    *,
    top_k_matches: int = 30,
) -> Dict:
    """
    Run the full v3 pipeline and return structured artefacts for inspection.
    """
    logger.info("[v3] Running SEC query experiment for: %r", query)

    topics = _generate_sec_topics(query)
    raw_chunks = _retrieve_sec_chunks_for_topics(
        topics, top_k_per_topic=10, alpha=0.5, max_total=top_k_matches
    )

    if not raw_chunks:
        logger.warning(
            "[v3] No raw chunks retrieved for query %r; topics=%r", query, topics
        )
        final_answer = (
            "I couldn't find any relevant content in the SEC knowledge base for this question. "
            "Please try rephrasing or narrowing your question or consult the SEC website directly."
            "\n\nSources: (no sec.gov documents matched)"
        )
        return {
            "query": query,
            "topics": topics,
            "raw_chunks": [],
            "scored_chunks": [],
            "summaries": [],
            "final_answer": final_answer,
        }

    truncated_chunks = _truncate_chunks(raw_chunks)
    scored_chunks = _score_chunks_for_question(query, truncated_chunks)
    summaries = _summarize_relevant_chunks(query, scored_chunks)
    final_answer = _generate_final_answer_from_summaries(query, summaries)

    return {
        "query": query,
        "topics": topics,
        "raw_chunks": [
            {"source_url": c.source_url, "content": c.content} for c in raw_chunks
        ],
        "scored_chunks": scored_chunks,
        "summaries": summaries,
        "final_answer": final_answer,
    }


def run_sec_query_experiment_v3_docs(
    query: str,
    *,
    top_k_matches: int = 30,
    top_docs: int = 10,
    progress_cb: ProgressCallback | None = None,
) -> Dict:
    """
    Document-level variant of the v3 pipeline with reranking and full-document summaries.
    """
    logger.info("[v3-docs] Running SEC query experiment (docs) for: %r", query)

    topics = _generate_sec_topics(query)
    if progress_cb is not None:
        try:
            progress_cb({"stage": "topics", "topics": topics})
        except Exception:
            pass
    retrieval_queries = _build_retrieval_queries(query, topics)
    if progress_cb is not None:
        try:
            progress_cb(
                {"stage": "retrieval_queries", "retrieval_queries": retrieval_queries}
            )
        except Exception:
            pass

    # Reuse the same retrieval helper but pass augmented queries.
    raw_chunks = _retrieve_sec_chunks_for_topics(
        retrieval_queries, top_k_per_topic=10, alpha=0.5, max_total=top_k_matches
    )
    if progress_cb is not None:
        try:
            progress_cb(
                {
                    "stage": "retrieval_done",
                    "chunk_count": len(raw_chunks),
                }
            )
        except Exception:
            pass

    if not raw_chunks:
        logger.warning(
            "[v3-docs] No raw chunks retrieved for query %r; topics=%r, retrieval_queries=%r",
            query,
            topics,
            retrieval_queries,
        )
        final_answer = (
            "I couldn't find any relevant content in the SEC knowledge base for this question. "
            "Please try rephrasing or narrowing your question or consult the SEC website directly."
            "\n\nSources: (no sec.gov documents matched)"
        )
        return {
            "query": query,
            "topics": topics,
            "retrieval_queries": retrieval_queries,
            "raw_chunks": [],
            "reranked_urls": [],
            "doc_summaries": [],
            "final_answer": final_answer,
        }

    truncated_chunks = _truncate_chunks(raw_chunks)
    grouped = _group_chunks_by_url(truncated_chunks)
    candidate_urls = list(grouped.keys())
    if progress_cb is not None:
        try:
            progress_cb(
                {
                    "stage": "candidates",
                    "candidate_url_count": len(candidate_urls),
                    "candidate_urls": candidate_urls[:25],
                }
            )
        except Exception:
            pass
    reranked_urls = _rerank_documents_for_query(
        query, grouped, max_candidates=15, top_n=top_docs
    )
    if progress_cb is not None:
        try:
            progress_cb({"stage": "reranked", "selected_urls": reranked_urls})
        except Exception:
            pass
    doc_summaries = _summarize_full_documents(
        query, reranked_urls, progress_cb=progress_cb
    )
    final_answer = _generate_final_answer_from_summaries(query, doc_summaries)

    return {
        "query": query,
        "topics": topics,
        "retrieval_queries": retrieval_queries,
        "raw_chunks": [
            {"source_url": c.source_url, "content": c.content} for c in raw_chunks
        ],
        "reranked_urls": reranked_urls,
        "doc_summaries": doc_summaries,
        "final_answer": final_answer,
    }


def answer_sec_query_v3(query: str) -> str:
    """
    Thin wrapper that returns only the final answer string for a query.
    """
    result = run_sec_query_experiment_v3(query)
    answer = (result.get("final_answer") or "").strip()
    if answer:
        return answer
    return (
        "I wasn't able to generate an answer from the available SEC summaries.\n\n"
        "Sources: see the SEC URLs included in the retrieved context."
    )


def answer_sec_query_v3_docs(query: str) -> str:
    """
    Wrapper that uses the document-level v3 pipeline.
    """
    result = run_sec_query_experiment_v3_docs(query)
    answer = (result.get("final_answer") or "").strip()
    if answer:
        return answer
    return (
        "I wasn't able to generate an answer from the available SEC documents.\n\n"
        "Sources: see the SEC URLs included in the retrieved context."
    )


def answer_sec_query_v3_docs_with_progress(
    query: str, progress_cb: ProgressCallback
) -> str:
    """
    Wrapper that uses the document-level v3 pipeline and emits progress updates.
    """
    result = run_sec_query_experiment_v3_docs(query, progress_cb=progress_cb)
    answer = (result.get("final_answer") or "").strip()
    if answer:
        return answer
    return (
        "I wasn't able to generate an answer from the available SEC documents.\n\n"
        "Sources: see the SEC URLs included in the retrieved context."
    )


if __name__ == "__main__":
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(
        description="Run chat_agent_v3 SEC query experiments."
    )
    parser.add_argument(
        "--test",
        type=int,
        choices=[-1, 1, 2, 3, 4],
        default=1,
        help=(
            "Select test mode: "
            "-1 = topics only (verify topic generation), "
            "1 = single hard-coded query (chunk pipeline), "
            "2 = batch from sample_questions.txt (doc pipeline), "
            "3 = compare chunk vs doc pipelines on a single query, "
            "4 = doc-pipeline regression on harder questions."
        ),
    )
    parser.add_argument(
        "--file",
        type=str,
        default="",
        help="Optional path to write questions and answers as a Markdown file.",
    )
    args = parser.parse_args()

    if args.test == -1:
        # example_query = (
        #     "How has the SEC approached the classification of crypto tokens under the "
        #     "Howey Test in its public guidance and speeches?"
        # )
        example_query = "How has the SEC’s interpretation of the Howey Test evolved across enforcement cases related to crypto tokens, and what classification patterns can the knowledge base identify?"
        print(f"[v3] Test -1: topic generation only\nQuery: {example_query}\n")
        topics = _generate_sec_topics(example_query)
        print(f"\n[v3] Topics ({len(topics)}):")
        for i, t in enumerate(topics, 1):
            print(f"  {i}. {t}")

    elif args.test == 1:
        example_query = (
            "How has the SEC approached the classification of crypto tokens under the "
            "Howey Test in its public guidance and speeches?"
        )
        exp = run_sec_query_experiment_v3(example_query, top_k_matches=25)
        print("\n[v3] Topics:", exp.get("topics"))
        print("[v3] Retrieved chunks:", len(exp.get("raw_chunks", [])))
        print("[v3] Summaries:", len(exp.get("summaries", [])))
        print("\n[v3] Final answer:\n")
        print(exp.get("final_answer", ""))

    elif args.test == 2:
        base_dir = Path(__file__).resolve().parent
        questions_path = base_dir / "sample_questions.txt"

        if not questions_path.exists():
            raise SystemExit(f"sample_questions.txt not found at {questions_path}")

        with questions_path.open("r", encoding="utf-8") as f:
            questions = [line.strip() for line in f.readlines() if line.strip()]

        results = []
        for idx, q in enumerate(questions[:10], start=1):
            print(f"\n[v3] Running question {idx}: {q}")
            # exp = run_sec_query_experiment_v3(q, top_k_matches=25)
            exp = run_sec_query_experiment_v3_docs(q, top_k_matches=30, top_docs=10)
            answer = exp.get("final_answer", "")
            results.append((q, answer))

        if args.file:
            out_path = Path(args.file).expanduser().resolve()
            with out_path.open("w", encoding="utf-8") as f:
                f.write("# Chat Agent v3 Batch Test\n\n")
                for idx, (q, ans) in enumerate(results, start=1):
                    f.write(f"## Question {idx}\n\n")
                    f.write(f"**Question**: {q}\n\n")
                    f.write("**Answer**:\n\n")
                    f.write(ans or "_No answer generated._")
                    f.write("\n\n---\n\n")
            print(f"\n[v3] Wrote batch results to {out_path}")
        else:
            for idx, (q, ans) in enumerate(results, start=1):
                print(f"\n=== Question {idx} ===")
                print(q)
                print("\nAnswer:\n")
                print(ans or "_No answer generated._")

    elif args.test == 3:
        example_query = (
            "How has the SEC’s interpretation of the Howey Test evolved across enforcement "
            "cases related to crypto tokens, and what classification patterns can the "
            "knowledge base identify?"
        )
        print(f"[v3] Test 3: compare chunk vs doc pipelines\nQuery: {example_query}\n")

        print("\n[v3] === Chunk-level pipeline ===")
        exp_chunk = run_sec_query_experiment_v3(example_query, top_k_matches=25)
        print("\n[v3] Chunk topics:", exp_chunk.get("topics"))
        print("[v3] Chunk retrieved chunks:", len(exp_chunk.get("raw_chunks", [])))
        print("[v3] Chunk summaries:", len(exp_chunk.get("summaries", [])))
        print("\n[v3] Chunk final answer:\n")
        print(exp_chunk.get("final_answer", ""))

        print("\n[v3] === Document-level pipeline ===")
        exp_docs = run_sec_query_experiment_v3_docs(
            example_query, top_k_matches=30, top_docs=10
        )
        print("\n[v3] Doc topics:", exp_docs.get("topics"))
        print("[v3] Doc retrieval queries:", len(exp_docs.get("retrieval_queries", [])))
        print("[v3] Doc raw chunks:", len(exp_docs.get("raw_chunks", [])))
        print("[v3] Doc reranked URLs:", len(exp_docs.get("reranked_urls", [])))
        print("[v3] Doc summaries:", len(exp_docs.get("doc_summaries", [])))
        print("\n[v3] Doc final answer:\n")
        print(exp_docs.get("final_answer", ""))

    elif args.test == 4:
        # Regression-style test: run doc pipeline on questions that previously
        # elicited meta disclaimers (e.g., "Not from the SEC.gov materials you provided").
        problem_queries = [
            "Can the system map which crypto-asset categories (stablecoins, DeFi tokens, NFTs) are most frequently cited in SEC enforcement actions or policy statements?",
            "How does the SEC’s current regulatory framework compare with the EU’s MiCA regime in terms of market authorization, investor protection, and stablecoin oversight?",
            "Can the system generate a comparative matrix of SEC regulations versus the UK’s phased crypto regime and highlight convergence or divergence areas?",
            "What regulatory approaches in MiCA or FATF guidance could be recommended to close gaps in the SEC’s current approach to DeFi oversight?",
            "Using historical SEC task force data, what precedents exist for shifting from enforcement-first to policy-led approaches?",
            "How might rulemaking scenarios (e.g., classifying stablecoins as securities vs. payment instruments) impact institutional adoption, based on global precedent analysis?",
            "What are the recurring themes and concerns in Task Force Written Inputs and Roundtable Transcripts, particularly from industry vs. academic participants?",
        ]

        for idx, q in enumerate(problem_queries, start=1):
            print(f"\n[v3] Test 4, question {idx}: {q}")
            exp = run_sec_query_experiment_v3_docs(
                q, top_k_matches=30, top_docs=10
            )
            answer = exp.get("final_answer", "")
            print("\nAnswer:\n")
            print(answer or "_No answer generated._")

