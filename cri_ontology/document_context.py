from __future__ import annotations

import csv
import json
import re
import urllib.parse
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup


def infer_source_type_from_url(url: str, doc_type: Optional[str] = None) -> str:
    """
    Best-effort SEC-centric source_type inference from URL patterns.
    Returns a short string label (not part of ontology; used as document context).
    """
    u = (url or "").lower()
    if doc_type == "pdf" or u.endswith(".pdf"):
        return "pdf"

    # SEC newsroom
    if "/newsroom/speeches-statements/" in u:
        return "speech_or_statement"
    if "/newsroom/press-releases/" in u:
        return "press_release"
    if "/enforcement-litigation/litigation-releases" in u or "/litigation-releases/" in u:
        return "litigation_release"

    # Rulemaking / staff guidance
    if "/rules-regulations/rulemaking-activity" in u or "/rules-regulations/" in u:
        return "rulemaking"
    if "/staff-guidance/" in u and "frequently-asked-questions" in u:
        return "faq"
    if "/staff-guidance/" in u:
        return "staff_guidance"

    # Crypto task force pages
    if "/about/crypto-task-force/roundtable" in u:
        return "roundtable"
    if "/about/crypto-task-force/written-submission" in u:
        return "written_submission"

    # Frameworks / corp fin pages
    if "framework" in u and "/division-corporation-finance/" in u:
        return "framework"

    return "webpage"


def _sec_headers() -> Dict[str, str]:
    return {
        "User-Agent": "Custody-Intelligence-Agent/1.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }


def _looks_like_pdf_url(url: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(url)
        return parsed.path.lower().endswith(".pdf")
    except Exception:
        return False


def _fetch_endpoint(url: str, *, timeout: int = 20) -> Tuple[str, bytes, str]:
    """
    Fetch an endpoint and return (doc_type, raw_bytes, final_url).

    doc_type is one of: "html", "pdf".
    """
    import requests

    resp = requests.get(url, headers=_sec_headers(), timeout=timeout, allow_redirects=True)
    resp.raise_for_status()
    content_type = (resp.headers.get("Content-Type") or "").lower()
    final_url = str(getattr(resp, "url", url) or url)

    if "pdf" in content_type or _looks_like_pdf_url(final_url):
        return "pdf", resp.content, final_url
    return "html", resp.content, final_url


def _extract_title_and_text_from_html(url: str, html: str) -> Tuple[str, str]:
    soup = BeautifulSoup(html or "", "html.parser")

    # Prefer the SEC content container when present.
    root = soup.select_one("div.content-wrapper") or soup

    # Title heuristics: prefer page H1 inside the content wrapper.
    h1 = None
    if root is not soup:
        h1 = root.select_one("h1.page-title__heading") or root.find("h1")
    if not h1:
        h1 = soup.select_one("h1.page-title__heading") or soup.find("h1")
    if h1 and h1.get_text(strip=True):
        title = h1.get_text(" ", strip=True)
    else:
        title = soup.title.string.strip() if soup.title and soup.title.string else url

    # Within content-wrapper, try to extract the main article region first.
    main_region = None
    if root is not soup:
        main_region = (
            root.select_one("div.node-details-layout__main-region__content")
            or root.select_one(".field--name-body")
            or root
        )
    else:
        main_region = root

    # Remove non-content elements, but only from the chosen subtree.
    for tag in main_region.find_all(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()

    text = " ".join(main_region.get_text(separator=" ", strip=True).split())

    # Fallback: if subtree selection produced almost nothing, fall back to whole page.
    if len(text) < 200:
        for tag in soup.find_all(["script", "style", "noscript", "header", "footer", "nav"]):
            tag.decompose()
        text = " ".join(soup.get_text(separator=" ", strip=True).split())

    return title, text


def _extract_text_from_pdf_bytes(content: bytes, *, max_pages: int = 3) -> Tuple[str, str]:
    pages = _extract_pdf_pages_from_bytes(content, max_pages=max_pages)
    if not pages:
        return "PDF Document", ""
    title = "PDF Document"
    return title, "\n".join(text for _, text in pages)


def _extract_pdf_pages_from_bytes(
    content: bytes, *, max_pages: int = 3
) -> List[Tuple[int, str]]:
    """Return list of (page_number, text). max_pages=0 means all pages."""
    from io import BytesIO

    try:
        from pypdf import PdfReader
    except Exception as e:  # pragma: no cover
        raise RuntimeError("Missing dependency: pypdf is required to parse PDF endpoints.") from e

    reader = PdfReader(BytesIO(content))
    n_pages = len(reader.pages)
    n = min(n_pages, max_pages if max_pages > 0 else n_pages)
    out: List[Tuple[int, str]] = []
    for i in range(n):
        page = reader.pages[i]
        txt = page.extract_text() or ""
        txt = " ".join(txt.split())
        if txt:
            out.append((i + 1, txt))
    return out


def _cap_text(text: str, *, max_chars: int) -> str:
    if not isinstance(text, str):
        return ""
    if max_chars <= 0:
        return text.strip()
    return text[:max_chars].strip()


def _parse_iso_date(s: str) -> Optional[str]:
    ss = (s or "").strip()
    if not ss:
        return None
    # Keep YYYY-MM-DD when possible.
    try:
        # Handle full ISO timestamps too.
        dt = datetime.fromisoformat(ss.replace("Z", "+00:00"))
        return dt.date().isoformat()
    except Exception:
        return None


def extract_publication_date_from_html(html: str) -> Optional[str]:
    """
    Best-effort extract publication date from SEC HTML using common meta tags and time elements.
    Returns ISO date string (YYYY-MM-DD) when found, else None.
    """
    if not html or not html.strip():
        return None
    soup = BeautifulSoup(html, "html.parser")

    # Common meta tags.
    candidates: List[str] = []
    for key in [
        ("meta", {"property": "article:published_time"}),
        ("meta", {"name": "article:published_time"}),
        ("meta", {"name": "pubdate"}),
        ("meta", {"name": "publishdate"}),
        ("meta", {"name": "date"}),
        ("meta", {"property": "og:updated_time"}),
        ("meta", {"name": "dcterms.date"}),
        ("meta", {"name": "dc.date"}),
    ]:
        tag = soup.find(key[0], attrs=key[1])
        if tag and tag.get("content"):
            candidates.append(str(tag.get("content")))

    # <time datetime="...">
    time_tag = soup.find("time")
    if time_tag:
        dt = time_tag.get("datetime")
        if dt:
            candidates.append(str(dt))
        else:
            candidates.append(time_tag.get_text(" ", strip=True))

    # Look for a visible date pattern in the page text (fallback).
    text = soup.get_text(" ", strip=True)
    m = re.search(r"\b(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b", text)
    if m:
        yyyy, mm, dd = m.group(1), m.group(2).zfill(2), m.group(3).zfill(2)
        candidates.append(f"{yyyy}-{mm}-{dd}")

    for c in candidates:
        iso = _parse_iso_date(c)
        if iso:
            return iso

    return None


def build_document_context_from_metadata(meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalized document context object passed to the LLM classifier.
    """
    if not isinstance(meta, dict):
        return {}
    out: Dict[str, Any] = {}

    title = meta.get("title") or meta.get("document_title")
    if isinstance(title, str) and title.strip():
        out["document_title"] = title.strip()

    source_url = meta.get("source_url") or meta.get("document_url")
    if isinstance(source_url, str) and source_url.strip():
        out["source_url"] = source_url.strip()

    publication_date = meta.get("publication_date")
    if isinstance(publication_date, str) and publication_date.strip():
        out["publication_date"] = publication_date.strip()

    source_type = meta.get("source_type")
    if isinstance(source_type, str) and source_type.strip():
        out["source_type"] = source_type.strip()

    reg_body = meta.get("regulatory_body")
    if isinstance(reg_body, list) and reg_body:
        out["regulatory_body"] = [str(x) for x in reg_body if str(x).strip()]

    # Keep doc_type/page if present (helps infer “pdf page”, etc.)
    doc_type = meta.get("type") or meta.get("doc_type")
    if isinstance(doc_type, str) and doc_type.strip():
        out["source_doc_type"] = doc_type.strip()
    page = meta.get("page")
    if isinstance(page, (int, str)) and str(page).strip():
        out["page"] = page

    return out


def fetch_sec_document(
    url: str,
    *,
    max_html_chars: Optional[int] = None,
    max_pdf_pages: int = 0,
    timeout_seconds: int = 20,
    regulatory_body_default: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch an SEC HTML or PDF endpoint and return one dict per logical page.

    Each dict includes: final_url, doc_type, title, full_text, page (int or None),
    publication_date, source_type, document_context.

    max_pdf_pages=0 extracts all PDF pages. max_html_chars=None keeps full HTML text.
    """
    doc_type, raw_bytes, final_url = _fetch_endpoint(url, timeout=timeout_seconds)
    reg_body = regulatory_body_default or (
        ["SEC"] if "sec.gov" in (final_url or "").lower() else []
    )
    source_type = infer_source_type_from_url(final_url, doc_type=doc_type)
    pages_out: List[Dict[str, Any]] = []

    if doc_type == "pdf":
        for page_num, text in _extract_pdf_pages_from_bytes(
            raw_bytes, max_pages=max_pdf_pages
        ):
            full_text = text.strip()
            if max_html_chars is not None and max_html_chars > 0:
                full_text = _cap_text(full_text, max_chars=max_html_chars)
            if not full_text:
                continue
            title = f"PDF Document (page {page_num})"
            document_context: Dict[str, Any] = {
                "document_title": title,
                "source_url": final_url,
                "publication_date": "",
                "source_type": source_type,
                "regulatory_body": reg_body,
                "source_doc_type": doc_type,
                "page": page_num,
            }
            pages_out.append(
                {
                    "final_url": final_url,
                    "doc_type": doc_type,
                    "title": title,
                    "full_text": full_text,
                    "page": page_num,
                    "publication_date": "",
                    "source_type": source_type,
                    "document_context": document_context,
                }
            )
    else:
        html = raw_bytes.decode("utf-8", errors="replace")
        title, full_text = _extract_title_and_text_from_html(final_url, html)
        publication_date = extract_publication_date_from_html(html) or ""
        if max_html_chars is not None and max_html_chars > 0:
            full_text = _cap_text(full_text, max_chars=max_html_chars)
        full_text = full_text.strip()
        if not full_text:
            return pages_out
        document_context = {
            "document_title": title,
            "source_url": final_url,
            "publication_date": publication_date,
            "source_type": source_type,
            "regulatory_body": reg_body,
            "source_doc_type": doc_type,
        }
        pages_out.append(
            {
                "final_url": final_url,
                "doc_type": doc_type,
                "title": title,
                "full_text": full_text,
                "page": None,
                "publication_date": publication_date,
                "source_type": source_type,
                "document_context": document_context,
            }
        )

    return pages_out


def classify_endpoint_to_metadata(
    url: str,
    *,
    max_html_chars: int = 12_000,
    max_pdf_pages: int = 3,
    timeout_seconds: int = 20,
    regulatory_body_default: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Fetch an endpoint (HTML/PDF), extract best-effort context, and classify the content
    under the CRI regulatory ontology.

    Returns a flat dict intended to be CSV-serializable (lists are JSON strings).
    """
    from cri_ontology.classifier import classify_chunk
    from cri_ontology.validate import validate_classification

    out: Dict[str, Any] = {
        "url": url,
        "title": "",
        "doc_type": "",
        "source_type": "",
        "publication_date": "",
        "regulatory_body": json.dumps(
            regulatory_body_default
            or (["SEC"] if "sec.gov" in (url or "").lower() else []),
            ensure_ascii=False,
        ),
        "domain_primary": "",
        "domain_secondary": "[]",
        "subdomain": "[]",
        "lifecycle_stage": "",
        "durability_tier": "",
        "validation_status": "",
        "confidence_domain_primary": "",
        "confidence_subdomain": "",
        "confidence_lifecycle_stage": "",
        "confidence_durability_tier": "",
        "classification_reason": "",
        "error": "",
    }

    try:
        doc_type, raw_bytes, final_url = _fetch_endpoint(url, timeout=timeout_seconds)
        out["url"] = final_url
        out["doc_type"] = doc_type

        if doc_type == "pdf":
            title, full_text = _extract_text_from_pdf_bytes(raw_bytes, max_pages=max_pdf_pages)
            publication_date = ""
            capped_text = _cap_text(full_text, max_chars=max_html_chars)
        else:
            html = raw_bytes.decode("utf-8", errors="replace")
            title, full_text = _extract_title_and_text_from_html(final_url, html)
            publication_date = extract_publication_date_from_html(html) or ""
            capped_text = _cap_text(full_text, max_chars=max_html_chars)
        
        out["title"] = title
        out["publication_date"] = publication_date
        out["source_type"] = infer_source_type_from_url(final_url, doc_type=doc_type)

        document_context = {
            "document_title": title,
            "source_url": final_url,
            "publication_date": publication_date,
            "source_type": out["source_type"],
            "regulatory_body": json.loads(out["regulatory_body"]),
            "source_doc_type": doc_type,
        }

        try:
            classified = classify_chunk(capped_text, document_context=document_context)
        except Exception:
            # Retry once with a shorter excerpt for better formatting compliance.
            shorter = _cap_text(capped_text, max_chars=min(4000, len(capped_text)))
            classified = classify_chunk(shorter, document_context=document_context)

        normalized, errors = validate_classification(classified)

        out["domain_primary"] = normalized.get("domain_primary", "") or ""
        out["domain_secondary"] = json.dumps(normalized.get("domain_secondary") or [], ensure_ascii=False)
        out["subdomain"] = json.dumps(normalized.get("subdomain") or [], ensure_ascii=False)
        out["lifecycle_stage"] = normalized.get("lifecycle_stage", "") or ""
        out["durability_tier"] = normalized.get("durability_tier", "") or ""
        out["validation_status"] = normalized.get("validation_status", "") or ""
        out["classification_reason"] = normalized.get("reasoning_summary", "") or ""

        conf = normalized.get("confidence") or {}
        if isinstance(conf, dict):
            out["confidence_domain_primary"] = conf.get("domain_primary", "")
            out["confidence_subdomain"] = conf.get("subdomain", "")
            out["confidence_lifecycle_stage"] = conf.get("lifecycle_stage", "")
            out["confidence_durability_tier"] = conf.get("durability_tier", "")

        if errors:
            out["error"] = f"validation_errors={errors[:20]}"
    except Exception as e:
        out["error"] = str(e)[:500]

    return out


def _write_metadata_csv(rows: List[Dict[str, Any]], out_path: str) -> None:
    if not rows:
        return
    fieldnames: List[str] = [
        "url",
        "title",
        "doc_type",
        "source_type",
        "publication_date",
        "regulatory_body",
        "domain_primary",
        "domain_secondary",
        "subdomain",
        "lifecycle_stage",
        "durability_tier",
        "validation_status",
        "confidence_domain_primary",
        "confidence_subdomain",
        "confidence_lifecycle_stage",
        "confidence_durability_tier",
        "classification_reason",
        "error",
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


if __name__ == "__main__":
    SEC_ENDPOINTS: List[str] = [
        "https://www.sec.gov/newsroom/press-releases/2026-44-sec-charges-21-individuals-alleged-wide-reaching-insider-trading-scheme",
        "https://www.sec.gov/newsroom/press-releases/2026-43-sec-divisions-investment-management-corporation-finance-issue-staff-guidance-supporting-retirement",
        "https://www.sec.gov/newsroom/press-releases/2026-42-sec-proposes-amendments-permit-optional-semiannual-reporting-public-companies",
        "https://www.sec.gov/newsroom/speeches-statements/uyeda-remarks-conference-financial-market-regulation-050726",
        "https://www.sec.gov/newsroom/speeches-statements/atkins-statement-facilitating-access-trump-accounts-050526",
        "https://www.sec.gov/newsroom/speeches-statements/selway-options-industry-conference-050526-fixing-failures-communicate",
        "https://www.sec.gov/newsroom/speeches-statements/atkins-statement-proposing-release-semiannual-reporting-050526",
        "https://www.sec.gov/newsroom/meetings-events/sunshine-act-notice-closed-04-30-2026"
        "https://www.sec.gov/files/rules/proposed/2026/33-11414.pdf",
        "https://www.sec.gov/files/rules/final/2026/34-105346.pdf",
        "https://www.sec.gov/files/rules/proposed/2026/ia-6959.pdf"
    ]

    rows_out: List[Dict[str, Any]] = []
    for u in SEC_ENDPOINTS:
        rows_out.append(classify_endpoint_to_metadata(u))

    _write_metadata_csv(rows_out, "endpoint_metadata.csv")

