"""
SEC Q&A Chat Agent.

This module implements a question‑answering agent tailored for
United States Securities and Exchange Commission (SEC) topics.  It
fetches the latest material from SEC web properties at runtime and
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
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from dotenv import load_dotenv
from openai import OpenAI

# ``crawl_sec_pages`` is provided by the ``new_crawler_tool`` package.  It
# performs a depth‑limited crawl starting from a list of seed URLs and
# returns a list of documents with ``source_url`` and ``content`` keys.
from new_crawler_tool import crawl_sec_pages

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


# Core SEC entry points (sec.gov only).  We bias our crawl to these
# starting points instead of generic web search.  Additional seeds
# may be appended based on the user's query.
SEC_BASE_SOURCES: List[str] = [
    "https://www.sec.gov/newsroom/speeches-statements",
    "https://www.sec.gov/newsroom/press-releases",
    "https://www.sec.gov/featured-topics/crypto-task-force",
    "https://www.sec.gov/featured-topics/cybersecurity",
    "https://www.sec.gov/enforcement-litigation/litigation-releases",
    "https://www.sec.gov/rules-regulations/rulemaking-activity",
]


def _normalize_tokens(text: str) -> List[str]:
    """
    Normalise a piece of text into lowercase alphanumeric tokens.

    Non‑word characters are treated as delimiters.  Empty tokens
    are discarded.  This helper is used for computing simple
    keyword overlap between the query and document content.
    """
    return [tok for tok in re.split(r"\W+", text.lower()) if tok]


def _select_seed_urls_for_query(query: str) -> List[str]:
    """
    Heuristic selection of SEC index pages to crawl for a given query.

    The agent cannot search the open web; instead, it uses a small set
    of curated SEC pages as entry points.  This function analyses the
    query to decide which of those pages are most likely to contain
    relevant material.  The returned list is deduplicated and ordered
    with the most relevant seeds first.

    Parameters
    ----------
    query : str
        User's natural language question.

    Returns
    -------
    List[str]
        A list of SEC URLs to serve as crawler seeds.
    """
    q = query.lower()
    seeds: List[str] = []

    # Always include rulemaking and enforcement sources.  Many
    # questions relate to new rules or enforcement actions even if
    # the query does not explicitly mention them.
    seeds.append("https://www.sec.gov/rules-regulations/rulemaking-activity")
    seeds.append("https://www.sec.gov/enforcement-litigation/litigation-releases")

    # Speeches and commissioner statements are key for interpretive
    # guidance and policy direction.
    if any(word in q for word in ("speech", "remarks", "statement", "commissioner", "chair", "uyeda", "gallagher", "woody", "peirce", "crenshaw", "litzman", "atlkins")):
        seeds.append("https://www.sec.gov/newsroom/speeches-statements")

    # Press releases cover announcements, charges, and settlements.
    if any(word in q for word in ("press release", "announcement", "charges", "settled", "settlement", "fine", "indictment")):
        seeds.append("https://www.sec.gov/newsroom/press-releases")

    # Target crypto‑specific index when crypto‑related terms appear.
    if any(word in q for word in ("crypto", "digital asset", "token", "stablecoin", "defi")):
        seeds.append("https://www.sec.gov/featured-topics/crypto-task-force")

    # Cybersecurity and incidents may relate to breach disclosures.
    if any(word in q for word in ("cyber", "incident", "breach", "ransomware", "cybersecurity")):
        seeds.append("https://www.sec.gov/featured-topics/cybersecurity")

    # Explicit triggers for rulemaking (e.g., amendments, proposals).
    if any(word in q for word in ("rule", "regulation", "amendment", "proposal", "release", "no‑action", "guidance")):
        seeds.append("https://www.sec.gov/rules-regulations/rulemaking-activity")

    # Explicit triggers for enforcement actions.
    if any(word in q for word in ("enforcement", "fraud", "penalty", "complaint", "litigation", "charge", "commingling")):
        seeds.append("https://www.sec.gov/enforcement-litigation/litigation-releases")

    # Fallback: if none of the above triggers matched, include all base sources.
    if len(seeds) == 2:  # only rulemaking + enforcement added
        seeds.extend(SEC_BASE_SOURCES)

    # Deduplicate while preserving order.
    seen = set()
    deduped: List[str] = []
    for url in seeds:
        if url not in seen:
            seen.add(url)
            deduped.append(url)
    return deduped


def _score_documents_for_query(query: str, documents: Sequence[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Rank documents by how well they match the query using a simple
    keyword scoring algorithm.

    The score is the sum of two components:

    * ``hits``: the number of unique query tokens found anywhere in
      the document content.
    * ``coverage``: the fraction of query tokens that appear in the
      document.  This penalises documents that match only one word
      from a multi‑term query.

    Documents with higher scores are considered more relevant.  Only
    documents that contain at least one query token are returned.

    Parameters
    ----------
    query : str
        User's natural language question.
    documents : sequence of dict
        Each dict must have ``"content"`` and ``"source_url"`` keys.

    Returns
    -------
    List[Dict[str, str]]
        The input documents sorted in descending order of relevance.
    """
    q_tokens = set(_normalize_tokens(query))
    ranked: List[Tuple[float, Dict[str, str]]] = []
    for doc in documents:
        content = (doc.get("content") or "").lower()
        if not content:
            continue
        # Compute how many query tokens occur in the document.
        hits = sum(1 for tok in q_tokens if tok in content)
        if hits == 0:
            continue  # skip docs that don't mention any query token
        coverage = hits / len(q_tokens) if q_tokens else 0
        score = hits + coverage  # simple linear combination
        ranked.append((score, doc))
    ranked.sort(key=lambda x: x[0], reverse=True)
    return [doc for _, doc in ranked]


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
    max_crawl_pages: int = 40,
    max_docs_for_context: int = 8,
) -> str:
    """
    Answer a user question about SEC topics using only sec.gov content.

    This function orchestrates the pipeline: selecting seed URLs,
    crawling the SEC site, ranking the retrieved documents, and
    invoking the OpenAI language model with the best context.  The
    response is formatted in Markdown and always includes a sources
    section referencing the SEC URLs used.

    Parameters
    ----------
    query : str
        The current user question.
    messages : sequence of dict
        Chat history as a list of objects with ``"role"`` and
        ``"content"`` fields.
    max_crawl_pages : int, optional
        Maximum number of pages to fetch during the crawl.  Lower
        values reduce latency and token usage but may miss some
        documents.
    max_docs_for_context : int, optional
        Number of top documents to include in the context passed to
        the language model.  Excess documents increase cost without
        necessarily improving the answer quality.

    Returns
    -------
    str
        A Markdown string containing the answer and a sources list.
    """
    # 1. Determine which SEC entry pages to crawl.
    seed_urls = _select_seed_urls_for_query(query)
    print(f"Selected {len(seed_urls)} SEC seed URL(s) for query.")

    # 2. Crawl SEC.gov.  Limit depth to 1 so we only fetch index pages
    # and their immediate children.  The crawler may still follow
    # relative links; adjust ``max_depth`` in crawl_sec_pages if deeper
    # exploration is warranted.
    try:
        documents = crawl_sec_pages(
            seed_urls=seed_urls,
            max_depth=1,
            max_pages=max_crawl_pages,
            delay_seconds=1.5,
        )
    except Exception as e:
        # In the event of a crawler error, log and return early.
        print(f"Crawler error: {e}")
        return (
            "I encountered an error while retrieving content from sec.gov. "
            "Please try again later or refine your question.\n\n"
            "Sources: (none)"
        )
    print(f"Crawled {len(documents)} SEC page(s) for query.")

    # If the crawler returned no documents, inform the user.
    if not documents:
        return (
            "I couldn't retrieve any relevant content from sec.gov right now. "
            "Please try again later or narrow your question.\n\n"
            "Sources: (no sec.gov pages could be fetched)"
        )

    # Deduplicate documents by URL to prevent duplicate context entries.
    seen_urls: set[str] = set()
    deduped_docs: List[Dict[str, str]] = []
    for doc in documents:
        url = doc.get("source_url") or ""
        if url and url not in seen_urls:
            seen_urls.add(url)
            # Truncate content to reduce token count and remove high
            # overlap across large documents.  6000 characters is
            # roughly 1500 tokens.
            content = doc.get("content") or ""
            doc["content"] = content[:6000]
            deduped_docs.append(doc)

    # 3. Rank documents by relevance to the query.
    ranked_docs = _score_documents_for_query(query, deduped_docs)
    # If no document matches even a single token, include a few
    # unranked documents so that the model has some context.  Use
    # whichever deduped docs are available.
    if not ranked_docs:
        ranked_docs = deduped_docs

    # Select the top N documents for the model context.
    top_docs = ranked_docs[:max_docs_for_context]

    # Build the JSON payload that will be passed to the model.  Keep
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
 - Separate, where useful:
   - FACTS (directly supported by the SEC documents)
   - ANALYSIS (your interpretation)
   - INFERENCE (your forecast or best guess)
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
        max_output_tokens=2000,
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
    q = "What did Commissioner Uyeda recently say about tokenisation and crypto custody?"
    ans = answer_sec_query(q, messages=[])
    out_path = Path("sec_chat_example_answer.md")
    out_path.write_text(ans, encoding="utf-8")
    print(f"\nAnswer written to {out_path.resolve()}\n")