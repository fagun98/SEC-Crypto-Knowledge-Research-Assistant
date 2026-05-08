#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone

from cri_ontology.classifier import classify_chunk
from cri_ontology.document_context import build_document_context_from_metadata
from cri_ontology.validate import validate_classification

load_dotenv()


def _env(name: str, default: str = "") -> str:
    v = os.getenv(name)
    return v if v is not None and str(v).strip() else default


def _get_index_name() -> str:
    return _env("PINECONE_INDEX_NAME") or _env("PINECONE_INDEX")


def _iter_ids(index, *, namespace: str) -> Iterable[str]:
    if not hasattr(index, "list"):
        raise RuntimeError(
            "Pinecone Index.list() is not available in this client; cannot enumerate IDs."
        )
    for item in index.list(namespace=namespace):
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


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _jsonl_write(path: str, obj: Dict[str, Any]) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Backfill CRI ontology metadata for existing Pinecone vectors."
    )
    ap.add_argument("--namespace", type=str, default=_env("PINECONE_NAMESPACE", ""))
    ap.add_argument("--index", type=str, default=_get_index_name())
    ap.add_argument("--max-records", type=int, default=0, help="0 = no limit")
    ap.add_argument("--list-batch-size", type=int, default=500)
    ap.add_argument("--fetch-batch-size", type=int, default=200)
    ap.add_argument("--skip-if-present", action="store_true")
    ap.add_argument("--log-jsonl", type=str, default="cri_backfill_log.jsonl")
    ap.add_argument("--pending-review-json", type=str, default="cri_pending_review_ids.json")
    ap.add_argument("--failures-json", type=str, default="cri_backfill_failures.json")
    ap.add_argument("--ontology-version", type=str, default="v1")
    args = ap.parse_args()

    pinecone_key = _env("PINECONE_API_KEY")
    if not pinecone_key:
        print("ERROR: PINECONE_API_KEY is not set.", file=sys.stderr)
        return 2
    if not args.index:
        print("ERROR: Pinecone index not provided (PINECONE_INDEX_NAME or PINECONE_INDEX).", file=sys.stderr)
        return 2
    if not args.namespace:
        print("ERROR: PINECONE_NAMESPACE is not set / provided.", file=sys.stderr)
        return 2

    pc = Pinecone(api_key=pinecone_key)
    index = pc.Index(args.index)

    openai_client = OpenAI()

    processed = 0
    updated = 0
    skipped = 0
    failed = 0
    pending_review: List[str] = []
    failures: List[Dict[str, Any]] = []

    for id_page in _batched(_iter_ids(index, namespace=args.namespace), args.list_batch_size):
        for id_batch in _batched(id_page, args.fetch_batch_size):
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

                if args.skip_if_present and all(
                    str(meta.get(k, "")).strip()
                    for k in ("domain_primary", "lifecycle_stage", "durability_tier")
                ):
                    skipped += 1
                    continue

                chunk_text = (
                    meta.get("document_text")
                    or meta.get("text")
                    or meta.get("content")
                    or ""
                )
                if not isinstance(chunk_text, str) or not chunk_text.strip():
                    failed += 1
                    err = {
                        "id": vid,
                        "error": "Missing chunk text in metadata (document_text/text/content).",
                    }
                    failures.append(err)
                    _jsonl_write(args.log_jsonl, {"type": "failure", **err})
                    continue

                doc_ctx = build_document_context_from_metadata(meta)
                try:
                    classified = classify_chunk(
                        chunk_text=chunk_text,
                        document_context=doc_ctx,
                        client=openai_client,
                    )
                except Exception as e:
                    failed += 1
                    err = {
                        "id": vid,
                        "error": f"classify_chunk failed: {e}",
                        "source_url": meta.get("source_url"),
                    }
                    failures.append(err)
                    _jsonl_write(args.log_jsonl, {"type": "failure", **err})
                    continue

                normalized, errors = validate_classification(classified)

                # Map to Pinecone metadata shape in the spec
                set_metadata: Dict[str, Any] = {
                    "domain_primary": normalized["domain_primary"],
                    "domain_secondary": normalized["domain_secondary"],
                    "subdomain": normalized["subdomain"],
                    "lifecycle_stage": normalized["lifecycle_stage"],
                    "durability_tier": normalized["durability_tier"],
                    "classification_confidence": normalized["confidence"],
                    "classification_reason": normalized.get("reasoning_summary", ""),
                    "validation_status": normalized["validation_status"],
                    "ontology_version": args.ontology_version,
                    "classified_at": _now_iso(),
                }
                if errors:
                    set_metadata["classification_validation_errors"] = errors[:50]

                try:
                    index.update(
                        id=vid,
                        namespace=args.namespace,
                        set_metadata=set_metadata,
                    )
                    updated += 1
                except Exception as e:
                    failed += 1
                    err = {
                        "id": vid,
                        "error": f"Pinecone update failed: {e}",
                        "source_url": meta.get("source_url"),
                    }
                    failures.append(err)
                    _jsonl_write(args.log_jsonl, {"type": "failure", **err})
                    continue

                if normalized["validation_status"] != "auto":
                    pending_review.append(vid)

                _jsonl_write(
                    args.log_jsonl,
                    {
                        "type": "updated",
                        "id": vid,
                        "validation_status": normalized["validation_status"],
                        "domain_primary": normalized["domain_primary"],
                        "lifecycle_stage": normalized["lifecycle_stage"],
                        "durability_tier": normalized["durability_tier"],
                        "source_url": meta.get("source_url"),
                    },
                )

        if args.max_records and processed >= args.max_records:
            break

    with open(args.pending_review_json, "w", encoding="utf-8") as f:
        json.dump(pending_review, f, ensure_ascii=False, indent=2)
    with open(args.failures_json, "w", encoding="utf-8") as f:
        json.dump(failures, f, ensure_ascii=False, indent=2)

    print(
        f"Done. processed={processed} updated={updated} skipped={skipped} failed={failed} "
        f"pending_review={len(pending_review)}"
    )
    print(f"Logs: {args.log_jsonl}")
    print(f"Pending review IDs: {args.pending_review_json}")
    print(f"Failures: {args.failures_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

