"""
Tools for the Crypto Custody Newsletter Agent (v3).

Aligned with Process: Crypto custody newsletter.pdf:
- search_sec_documents: Simulates browser.search — returns SEC URLs to check for a given week/queries.
- find_in_document: Simulates browser.find — locate key phrases within document content for citations.
- format_citation: Build citation strings (source_url + optional excerpt) for FACTS in the report.
"""

import re
from typing import List, Tuple

# Canonical SEC custody-relevant entry points (from custody-agent-source.txt and process PDF)
SEC_SPEECHES_STATEMENTS = "https://www.sec.gov/newsroom/speeches-statements"
SEC_CRYPTO_TASK_FORCE = "https://www.sec.gov/featured-topics/crypto-task-force"
SEC_CRYPTO_TASK_FORCE_WRITTEN_INPUT = "https://www.sec.gov/featured-topics/crypto-task-force/crypto-task-force-written-input"
SEC_TRADING_MARKETS = "https://www.sec.gov/about/divisions-offices/division-trading-markets"
SEC_INVESTMENT_MGMT = "https://www.sec.gov/about/divisions-offices/division-investment-management"
SEC_LITIGATION_RELEASES = "https://www.sec.gov/enforcement-litigation/litigation-releases"
SEC_RULEMAKING = "https://www.sec.gov/rules-regulations/rulemaking-activity"
SEC_STAFF_GUIDANCE_FAQ = "https://www.sec.gov/rules-regulations/staff-guidance/trading-markets-frequently-asked-questions"

# Custody phrases to find in documents for citations (process: browser.find)
DEFAULT_CUSTODY_PHRASES = [
    "qualified custodian",
    "key management",
    "physical possession",
    "custody",
    "segregation",
    "Rule 15c3-3",
    "Rule 206(4)-2",
    "tokenisation",
    "tokenization",
    "Project Crypto",
    "digital asset",
    "crypto asset",
]


def search_sec_documents(
    queries: List[str],
    start_date: str,
    end_date: str,
) -> List[str]:
    """
    Simulate browser.search: return SEC.gov URLs to fetch for the given week and search themes.

    Process step: "Search for SEC documents" — agent focuses on speeches, task force, enforcement.
    Does not perform live web search; returns canonical SEC custody entry points plus any
    query-specific paths (e.g. speeches-statements for Commissioner/Chairman speeches).
    """
    urls = [
        SEC_CRYPTO_TASK_FORCE,
        SEC_CRYPTO_TASK_FORCE_WRITTEN_INPUT,
        SEC_SPEECHES_STATEMENTS,
        SEC_TRADING_MARKETS,
        SEC_INVESTMENT_MGMT,
        SEC_LITIGATION_RELEASES,
        SEC_RULEMAKING,
    ]
    q_lower = " ".join(queries).lower()
    if any(
        x in q_lower
        for x in (
            "speech",
            "commissioner",
            "chairman",
            "uyeda",
            "atkins",
            "statement",
            "remark",
        )
    ):
        if SEC_SPEECHES_STATEMENTS not in urls:
            urls.append(SEC_SPEECHES_STATEMENTS)
    if any(x in q_lower for x in ("enforcement", "litigation", "action")):
        urls.append(SEC_LITIGATION_RELEASES)
    if any(x in q_lower for x in ("task force", "written input", "roundtable")):
        urls.append(SEC_CRYPTO_TASK_FORCE)
        urls.append(SEC_CRYPTO_TASK_FORCE_WRITTEN_INPUT)
    return list(dict.fromkeys(urls))  # dedupe order-preserving


def find_in_document(
    content: str,
    phrases: List[str],
    context_chars: int = 300,
) -> List[Tuple[str, str]]:
    """
    Simulate browser.find: locate each phrase in content and return (phrase, excerpt) for citations.

    Process step: "For long documents, browser.find was called to search within the page for
    key phrases ('digital asset securities,' 'qualified custodian,' 'key management controls')."
    """
    if not content or not phrases:
        return []
    content_lower = content.lower()
    results: List[Tuple[str, str]] = []
    for phrase in phrases:
        p_lower = phrase.lower()
        start = content_lower.find(p_lower)
        if start == -1:
            continue
        # Extract surrounding context
        from_start = max(0, start - context_chars)
        to_end = min(len(content), start + len(phrase) + context_chars)
        excerpt = content[from_start:to_end]
        excerpt = " ".join(excerpt.split())
        if excerpt and (phrase, excerpt) not in results:
            results.append((phrase, excerpt))
    return results


def format_citation(source_url: str, excerpt: str = "", line_ref: str = "") -> str:
    """
    Build a citation string for the report (process: "record citations using line numbers").
    In our pipeline we use source_url + optional excerpt; line_ref can be filled if we add line numbering.
    """
    parts = [source_url]
    if line_ref:
        parts.append(f" (ref: {line_ref})")
    if excerpt:
        short = excerpt[:200] + "..." if len(excerpt) > 200 else excerpt
        parts.append(f" — \"{short}\"")
    return "".join(parts)


def extract_citations_from_documents(
    documents: List[dict],
    phrases: List[str] = None,
) -> List[dict]:
    """
    Run find_in_document on each document and return list of {source_url, phrase, excerpt}
    for use in summarization/synthesis (FACTS must be accompanied by citations).
    """
    phrases = phrases or DEFAULT_CUSTODY_PHRASES
    out = []
    for d in documents:
        url = d.get("source_url") or ""
        content = d.get("content") or ""
        for phrase, excerpt in find_in_document(content, phrases):
            out.append({"source_url": url, "phrase": phrase, "excerpt": excerpt})
    return out
