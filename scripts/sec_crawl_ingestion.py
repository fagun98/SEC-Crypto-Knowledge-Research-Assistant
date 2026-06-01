#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI

from cri_ontology.classifier import classify_chunk
from cri_ontology.document_context import fetch_sec_document
from cri_ontology.validate import validate_classification

from crypto_ingest import (
    DocumentChunk,
    chunk_text,
    embed_texts,
    encode_sparse,
    make_chunk_id,
)


@dataclass
class BufferedVector:
    chunk: DocumentChunk
    metadata: Dict[str, Any]


def sanitize_metadata_for_pinecone(meta: Dict[str, Any]) -> Dict[str, Any]:
    """Pinecone metadata: string, number, boolean, or list of strings only."""
    out: Dict[str, Any] = {}
    for key, value in meta.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            out[key] = value
        elif isinstance(value, list):
            out[key] = [str(v) for v in value if v is not None]
        elif isinstance(value, dict):
            out[key] = json.dumps(value, ensure_ascii=False)
        else:
            out[key] = str(value)
    return out


def classify_document_metadata(
    document_text: str,
    document_context: Dict[str, Any],
    *,
    client: Optional[OpenAI] = None,
) -> Dict[str, Any]:
    """Classify full document/segment text and return Pinecone-ready metadata fields."""
    meta: Dict[str, Any] = {}
    try:
        classified = classify_chunk(
            chunk_text=document_text,
            document_context=document_context,
            client=client,
        )
        normalized, errors = validate_classification(classified)
        meta.update(
            {
                "domain_primary": normalized["domain_primary"],
                "domain_secondary": normalized["domain_secondary"],
                "subdomain": normalized["subdomain"],
                "lifecycle_stage": normalized["lifecycle_stage"],
                "durability_tier": normalized["durability_tier"],
                "classification_confidence": normalized["confidence"],
                "classification_reason": normalized.get("reasoning_summary", ""),
                "validation_status": normalized["validation_status"],
            }
        )
        if errors:
            meta["classification_validation_errors"] = errors[:50]
    except Exception as e:
        meta["validation_status"] = "pending_review"
        meta["classification_error"] = str(e)[:500]
    return meta


def classify_chunk_metadata(
    chunk_text_value: str,
    document_context: Dict[str, Any],
    *,
    client: Optional[OpenAI] = None,
) -> Dict[str, Any]:
    """Classify a chunk and return Pinecone-ready metadata fields."""
    return classify_document_metadata(
        chunk_text_value, document_context, client=client
    )


def page_extracts_to_chunks(
    page_extracts: List[Dict[str, Any]],
) -> List[Tuple[DocumentChunk, Dict[str, Any]]]:
    """Convert fetch_sec_document page dicts into DocumentChunks with base metadata."""
    out: List[Tuple[DocumentChunk, Dict[str, Any]]] = []
    for page in page_extracts:
        final_url = page["final_url"]
        doc_type = page["doc_type"]
        title = page["title"]
        page_num = page.get("page")
        document_context = page["document_context"]
        text_chunks = chunk_text(page["full_text"])
        for idx, text in enumerate(text_chunks):
            cid = make_chunk_id(final_url, page_num, idx)
            chunk = DocumentChunk(
                id=cid,
                text=text,
                source_url=final_url,
                title=title,
                page=page_num,
                doc_type=doc_type,
            )
            base_meta: Dict[str, Any] = {
                "source_url": final_url,
                "title": title or "N/A",
                "page": page_num if page_num is not None else "N/A",
                "type": doc_type or "N/A",
                "document_text": text,
                "publication_date": page.get("publication_date") or "",
                "source_type": page.get("source_type") or "",
                "regulatory_body": document_context.get("regulatory_body") or ["SEC"],
            }
            out.append((chunk, {**base_meta, "_document_context": document_context}))
    return out


def build_buffered_vectors(
    chunk_pairs: List[Tuple[DocumentChunk, Dict[str, Any]]],
    *,
    client: Optional[OpenAI] = None,
) -> List[BufferedVector]:
    buffered: List[BufferedVector] = []
    for chunk, meta in chunk_pairs:
        doc_ctx = meta.pop("_document_context", {})
        classified_meta = classify_chunk_metadata(
            chunk.text, doc_ctx if isinstance(doc_ctx, dict) else {}, client=client
        )
        full_meta = sanitize_metadata_for_pinecone({**meta, **classified_meta})
        buffered.append(BufferedVector(chunk=chunk, metadata=full_meta))
    return buffered


def buffered_to_pinecone_vectors(
    items: List[BufferedVector],
) -> List[Dict[str, Any]]:
    texts = [bv.chunk.text for bv in items]
    dense_embeddings = embed_texts(texts)
    sparse_embeddings = encode_sparse(texts)
    vectors: List[Dict[str, Any]] = []
    for bv, dense_emb, sparse_emb in zip(items, dense_embeddings, sparse_embeddings):
        vectors.append(
            {
                "id": bv.chunk.id,
                "values": dense_emb,
                "sparse_values": {
                    "indices": sparse_emb["indices"],
                    "values": sparse_emb["values"],
                },
                "metadata": bv.metadata,
            }
        )
    return vectors


def upsert_vector_batch(
    vectors: List[Dict[str, Any]],
    index: Any,
    namespace: str,
) -> None:
    if not vectors:
        return
    index.upsert(vectors=vectors, namespace=namespace)


def flush_chunk_buffer(
    buffer: List[BufferedVector],
    batch_size: int,
    index: Any,
    namespace: str,
) -> Tuple[List[BufferedVector], int]:
    """
    Upsert complete batches from buffer. Returns (remaining_buffer, chunks_upserted_count).
    """
    upserted = 0
    while len(buffer) >= batch_size:
        batch = buffer[:batch_size]
        buffer = buffer[batch_size:]
        vectors = buffered_to_pinecone_vectors(batch)
        upsert_vector_batch(vectors, index, namespace)
        upserted += len(batch)
    return buffer, upserted


def process_url(
    url: str,
    *,
    client: Optional[OpenAI] = None,
    max_pdf_pages: int = 0,
    timeout_seconds: int = 20,
) -> Tuple[List[BufferedVector], Optional[str]]:
    """
    Fetch, chunk, and classify a URL. Returns (buffered_vectors, error_message).
    """
    try:
        page_extracts = fetch_sec_document(
            url,
            max_html_chars=None,
            max_pdf_pages=max_pdf_pages,
            timeout_seconds=timeout_seconds,
        )
    except Exception as e:
        return [], str(e)

    if not page_extracts:
        return [], "No extractable text from URL"

    chunk_pairs = page_extracts_to_chunks(page_extracts)
    if not chunk_pairs:
        return [], "No chunks produced from URL"

    buffered = build_buffered_vectors(chunk_pairs, client=client)
    return buffered, None
