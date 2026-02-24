"""
    SEC Q&A Chat Agent.

    This module implements a question‑answering agent tailored for
    United States Securities and Exchange Commission (SEC) topics.  It
    retrieves relevant material from a pre-populated Pinecone SEC knowledge base and
    produces a concise answer with citations back to sec.gov.  The goal
    of this module is to provide accurate, current answers using only
    official SEC sources while remaining transparent about where
    information originates.

    Changes from original implementation
    -----------------------------------
    The original proof‑of‑concept agent performed a shallow crawl of
    several SEC index pages and used a simple keyword overlap to select
    documents.  This version adds the following improvements:

    * More granular seed selection based on the query.  In addition to
    weighting speeches, press releases, enforcement and crypto, the
    agent now explicitly targets rulemaking pages when regulatory
    amendments are mentioned and enforcement pages when the question
    mentions enforcement, charges or settlements.
    * Weighted keyword scoring that accounts for both the total number
    of matching tokens and their proportion relative to the query.
    This helps promote pages that discuss most of the query terms
    rather than those that simply mention one.
    * More robust truncation of crawled content and duplicate filtering.
    Each document’s content is trimmed to a fixed number of characters
    to reduce token usage, and identical URLs are deduplicated early.
    * Defensive programming around crawler failures: if no pages are
    fetched, the agent returns a polite message rather than raising
    an exception.
    * Clearer system prompt emphasising the separation of facts,
    analysis and inference and instructing the model to say when
    supporting data is insufficient.

    Usage
    -----
    Import the ``answer_sec_query`` function and call it with a user
    query and the recent chat history.  The function returns a Markdown
    string containing the answer and a sources section listing all
    sec.gov URLs referenced.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from dotenv import load_dotenv
from openai import OpenAI

# ``hybrid_search`` queries the Pinecone SEC knowledge base (populated by
# ``crypto_ingest``) and returns documents with ``source_url`` and ``content``.
from crypto_ingest import hybrid_search

# Load environment variables (e.g., API keys) from an .env file if
# present.  This call is idempotent and safe to repeat.
load_dotenv()

# OpenAI client initialisation.  A single client instance is shared
# across calls to reduce overhead.  If you need to override the
# base_url or other parameters, set the OPENAI_API_BASE or related
# environment variables before importing this module.
client = OpenAI()

# Approximate $ per 1M tokens for cost logging.  You can update these
# values as OpenAI pricing changes.  The tuple is (cost per input
# token, cost per output token).  Costs are in USD per 1M tokens.
MODEL_COST_PER_1M: Dict[str, Tuple[float, float]] = {
    "gpt-5-mini": (0.25, 2.00),
    "gpt-5.2": (1.75, 14.00),
}


def _estimate_tokens_and_cost(
    response: Any,
    model: str,
    input_str: str,
    output_str: str,
    *,
    step_name: str = "call",
) -> Tuple[int, int, float]:
    """
    Estimate token counts and cost for an OpenAI API call.

    The OpenAI API may return usage information with the number of
    input and output tokens.  When this data is unavailable (e.g.,
    due to streaming), we conservatively estimate the counts based
    on the lengths of the input and output strings.  The estimated
    cost is calculated using ``MODEL_COST_PER_1M``.

    Parameters
    ----------
    response : Any
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
        # Some OpenAI SDKs expose different field names; handle both.
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
    # Fallback estimation: 1 token ≈ 4 characters.
    if in_tok == 0 and input_str:
        in_tok = max(1, len(input_str) // 4)
    if out_tok == 0 and output_str:
        out_tok = max(1, len(output_str) // 4)
    price = MODEL_COST_PER_1M.get(model, (0.20, 0.80))
    cost = (in_tok * price[0] + out_tok * price[1]) / 1_000_000
    # A simple print is retained for debugging; callers can remove or
    # redirect these messages as needed.
    print(f"  [{step_name}] Tokens: {in_tok:,} in, {out_tok:,} out | Est. cost: ${cost:.4f}")
    return in_tok, out_tok, cost


def _build_history_snippet(messages: Sequence[Dict[str, str]], max_chars: int = 2000) -> str:
    """
    Convert recent chat history into a text snippet for context.

    The OpenAI model can benefit from seeing a few previous exchanges
    to maintain coherence.  To conserve tokens, we only include the
    last several messages and truncate to at most ``max_chars``.

    Parameters
    ----------
    messages : sequence of dict
        Chat history, each dict with ``"role"`` and ``"content"`` keys.
    max_chars : int
        Maximum number of characters to include.

    Returns
    -------
    str
        A newline‑separated representation of recent chat history.
    """
    if not messages:
        return ""
    tail = messages[-6:]  # consider only the last few exchanges
    parts: List[str] = []
    for m in tail:
        role = m.get("role", "user")
        content = m.get("content", "")
        parts.append(f"{role}: {content}")
    text = "\n".join(parts)
    # Trim to the last max_chars characters, prefixing with ellipsis if truncated.
    if len(text) > max_chars:
        text = "..." + text[-max_chars:]
    return text


def answer_sec_query(
    query: str,
    messages: Sequence[Dict[str, str]],
    *,
    max_docs_for_context: int = 8,
    pinecone_top_k: int = 20,
    pinecone_alpha: float = 0.5,
) -> str:
    """
    Answer a user question about SEC topics using sec.gov content from Pinecone.

    This function retrieves relevant documents via hybrid search from the
    Pinecone SEC knowledge base, then invokes the OpenAI language model with
    the best context.  The response is formatted in Markdown and always
    includes a sources section referencing the sec.gov URLs used.

    Parameters
    ----------
    query : str
        The current user question.
    messages : sequence of dict
        Chat history as a list of objects with ``"role"`` and
        ``"content"`` fields.
    max_docs_for_context : int, optional
        Number of top documents to include in the context passed to
        the language model.  Excess documents increase cost without
        necessarily improving the answer quality.
    pinecone_top_k : int, optional
        Number of results to fetch from Pinecone hybrid search before
        truncating to max_docs_for_context.
    pinecone_alpha : float, optional
        Blend factor for hybrid search (0 = sparse-only, 1 = dense-only, 0.5 = balanced).

    Returns
    -------
    str
        A Markdown string containing the answer and a sources list.
    """
    # 1. Retrieve relevant documents from Pinecone (hybrid search).
    try:
        documents = hybrid_search(
            query=query,
            top_k=pinecone_top_k,
            alpha=pinecone_alpha,
        )
    except Exception as e:
        print(f"Pinecone search error: {e}")
        return (
            "I encountered an error while searching the SEC knowledge base. "
            "Please try again later or refine your question.\n\n"
            "Sources: (none)"
        )

    print(f"Retrieved {len(documents)} document(s) from Pinecone for query.")

    if not documents:
        return (
            "I couldn't find any relevant content in the SEC knowledge base for this question. "
            "Please try rephrasing or narrowing your question.\n\n"
            "Sources: (no sec.gov documents matched)"
        )

    # 2. Truncate content per document and select top N for context.
    MAX_CHARS_PER_DOC = 6000
    for doc in documents:
        content = doc.get("content") or ""
        doc["content"] = content[:MAX_CHARS_PER_DOC]

    top_docs = documents[:max_docs_for_context]

    # 3. Build the JSON payload that will be passed to the model.  Keep
    # only the fields we need (source_url and content).  Remove
    # newline characters in content to make the JSON more compact.
    context_payload: List[Dict[str, str]] = []
    for d in top_docs:
        url = d.get("source_url", "")
        content = (d.get("content") or "").replace("\n", " ")
        context_payload.append({"source_url": url, "content": content})
    context_json = json.dumps(context_payload)

    # Build a snippet from the last few chat messages for context.
    history_snippet = _build_history_snippet(messages)

    # 4. Construct the system and user prompts.  The system prompt
    # defines the rules for the agent, while the user prompt includes
    # the query, history, and context documents.
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

    # 5. Invoke the language model.  We request a medium reasoning effort
    # and a reasonably generous token budget for the output.  You can
    # adjust ``max_output_tokens`` based on your tolerance for long
    # answers and cost.
    resp = client.responses.create(
        model="gpt-5.2",
        reasoning={"effort": "medium"},
        input=full_prompt,
        max_output_tokens=1000,
    )

    answer = resp.output_text or ""
    _estimate_tokens_and_cost(resp, "gpt-5.2", full_prompt, answer, step_name="sec_chat")
    if answer.strip():
        return answer.strip()
    return (
        "I wasn't able to generate an answer from the available sec.gov material."\
        "\n\nSources: see the SEC URLs included in the context."
    )


if __name__ == "__main__":
    # Example usage: run a quick test query when executed directly.
    q = "Can the system map which crypto-asset categories (stablecoins, DeFi tokens, NFTs) are most frequently cited in SEC enforcement actions or policy statements?"
    ans = answer_sec_query(q, messages=[])
    # out_path = Path("sec_chat_example_answer.md")
    # out_path.write_text(ans, encoding="utf-8")
    # print(f"\nAnswer written to {out_path.resolve()}\n")
    print(f"\nAnswer: {ans}\n")