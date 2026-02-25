"""
Crypto Custody Newsletter Agent (v4).

Pipeline:
1. Phase 1: Fetch raw HTML for top sec_urls -> Agent extracts article/published links
   with dates -> 2 layers (layer-1 then layer-2) -> dedupe + date filter.
2. Phase 2: For each URL, fetch content -> Agent summarizes (facts, quotes, decisions,
   implications) one-by-one -> per_url_summaries.
3. Optional RAG: custody-angle query -> chat_agent_v3 docs pipeline -> full-doc
   summaries merged into pool.
4. Phase 3: If under token limit: single synthesis; else batch synthesis + merge ->
   single markdown newsletter (same format as v3).
"""

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from openai import OpenAI

from new_crawler_tool import fetch_sec_html, fetch_sec_url
from new_agent_v3 import (
    BASE_NEWSLETTER_SYSTEM_PROMPT,
    _placeholder_newsletter,
    write_newsletter_sync,
)

load_dotenv()

client = OpenAI()

# Token budget for synthesis input (conservative estimate: ~4 chars per token)
SYNTHESIS_INPUT_TOKEN_BUDGET = 100_000
CHARS_PER_TOKEN = 4
MAX_HTML_CHARS_FOR_LINK_EXTRACTOR = 80_000
MAX_DOC_CHARS_FOR_EXTRACTOR = 55_000

MODEL_COST_PER_1M = {
    "gpt-5-mini": (0.25, 2.00),
    "gpt-5.2": (1.75, 14.00),
}


def _estimate_tokens_and_cost(
    response: Any,
    model: str,
    input_str: str,
    output_str: str,
    step_name: str = "call",
) -> Tuple[int, int, float]:
    in_tok = out_tok = 0
    usage = getattr(response, "usage", None)
    if usage is not None:
        in_tok = getattr(usage, "input_tokens", None) or getattr(usage, "prompt_tokens", None) or 0
        out_tok = getattr(usage, "output_tokens", None) or getattr(usage, "completion_tokens", None) or 0
    if in_tok == 0 and input_str:
        in_tok = max(1, len(input_str) // 4)
    if out_tok == 0 and output_str:
        out_tok = max(1, len(output_str) // 4)
    price = MODEL_COST_PER_1M.get(model, (0.20, 0.80))
    cost = (in_tok * price[0] + out_tok * price[1]) / 1_000_000
    print(f"  [{step_name}] Tokens: {in_tok:,} in, {out_tok:,} out | Est. cost: ${cost:.4f}")
    return in_tok, out_tok, cost


def _parse_json_array(raw: str) -> List[Any]:
    """Extract a JSON array from model output (may be wrapped in markdown)."""
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```\s*$", "", raw)
    start = raw.find("[")
    if start == -1:
        return []
    end = raw.rfind("]") + 1
    if end <= start:
        return []
    try:
        return json.loads(raw[start:end])
    except json.JSONDecodeError:
        return []


def _parse_json_object(raw: str) -> Dict[str, Any]:
    """Extract a JSON object from model output."""
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```\s*$", "", raw)
    start = raw.find("{")
    if start == -1:
        return {}
    end = raw.rfind("}") + 1
    if end <= start:
        return {}
    try:
        return json.loads(raw[start:end])
    except json.JSONDecodeError:
        return {}


# ---------- Phase 1: URL discovery (2 layers, date-filtered) ----------


def _extract_article_links_from_html(
    page_url: str,
    html: str,
    start_date: str,
    end_date: str,
) -> List[Dict[str, str]]:
    """
    Agent 1: Given raw HTML and date range, return list of { url, date, label }
    for links that are article-like (speeches, statements, newsroom, etc.) and
    published within [start_date, end_date].
    """
    html_trunc = html[:MAX_HTML_CHARS_FOR_LINK_EXTRACTOR]
    if len(html) > MAX_HTML_CHARS_FOR_LINK_EXTRACTOR:
        html_trunc += "\n... [truncated]"

    prompt = f"""You are analyzing an SEC.gov web page to find links to article-like or published material (speeches, statements, newsroom items, press releases, enforcement releases, rulemakings, etc.).

Page URL: {page_url}
Date range to include: {start_date} to {end_date} (inclusive).

From the HTML below, identify every link that:
1. Points to a specific article, speech, statement, release, or other published piece (not just a section or category page).
2. Has a publication or post date that falls within {start_date} and {end_date}. Infer the date from the page context (e.g. text next to the link, list item, or visible date on the page). If you cannot determine a date, omit the link.
3. Is an absolute URL under sec.gov.

Return ONLY a valid JSON array. Each element must have exactly:
- "url": string (absolute SEC.gov URL)
- "date": string (YYYY-MM-DD)
- "label": string (short description, e.g. "Chair speech on custody")

If there are no such links, return [].
Do not include markdown code fences or any text outside the JSON array.

HTML:
{html_trunc}
"""

    try:
        resp = client.responses.create(
            model="gpt-5-mini",
            input=prompt,
            max_output_tokens=8000,
        )
        out = resp.output_text or ""
        _estimate_tokens_and_cost(resp, "gpt-5-mini", prompt, out, "link_extract")
        arr = _parse_json_array(out)
        result = []
        for item in arr:
            if not isinstance(item, dict):
                continue
            u = (item.get("url") or "").strip()
            d = (item.get("date") or "").strip()
            if u and d:
                result.append({"url": u, "date": d, "label": (item.get("label") or "")[:200]})
        return result
    except Exception as e:
        print(f"  Link extraction failed for {page_url}: {e}")
        return []


def _discover_urls_two_layers(
    sec_urls: List[str],
    start_date: str,
    end_date: str,
    *,
    delay_seconds: float = 1.5,
) -> List[Dict[str, str]]:
    """
    Layer 0: run link extractor on each of sec_urls -> layer1_entries.
    Layer 1: for each layer1 URL, fetch HTML and run link extractor -> layer2_entries.
    Return union of layer1 and layer2, deduped by url, with date in range.
    """
    seen_urls: set = set()
    all_entries: List[Dict[str, str]] = []

    # Layer 0: seed pages
    for url in sec_urls:
        if not url.strip().startswith("https://www.sec.gov"):
            continue
        time.sleep(delay_seconds)
        html = ""
        try:
            html = fetch_sec_html(url)
        except Exception as e:
            print(f"  Failed to fetch HTML for {url}: {e}")
            continue
        if not html:
            continue
        entries = _extract_article_links_from_html(url, html, start_date, end_date)
        for e in entries:
            u = e.get("url", "").strip()
            if u and u not in seen_urls and start_date <= e.get("date", "") <= end_date:
                seen_urls.add(u)
                all_entries.append(e)
    layer1_urls = [e["url"] for e in all_entries]

    # Layer 1: pages linked from seeds
    for url in layer1_urls:
        time.sleep(delay_seconds)
        html = ""
        try:
            html = fetch_sec_html(url)
        except Exception as e:
            print(f"  Failed to fetch HTML for {url}: {e}")
            continue
        if not html:
            continue
        entries = _extract_article_links_from_html(url, html, start_date, end_date)
        for e in entries:
            u = e.get("url", "").strip()
            if u and u not in seen_urls and start_date <= e.get("date", "") <= end_date:
                seen_urls.add(u)
                all_entries.append(e)

    return all_entries


# ---------- Phase 2: Per-URL content extraction ----------


def _extract_document_summary(source_url: str, doc_text: str) -> Dict[str, Any]:
    """
    Agent 2: Summarize one document for newsletter use: facts, quotes, decisions,
    implications (BD/RIA/bank/custodian), title, date.
    """
    text = doc_text[:MAX_DOC_CHARS_FOR_EXTRACTOR]
    if len(doc_text) > MAX_DOC_CHARS_FOR_EXTRACTOR:
        text += "\n... [truncated]"

    prompt = f"""You are extracting structured information from an SEC.gov document for a crypto custody regulatory newsletter.

Source URL: {source_url}

Extract everything needed to write the newsletter: key facts, notable quotes, decisions or main steps, implications for broker-dealers, RIAs, banks/trust companies, and crypto-native custodians. Include document title and date if visible.

Return ONLY a single JSON object with these keys (use empty arrays/strings if not applicable):
- "title": string
- "date": string (YYYY-MM-DD if available)
- "facts": string (3-7 sentences, plain English)
- "quotes": array of strings (short notable quotes)
- "decisions": array of strings (main decisions or steps)
- "implications": object with optional keys "broker_dealers", "rias", "banks_trusts", "crypto_custodians" (each array of strings)
- "topics": array of strings (e.g. qualified custodian, key management, segregation, enforcement)
- "entity_types": array of strings (e.g. BD, RIA, bank, trust, custodian)

Document text:
\"\"\"{text}\"\"\"
"""

    try:
        resp = client.responses.create(
            model="gpt-5-mini",
            input=prompt,
            max_output_tokens=4000,
        )
        out = resp.output_text or ""
        _estimate_tokens_and_cost(resp, "gpt-5-mini", prompt, out, "doc_extract")
        obj = _parse_json_object(out)
        if obj:
            obj["source_url"] = source_url
        return obj
    except Exception as e:
        print(f"  Document extraction failed for {source_url}: {e}")
        return {"source_url": source_url, "facts": "", "quotes": [], "decisions": [], "implications": {}}


def _fetch_document_text(url: str, max_chars: int = MAX_DOC_CHARS_FOR_EXTRACTOR) -> str:
    """Fetch full text from SEC URL (HTML or PDF). Capped for context."""
    try:
        text = fetch_sec_url(url)
    except Exception as e:
        print(f"  Failed to fetch {url}: {e}")
        return ""
    text = " ".join((text or "").split())
    if len(text) > max_chars:
        text = text[:max_chars]
    return text


def _run_phase2_per_url_extraction(
    url_entries: List[Dict[str, str]],
    delay_seconds: float = 1.0,
) -> List[Dict[str, Any]]:
    """For each URL, fetch content and run extractor agent. Return list of summary dicts."""
    per_url_summaries: List[Dict[str, Any]] = []
    for i, entry in enumerate(url_entries):
        url = entry.get("url", "").strip()
        if not url:
            continue
        time.sleep(delay_seconds)
        doc_text = _fetch_document_text(url)
        if not doc_text or len(doc_text) < 200:
            print(f"  Skip (no/minimal content): {url}")
            continue
        summary = _extract_document_summary(url, doc_text)
        if summary.get("facts") or summary.get("quotes") or summary.get("decisions"):
            if "date" not in summary or not summary["date"]:
                summary["date"] = entry.get("date", "")
            if "title" not in summary or not summary["title"]:
                summary["title"] = entry.get("label", "") or url
            per_url_summaries.append(summary)
        print(f"  Extracted {i+1}/{len(url_entries)}: {url[:60]}...")
    return per_url_summaries


# ---------- Optional RAG (chat_agent_v3 docs pipeline) ----------


def _run_rag_docs_pipeline(
    query: str,
    *,
    top_k_matches: int = 30,
    top_docs: int = 7,
) -> List[Dict[str, Any]]:
    """
    Run chat_agent_v3 docs pipeline: topics -> retrieval -> group by URL ->
    rerank -> fetch full doc -> summarize full doc by query angle.
    Returns list of { source_url, summary } compatible with per_url_summaries.
    """
    try:
        from chat_agent_v3 import (
            _build_retrieval_queries,
            _fetch_full_document_text,
            _generate_sec_topics,
            _group_chunks_by_url,
            _rerank_documents_for_query,
            _retrieve_sec_chunks_for_topics,
            _summarize_full_documents,
            _truncate_chunks,
        )
    except ImportError as e:
        print(f"  RAG docs pipeline skipped (import error): {e}")
        return []

    topics = _generate_sec_topics(query)
    retrieval_queries = _build_retrieval_queries(query, topics)
    raw_chunks = _retrieve_sec_chunks_for_topics(
        retrieval_queries, top_k_per_topic=10, alpha=0.5, max_total=top_k_matches
    )
    if not raw_chunks:
        return []
    truncated = _truncate_chunks(raw_chunks, max_chars_per_chunk=4000)
    grouped = _group_chunks_by_url(truncated)
    reranked_urls = _rerank_documents_for_query(
        query, grouped, max_candidates=15, top_n=top_docs
    )
    doc_summaries = _summarize_full_documents(query, reranked_urls, max_docs=top_docs)
    # Normalize to same shape as Phase 2 summaries (source_url + summary; newsletter can use summary as "facts")
    result = []
    for s in doc_summaries:
        result.append({
            "source_url": s.get("source_url", ""),
            "summary": s.get("summary", ""),
            "facts": s.get("summary", ""),
            "title": "",
            "date": "",
            "quotes": [],
            "decisions": [],
            "implications": {},
            "topics": [],
            "entity_types": [],
            "_from_rag": True,
        })
    return result


# ---------- Phase 3: Newsletter synthesis (with token-limit handling) ----------


def _estimate_input_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


def _synthesize_newsletter_single(
    per_url_summaries: List[Dict[str, Any]],
    start_date: str,
    end_date: str,
) -> str:
    """One synthesis call: system prompt + all summaries -> full newsletter."""
    summaries_json = json.dumps(per_url_summaries, indent=0)
    prompt = f"""
{BASE_NEWSLETTER_SYSTEM_PROMPT}

YOUR TASK:

Generate a weekly Crypto Custody Intelligence newsletter in MARKDOWN format. Use ONLY the per-document summaries below for the week {start_date} - {end_date}.

Requirements:
- Follow the REQUIRED NEWSLETTER STRUCTURE exactly: This Week at a Glance (table + Bottom Line), numbered Top Stories with Implications by entity, Regulatory Tracker (two tables), Enforcement Watch (table + Trends), Banking Regulator Corner, What's Coming (calendar table + Questions We're Tracking), Compliance Action Items, Resource Library (table with links), footer.
- Cite source_url for every fact; separate FACTS, ANALYSIS, and INFERENCE.
- Do not invent documents not in the inputs.

PER-DOCUMENT SUMMARIES (JSON):
{summaries_json}

Output: A single complete newsletter in Markdown, ready to save as a .md file.
"""

    resp = client.responses.create(
        model="gpt-5.2",
        reasoning={"effort": "high"},
        input=prompt,
        max_output_tokens=100_000,
    )
    out = resp.output_text or ""
    _estimate_tokens_and_cost(resp, "gpt-5.2", prompt, out, "synthesize")
    return out


def _synthesize_newsletter_batch_merge(
    per_url_summaries: List[Dict[str, Any]],
    start_date: str,
    end_date: str,
    *,
    batch_char_limit: int = (SYNTHESIS_INPUT_TOKEN_BUDGET * CHARS_PER_TOKEN) // 2,
) -> str:
    """
    Split summaries into batches, generate partial newsletter per batch,
    then merge into one dense newsletter.
    """
    # Build batches by cumulative char count
    batches: List[List[Dict[str, Any]]] = []
    current: List[Dict[str, Any]] = []
    current_len = 0
    for s in per_url_summaries:
        s_len = len(json.dumps(s))
        if current_len + s_len > batch_char_limit and current:
            batches.append(current)
            current = []
            current_len = 0
        current.append(s)
        current_len += s_len
    if current:
        batches.append(current)

    partials: List[str] = []
    for i, batch in enumerate(batches):
        print(f"  Synthesis batch {i+1}/{len(batches)} ({len(batch)} docs)...")
        partial = _synthesize_newsletter_single(batch, start_date, end_date)
        partials.append(partial)

    # Merge: one final call to produce single newsletter from partials
    merge_prompt = f"""
You are editing the Crypto Custody Intelligence newsletter. You have {len(partials)} partial newsletters (each with the same section structure but different content). Merge them into ONE dense, non-redundant newsletter.

Rules:
- Keep the exact REQUIRED NEWSLETTER STRUCTURE: # Custody Intelligence Weekly, ## This Week at a Glance, ## Top Stories, ## Regulatory Tracker Update, ## Enforcement Watch, ## Banking Regulator Corner, ## What's Coming, ## Compliance Action Items, ## Resource Library, ## Feedback, About, footer.
- Combine metrics in "This Week at a Glance" (sum where appropriate).
- Merge Top Stories: deduplicate and order by importance; keep all source URLs.
- Merge Regulatory Tracker, Enforcement Watch, Resource Library tables (union rows, dedupe).
- Keep all Compliance Action Items.
- Preserve every source URL cited in the partials in the final Resource Library or inline citations.
- Output a single markdown document. No placeholders like "see batch 2".
- Week of {start_date} – {end_date}.

PARTIAL NEWSLETTERS:
{chr(10).join(f'--- PARTIAL {i+1} ---{chr(10)}{p}' for i, p in enumerate(partials))}
"""

    resp = client.responses.create(
        model="gpt-5.2",
        reasoning={"effort": "high"},
        input=merge_prompt,
        max_output_tokens=100_000,
    )
    merged = resp.output_text or ""
    _estimate_tokens_and_cost(resp, "gpt-5.2", merge_prompt, merged, "merge")
    return merged


def _run_phase3_synthesis(
    per_url_summaries: List[Dict[str, Any]],
    start_date: str,
    end_date: str,
) -> str:
    """Decide single vs batch+merge by token estimate; return final newsletter markdown."""
    if not per_url_summaries:
        return _placeholder_newsletter(start_date, end_date)

    summaries_json = json.dumps(per_url_summaries)
    system_and_structure = len(BASE_NEWSLETTER_SYSTEM_PROMPT) + 1500
    total_chars = system_and_structure + len(summaries_json)
    est_tokens = total_chars // CHARS_PER_TOKEN

    if est_tokens <= SYNTHESIS_INPUT_TOKEN_BUDGET:
        return _synthesize_newsletter_single(per_url_summaries, start_date, end_date)
    return _synthesize_newsletter_batch_merge(per_url_summaries, start_date, end_date)


# ---------- Main entry ----------


def generate_crypto_custody_report_v4(
    sec_urls: List[str],
    start_date: str,
    end_date: str,
    *,
    use_rag: bool = False,
    rag_query: Optional[str] = None,
    delay_seconds: float = 1.5,
) -> str:
    """
    Custody Newsletter Agent v4: HTML-driven URL discovery (2 layers, date-filtered)
    -> per-URL extraction -> optional RAG docs pipeline -> newsletter synthesis.
    """
    print("[v4] Phase 1: URL discovery (2 layers, date-filtered)...")
    url_entries = _discover_urls_two_layers(sec_urls, start_date, end_date, delay_seconds=delay_seconds)
    # Dedupe by url (already done in _discover); also include seed URLs that might be article pages?
    urls_only = list({e["url"] for e in url_entries})
    print(f"[v4] Discovered {len(urls_only)} URLs in date range.")

    if not url_entries:
        print("[v4] No URLs in range. Returning placeholder.")
        return _placeholder_newsletter(start_date, end_date)

    print("[v4] Phase 2: Per-URL content extraction...")
    per_url_summaries = _run_phase2_per_url_extraction(url_entries, delay_seconds=delay_seconds)

    if use_rag and (rag_query or "SEC crypto custody guidance, enforcement, and speeches"):
        print("[v4] Optional RAG: running docs pipeline...")
        q = rag_query or "SEC crypto custody guidance, enforcement, and speeches for the week"
        rag_summaries = _run_rag_docs_pipeline(q, top_k_matches=30, top_docs=7)
        for s in rag_summaries:
            if s.get("source_url") and s.get("summary"):
                # Avoid duplicate URL if already in per_url_summaries
                if not any(p.get("source_url") == s["source_url"] for p in per_url_summaries):
                    per_url_summaries.append(s)
        print(f"[v4] RAG added {len(rag_summaries)} doc summaries.")

    print("[v4] Phase 3: Newsletter synthesis...")
    newsletter = _run_phase3_synthesis(per_url_summaries, start_date, end_date)
    return newsletter or _placeholder_newsletter(start_date, end_date)


if __name__ == "__main__":
    sec_urls = [
        "https://www.sec.gov/featured-topics/crypto-task-force",
        "https://www.sec.gov/about/divisions-offices/division-trading-markets",
        "https://www.sec.gov/about/divisions-offices/division-investment-management",
        "https://www.sec.gov/newsroom/speeches-statements",
        "https://www.sec.gov/enforcement-litigation/litigation-releases",
        "https://www.sec.gov/rules-regulations/rulemaking-activity",
        "https://www.sec.gov/rules/policy-statements",
        "https://www.sec.gov/rules/orders",
        "https://www.sec.gov/rules/interp",
        "https://www.sec.gov/newsroom/press-releases",
        "https://www.sec.gov/enforcement/administrative-proceedings",
        "https://www.sec.gov/enforcement/trading-suspensions",
        "https://www.sec.gov/enforcement/distributions-harmed-investors",
        "https://www.sec.gov/featured-topics/sec-cftc-harmonization-initiative",
        "https://www.sec.gov/rules/proposed",
        "https://www.sec.gov/rules/final",
        "https://www.sec.gov/about/reports-publications/examination-priorities",
        "https://www.sec.gov/about/reports-publications/risk-alerts",
    ]

    start_date = "2026-02-03"
    end_date = "2026-02-09"

    print("Generating Crypto Custody Intelligence newsletter (v4)...")
    report = generate_crypto_custody_report_v4(
        sec_urls=sec_urls,
        start_date=start_date,
        end_date=end_date,
        use_rag=False,
        delay_seconds=1.5,
    )
    output_path = "custody_newsletter_v5.md"
    write_newsletter_sync(report, output_path)
    print(f"\nNewsletter ready: {output_path}\n")
