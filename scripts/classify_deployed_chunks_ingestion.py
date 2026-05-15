#!/usr/bin/env python3
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Set, Tuple

from openai import OpenAI

from cri_ontology.classifier import classify_chunk

CLASSIFIED_FIELDS = [
    "domain_primary",
    "domain_secondary",
    "subdomain",
    "lifecycle_stage",
    "durability_tier",
]

TEXT_METADATA_KEYS = frozenset({"document_text", "text", "content"})


def load_id_lines(path: str) -> List[str]:
    """Read newline-delimited IDs; strip blanks; ignore # comments. Preserves order."""
    ids: List[str] = []
    seen: Set[str] = set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                if s not in seen:
                    seen.add(s)
                    ids.append(s)
    except FileNotFoundError:
        pass
    return ids


def load_id_set(path: str) -> Set[str]:
    return set(load_id_lines(path))


def append_id_lines(path: str, ids: List[str]) -> None:
    if not ids:
        return
    needs_leading_newline = False
    if os.path.exists(path) and os.path.getsize(path) > 0:
        with open(path, "rb") as f:
            f.seek(-1, os.SEEK_END)
            if f.read(1) != b"\n":
                needs_leading_newline = True
    with open(path, "a", encoding="utf-8") as f:
        if needs_leading_newline:
            f.write("\n")
        for vid in ids:
            f.write(f"{vid}\n")


def extract_chunk_text(meta: Dict[str, Any]) -> str:
    chunk_text = (
        meta.get("document_text")
        or meta.get("text")
        or meta.get("content")
        or ""
    )
    if not isinstance(chunk_text, str) or not chunk_text.strip():
        raise ValueError("Missing chunk text in metadata (document_text/text/content)")
    return chunk_text


def build_document_context(meta: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in meta.items() if k not in TEXT_METADATA_KEYS}


def classify_and_merge_metadata(
    vector_id: str,
    index: Any,
    namespace: str,
    *,
    client: Optional[OpenAI] = None,
) -> Dict[str, Any]:
    """
    Fetch a vector from Pinecone, classify its chunk text, merge ontology fields
    into existing metadata (notebook-style), and return the merged metadata dict.
    """
    response = index.fetch(ids=[vector_id], namespace=namespace)
    vectors = getattr(response, "vectors", None) or {}
    if not vectors or vector_id not in vectors:
        raise ValueError(f"Vector ID {vector_id} not found in the namespace.")

    vec = vectors[vector_id]
    old_meta = getattr(vec, "metadata", None) or {}
    if not isinstance(old_meta, dict):
        old_meta = {}

    chunk_text = extract_chunk_text(old_meta)
    document_context = build_document_context(old_meta)

    classified = classify_chunk(
        chunk_text=chunk_text,
        document_context=document_context,
        client=client,
    )

    new_meta = old_meta.copy()
    for field in CLASSIFIED_FIELDS:
        new_meta[field] = classified.get(field)
    new_meta["regulatory_body"] = "SEC"
    return new_meta


def process_batch(
    batch_ids: List[str],
    index: Any,
    namespace: str,
    *,
    client: Optional[OpenAI] = None,
    on_error: Optional[Any] = None,
) -> Tuple[List[str], List[str]]:
    """
    Fetch a batch of vectors, classify each, and update Pinecone metadata.

    Returns (success_ids, failed_ids) in batch order.
    """
    success_ids: List[str] = []
    failed_ids: List[str] = []

    if not batch_ids:
        return success_ids, failed_ids

    fetch_resp = index.fetch(ids=batch_ids, namespace=namespace)
    vectors = getattr(fetch_resp, "vectors", None) or {}

    for vector_id in batch_ids:
        vec = vectors.get(vector_id)
        if vec is None:
            failed_ids.append(vector_id)
            if on_error:
                on_error(vector_id, f"Vector ID {vector_id} not found in the namespace.")
            continue

        old_meta = getattr(vec, "metadata", None) or {}
        if not isinstance(old_meta, dict):
            old_meta = {}

        try:
            chunk_text = extract_chunk_text(old_meta)
        except ValueError as e:
            failed_ids.append(vector_id)
            if on_error:
                on_error(vector_id, str(e))
            continue

        document_context = build_document_context(old_meta)
        try:
            classified = classify_chunk(
                chunk_text=chunk_text,
                document_context=document_context,
                client=client,
            )
        except Exception as e:
            failed_ids.append(vector_id)
            if on_error:
                on_error(vector_id, f"classify_chunk failed: {e}")
            continue

        new_meta = old_meta.copy()
        for field in CLASSIFIED_FIELDS:
            new_meta[field] = classified.get(field)
        new_meta["regulatory_body"] = "SEC"

        try:
            index.update(
                id=vector_id,
                set_metadata=new_meta,
                namespace=namespace,
            )
            success_ids.append(vector_id)
        except Exception as e:
            failed_ids.append(vector_id)
            if on_error:
                on_error(vector_id, f"Pinecone update failed: {e}")

    return success_ids, failed_ids
