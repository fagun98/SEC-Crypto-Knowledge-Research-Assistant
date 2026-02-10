from typing import List

from openai import OpenAI

from new_tools import fetch_sec_url

client = OpenAI()

def generate_crypto_custody_report_from_urls(
    sec_urls: List[str],
    start_date: str,
    end_date: str
) -> str:
    """
    Agent-driven SEC-only crypto custody report generator.
    """

    # 1. Fetch documents
    documents = []
    for url in sec_urls:
        try:
            content = fetch_sec_url(url)
            documents.append({
                "source_url": url,
                "content": content
            })
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")

    # 2. CLASSIFY
    classify_prompt = f"""
You are a regulatory classifier.

From the SEC documents below, identify ONLY items that are
relevant to CRYPTO CUSTODY.

Custody relevance means:
- Who can hold customer crypto
- Key management
- Segregation
- Qualified custodians
- Broker-dealer or RIA custody rules

Return JSON list with:
- source_url
- relevance (true/false)
- entity_types
- topics
- importance (critical/high/medium)

SEC DOCUMENTS:
{documents}
"""

    classification = client.responses.create(
        model="gpt-5-mini",
        input=classify_prompt,
        max_output_tokens=4000
    ).output_text

    # 3. SUMMARIZE (facts only)
    summarize_prompt = f"""
Using ONLY the custody-relevant items identified below,
write FACTUAL summaries.

Rules:
- No opinions
- No forecasting
- Cite SEC language accurately

CLASSIFICATION OUTPUT:
{classification}
"""

    summaries = client.responses.create(
        model="gpt-5-mini",
        input=summarize_prompt,
        max_output_tokens=6000
    ).output_text

    # 4. SYNTHESIZE (newsletter)
    synthesize_prompt = f"""
You are a Crypto Custody Regulatory Intelligence Agent.

Using the factual summaries below, generate a WEEKLY
Crypto Custody Intelligence newsletter for:

{start_date} to {end_date}

You MUST:
- Separate FACTS / ANALYSIS / INFERENCE
- Explain impact for BD, RIA, Bank, Custodian
- Include tracker table and compliance actions
- Use plain English
- Format as Markdown

SUMMARIES:
{summaries}
"""

    newsletter = client.responses.create(
        model="gpt-5.2",
        reasoning={"effort": "high"},
        input=synthesize_prompt,
        max_output_tokens=12000
    )

    return newsletter.output_text


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
        "https://www.cftc.gov/PressRoom/PressReleases",
        "https://www.cftc.gov/LawRegulation/CFTCStaffLetters/index.htm",
        "https://www.cftc.gov/LawRegulation/CFTCStaffLetters/letters.htm",
        
        # Banking Regulators - OCC
        "https://www.occ.treas.gov/topics/charters-and-licensing/interpretations-and-actions/index-interpretations-and-actions.html",
        
        # Banking Regulators - FDIC
        "https://www.fdic.gov/bank-examinations/laws-regulations-and-supervisory-guidance",
        
        # Banking Regulators - Federal Reserve
        "https://www.federalreserve.gov/supervisionreg/topics/topics.htm",
        
        # State banking - NYDFS
        "https://www.dfs.ny.gov/virtual_currency_businesses",
        "https://www.dfs.ny.gov/industry_guidance/industry_letters",
        "https://www.dfs.ny.gov/industry_guidance/enforcement_actions",
        
        # State banking - Wyoming SPDI
        "https://wyomingbankingdivision.wyo.gov/banks-and-trust-companies/special-purpose-depository-institutions",
    ]

    start_date = "2025-02-03"
    end_date = "2025-02-09"

    print("Generating Crypto Custody Intelligence report...")
    report = generate_crypto_custody_report_from_urls(sec_urls, start_date, end_date)
    print("\n" + "=" * 80 + "\n")
    print(report)

