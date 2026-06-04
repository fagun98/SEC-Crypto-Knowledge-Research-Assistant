from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from chat_agent.env import load_dotenv_env, require_pinecone_config, setup_openai_api_key

load_dotenv_env()

from cri_ontology.classifier import classify_query  # noqa: E402
from chat_agent.models import get_query_classifier_model, get_rerank_model
from chat_agent.retrieval_filters import build_pinecone_filter
from chat_agent.rerank import rerank_chunks
from chat_agent.types import CONTEXT_METADATA_KEYS, RetrievedChunk, RetrievalPass
from pinecone_hybrid import get_pinecone_hybrid_db  # noqa: E402
from utils import get_env_float, get_env_int

__all__ = ["RetrievedChunk", "RetrievalContext", "collect_context", "CONTEXT_METADATA_KEYS"]


@dataclass
class RetrievalContext:
    query: str
    classification: Dict[str, Any]
    pinecone_filter: Optional[Dict[str, Any]]
    filtered_chunks: List[RetrievedChunk]
    unfiltered_chunks: List[RetrievedChunk]
    merged_chunks: List[RetrievedChunk]
    ranked_chunks: List[RetrievedChunk]
    rerank_debug: List[Dict[str, Any]]

    def to_debug_dict(self) -> Dict[str, Any]:
        norm = self.classification.get("normalized") or {}
        return {
            "query": self.query,
            "classification": {
                "domain_primary": norm.get("domain_primary"),
                "domain_secondary": norm.get("domain_secondary"),
                "subdomain": norm.get("subdomain"),
                "lifecycle_stage": norm.get("lifecycle_stage"),
                "durability_tier": norm.get("durability_tier"),
                "validation_status": norm.get("validation_status"),
                "reasoning_summary": norm.get("reasoning_summary"),
                "validation_errors": self.classification.get("validation_errors"),
            },
            "pinecone_filter": self.pinecone_filter,
            "filtered_count": len(self.filtered_chunks),
            "unfiltered_count": len(self.unfiltered_chunks),
            "merged_count": len(self.merged_chunks),
            "ranked_count": len(self.ranked_chunks),
            "ranked_ids": [c.id for c in self.ranked_chunks],
            "rerank_debug": self.rerank_debug,
            "models": (self.classification.get("_models") or {}),
        }


def _extract_chunk_text(meta: Dict[str, Any]) -> str:
    return (
        meta.get("document_text")
        or meta.get("text")
        or meta.get("content")
        or meta.get("snippet")
        or ""
    )


def _hits_to_chunks(
    hits: List[Dict[str, Any]],
    retrieval_pass: RetrievalPass,
) -> List[RetrievedChunk]:
    out: List[RetrievedChunk] = []
    for hit in hits:
        cid = str(hit.get("_id") or hit.get("id") or "").strip()
        if not cid:
            continue
        score = float(hit.get("_score") or 0.0)
        meta = {k: v for k, v in hit.items() if not k.startswith("_")}
        out.append(
            RetrievedChunk(
                id=cid,
                text=str(_extract_chunk_text(hit)),
                metadata=meta,
                pinecone_score=score,
                retrieval_passes=[retrieval_pass],
            )
        )
    return out


def _merge_chunks(
    filtered: List[RetrievedChunk],
    unfiltered: List[RetrievedChunk],
) -> List[RetrievedChunk]:
    by_id: Dict[str, RetrievedChunk] = {}
    for chunk in filtered + unfiltered:
        existing = by_id.get(chunk.id)
        if existing is None:
            by_id[chunk.id] = RetrievedChunk(
                id=chunk.id,
                text=chunk.text,
                metadata=chunk.metadata,
                pinecone_score=chunk.pinecone_score,
                retrieval_passes=list(chunk.retrieval_passes),
            )
        else:
            for p in chunk.retrieval_passes:
                if p not in existing.retrieval_passes:
                    existing.retrieval_passes.append(p)
            if chunk.pinecone_score > existing.pinecone_score:
                existing.pinecone_score = chunk.pinecone_score
                if chunk.text:
                    existing.text = chunk.text
    merged = list(by_id.values())
    merged.sort(key=lambda c: c.pinecone_score, reverse=True)
    return merged


def collect_context(
    query: str,
    *,
    db: Optional[Any] = None,
    filter_mode: str = "domain_primary",
) -> RetrievalContext:
    """
    Classify query, dual Pinecone retrieval, merge, and LLM rerank.
    """
    query = query.strip()
    if not query:
        raise ValueError("query must be non-empty")

    top_k = get_env_int("CHAT_RETRIEVAL_TOP_K", 10)
    alpha = get_env_float("CHAT_HYBRID_ALPHA", 0.5)
    score_threshold = get_env_float("CHAT_SCORE_THRESHOLD", 0.0)

    setup_openai_api_key()
    classification = classify_query(query)
    pinecone_filter = build_pinecone_filter(classification, mode=filter_mode)

    require_pinecone_config()
    vector_db = db or get_pinecone_hybrid_db(score_threshold=score_threshold)

    filtered_hits: List[Dict[str, Any]] = []
    if pinecone_filter:
        filtered_hits = vector_db.fetch(
            query=query,
            top_k=top_k,
            alpha=alpha,
            filter=pinecone_filter,
            include_scores=True,
        )

    unfiltered_hits = vector_db.fetch(
        query=query,
        top_k=top_k,
        alpha=alpha,
        filter=None,
        include_scores=True,
    )

    filtered_chunks = _hits_to_chunks(filtered_hits, "filtered")
    unfiltered_chunks = _hits_to_chunks(unfiltered_hits, "unfiltered")
    merged_chunks = _merge_chunks(filtered_chunks, unfiltered_chunks)

    ranked_chunks, rerank_debug = rerank_chunks(query, merged_chunks)

    debug_models = {
        "query_classifier_model": get_query_classifier_model(),
        "rerank_model": get_rerank_model(),
    }
    classification.setdefault("_models", debug_models)

    return RetrievalContext(
        query=query,
        classification=classification,
        pinecone_filter=pinecone_filter,
        filtered_chunks=filtered_chunks,
        unfiltered_chunks=unfiltered_chunks,
        merged_chunks=merged_chunks,
        ranked_chunks=ranked_chunks,
        rerank_debug=rerank_debug,
    )
