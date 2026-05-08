#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
import time
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from dotenv import load_dotenv
from pinecone import Pinecone

from crypto_ingest import fetch_url
from cri_ontology.document_context import (
    extract_publication_date_from_html,
    infer_source_type_from_url,
)

load_dotenv()


def _env(name: str, default: str = "") -> str:
    v = os.getenv(name)
    return v if v is not None and str(v).strip() else default


def _get_pinecone_index_name() -> str:
    # Support both conventions used in this repo.
    return (
        _env("PINECONE_INDEX_NAME")
        or _env("PINECONE_INDEX")
        or _env("PINECONE_INDEXNAME")
    )


def _iter_ids(index, *, namespace: str) -> Iterable[str]:
    """
    Iterate all vector IDs in a namespace.

    Requires pinecone client with Index.list() support (pinecone>=3+; here pinecone 8).
    """
    if not hasattr(index, "list"):
        raise RuntimeError(
            "Pinecone Index.list() is not available in this client; cannot enumerate IDs."
        )
    # Pinecone list() returns an iterator over IDs (or over pages).
    for item in index.list(namespace=namespace):
        # New clients may yield strings directly or dict-like items.
        if isinstance(item, str):
            yield item
        elif isinstance(item, dict) and "id" in item:
            yield str(item["id"])


def _batched(items: Iterable[str], batch_size: int) -> Iterable[List[str]]:
    batch: List[str] = []
    for x in items:
        batch.append(x)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def _extract_url_and_doc_type(meta: Dict[str, Any]) -> Tuple[str, Optional[str]]:
    url = (meta.get("source_url") or meta.get("document_url") or "").strip()
    doc_type = meta.get("type") or meta.get("doc_type")
    doc_type_str = str(doc_type).strip() if isinstance(doc_type, str) else None
    return url, doc_type_str


def _enrich_url(
    url: str,
    *,
    doc_type: Optional[str],
    delay_s: float,
) -> Dict[str, Any]:
    source_type = infer_source_type_from_url(url, doc_type=doc_type)
    regulatory_body = ["SEC"] if "sec.gov" in (url or "").lower() else []

    publication_date: Optional[str] = None
    if url and url.lower().startswith(("http://", "https://")):
        resp = fetch_url(url)
        if resp is not None:
            ct = (resp.headers.get("Content-Type") or "").lower()
            if "html" in ct and resp.text:
                publication_date = extract_publication_date_from_html(resp.text)
        time.sleep(max(delay_s, 0.0))

    out: Dict[str, Any] = {
        "publication_date": publication_date or "",
        "source_type": source_type,
        "regulatory_body": regulatory_body,
    }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Enrich Pinecone metadata with document-level context (publication_date/source_type/regulatory_body)."
    )
    ap.add_argument("--namespace", type=str, default=_env("PINECONE_NAMESPACE", ""))
    ap.add_argument("--index", type=str, default=_get_pinecone_index_name())
    ap.add_argument("--max-records", type=int, default=0, help="0 = no limit")
    ap.add_argument("--batch-size", type=int, default=200)
    ap.add_argument("--delay-seconds", type=float, default=0.2)
    ap.add_argument(
        "--only-missing",
        action="store_true",
        help="Only write fields when missing/empty in metadata.",
    )
    args = ap.parse_args()

    api_key = _env("PINECONE_API_KEY")
    if not api_key:
        print("ERROR: PINECONE_API_KEY is not set.", file=sys.stderr)
        return 2
    if not args.index:
        print(
            "ERROR: Pinecone index name not provided (PINECONE_INDEX_NAME or PINECONE_INDEX).",
            file=sys.stderr,
        )
        return 2
    if not args.namespace:
        print("ERROR: Namespace not provided (PINECONE_NAMESPACE).", file=sys.stderr)
        return 2

    pc = Pinecone(api_key=api_key)
    index = pc.Index(args.index)

    # Cache by URL: (url, doc_type) -> enrichment dict
    enrichment_cache: Dict[Tuple[str, Optional[str]], Dict[str, Any]] = {}

    processed = 0
    updated = 0
    skipped = 0
    missing_url = 0

    # Track how many records share the same URL (useful sanity output).
    url_counts: Dict[str, int] = defaultdict(int)

    for id_batch in _batched(_iter_ids(index, namespace=args.namespace), args.batch_size):
        if args.max_records and processed >= args.max_records:
            break

        fetch_resp = index.fetch(ids=id_batch, namespace=args.namespace)
        vectors = getattr(fetch_resp, "vectors", None) or {}

        for vid, vec in vectors.items():
            if args.max_records and processed >= args.max_records:
                break
            processed += 1

            meta = (getattr(vec, "metadata", None) or {}) if vec is not None else {}
            if not isinstance(meta, dict):
                meta = {}

            url, doc_type = _extract_url_and_doc_type(meta)
            if not url:
                missing_url += 1
                continue
            url_counts[url] += 1

            # If only missing, check whether we need to update.
            if args.only_missing:
                pub_ok = bool(str(meta.get("publication_date") or "").strip())
                st_ok = bool(str(meta.get("source_type") or "").strip())
                rb_ok = isinstance(meta.get("regulatory_body"), list) and bool(meta.get("regulatory_body"))
                if pub_ok and st_ok and rb_ok:
                    skipped += 1
                    continue

            cache_key = (url, doc_type)
            if cache_key not in enrichment_cache:
                enrichment_cache[cache_key] = _enrich_url(
                    url, doc_type=doc_type, delay_s=args.delay_seconds
                )

            enrich = enrichment_cache[cache_key]
            set_meta: Dict[str, Any] = {}
            for k in ("publication_date", "source_type", "regulatory_body"):
                if args.only_missing:
                    existing = meta.get(k)
                    if k == "regulatory_body":
                        if isinstance(existing, list) and existing:
                            continue
                    else:
                        if isinstance(existing, str) and existing.strip():
                            continue
                set_meta[k] = enrich.get(k)

            if not set_meta:
                skipped += 1
                continue

            index.update(id=vid, namespace=args.namespace, set_metadata=set_meta)
            updated += 1

    top_urls = sorted(url_counts.items(), key=lambda kv: kv[1], reverse=True)[:10]
    print(
        f"Done. processed={processed} updated={updated} skipped={skipped} missing_url={missing_url} "
        f"unique_urls={len(url_counts)}"
    )
    if top_urls:
        print("Top URLs by chunk count:")
        for u, c in top_urls:
            print(f"  {c:>5}  {u}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

