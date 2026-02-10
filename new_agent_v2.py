import json
import re
from typing import Any, List, Tuple

from dotenv import load_dotenv
from openai import OpenAI

from new_tools import fetch_sec_url
from new_crawler_tool import crawl_sec_pages

load_dotenv()

client = OpenAI()

# Keep classify prompt within context: small batches + cap per-doc content
CLASSIFY_BATCH_SIZE = 8
CLASSIFY_MAX_CHARS_PER_DOC = 8000

# Approximate $ per 1M tokens (input, output) for cost estimate. Update from platform.openai.com/pricing.
MODEL_COST_PER_1M = {
    "gpt-5-mini": (0.25, 2.00),
    "gpt-5.2": (1.75, 14.00),
    "gpt-5": (1.25, 10.00),  # optional, for completeness
}



def _estimate_tokens_and_cost(
    response: Any,
    model: str,
    input_str: str,
    output_str: str,
    step_name: str = "call",
) -> Tuple[int, int, float]:
    """Get token counts from response.usage or estimate from text. Compute cost. Print and return (in_tok, out_tok, cost)."""
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

# Pulled from example-run-prompt.txt – truncated if needed, but should
# capture the role, goals, capabilities, output expectations, and sample layout.
BASE_NEWSLETTER_SYSTEM_PROMPT = """
You are a “Crypto Custody Regulatory Intelligence Agent.”

GOAL
Your goal is to continuously monitor, summarize, and explain all regulatory developments that affect **crypto custody** – i.e., who can legally hold customer crypto assets, under what rules, and with what controls – for broker‑dealers, RIAs, banks/trust companies, and specialized crypto custodians.

DATA YOU SHOULD USE (AND EXPECT TO RECEIVE)

You are powered by structured and unstructured data from:

- SEC CUSTODY SOURCES (sec.gov)
   - Staff Accounting Bulletins related to crypto custody (e.g., SAB 121/122)
   - Division of Trading & Markets statements and FAQs on:
     - Rule 15c3‑3 (customer protection / “control” and “physical possession”)
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
     - “What this means for broker‑dealers”
     - “What this means for RIAs”
     - “What this means for banks/trust companies”
     - “What this means for crypto‑native custodians”
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
   - Given the past week’s new items:
     - Write a weekly newsletter‑style summary:
       - “This Week at a Glance” metrics
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

SAMPLE NEWSLETTER STRUCTURE (FOLLOW THIS LAYOUT, BUT FILL WITH NEW CONTENT):

# 🔐 Custody Intelligence Weekly

## The Regulatory Digest for Crypto Custodians

### Week of [DATE RANGE] | Issue #[N]

## 📊 This Week at a Glance

## 🔥 Top Story

## 📋 Regulatory Tracker Update

## ⚖️ Enforcement Watch: Custody Cases

## 🏦 Banking Regulator Corner

## 🔮 What's Coming

## 💡 Compliance Action Items

## 📚 Resource Library

## 📬 Feedback & Questions

## About Custody Intelligence Weekly
"""


def generate_crypto_custody_report_from_urls(
    sec_urls: List[str],
    start_date: str,
    end_date: str,
    *,
    use_crawler: bool = True,
    max_crawl_pages: int = 50,
    crawl_delay: float = 1.5,
) -> str:
    """
    Agent-driven SEC-only crypto custody report generator.

    If use_crawler is True (default), crawls SEC.gov from seed URLs up to 2 levels
    deep (max_crawl_pages, rate-limited by crawl_delay). Otherwise fetches only
    the seed URLs.
    """

    def _parse_classification_json(raw: str) -> List[Any]:
        """Extract a JSON array from model output (may be wrapped in markdown)."""
        raw = raw.strip()
        # Strip ```json ... ``` or ``` ... ```
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```\s*$", "", raw)
        # Find first [ and last ]
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

    # 1. Fetch documents (crawl 1–2 levels from seeds, or single-page fetch)
    if use_crawler:
        print(f"Crawling SEC.gov (max_depth=2, max_pages={max_crawl_pages})...")
        documents = crawl_sec_pages(
            seed_urls=sec_urls,
            max_depth=2,
            max_pages=max_crawl_pages,
            delay_seconds=crawl_delay,
        )
        print(f"Crawled {len(documents)} pages.")
    else:
        documents = []
        for url in sec_urls:
            if not url.startswith("https://www.sec.gov"):
                print(f"Skipping non-SEC URL: {url}")
                continue
            try:
                content = fetch_sec_url(url)
                documents.append({"source_url": url, "content": content})
            except Exception as e:
                print(f"Failed to fetch {url}: {e}")

    # 2. CLASSIFY in batches (avoids 100k+ token prompt; each batch ~20–30k tokens)
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
                + ("..." if len((d["content"] or "")) > max_chars else ""),
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
        _, _, cost = _estimate_tokens_and_cost(resp, "gpt-5-mini", classify_prompt, out or "", f"classify batch {b // batch_size + 1}")
        total_est_cost += cost
        arr = _parse_classification_json(out)
        for i, item in enumerate(arr):
            if isinstance(item, dict):
                item["id"] = f"sec-{len(all_classifications) + i + 1}"
                all_classifications.append(item)
    classification = json.dumps(all_classifications)
    print(f"Classification: {len(all_classifications)} custody-relevant item(s).")

    # 3. SUMMARIZE (facts / analysis / inference, audience-specific impacts)
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

    # 4. SYNTHESIZE (full newsletter in the sample structure)
    synthesize_prompt = f"""
    {BASE_NEWSLETTER_SYSTEM_PROMPT}

    YOUR TASK:

    Generate a weekly Crypto Custody Intelligence newsletter in MARKDOWN format,
    using ONLY sources from sec.gov for the week {start_date} - {end_date}.

    Requirements:
    - Follow the "Custody Intelligence Weekly" structure from the sample newsletter.
    - Include: "This Week at a Glance", Top stories, Regulatory Tracker tables,
    Enforcement Watch, Banking Corner, What's Coming, Compliance Action Items,
    and a short Resource Library section.
    - Clearly separate FACTS, ANALYSIS, and INFERENCE where applicable.
    - Use only the classification and summaries provided below – do NOT invent new documents.

    INPUT DATA (machine-readable):
    - classification (JSON array of items): {classification}
    - summaries (JSON keyed by id): {summaries}

    Output:
    - A single complete newsletter in Markdown, ready to save as a .md file.
    """

    resp_newsletter = client.responses.create(
        model="gpt-5.2",
        reasoning={"effort": "high"},
        input=synthesize_prompt,
        max_output_tokens=100000,
    )
    newsletter_text = resp_newsletter.output_text
    _, _, cost = _estimate_tokens_and_cost(resp_newsletter, "gpt-5.2", synthesize_prompt, newsletter_text or "", "synthesize")
    total_est_cost += cost
    print(f"  Total est. cost (this run): ${total_est_cost:.4f}")

    return newsletter_text


if __name__ == "__main__":
    # Example SEC URLs for crypto custody–related content
    sec_urls = [
        "https://www.sec.gov/featured-topics/crypto-task-force",
        "https://www.sec.gov/about/divisions-offices/division-trading-markets",
        "https://www.sec.gov/about/divisions-offices/division-investment-management",
        # SEC.gov sources
        "https://www.sec.gov/newsroom/speeches-statements",
        "https://www.sec.gov/enforcement-litigation/litigation-releases",
        "https://www.sec.gov/rules-regulations/rulemaking-activity",
        
        # CFTC.gov sources
        # "https://www.cftc.gov/PressRoom/PressReleases",
        # "https://www.cftc.gov/LawRegulation/CFTCStaffLetters/index.htm",
        # "https://www.cftc.gov/LawRegulation/CFTCStaffLetters/letters.htm",
        
        # # Banking Regulators - OCC
        # "https://www.occ.treas.gov/topics/charters-and-licensing/interpretations-and-actions/index-interpretations-and-actions.html",
        
        # # Banking Regulators - FDIC
        # "https://www.fdic.gov/bank-examinations/laws-regulations-and-supervisory-guidance",
        
        # # Banking Regulators - Federal Reserve
        # "https://www.federalreserve.gov/supervisionreg/topics/topics.htm",
        
        # # State banking - NYDFS
        # "https://www.dfs.ny.gov/virtual_currency_businesses",
        # "https://www.dfs.ny.gov/industry_guidance/industry_letters",
        # "https://www.dfs.ny.gov/industry_guidance/enforcement_actions",
        
        # # State banking - Wyoming SPDI
        # "https://wyomingbankingdivision.wyo.gov/banks-and-trust-companies/special-purpose-depository-institutions",
    ]

    # Example week – adjust to target week as needed
    start_date = "2026-02-03"
    end_date = "2026-02-09"

    print("Generating Crypto Custody Intelligence newsletter...")
    report = generate_crypto_custody_report_from_urls(
        sec_urls=sec_urls,
        start_date=start_date,
        max_crawl_pages=150,
        end_date=end_date,
    )

    # Save as markdown file for download/sharing
    output_path = "custody_newsletter_v4.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\nNewsletter written to {output_path}\n")

