#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Set

from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
for p in (_REPO_ROOT, _SCRIPT_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from crypto_ingest import (
    EMBEDDED_URLS_PATH,
    ensure_index_exists,
    load_embedded_urls,
    save_embedded_urls,
)
from new_crawler_tool import DEFAULT_SEED_URLS, iter_crawl_sec_pages
from sec_crawl_ingestion import (
    BufferedVector,
    buffered_to_pinecone_vectors,
    flush_chunk_buffer,
    process_url,
    upsert_vector_batch,
)

load_dotenv()


def _env(name: str, default: str = "") -> str:
    v = os.getenv(name)
    return v if v is not None and str(v).strip() else default


def _get_index_name() -> str:
    return _env("PINECONE_INDEX_NAME") or _env("PINECONE_INDEX")


def _load_seed_urls(seeds_file: str | None, cli_seeds: List[str]) -> List[str]:
    seeds: List[str] = []
    if seeds_file:
        path = Path(seeds_file)
        if path.is_file():
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    s = line.strip()
                    if s and not s.startswith("#"):
                        seeds.append(s)
    seeds.extend(cli_seeds)
    if not seeds:
        seeds = list(DEFAULT_SEED_URLS)
    return seeds


def _append_failure_jsonl(path: str, url: str, error: str) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"url": url, "error": error}, ensure_ascii=False) + "\n")


@dataclass
class CrawlRunConfig:
    batch_size: int = 100
    test: bool = False
    seeds_file: str = ""
    seeds: List[str] | None = None
    max_depth: int = 2
    max_pages: int = 300
    delay: float = 1.5
    embedded_urls: str = EMBEDDED_URLS_PATH
    failures_log: str = "crawl_ingest_failures.jsonl"
    namespace: str = ""
    index: str = ""
    timeout: int = 20

    def __post_init__(self) -> None:
        if self.seeds is None:
            self.seeds = []
        if not self.index:
            self.index = _get_index_name()
        if not self.namespace:
            self.namespace = _env("PINECONE_NAMESPACE", "")


def validate_crawl_config(config: CrawlRunConfig) -> int | None:
    """Return exit code if invalid, else None."""
    if config.batch_size < 1:
        print("ERROR: batch_size must be >= 1.", file=sys.stderr)
        return 2
    if not _env("PINECONE_API_KEY"):
        print("ERROR: PINECONE_API_KEY is not set.", file=sys.stderr)
        return 2
    if not _env("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY is not set.", file=sys.stderr)
        return 2
    if not config.index:
        print(
            "ERROR: Pinecone index not provided (PINECONE_INDEX_NAME or PINECONE_INDEX).",
            file=sys.stderr,
        )
        return 2
    if not config.namespace:
        print("ERROR: PINECONE_NAMESPACE is not set / provided.", file=sys.stderr)
        return 2
    return None


def add_crawl_arguments(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("--batch-size", type=int, default=100)
    ap.add_argument(
        "--test",
        action="store_true",
        help="Ingest exactly one URL not already in embedded_urls.json.",
    )
    ap.add_argument("--seeds-file", type=str, default="")
    ap.add_argument("--seeds", action="append", default=[], help="Seed URL (repeatable)")
    ap.add_argument("--max-depth", type=int, default=2)
    ap.add_argument(
        "--max-pages",
        type=int,
        default=300,
        help="Max pages to visit per run (0 = unlimited).",
    )
    ap.add_argument("--delay", type=float, default=1.5)
    ap.add_argument("--embedded-urls", type=str, default=EMBEDDED_URLS_PATH)
    ap.add_argument("--failures-log", type=str, default="crawl_ingest_failures.jsonl")
    ap.add_argument("--namespace", type=str, default=_env("PINECONE_NAMESPACE", ""))
    ap.add_argument("--index", type=str, default=_get_index_name())
    ap.add_argument("--timeout", type=int, default=20, help="Fetch timeout seconds")


def crawl_config_from_args(args: argparse.Namespace) -> CrawlRunConfig:
    return CrawlRunConfig(
        batch_size=args.batch_size,
        test=args.test,
        seeds_file=args.seeds_file,
        seeds=list(args.seeds),
        max_depth=args.max_depth,
        max_pages=args.max_pages,
        delay=args.delay,
        embedded_urls=args.embedded_urls,
        failures_log=args.failures_log,
        namespace=args.namespace,
        index=args.index,
        timeout=args.timeout,
    )


def run_crawl_job(config: CrawlRunConfig) -> int:
    err_code = validate_crawl_config(config)
    if err_code is not None:
        return err_code

    seed_urls = _load_seed_urls(config.seeds_file or None, config.seeds or [])
    embedded: Set[str] = load_embedded_urls(config.embedded_urls)
    if embedded:
        print(f"Loaded {len(embedded)} embedded URL(s) from {config.embedded_urls}")

    ensure_index_exists()
    pc = Pinecone(api_key=_env("PINECONE_API_KEY"))
    index = pc.Index(config.index)
    openai_client = OpenAI()

    buffer: List[BufferedVector] = []
    pages_visited = 0
    pages_skipped = 0
    pages_ingested = 0
    pages_failed = 0
    chunks_upserted = 0

    crawl_max_pages = 0 if config.test else config.max_pages

    print(
        f"Starting crawl (test={config.test}, max_depth={config.max_depth}, "
        f"max_pages={crawl_max_pages or 'unlimited'}, batch_size={config.batch_size})"
    )

    for item in iter_crawl_sec_pages(
        seed_urls,
        max_depth=config.max_depth,
        max_pages=crawl_max_pages,
        delay_seconds=config.delay,
    ):
        url = str(item["source_url"])
        if url in embedded:
            pages_skipped += 1
            continue

        pages_visited += 1
        print(f"\nProcessing: {url}")

        new_vectors, err = process_url(
            url,
            client=openai_client,
            timeout_seconds=config.timeout,
        )
        if err:
            pages_failed += 1
            print(f"  FAILED: {err}", file=sys.stderr)
            _append_failure_jsonl(config.failures_log, url, err)
            if config.test:
                return 1
            continue

        buffer.extend(new_vectors)
        print(f"  Classified {len(new_vectors)} chunk(s); buffer size={len(buffer)}")

        while len(buffer) >= config.batch_size:
            buffer, n_upserted = flush_chunk_buffer(
                buffer, config.batch_size, index, config.namespace
            )
            chunks_upserted += n_upserted
            if n_upserted:
                print(f"  Upserted {n_upserted} chunk(s) to Pinecone")

        if buffer:
            vectors = buffered_to_pinecone_vectors(buffer)
            upsert_vector_batch(vectors, index, config.namespace)
            chunks_upserted += len(buffer)
            print(f"  Upserted {len(buffer)} chunk(s) to Pinecone (page flush)")
            buffer = []

        embedded.add(url)
        save_embedded_urls(embedded, config.embedded_urls)
        pages_ingested += 1
        print(f"  Recorded URL in {config.embedded_urls}")

        if config.test:
            print(f"\nTest mode complete: ingested 1 URL ({len(new_vectors)} chunks).")
            break

    print(
        f"\nDone. visited={pages_visited} ingested={pages_ingested} "
        f"skipped={pages_skipped} failed={pages_failed} chunks_upserted={chunks_upserted}"
    )
    print(f"Embedded URLs: {config.embedded_urls}")
    print(f"Failures log: {config.failures_log}")
    return 0 if pages_failed == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Crawl SEC.gov, classify chunks, and upsert to Pinecone in batches."
    )
    add_crawl_arguments(ap)
    args = ap.parse_args()
    return run_crawl_job(crawl_config_from_args(args))


if __name__ == "__main__":
    raise SystemExit(main())
