import io
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

from typing import List, Dict, Tuple

# SEC domain we allow (no crawling outside this)
SEC_NETLOC = "www.sec.gov"
SEC_BASE = "https://www.sec.gov"

# Default delay between requests (seconds) to be polite to SEC.gov
DEFAULT_CRAWL_DELAY = 1.5


def _get_headers() -> Dict[str, str]:
    """Common request headers for SEC.gov."""
    return {
        "User-Agent": "Custody-Intelligence-Agent/1.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }


def _get_soup(url: str) -> BeautifulSoup:
    """Fetch URL and return BeautifulSoup object. Raises on request errors."""
    response = requests.get(url, headers=_get_headers(), timeout=20)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def _fetch_pdf_text(url: str) -> str:
    """Fetch PDF from URL and return extracted text. Raises on request or parse errors."""
    response = requests.get(url, headers=_get_headers(), timeout=30)
    response.raise_for_status()
    reader = PdfReader(io.BytesIO(response.content))
    parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            parts.append(text)
    return " ".join(" ".join(p.split()) for p in parts)


def fetch_sec_html(url: str) -> str:
    """
    Fetches raw HTML from an SEC.gov page. Use for link-extraction passes where
    the agent needs to see <a href>, list structure, and date-like text.
    PDF URLs return empty string (no HTML to parse for links).
    """
    if _is_pdf_url(url):
        return ""
    response = requests.get(url, headers=_get_headers(), timeout=20)
    response.raise_for_status()
    return response.text


def fetch_sec_url(url: str) -> str:
    """
    Fetches text content from an SEC.gov page (HTML or PDF).
    HTML is parsed with BeautifulSoup; PDF text is extracted with pypdf.
    """
    if _is_pdf_url(url):
        return _fetch_pdf_text(url)
    soup = _get_soup(url)
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    return " ".join(text.split())


def _normalize_url(url: str) -> str:
    """Strip fragment and trailing slash for deduplication."""
    u = url.split("#")[0].rstrip("/") or url
    return u


def _is_pdf_url(url: str) -> bool:
    """True if URL points to a PDF (by path or common SEC patterns)."""
    path = (urlparse(url).path or "").lower()
    return path.endswith(".pdf") or "/pdf/" in path


def _is_sec_page(href: str, current_base: str) -> bool:
    """True if href is a same-domain SEC page we can crawl (HTML or PDF; no zip, mailto, etc.)."""
    if not href or href.startswith("#") or href.startswith("mailto:") or href.startswith("javascript:"):
        return False
    full = urljoin(current_base, href)
    parsed = urlparse(full)
    if parsed.netloc and parsed.netloc.lower() != SEC_NETLOC:
        return False
    path = (parsed.path or "").lower()
    if path.endswith(".zip") or "/ix?doc=" in full:
        return False
    return True


def _extract_sec_links(soup: BeautifulSoup, page_url: str) -> List[str]:
    """Return list of absolute SEC.gov URLs from <a href> on the page."""
    out = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not _is_sec_page(href, page_url):
            continue
        full = urljoin(page_url, href)
        full = _normalize_url(full)
        if full not in out:
            out.append(full)
    return out


def crawl_sec_pages(
    seed_urls: List[str],
    max_depth: int = 2,
    max_pages: int = 50,
    delay_seconds: float = DEFAULT_CRAWL_DELAY,
) -> List[Dict[str, str]]:
    """
    Crawl SEC.gov starting from seed URLs, following links up to max_depth (1 or 2).
    Fetches both HTML and PDF pages; PDF text is extracted via pypdf.

    - Only visits pages under www.sec.gov.
    - Rate-limited by delay_seconds between requests.
    - Returns a list of dicts: one entry per crawled page (HTML or PDF). Each entry is
      {"source_url": url, "content": text}. All crawled pages are returned as separate
      list items; content is NOT concatenated into one string.

    Example: crawl_sec_pages(["https://www.sec.gov/newsroom/speeches-statements"], max_depth=2, max_pages=40)
    """
    seen: set = set()
    results: List[Dict[str, str]] = []
    # Queue: (url, depth)
    queue: List[Tuple[str, int]] = []
    for u in seed_urls:
        u = u.strip()
        if u.startswith("https://www.sec.gov"):
            queue.append((_normalize_url(u), 0))

    while queue and len(results) < max_pages:
        url, depth = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)

        if _is_pdf_url(url):
            try:
                content = _fetch_pdf_text(url)
            except Exception as e:
                print(f"Failed to fetch PDF {url}: {e}")
                continue
            results.append({"source_url": url, "content": content})
            print(url)
            # PDFs: no link extraction
        else:
            try:
                soup = _get_soup(url)
            except Exception as e:
                print(f"Failed to fetch {url}: {e}")
                continue
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            text = soup.get_text(separator=" ")
            content = " ".join(text.split())
            results.append({"source_url": url, "content": content})
            print(url)

            if depth < max_depth:
                for link in _extract_sec_links(soup, url):
                    if link not in seen:
                        queue.append((link, depth + 1))

        time.sleep(delay_seconds)

    print(f"\nVisited {len(results)} URL(s).")
    return results


# Example run to test fetch_sec_url function
if __name__ == "__main__":
    seed_urls = [
        "https://www.sec.gov/featured-topics/crypto-task-force",
        "https://www.sec.gov/about/divisions-offices/division-trading-markets",
        "https://www.sec.gov/about/divisions-offices/division-investment-management",
        "https://www.sec.gov/newsroom/speeches-statements",
        "https://www.sec.gov/enforcement-litigation/litigation-releases",
        "https://www.sec.gov/rules-regulations/rulemaking-activity",
    ]

    results = crawl_sec_pages(seed_urls)
    print(results)
