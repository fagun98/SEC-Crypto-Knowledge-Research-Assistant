"""
SEC Q&A Chat Agent (v2).

This module implements an improved question–answering agent for
topics related to the U.S. Securities and Exchange Commission
(SEC).  The agent retrieves relevant material from a pre‑indexed
SEC knowledge base (stored in Pinecone) and produces a concise
answer with citations back to sec.gov.  Compared to earlier
versions, this agent attempts to understand multi‑part queries
and issues separate targeted searches for each part, aggregating
results before passing them to the language model.  The goal is
to achieve better recall on complex questions without sacrificing
accuracy.

Key features
------------

* **Subquery extraction**: long questions or compound questions
  are split into smaller subqueries using simple heuristics (e.g.,
  splitting on question marks, semicolons, and numbered lists).
  Each subquery is sent separately to the Pinecone hybrid search
  function.  Documents returned across subqueries are combined
  and deduplicated.

* **Result aggregation**: documents from multiple searches are
  merged while preserving the order of relevance within each
  subquery.  This increases the chance that the final context
  includes a diverse set of materials relevant to different
  aspects of the user’s question.

* **Graceful fallback**: if no subqueries yield results (for
  example, because the question is outside the scope of the
  knowledge base), the agent responds politely and suggests that
  the user rephrase the question or consult other SEC sources.

* **Strict sourcing**: answers are built exclusively from the
  provided SEC document snippets.  The agent does not invent
  information.  All factual statements must be tied back to
  content in the context and cited accordingly.

Usage
-----

Call the ``answer_sec_query`` function with a user question and
an optional list of previous chat messages.  The function
returns a Markdown string containing the answer and a sources
section listing the sec.gov URLs used.

Note that this implementation assumes an external indexing
pipeline (``crypto_ingest.hybrid_search``) has already populated
the Pinecone index with SEC documents.  If the index is empty
or unavailable, the agent will gracefully inform the user.
"""

from __future__ import annotations

import json
import re
from typing import Dict, Iterable, List, Sequence, Tuple

from dotenv import load_dotenv
from openai import OpenAI

# ``hybrid_search`` queries the Pinecone SEC knowledge base (populated by
# ``crypto_ingest``) and returns documents with ``source_url`` and ``content``.
from crypto_ingest import hybrid_search

load_dotenv()

# OpenAI client initialisation.  A single client instance is
# shared across calls to reduce overhead.
client = OpenAI()

# Approximate $ per 1M tokens for cost logging.  Update as
# needed when OpenAI pricing changes.  The tuple is
# (cost per input token, cost per output token).  Costs are
# denominated in USD per 1M tokens.
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
    """
    Estimate token counts and cost for an OpenAI API call.

    The OpenAI API may return usage information with the number of
    input and output tokens.  When this data is unavailable
    (e.g., due to streaming), we conservatively estimate the counts
    based on the lengths of the input and output strings.  The
    estimated cost is calculated using ``MODEL_COST_PER_1M``.

    Parameters
    ----------
    response : object
        The response object returned by the OpenAI client.  It may
        contain a ``usage`` attribute with ``input_tokens`` and
        ``output_tokens`` fields.
    model : str
        The name of the model used.
    input_str : str
        The full prompt sent to the model.
    output_str : str
        The raw completion returned by the model.
    step_name : str, optional
        A human‑readable label for logging; defaults to ``"call"``.

    Returns
    -------
    Tuple[int, int, float]
        A tuple of (input_tokens, output_tokens, estimated_cost).
    """
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
    print(
        f"  [{step_name}] Tokens: {in_tok:,} in, {out_tok:,} out | Est. cost: ${cost:.4f}"
    )
    return in_tok, out_tok, cost


def _build_history_snippet(
    messages: Sequence[Dict[str, str]], max_chars: int = 2000
) -> str:
    """
    Convert recent chat history into a text snippet for context.

    The OpenAI model can benefit from seeing a few previous
    exchanges to maintain coherence.  To conserve tokens, we only
    include the last several messages and truncate to at most
    ``max_chars`` characters.

    Parameters
    ----------
    messages : sequence of dict
        Chat history, each dict with ``"role"`` and
        ``"content"`` keys.
    max_chars : int
        Maximum number of characters to include.

    Returns
    -------
    str
        A newline‑separated representation of recent chat history.
    """
    if not messages:
        return ""
    # Use only the last few messages for brevity.
    tail = messages[-6:]
    parts: List[str] = []
    for m in tail:
        role = m.get("role", "user")
        content = m.get("content", "")
        parts.append(f"{role}: {content}")
    text = "\n".join(parts)
    if len(text) > max_chars:
        text = "..." + text[-max_chars:]
    return text


def _extract_subqueries(query: str) -> List[str]:
    """
    Split a complex query into simpler subqueries.

    This helper attempts to identify independent clauses or
    questions within a single user query.  Heuristics include
    splitting on question marks, semicolons, enumerated list
    markers (e.g., "1.", "2.") and conjunctions such as "and"
    or "or".  Stop words and extremely short segments are
    filtered out.  The intention is to permit targeted searches
    against the SEC knowledge base for each aspect of the query.

    Parameters
    ----------
    query : str
        The original user query.

    Returns
    -------
    List[str]
        A list of cleaned subqueries.  If no meaningful splits
        are found, the list will contain only the original query.
    """
    # Normalize whitespace and strip leading/trailing punctuation.
    q = re.sub(r"\s+", " ", query).strip().rstrip(";.")
    # Split on question marks and semicolons.  Also split on bullet
    # points like "1." or "(1)" etc.
    splits = re.split(r"[?;]|\s+[0-9]+\.\s+|\s+\([0-9]+\)\s+", q)
    # Further split on ' and ' or ' or ' when there are multiple
    # concepts joined.  Only do this for sufficiently long segments.
    subqueries: List[str] = []
    for segment in splits:
        segment = segment.strip()
        if not segment:
            continue
        # Avoid splitting very short segments (less than 5 words).
        if len(segment.split()) >= 5:
            # Only split on ' and ' or ' or ' when there are 2 or more
            # occurrences.
            if segment.count(" and ") > 0 or segment.count(" or ") > 0:
                # Use regex to split but keep connectors outside the
                # resulting substrings.
                parts = re.split(r"\s+and\s+|\s+or\s+", segment)
                for part in parts:
                    part = part.strip()
                    if part:
                        subqueries.append(part)
            else:
                subqueries.append(segment)
        else:
            subqueries.append(segment)
    # Remove duplicates while preserving order.
    seen = set()
    unique_subqueries: List[str] = []
    for sq in subqueries:
        sq_norm = sq.lower()
        if sq_norm not in seen:
            seen.add(sq_norm)
            unique_subqueries.append(sq)
    # Ensure we always return at least the original query.
    return unique_subqueries if unique_subqueries else [query]


def _collect_documents(
    subqueries: Iterable[str],
    *,
    top_k: int = 10,
    alpha: float = 0.5,
) -> List[Dict[str, str]]:
    """
    Run hybrid search for each subquery and combine results.

    Parameters
    ----------
    subqueries : Iterable[str]
        A collection of subqueries derived from the user query.
    top_k : int, optional
        Number of results to request from Pinecone per subquery.  A
        smaller value reduces costs but may miss relevant items.
    alpha : float, optional
        Blend factor for hybrid search (0 = sparse‑only, 1 = dense‑only,
        0.5 = balanced).

    Returns
    -------
    List[Dict[str, str]]
        A deduplicated list of documents ordered by their first
        appearance across subqueries.
    """
    aggregated: List[Dict[str, str]] = []
    seen_urls: set[str] = set()
    for idx, sq in enumerate(subqueries):
        try:
            docs = hybrid_search(query=sq, top_k=top_k, alpha=alpha)
        except Exception as e:
            print(f"Pinecone search error for subquery '{sq}': {e}")
            continue
        for doc in docs:
            url = doc.get("source_url")
            if not url:
                continue
            if url not in seen_urls:
                # Truncate content early to reduce memory footprint.
                content = doc.get("content") or ""
                doc["content"] = content
                aggregated.append(doc)
                seen_urls.add(url)
        if aggregated:
            # Limit total aggregated documents to avoid excessive context.
            if len(aggregated) >= top_k:
                break
    return aggregated


def answer_sec_query(
    query: str,
    messages: Sequence[Dict[str, str]],
    *,
    max_docs_for_context: int = 8,
    pinecone_top_k: int = 15,
    pinecone_alpha: float = 0.5,
) -> str:
    """
    Answer a user question about SEC topics using sec.gov content from Pinecone.

    This function processes the query to extract subtopics, retrieves
    relevant documents from the SEC knowledge base via hybrid
    search, and passes a curated context to the OpenAI language
    model.  The response is formatted in Markdown and always
    includes a sources section referencing the sec.gov URLs used.

    Parameters
    ----------
    query : str
        The current user question.
    messages : sequence of dict
        Chat history as a list of objects with ``"role"`` and
        ``"content"`` fields.
    max_docs_for_context : int, optional
        Number of top documents to include in the context passed
        to the language model.  A smaller number helps keep the
        prompt size manageable.
    pinecone_top_k : int, optional
        Number of results to fetch from Pinecone per subquery before
        deduplication.  This number may be slightly larger than
        ``max_docs_for_context`` to allow diversity.
    pinecone_alpha : float, optional
        Blend factor for hybrid search (0 = sparse‑only, 1 = dense‑only,
        0.5 = balanced).

    Returns
    -------
    str
        A Markdown string containing the answer and a sources list.
    """
    # 1. Extract meaningful subqueries from the user’s question.
    subqueries = _extract_subqueries(query)
    print(f"Identified {len(subqueries)} subquery(ies): {subqueries}")

    # 2. Retrieve relevant documents across all subqueries.
    documents = _collect_documents(
        subqueries,
        top_k=pinecone_top_k,
        alpha=pinecone_alpha,
    )
    print(f"Aggregated {len(documents)} document(s) for query.")

    if not documents:
        return (
            "I couldn't find any relevant content in the SEC knowledge base for this question. "
            "Please try rephrasing or narrowing your question or consult the SEC website directly."
            "\n\nSources: (no sec.gov documents matched)"
        )

    # 3. Truncate each document’s content for token economy.
    MAX_CHARS_PER_DOC = 6000
    for doc in documents:
        content = doc.get("content") or ""
        doc["content"] = content[:MAX_CHARS_PER_DOC]

    # 4. Select the top documents for context.  Here we simply take
    # the first N aggregated documents.  Further ranking could be
    # added if needed (e.g., scoring by keyword overlap).
    top_docs = documents[:max_docs_for_context]

    # Prepare context payload: only include fields needed by the model.
    context_payload: List[Dict[str, str]] = []
    for d in top_docs:
        url = d.get("source_url", "")
        # Remove newlines to keep the JSON compact.
        content = (d.get("content") or "").replace("\n", " ")
        context_payload.append({"source_url": url, "content": content})
    context_json = json.dumps(context_payload)

    # Build a snippet from the last few chat messages for context.
    history_snippet = _build_history_snippet(messages)

    # 5. Construct system and user prompts.
    system_prompt = """
You are an **SEC Q&A Chat Agent**.

Rules:
 - Answer questions **only** using information from SEC (sec.gov) documents provided to you.
 - If the SEC documents do not contain enough information to answer confidently, say so and
   suggest what the user might look for on sec.gov.
 - Write in clear, non‑legalistic English.
 - Provide concise factual answers strictly based on the SEC documents. Do **not** offer
   personal interpretations or forecasts unless the documents themselves include such
   analysis. You may summarise the SEC's own interpretive statements when they appear,
   but avoid adding inference beyond what is stated.
 - At the **end** of every answer, include a Markdown section titled "Sources" with bullet points:

   Sources:

   - <short description> — <sec.gov URL>
   - ...

   Only cite URLs that appear in the context documents you received.
"""

    user_prompt = f"""
User query:
{query}

Recent chat history (for context):
{history_snippet}

You have access to the following SEC.gov documents (JSON list of objects with
"source_url" and "content"):
{context_json}

Instructions:
 - Carefully read the SEC documents above and answer the user query as accurately as possible.
 - Use only information that is reasonably supported by these documents.
 - When you make factual statements, cite one or more of the SEC URLs in the context.  Each factual
   statement should be traceable to the content provided.
 - If the documents do not answer the question, say so and, if appropriate, suggest what the user
   could search for on sec.gov.
 - At the end of your answer, add a "Sources" section with bullet points listing the most relevant
   sec.gov URLs you used.
"""

    full_prompt = system_prompt + "\n\n" + user_prompt

    # 6. Invoke the language model.  We request a moderate reasoning effort
    # and a token budget appropriate for concise answers.
    resp = client.responses.create(
        model="gpt-5.2",
        reasoning={"effort": "medium"},
        input=full_prompt,
        max_output_tokens=1000,
    )

    answer = resp.output_text or ""
    _estimate_tokens_and_cost(resp, "gpt-5.2", full_prompt, answer, step_name="sec_chat_v2")
    if answer.strip():
        return answer.strip()
    return (
        "I wasn't able to generate an answer from the available sec.gov material."\
        "\n\nSources: see the SEC URLs included in the context."
    )


if __name__ == "__main__":
    # Example usage: run a test query when executed directly.
    q = (
        "How has the SEC’s interpretation of the Howey Test evolved across enforcement "
        "cases related to crypto tokens, and what classification patterns can be identified?"
    )
    ans = answer_sec_query(q, messages=[])
    print("\nAnswer:\n", ans)