from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from pinecone import Pinecone

from utils import _get_secret, get_dense_embedder, get_sparse_embedder

load_dotenv()


def _pinecone_config() -> tuple[str, str, str]:
    api_key = _get_secret("PINECONE_API_KEY")
    index_name = _get_secret("PINECONE_INDEX") or _get_secret("PINECONE_INDEX_NAME")
    namespace = _get_secret("PINECONE_NAMESPACE")
    return api_key, index_name, namespace


@dataclass
class PineconeVectorDB:
    """Pinecone hybrid dense + sparse vector search."""

    def __init__(self, score_threshold: float = 0.5) -> None:
        api_key, index_name, namespace = _pinecone_config()
        if not api_key:
            raise RuntimeError("PINECONE_API_KEY is not set in the environment.")
        if not index_name:
            raise RuntimeError("PINECONE_INDEX / PINECONE_INDEX_NAME is not set.")

        self.pc = Pinecone(api_key=api_key)
        self.index_name = index_name
        self.index = self.pc.Index(self.index_name)
        self.embedder = get_dense_embedder()
        self.namespace: str = namespace
        self.score_threshold: float = score_threshold
        self.splade_encoder = get_sparse_embedder()

    @staticmethod
    def hybrid_score_norm(
        dense: List[float],
        sparse: Dict[str, List[float]],
        alpha: float = 0.5,
    ) -> Tuple[List[float], Dict[str, List[float]]]:
        if alpha < 0 or alpha > 1:
            raise ValueError("Alpha must be between 0 and 1")

        hs = {
            "indices": sparse["indices"],
            "values": [v * (1 - alpha) for v in sparse["values"]],
        }
        return [v * alpha for v in dense], hs

    def fetch(
        self,
        query: str,
        top_k: int = 20,
        alpha: float = 0.5,
        include_scores: bool = True,
        filter: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """
        Fetch top_k records from Pinecone using hybrid dense + sparse scoring.
        """
        if not query.strip():
            return []

        dense_query_vector = self.embedder.embed_query(query)
        sparse_query_vector = self.splade_encoder.encode_documents([query])[0]

        dense_vector, sparse_vector = self.hybrid_score_norm(
            dense_query_vector, sparse_query_vector, alpha
        )

        query_kwargs: Dict[str, Any] = {
            "namespace": self.namespace or None,
            "top_k": top_k,
            "vector": dense_vector,
            "sparse_vector": sparse_vector,
            "include_metadata": True,
        }
        if filter:
            query_kwargs["filter"] = filter
        query_kwargs.update(kwargs)

        response = self.index.query(**query_kwargs)

        results: List[Dict[str, Any]] = []
        for match in response.matches:
            if match.score is not None and match.score < self.score_threshold:
                continue
            item: Dict[str, Any] = dict(match.metadata or {})
            if include_scores:
                item["_score"] = match.score
                item["_id"] = match.id
            results.append(item)

        return results


def get_pinecone_hybrid_db(score_threshold: float = 0.5) -> PineconeVectorDB:
    return PineconeVectorDB(score_threshold=score_threshold)


def main() -> None:
    db = get_pinecone_hybrid_db(score_threshold=0.5)
    test_query = "broker-dealer custody requirements for crypto assets"
    print(f"Testing query: '{test_query}'\n")
    for alpha in (0.0, 0.5, 1.0):
        print(f"\nAlpha = {alpha}")
        results = db.fetch(query=test_query, top_k=5, alpha=alpha, include_scores=True)
        for idx, result in enumerate(results, 1):
            title = result.get("title", result.get("_id", f"Result {idx}"))
            print(f"  {idx}. {title} (score={result.get('_score')})")


if __name__ == "__main__":
    main()
