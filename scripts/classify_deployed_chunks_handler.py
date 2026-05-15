#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
for p in (_REPO_ROOT, _SCRIPT_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from classify_deployed_chunks_ingestion import (
    append_id_lines,
    load_id_lines,
    load_id_set,
    process_batch,
)

load_dotenv()


def _env(name: str, default: str = "") -> str:
    v = os.getenv(name)
    return v if v is not None and str(v).strip() else default


def _get_index_name() -> str:
    return _env("PINECONE_INDEX_NAME") or _env("PINECONE_INDEX")


def _batched(items: List[str], batch_size: int) -> List[List[str]]:
    batches: List[List[str]] = []
    batch: List[str] = []
    for x in items:
        batch.append(x)
        if len(batch) >= batch_size:
            batches.append(batch)
            batch = []
    if batch:
        batches.append(batch)
    return batches


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Classify deployed Pinecone chunks in batches (resume via ledger files)."
    )
    ap.add_argument("--batch-size", type=int, default=100)
    ap.add_argument(
        "--test",
        action="store_true",
        help="Process exactly one pending vector ID (smoke test).",
    )
    ap.add_argument("--ids-file", type=str, default="temp_global_indicies.txt")
    ap.add_argument("--updated-file", type=str, default="temp_updated_indices.txt")
    ap.add_argument("--failed-file", type=str, default="temp_failed_indices.txt")
    ap.add_argument("--namespace", type=str, default=_env("PINECONE_NAMESPACE", ""))
    ap.add_argument("--index", type=str, default=_get_index_name())
    args = ap.parse_args()

    if args.batch_size < 1:
        print("ERROR: --batch-size must be >= 1.", file=sys.stderr)
        return 2

    pinecone_key = _env("PINECONE_API_KEY")
    if not pinecone_key:
        print("ERROR: PINECONE_API_KEY is not set.", file=sys.stderr)
        return 2
    if not _env("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY is not set.", file=sys.stderr)
        return 2
    if not args.index:
        print(
            "ERROR: Pinecone index not provided (PINECONE_INDEX_NAME or PINECONE_INDEX).",
            file=sys.stderr,
        )
        return 2
    if not args.namespace:
        print("ERROR: PINECONE_NAMESPACE is not set / provided.", file=sys.stderr)
        return 2

    global_ids = load_id_lines(args.ids_file)
    if not global_ids:
        print(f"ERROR: No IDs found in {args.ids_file}.", file=sys.stderr)
        return 2

    updated_set = load_id_set(args.updated_file)
    pending = [vid for vid in global_ids if vid not in updated_set]

    if not pending:
        print("No pending IDs to process (all IDs are in the updated ledger).")
        return 0

    if args.test:
        pending = pending[:1]
        batch_size = 1
        print(f"Test mode: processing 1 pending vector ({pending[0]})")
    else:
        batch_size = args.batch_size
        print(
            f"Processing {len(pending)} pending vectors "
            f"(batch_size={batch_size}, skipped {len(updated_set)} already updated)"
        )

    pc = Pinecone(api_key=pinecone_key)
    index = pc.Index(args.index)
    openai_client = OpenAI()

    batches = _batched(pending, batch_size)
    total_success = 0
    total_failed = 0

    def on_error(vector_id: str, message: str) -> None:
        print(f"  FAILED {vector_id}: {message}", file=sys.stderr)

    for batch_num, batch_ids in enumerate(batches, start=1):
        print(f"\nBatch {batch_num}/{len(batches)} ({len(batch_ids)} IDs)...")
        success_ids, failed_ids = process_batch(
            batch_ids,
            index,
            args.namespace,
            client=openai_client,
            on_error=on_error,
        )

        append_id_lines(args.updated_file, success_ids)
        append_id_lines(args.failed_file, failed_ids)

        total_success += len(success_ids)
        total_failed += len(failed_ids)

        print(
            f"  Batch {batch_num} done: success={len(success_ids)} failed={len(failed_ids)} "
            f"| running totals: success={total_success} failed={total_failed}"
        )
        for vid in success_ids:
            print(f"  Updated: {vid}")

    print(
        f"\nDone. processed={total_success + total_failed} "
        f"updated={total_success} failed={total_failed}"
    )
    print(f"Updated ledger: {args.updated_file}")
    print(f"Failed ledger: {args.failed_file}")
    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
