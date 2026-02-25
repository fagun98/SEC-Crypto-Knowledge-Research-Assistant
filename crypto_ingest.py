import os
import time
import hashlib
import urllib.parse
import json
from dataclasses import dataclass
from typing import Iterable, List, Dict, Tuple, Set

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec
from pinecone_text.sparse import SpladeEncoder
from pypdf import PdfReader
from tqdm import tqdm

load_dotenv()

INDEX_NAME = "sec-cryto-knowledge-base-rag"
OPENAI_EMBED_MODEL = "text-embedding-3-small"
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", INDEX_NAME)
PINECONE_NAMESPACE = os.getenv("PINECONE_NAMESPACE", "sec-knowledge-base")
EMBEDDED_URLS_PATH = os.getenv("EMBEDDED_URLS_PATH", "embedded_urls.json")

client = OpenAI()
pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
sparse_encoder = SpladeEncoder()


def _get_headers() -> Dict[str, str]:
    """Common request headers for SEC.gov (reuse from new_crawler_tool)."""
    return {
        "User-Agent": "Custody-Intelligence-Agent/1.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }


def load_embedded_urls(path: str = EMBEDDED_URLS_PATH) -> Set[str]:
    """Load set of URLs that have already been embedded (from JSON list)."""
    if not os.path.exists(path):
        return set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return set(str(u) for u in data)
    except Exception as e:
        print(f"Warning: could not read embedded URLs file {path}: {e}")
    return set()


def save_embedded_urls(urls: Set[str], path: str = EMBEDDED_URLS_PATH) -> None:
    """Persist set of embedded URLs as a JSON list."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(sorted(urls), f, indent=2)
    except Exception as e:
        print(f"Warning: could not write embedded URLs file {path}: {e}")


@dataclass
class CrawlConfig:
    max_depth: int = 2
    max_pages: int = 300
    delay_seconds: float = 1.0
    allowed_domains: Tuple[str, ...] = tuple()  # optional domain whitelist (by hostname)
    allowed_path_prefixes: Tuple[str, ...] = tuple()  # optional path prefixes, e.g. ("/newsroom",)


@dataclass
class DocumentChunk:
    id: str
    text: str
    source_url: str
    title: str
    page: int | None
    doc_type: str  # "html" or "pdf"


def ensure_index_exists(dim: int = 1536) -> None:
    """Create Pinecone index if it does not already exist."""
    existing = {idx["name"] for idx in pc.list_indexes()}
    if PINECONE_INDEX_NAME in existing:
        return
    pc.create_index(
        name=PINECONE_INDEX_NAME,
        dimension=dim,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )


def is_pdf_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    if parsed.path.lower().endswith(".pdf"):
        return True
    # Sometimes PDFs lack .pdf extension; you could do a HEAD request and
    # inspect Content-Type, but that is slower. For now we keep it simple.
    return False


def normalize_url(base: str, href: str) -> str | None:
    if not href:
        return None
    href = href.strip()
    if href.startswith("#") or href.lower().startswith("javascript:"):
        return None
    abs_url = urllib.parse.urljoin(base, href)
    parsed = urllib.parse.urlparse(abs_url)
    if parsed.scheme not in ("http", "https"):
        return None
    return abs_url


def fetch_url(url: str, timeout: int = 20) -> requests.Response | None:
    try:
        resp = requests.get(url, headers=_get_headers(), timeout=timeout)
        if resp.status_code == 200:
            return resp
        else:
            print(
                f"Non-200 status for {url}: {resp.status_code} {resp.reason} "
                f"(Content-Type={resp.headers.get('Content-Type', '')})"
            )
    except Exception as e:
        print(f"Fetch error for {url}: {e}")
    return None


def extract_text_from_html(url: str, html: str) -> Tuple[str, str]:
    """Return (title, main_text). This can be made more sophisticated."""
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else url
    # Very simple main-content heuristic – customize as needed.
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()
    text = " ".join(soup.get_text(separator=" ", strip=True).split())
    return title, text


def extract_text_from_pdf(url: str, content: bytes) -> List[Tuple[int, str]]:
    """Return list of (page_number, text)."""
    from io import BytesIO

    reader = PdfReader(BytesIO(content))
    pages: List[Tuple[int, str]] = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        text = " ".join(text.split())
        if text:
            pages.append((i + 1, text))
    return pages


def crawl(seed_urls: List[str], cfg: CrawlConfig) -> List[Tuple[str, str, str, int | None, str]]:
    """
    Crawl up to `max_depth` from seeds. Prioritize PDFs in the queue.
    Returns list of (url, title, text, page, doc_type).
    """
    seen: Set[str] = set()
    results: List[Tuple[str, str, str, int | None, str]] = []

    # queue entries: (priority, depth, url)
    # priority: 0 = pdf (higher), 1 = html
    from heapq import heappush, heappop

    queue: list[Tuple[int, int, str]] = []

    for u in seed_urls:
        heappush(queue, (1, 0, u))

    pages_fetched = 0

    while queue and pages_fetched < cfg.max_pages:
        priority, depth, url = heappop(queue)
        if url in seen or depth > cfg.max_depth:
            continue

        parsed_url = urllib.parse.urlparse(url)

        # Domain filter (if configured)
        if cfg.allowed_domains:
            domain = parsed_url.netloc
            if not any(domain.endswith(d) for d in cfg.allowed_domains):
                continue

        # Path prefix filter (if configured) - only applies to discovered URLs (depth > 0), not seed URLs
        # This allows seed URLs to be crawled regardless of path, but restricts discovered links
        if cfg.allowed_path_prefixes and depth > 0:
            path = parsed_url.path or ""
            if not any(path.startswith(prefix) for prefix in cfg.allowed_path_prefixes):
                continue
        seen.add(url)

        print(f"Crawling ({depth}) {url}")
        resp = fetch_url(url)
        if not resp:
            continue
        pages_fetched += 1
        content_type = resp.headers.get("Content-Type", "").lower()

        # PDF handling
        if "pdf" in content_type or is_pdf_url(url):
            pdf_pages = extract_text_from_pdf(url, resp.content)
            for page_num, text in pdf_pages:
                if not text:
                    continue
                title = f"{url} (page {page_num})"
                results.append((url, title, text, page_num, "pdf"))
        else:
            title, text = extract_text_from_html(url, resp.text)
            if text:
                results.append((url, title, text, None, "html"))

            # Only follow links on HTML pages
            if depth < cfg.max_depth:
                soup = BeautifulSoup(resp.text, "html.parser")
                for a in soup.find_all("a", href=True):
                    next_url = normalize_url(url, a["href"])
                    if not next_url or next_url in seen:
                        continue
                    # prioritize PDFs
                    prio = 0 if is_pdf_url(next_url) else 1
                    heappush(queue, (prio, depth + 1, next_url))

        time.sleep(cfg.delay_seconds)

    print(f"Collected {len(results)} document texts/chunks before splitting.")
    return results


def chunk_text(text: str, max_tokens: int = 500, overlap_tokens: int = 100) -> List[str]:
    """
    Token-agnostic simple chunking using characters as proxy.
    Roughly 4 chars per token.
    """
    max_chars = max_tokens * 4
    overlap_chars = overlap_tokens * 4
    chunks: List[str] = []

    start = 0
    n = len(text)
    while start < n:
        end = min(n, start + max_chars)
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        if end == n:
            break
        start = end - overlap_chars
    return chunks


def make_chunk_id(url: str, page: int | None, chunk_idx: int) -> str:
    base = f"{url}|{page or 0}|{chunk_idx}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def build_document_chunks(
    crawled: List[Tuple[str, str, str, int | None, str]]
) -> List[DocumentChunk]:
    chunks: List[DocumentChunk] = []
    for url, title, text, page, doc_type in crawled:
        text_chunks = chunk_text(text)
        for idx, chunk in enumerate(text_chunks):
            cid = make_chunk_id(url, page, idx)
            chunks.append(
                DocumentChunk(
                    id=cid,
                    text=chunk,
                    source_url=url,
                    title=title,
                    page=page,
                    doc_type=doc_type,
                )
            )
    print(f"Built {len(chunks)} chunks from crawled content.")
    return chunks


def embed_texts(texts: List[str]) -> List[List[float]]:
    resp = client.embeddings.create(model=OPENAI_EMBED_MODEL, input=texts)
    return [d.embedding for d in resp.data]


def encode_sparse(texts: List[str]) -> List[Dict[str, List[float]]]:
    """
    Encode texts into sparse representations for hybrid search using SPLADE.
    Returns a list of dicts with 'indices' and 'values' keys.
    """
    return sparse_encoder.encode_documents(texts)


def upsert_chunks(chunks: List[DocumentChunk], batch_size: int = 100) -> None:
    ensure_index_exists()
    index = pc.Index(PINECONE_INDEX_NAME)

    for i in tqdm(
        range(0, len(chunks), batch_size),
        desc="Upserting chunks to Pinecone",
    ):
        batch = chunks[i : i + batch_size]
        vectors = []
        texts = [c.text for c in batch]

        dense_embeddings = embed_texts(texts)
        sparse_embeddings = encode_sparse(texts)

        for c, dense_emb, sparse_emb in zip(batch, dense_embeddings, sparse_embeddings):
            vectors.append(
                {
                    "id": c.id,
                    "values": dense_emb,
                    "sparse_values": {
                        "indices": sparse_emb["indices"],
                        "values": sparse_emb["values"],
                    },
                    "metadata": {
                        "source_url": c.source_url or "N/A",
                        "title": c.title or "N/A",
                        "page": c.page or "N/A",
                        "type": c.doc_type or "N/A",
                        "document_text": c.text or "N/A",
                    },
                }
            )
        index.upsert(vectors=vectors, namespace=PINECONE_NAMESPACE)


def hybrid_search(
    query: str,
    top_k: int = 10,
    alpha: float = 0.5,
    namespace: str | None = None,
) -> List[Dict[str, str]]:
    """
    Query the Pinecone SEC knowledge base using hybrid (dense + sparse) search.

    Args:
        query: Search query string.
        top_k: Maximum number of results to return.
        alpha: Blend factor between dense (1.0) and sparse (0.0) search. 0.5 = balanced.
        namespace: Pinecone namespace. Defaults to PINECONE_NAMESPACE.

    Returns:
        List of dicts with "source_url" and "content" keys for compatibility with
        chat agents and RAG pipelines.
    """
    if not query or not query.strip():
        return []

    ns = namespace or PINECONE_NAMESPACE
    index = pc.Index(PINECONE_INDEX_NAME)

    # Dense embedding
    dense_vec = embed_texts([query])[0]

    # Sparse encoding (use encode_queries for query-side)
    sparse_result = sparse_encoder.encode_queries([query])[0]
    sparse_vec = {
        "indices": sparse_result["indices"],
        "values": [v * (1 - alpha) for v in sparse_result["values"]],
    }
    
    dense_scaled = [v * alpha for v in dense_vec]

    response = index.query(
        vector=dense_scaled,
        sparse_vector=sparse_vec,
        top_k=top_k,
        namespace=ns,
        include_metadata=True,
    )

    docs: List[Dict[str, str]] = []
    for match in (response.matches or []):
        meta = match.metadata or {}
        url = meta.get("source_url") or meta.get("document_url") or ""
        content = meta.get("document_text") or meta.get("text") or meta.get("content") or ""

        if not content:
            continue

        docs.append({
            "source_url": url or "N/A",
            "content": content,
        })

    return docs


def run_ingestion(seed_urls: List[str], max_pages: int = 300, max_depth: int = 2, delay_seconds: float = 1.0, allowed_domains: Tuple[str, ...] = tuple(), allowed_path_prefixes: Tuple[str, ...] = tuple()) -> None:
    cfg = CrawlConfig(
        max_depth=max_depth,
        max_pages=max_pages,
        delay_seconds=delay_seconds,
        # Example: restrict to specific domain(s) and optionally narrow to certain paths.
        # For a narrow crawl like only SEC newsroom pages, you could use:
        # allowed_domains=("www.sec.gov",),
        # allowed_path_prefixes=("/newsroom",),
        allowed_domains=allowed_domains,
        allowed_path_prefixes=allowed_path_prefixes,
    )

    # Load URLs that were already embedded in previous runs (if any)
    embedded_urls = load_embedded_urls()
    if embedded_urls:
        print(f"Loaded {len(embedded_urls)} previously embedded URL(s); will skip re-embedding them.")

    crawled = crawl(seed_urls, cfg)
    print(f"Crawl returned {len(crawled)} documents before filtering already-embedded URLs.")

    # Filter out any documents whose source URL has already been embedded
    crawled_filtered: List[Tuple[str, str, str, int | None, str]] = []
    for url, title, text, page, doc_type in crawled:
        if url in embedded_urls:
            # Skip re-embedding this document
            continue
        crawled_filtered.append((url, title, text, page, doc_type))

    print(
        f"After filtering, {len(crawled_filtered)} documents remain to embed "
        f"({len(crawled) - len(crawled_filtered)} skipped as already embedded)."
    )

    for i, (url, title, text, page, doc_type) in enumerate(crawled_filtered[:3]):
        print(
            f"[CRAWLED DOC {i}] type={doc_type} page={page} "
            f"url={url}\n  title={title}\n  text_sample={text[:400]!r}\n"
        )

    chunks = build_document_chunks(crawled_filtered)
    print(f"First {min(3, len(chunks))} chunks that will be embedded:")
    for i, c in enumerate(chunks[:3]):
        print(
            f"[CHUNK {i}] type={c.doc_type} page={c.page} "
            f"url={c.source_url}\n  title={c.title}\n  text_sample={c.text[:400]!r}\n"
        )

    if not chunks:
        print("No new chunks to embed; nothing to upsert.")
        return

    upsert_chunks(chunks)

    # Update and persist the set of embedded URLs with the URLs we just processed
    new_urls = {url for url, _, _, _, _ in crawled_filtered}
    if new_urls:
        embedded_urls.update(new_urls)
        save_embedded_urls(embedded_urls)
        print(f"Recorded {len(new_urls)} newly embedded URL(s) to {EMBEDDED_URLS_PATH}.")


if __name__ == "__main__":
    seeds = [
        # "https://www.sec.gov/about/divisions-offices/division-corporation-finance/framework-investment-contract-analysis-digital-assets",
        # "https://www.sec.gov/files/dlt-framework.pdf",
        # "https://www.sec.gov/newsroom/speeches-statements/speech-hinman-061418",
        # "https://www.sec.gov/newsroom/speeches-statements/peirce-how-we-howey-050919",
        # "https://www.sec.gov/newsroom/press-releases/2018-88",
        # "https://www.sec.gov/newsroom/speeches-statements/statement-certain-proof-work-mining-activities-032025",
        # "https://www.sec.gov/newsroom/speeches-statements/statement-stablecoins-040425",
        # "https://www.sec.gov/newsroom/speeches-statements/statement-certain-protocol-staking-activities-052925",
        # "https://www.sec.gov/newsroom/speeches-statements/crenshaw-statement-protocol-staking-052925",
        # "https://www.sec.gov/newsroom/speeches-statements/peirce-statement-rfi-022125",
        # "https://www.sec.gov/newsroom/speeches-statements/peirce-remarks-sec-speaks-051925-new-paradigm-remarks-sec-speaks",
        # "https://www.sec.gov/newsroom/speeches-statements/atkins-111225-secs-approach-digital-assets-inside-project-crypto",
        # "https://www.sec.gov/about/crypto-task-force/written-submission/ctf-input-reiners-2025-3-18",
        # "https://www.sec.gov/about/crypto-task-force/written-submission/ctf-input-daugherty-2025-3-20"
        # "https://www.sec.gov/enforcement-litigation/litigation-releases",
        # "https://www.sec.gov/rules-regulations/rulemaking-activity",
        # "https://www.sec.gov/rules-regulations/staff-guidance/trading-markets-frequently-asked-questions",
        # "https://www.sec.gov/about/divisions-offices/division-investment-management",
        "https://www.sec.gov/about",
        "https://www.sec.gov/about/sec-commissioners",
        "https://www.sec.gov/about/commission-votes"
    ]

    print("=== Running full ingestion (PDFs prioritized but HTML also embedded) ===")
    for seed in seeds:
        run_ingestion([seed], max_pages=30, max_depth=2, delay_seconds=1.0, allowed_domains=("www.sec.gov",))