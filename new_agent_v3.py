"""
Crypto Custody Newsletter Agent (v3).

Process alignment (Process: Crypto custody newsletter.pdf):

1. Define research scope: week (start_date–end_date), SEC custody focus.
2. Search for SEC documents: search_sec_documents(queries, dates) → URLs (speeches, task force, enforcement).
3. Open and navigate: crawl/fetch pages; find_in_document(content, phrases) for key custody phrases.
4. Capture citations: source_url + excerpt for FACTS in the report.
5. Extract metrics and enforcement: classify tags enforcement; synthesize YTD and case table.
6. Organise findings: FACTS (with citations), ANALYSIS, INFERENCE per item.
7. Maintain regulatory tracker: table of guidance (effective date, status, impact).
8. Write newsletter: sections and tables matching Crypto custody newsletter result.pdf.
9. Create Markdown file and sync for download.

Output format follows Crypto custody newsletter result.pdf: This Week at a Glance (table + Bottom Line),
numbered Top Stories with Implications by entity, Regulatory Tracker (two tables), Enforcement Watch (table + Trends),
Banking Regulator Corner, What's Coming (calendar table + Questions We're Tracking), Compliance Action Items,
Resource Library (table with links), footer.
"""

import json
import re
from pathlib import Path
from typing import Any, List, Optional, Set, Tuple

from dotenv import load_dotenv
from openai import OpenAI

from new_tools import fetch_sec_url
from new_crawler_tool import crawl_sec_pages
from custody_agent_tools import (
    search_sec_documents,
    extract_citations_from_documents,
    DEFAULT_CUSTODY_PHRASES,
)

load_dotenv()

client = OpenAI()

CLASSIFY_BATCH_SIZE = 8
CLASSIFY_MAX_CHARS_PER_DOC = 8000

# Optional: path to custody keywords for pre-filtering (keyword gate)
KEYWORDS_FILE = Path(__file__).resolve().parent / "custody_agent_keywords.txt"

MODEL_COST_PER_1M = {
    "gpt-5-mini": (0.25, 2.00),
    "gpt-5.2": (1.75, 14.00),
    "gpt-5": (1.25, 10.00),
}


def _load_custody_keywords() -> Set[str]:
    """Load custody keywords from custody_agent_keywords.txt for optional keyword gate."""
    if not KEYWORDS_FILE.exists():
        return set()
    lines = KEYWORDS_FILE.read_text(encoding="utf-8").strip().splitlines()
    return {line.strip().lower() for line in lines if line.strip()}


def _keyword_gate(documents: List[dict], keywords: Set[str]) -> List[dict]:
    """
    Pipeline step: keep only documents whose content contains at least one custody keyword.
    If keywords is empty, returns all documents (no gating).
    """
    if not keywords:
        return documents
    kept = []
    for d in documents:
        content = (d.get("content") or "").lower()
        if any(kw in content for kw in keywords):
            kept.append(d)
    return kept


def _estimate_tokens_and_cost(
    response: Any,
    model: str,
    input_str: str,
    output_str: str,
    step_name: str = "call",
) -> Tuple[int, int, float]:
    """Get token counts from response.usage or estimate. Compute cost. Print and return (in_tok, out_tok, cost)."""
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


BASE_NEWSLETTER_SYSTEM_PROMPT = """
You are a "Crypto Custody Regulatory Intelligence Agent."

GOAL
Your goal is to continuously monitor, summarize, and explain all regulatory developments that affect **crypto custody** – i.e., who can legally hold customer crypto assets, under what rules, and with what controls – for broker‑dealers, RIAs, banks/trust companies, and specialized crypto custodians.

DATA YOU SHOULD USE (AND EXPECT TO RECEIVE)

You are powered by structured and unstructured data from:

- SEC CUSTODY SOURCES (sec.gov)
   - Staff Accounting Bulletins related to crypto custody (e.g., SAB 121/122)
   - Division of Trading & Markets statements and FAQs on:
     - Rule 15c3‑3 (customer protection / "control" and "physical possession")
     - Broker‑dealer custody of crypto asset securities
   - Division of Investment Management guidance and no‑action letters on:
     - RIA custody rule (Rule 206(4)‑2)
     - Use of state trust companies and banks as qualified custodians
   - SEC Crypto Task Force releases touching custody
   - Commissioner and Chair speeches that address:
     - Qualified custodians
     - Segregation of client assets
     - Key management and operational controls
   - Crypto‑related enforcement actions where custody / segregation / customer protection are central issues

WHAT YOU MUST BE ABLE TO DO

Given this data, you must be able to:

1. IDENTIFY & TAG CUSTODY‑RELEVANT ITEMS
   - Decide if a new document is custody‑relevant.
   - Tag it by:
     - Entity type affected (BD, RIA, bank, trust, custodian, issuer)
     - Topic (qualified custodian, key management, segregation, accounting, collateral, etc.)
     - Severity/importance (critical / high / medium).

2. SUMMARIZE IN PLAIN ENGLISH
   For each custody‑relevant item:
   - 3–7 sentence plain‑English summary of what changed or what is clarified.
   - Bullet list of:
     - "What this means for broker‑dealers"
     - "What this means for RIAs"
     - "What this means for banks/trust companies"
     - "What this means for crypto‑native custodians"
   - Mark clearly:
     - FACTS: direct statements from the document
     - ANALYSIS: your interpretation of implications
     - INFERENCE: your forecast or best guess.

3. MAINTAIN A REGULATORY TRACKER
   - Maintain a structured list of all custody‑relevant items with:
     - Date, source, type, status
     - Short title and 1–2 line summary
     - A few tags (topic, entity type, jurisdiction)

4. GENERATE WEEKLY CUSTODY DIGESTS
   - Given the past week's new items:
     - Write a weekly newsletter‑style summary:
       - "This Week at a Glance" metrics
       - Top 1–3 custody stories
       - Updated tracker snapshot
       - 3–5 concrete compliance action items
   - Tailor explanations by audience where possible (BD vs RIA vs bank).

OUTPUT EXPECTATIONS

- Always write in clear, non‑legalistic English.
- Separate:
  - FACTS (citations to specific SEC docs when possible),
  - ANALYSIS (your interpretation),
  - INFERENCE (your forecast).
- Generate a newsletter in markdown format.

REQUIRED NEWSLETTER STRUCTURE (match Crypto custody newsletter result.pdf exactly):

# 🔐 Custody Intelligence Weekly
## The Regulatory Digest for Crypto Custodians
### Week of [DATE RANGE] | Issue #[N]

[Optional 1–2 sentence intro summarising the week, e.g. speeches and written inputs.]

## 📊 This Week at a Glance

Use a TABLE with columns: Metric | This Week | YTD 2026
Rows: SEC custody-related releases, CFTC custody/collateral releases, No-action letters, Enforcement actions (custody), Banking regulator guidance.
Then a "Bottom Line" sentence (1–2 lines).

## 🔥 Top Stories

Number each story (1., 2., 3.). For each:
- Title and date/source.
- Key points (bullets).
- Implications: subheadings "Broker-dealers & crypto custodians:", "RIAs & investment funds:", "Banks/trust companies:", "Crypto-native custodians:" with bullets.
- Where possible, cite FACTS with source URL or excerpt; separate ANALYSIS and INFERENCE.

## 📋 Regulatory Tracker Update

Two tables:
1. "Rules & Guidance in effect" — columns: Guidance | Effective | Status | Impact
2. "Pending/Expected developments" — columns: Expected Development | Timeline | Confidence | Source

## ⚖️ Enforcement Watch: Custody Cases

Table: Case | Status | Issue | Next Event
Then a "Trends" paragraph (e.g. no new custody-specific actions; enforcement focused on fraud).

## 🏦 Banking Regulator Corner

If no new guidance: "No guidance was released this week from OCC, FDIC or Federal Reserve on crypto custody."
Include "Key outstanding questions" (bullets). Mention state trust company / written input letters if relevant.

## 🔮 What's Coming

Calendar TABLE: Date | Event | Relevance
Then "Questions We're Tracking" (numbered or bullet list).

## 💡 Compliance Action Items

Actionable bullets (e.g. Engage with Project Crypto; Update policies for tokenisation; Review key management; Monitor written inputs). Use [ ] for checkboxes where appropriate.

## 📚 Resource Library

TABLE: Document / Resource | Date | Description
Include direct SEC.gov links in the table or immediately below.

## 📬 Feedback & Questions
[Short line inviting feedback.]

## About Custody Intelligence Weekly
[One line description.]

---
© 2026 Your Company. All rights reserved. This newsletter is for informational purposes only and does not constitute legal advice. Consult with qualified counsel for advice specific to your situation.
"""


def _parse_classification_json(raw: str) -> List[Any]:
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


# Default search queries (process: "SEC Commissioner Uyeda crypto custody February 2026", etc.)
DEFAULT_SEARCH_QUERIES = [
    "SEC Commissioner crypto custody speech",
    "SEC Chairman custody speech",
    "crypto task force",
    "SEC enforcement custody",
]


def generate_crypto_custody_report_from_urls(
    sec_urls: List[str],
    start_date: str,
    end_date: str,
    *,
    use_crawler: bool = True,
    max_crawl_pages: int = 50,
    crawl_delay: float = 1.5,
    use_keyword_gate: bool = True,
    search_queries: Optional[List[str]] = None,
) -> str:
    """
    Agent-driven SEC-only crypto custody report generator (v3).

    Process (Process: Crypto custody newsletter.pdf):
    1. Define research scope: start_date, end_date, SEC custody.
    2. Search for SEC documents: search_sec_documents(queries, dates) → merge with sec_urls.
    3. Open and navigate: Crawl/fetch SEC pages.
    4. Optional keyword gate: Keep only pages that contain custody keywords.
    5. Capture citations: Extract key-phrase excerpts for FACTS (find_in_document).
    6. Classify: LLM identifies custody-relevant items and tags.
    7. Summarize: Facts (with citations), analysis, inference, audience impacts.
    8. Synthesize: Newsletter matching Crypto custody newsletter result.pdf (tables, numbered stories, footer).
    """
    # 1. Define research scope (start_date, end_date) ✓

    # 2. Search for SEC documents — expand seeds with query-based URLs
    queries = search_queries or DEFAULT_SEARCH_QUERIES
    search_urls = search_sec_documents(queries, start_date, end_date)
    all_seeds = list(dict.fromkeys(sec_urls + search_urls))

    # 3. Fetch documents (open and navigate)
    if use_crawler:
        print(f"Crawling SEC.gov (max_depth=2, max_pages={max_crawl_pages})...")
        documents = crawl_sec_pages(
            seed_urls=all_seeds,
            max_depth=2,
            max_pages=max_crawl_pages,
            delay_seconds=crawl_delay,
        )
        print(f"Crawled {len(documents)} pages.")
    else:
        documents = []
        for url in all_seeds:
            if not url.startswith("https://www.sec.gov"):
                print(f"Skipping non-SEC URL: {url}")
                continue
            try:
                content = fetch_sec_url(url)
                documents.append({"source_url": url, "content": content})
            except Exception as e:
                print(f"Failed to fetch {url}: {e}")
        print(f"Fetched {len(documents)} pages.")

    # 2. Optional keyword gate (pipeline: pass only chunks that hit custody keywords)
    if use_keyword_gate:
        keywords = _load_custody_keywords()
        if keywords:
            before = len(documents)
            documents = _keyword_gate(documents, keywords)
            print(f"Keyword gate: {before} -> {len(documents)} pages (custody keyword hit).")
        else:
            print("Keyword gate skipped (no keywords file or empty).")

    if not documents:
        print("No documents to classify. Returning short placeholder newsletter.")
        return _placeholder_newsletter(start_date, end_date)

    # 4. Capture citations (find_in_document for key phrases — for FACTS in report)
    citations = extract_citations_from_documents(documents, DEFAULT_CUSTODY_PHRASES)
    citations_json = json.dumps(citations[:100], indent=0)  # cap for prompt size

    # 5. Classify in batches
    all_classifications: List[Any] = []
    batch_size = CLASSIFY_BATCH_SIZE
    max_chars = CLASSIFY_MAX_CHARS_PER_DOC
    total_est_cost = 0.0

    for b in range(0, len(documents), batch_size):
        batch = documents[b : b + batch_size]
        batch_payload = [
            {
                "source_url": d["source_url"],
                "content": (d["content"] or "")[:max_chars]
                + ("..." if len(d["content"] or "") > max_chars else ""),
            }
            for d in batch
        ]
        classify_prompt = f"""
You are a regulatory classifier focused ONLY on CRYPTO CUSTODY issues in SEC documents.

From the SEC documents below, identify ONLY items that are relevant to CRYPTO CUSTODY.

Custody relevance means:
- Who can hold customer crypto
- Key management
- Segregation of client assets
- Qualified custodians
- Broker-dealer or RIA custody rules

Return a JSON array. Each element MUST have this exact schema:
{{
  "id": "string - e.g. sec-1, sec-2",
  "date": "string - best-effort YYYY-MM-DD",
  "source_url": "string - one of the URLs provided",
  "source_type": "string - one of: guidance, rule, statement, speech, enforcement, other",
  "short_title": "string - human-readable short title",
  "relevance": true,
  "entity_types": ["BD", "RIA", "bank", "trust", "custodian", "issuer"],
  "topics": ["qualified custodian", "key management", "segregation", "accounting", "collateral", "disclosure", "other"],
  "importance": "critical or high or medium",
  "jurisdiction": "SEC",
  "status": "active or proposed or pending or closed",
  "raw_excerpt": "string - 2–4 sentence excerpt of the most relevant custody language"
}}

Rules:
- Use ONLY the SEC documents provided in this batch.
- If a document has no custody-relevant content, omit it from the array.
- Return ONLY a valid JSON array, no markdown fences, no other text.

SEC_DOCUMENTS (batch {b // batch_size + 1}):
{batch_payload}
"""
        resp = client.responses.create(
            model="gpt-5-mini",
            input=classify_prompt,
            max_output_tokens=10000,
        )
        out = resp.output_text
        _, _, cost = _estimate_tokens_and_cost(
            resp, "gpt-5-mini", classify_prompt, out or "", f"classify batch {b // batch_size + 1}"
        )
        total_est_cost += cost
        arr = _parse_classification_json(out)
        for i, item in enumerate(arr):
            if isinstance(item, dict):
                item["id"] = f"sec-{len(all_classifications) + i + 1}"
                all_classifications.append(item)

    classification = json.dumps(all_classifications)
    print(f"Classification: {len(all_classifications)} custody-relevant item(s).")

    if not all_classifications:
        print("No custody-relevant items. Returning placeholder newsletter.")
        return _placeholder_newsletter(start_date, end_date)

    # 6. Summarize (facts with citations / analysis / inference, audience-specific impacts)
    summarize_prompt = f"""
You are summarizing SEC custody-relevant items that have already been classified.

For EACH item in CLASSIFICATION_OUTPUT (by its "id"), return a JSON object keyed by id.

The JSON MUST look like:
{{
"sec-1": {{
    "facts": "3–7 sentence factual summary. No opinions, no forecasting. Use plain English.",
    "analysis": "2–4 sentences: what this means in context, still grounded in the document.",
    "inference": "1–3 sentences: forward-looking implications / best guess, clearly marked as inference.",
    "impact": {{
    "broker_dealers": ["bullet", "bullet"],
    "rias": ["bullet", "bullet"],
    "banks_trusts": ["bullet", "bullet"],
    "crypto_custodians": ["bullet", "bullet"]
    }}
}},
"sec-2": {{ ... }}
}}

Rules:
- FACTS must be directly supported by the documents.
- ANALYSIS is your interpretation.
- INFERENCE is your forecast or speculation.
- Return ONLY valid JSON, no markdown, no prose outside the JSON.

CLASSIFICATION_OUTPUT:
{classification}
"""

    resp_summary = client.responses.create(
        model="gpt-5-mini",
        input=summarize_prompt,
        max_output_tokens=20000,
    )
    summaries = resp_summary.output_text
    _, _, cost = _estimate_tokens_and_cost(resp_summary, "gpt-5-mini", summarize_prompt, summaries or "", "summarize")
    total_est_cost += cost

    # 7. Synthesize (full newsletter matching Crypto custody newsletter result.pdf)
    synthesize_prompt = f"""
{BASE_NEWSLETTER_SYSTEM_PROMPT}

YOUR TASK:

Generate a weekly Crypto Custody Intelligence newsletter in MARKDOWN format that matches
the structure and style of "Crypto custody newsletter result.pdf". Use ONLY sources from
sec.gov for the week {start_date} - {end_date}.

Requirements:
- Follow the REQUIRED NEWSLETTER STRUCTURE above exactly: tables for This Week at a Glance
  (Metric | This Week | YTD 2026 + Bottom Line), numbered Top Stories with Implications
  by entity, Regulatory Tracker (two tables), Enforcement Watch (table + Trends),
  Banking Regulator Corner, What's Coming (calendar table + Questions We're Tracking),
  Compliance Action Items, Resource Library (table with links), and the footer disclaimer.
- For FACTS, cite source URLs or short excerpts where possible (use the citations list below).
- Clearly separate FACTS, ANALYSIS, and INFERENCE. Do not invent documents not in the inputs.

INPUT DATA (machine-readable):
- classification (JSON array of items): {classification}
- summaries (JSON keyed by id): {summaries}
- citations (source_url, phrase, excerpt for key custody phrases): {citations_json}

Output:
- A single complete newsletter in Markdown, ready to save as a .md file. Use proper markdown tables.
"""

    resp_newsletter = client.responses.create(
        model="gpt-5.2",
        reasoning={"effort": "high"},
        input=synthesize_prompt,
        max_output_tokens=100000,
    )
    newsletter_text = resp_newsletter.output_text
    _, _, cost = _estimate_tokens_and_cost(
        resp_newsletter, "gpt-5.2", synthesize_prompt, newsletter_text or "", "synthesize"
    )
    total_est_cost += cost
    print(f"  Total est. cost (this run): ${total_est_cost:.4f}")

    return newsletter_text or _placeholder_newsletter(start_date, end_date)


def _placeholder_newsletter(start_date: str, end_date: str) -> str:
    """Return a minimal newsletter when no data or no relevant items (structure matches result PDF)."""
    return f"""# 🔐 Custody Intelligence Weekly
## The Regulatory Digest for Crypto Custodians
### Week of **{start_date} – {end_date}** | Issue #1

No SEC custody-relevant items were identified for this date range.

## 📊 This Week at a Glance

| Metric | This Week | YTD 2026 |
|--------|-----------|----------|
| SEC custody-related releases | 0 | 0 |
| CFTC custody/collateral releases | 0 | 0 |
| No-action letters | 0 | 0 |
| Enforcement actions (custody) | 0 | 0 |
| Banking regulator guidance | 0 | 0 |

**Bottom Line:** No new custody items in range. Run the agent with a broader crawl or different dates.

## 🔥 Top Stories

(No items this week.)

## 📋 Regulatory Tracker Update

*Rules & Guidance in effect:* (None this week.)
*Pending/Expected:* (None.)

## ⚖️ Enforcement Watch: Custody Cases

| Case | Status | Issue | Next Event |
|------|--------|-------|------------|
| (None this week.) |

**Trends:** No new custody-specific actions in range.

## 🏦 Banking Regulator Corner

No guidance was released this week from OCC, FDIC or Federal Reserve on crypto custody.

## 🔮 What's Coming

| Date | Event | Relevance |
|------|-------|-----------|
| — | Monitor SEC crypto task force | Updates on custody guidance |

## 💡 Compliance Action Items

- [ ] Continue monitoring SEC custody guidance and enforcement.
- [ ] Review existing controls (key management, segregation, disclosures).

## 📚 Resource Library

| Document / Resource | Date | Description |
|---------------------|------|-------------|
| [SEC Crypto Task Force](https://www.sec.gov/featured-topics/crypto-task-force) | — | Custody-related aggregation |
| [SEC Speeches & Statements](https://www.sec.gov/newsroom/speeches-statements) | — | Commissioner and Chair remarks |

## 📬 Feedback & Questions

Send questions: Entity type | Custody model | What changed | Your question.

## About Custody Intelligence Weekly

A weekly digest of SEC regulatory and enforcement developments affecting crypto custody.

---
© 2026 Your Company. All rights reserved. This newsletter is for informational purposes only and does not constitute legal advice. Consult with qualified counsel for advice specific to your situation.
"""


def write_newsletter_sync(content: str, path: str) -> str:
    """
    Write the newsletter to a file and return its path (process: Create Markdown file; sync for download).
    """
    p = Path(path)
    p.write_text(content, encoding="utf-8")
    print(f"  Synced: {p.resolve()}")
    return str(p.resolve())


if __name__ == "__main__":
    sec_urls = [
        "https://www.sec.gov/featured-topics/crypto-task-force",
        "https://www.sec.gov/about/divisions-offices/division-trading-markets",
        "https://www.sec.gov/about/divisions-offices/division-investment-management",
        "https://www.sec.gov/newsroom/speeches-statements",
        "https://www.sec.gov/enforcement-litigation/litigation-releases",
        "https://www.sec.gov/rules-regulations/rulemaking-activity",
    ]

    start_date = "2026-02-03"
    end_date = "2026-02-09"

    print("Generating Crypto Custody Intelligence newsletter (v3)...")
    report = generate_crypto_custody_report_from_urls(
        sec_urls=sec_urls,
        start_date=start_date,
        end_date=end_date,
        use_crawler=True,
        max_crawl_pages=150,
        crawl_delay=1.5,
        use_keyword_gate=True,
    )

    output_path = "custody_newsletter_v2_1.md"
    write_newsletter_sync(report, output_path)
    print(f"\nNewsletter ready for download: {output_path}\n")
