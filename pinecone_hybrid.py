from __future__ import annotations

import os
import streamlit as st
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv
from pinecone import Pinecone

from utils import get_dense_embedder, get_sparse_embedder

load_dotenv()

PINECONE_API_KEY = st.secrets["PINECONE_API_KEY"] or os.getenv("PINECONE_API_KEY", "")
PINECONE_INDEX = st.secrets["PINECONE_INDEX"] or os.getenv("PINECONE_INDEX", "")
PINECONE_NAMESPACE = st.secrets["PINECONE_NAMESPACE"] or os.getenv("PINECONE_NAMESPACE", "")


@dataclass
class PineconeVectorDB:
    """Base class for Pinecone vector database operations."""


    def __init__(self, score_threshold: float = 0.5) -> None:
        """Initialize Pinecone connection and embedders."""
        if not PINECONE_API_KEY:
            raise RuntimeError("PINECONE_API_KEY is not set in the environment.")
        if not PINECONE_INDEX:
            raise RuntimeError("PINECONE_INDEX is not set in the environment.")

        self.pc = Pinecone(api_key=PINECONE_API_KEY)
        self.index_name = PINECONE_INDEX
        self.index = self.pc.Index(self.index_name)
        self.embedder = get_dense_embedder()
        self.namespace: str = PINECONE_NAMESPACE
        self.score_threshold: float = score_threshold
        self.splade_encoder = get_sparse_embedder()

    
    @staticmethod
    def hybrid_score_norm(
        dense: List[float],
        sparse: Dict[str, List[float]],
        alpha: float = 0.5,
    ) -> Tuple[List[float], Dict[str, List[float]]]:
        """
        Hybrid score using a convex combination:
            alpha * dense + (1 - alpha) * sparse

        Args:
            dense: list of floats representing dense query embedding.
            sparse: a dict with `indices` and `values` for SPLADE.
            alpha: scale between 0 and 1.

        Returns:
            Tuple of (normalized dense vector, normalized sparse vector).
        """
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
        include_scores: bool = False,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """
        Fetch top_k records from Pinecone using hybrid dense + sparse scoring.

        Args:
            query: Search query string.
            top_k: Number of results to return.
            alpha: Blend factor between dense (1.0) and sparse (0.0) search.
            include_scores: Whether to include score and ID in results.
            **kwargs: Additional arguments passed to Pinecone query.

        Returns:
            List of metadata dicts (optionally with scores).
        """
        if not query.strip():
            return []

        # Dense embedding from OpenAI (via langchain)
        dense_query_vector = self.embedder.embed_query(query)

        # Sparse representation from SPLADE
        sparse_query_vector = self.splade_encoder.encode_documents([query])[0]

        dense_vector, sparse_vector = self.hybrid_score_norm(
            dense_query_vector, sparse_query_vector, alpha
        )

        response = self.index.query(
            namespace=self.namespace or None,
            top_k=top_k,
            vector=dense_vector,
            sparse_vector=sparse_vector,
            include_metadata=True,
            **kwargs,
        )

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

def get_pinecone_hybrid_db(
    score_threshold: float = 0.5,
) -> PineconeVectorDB:
    """
    Convenience factory to create a configured PineconeVectorDB.

    Args:
        namespace: Pinecone namespace to query.
        score_threshold: Minimum score threshold for results.

    Returns:
        Configured PineconeVectorDB instance.
    """
    return PineconeVectorDB(score_threshold=score_threshold)

def main():
    """Demo function to test hybrid search with different alpha values."""
    # Initialize the database
    db = get_pinecone_hybrid_db(score_threshold=0.5)
    
    # Test query
    test_query = "To the extent possible and appropriate in the public interest under existing statutes, the Securities and Exchange Commission and the Commodity Futures Trading Commission should consider harmonizing product and venue definitions;"
    
    print(f"Testing query: '{test_query}'\n")
    print("=" * 80)
    
    # Test with different alpha values
    alphas = [0.0, 0.5, 1.0]  # sparse-only, balanced, dense-only
    
    for alpha in alphas:
        print(f"\nAlpha = {alpha} ({'sparse-only' if alpha == 0.0 else 'dense-only' if alpha == 1.0 else 'balanced'})")
        print("-" * 80)
        
        results = db.fetch(
            query=test_query,
            top_k=5,
            alpha=alpha,
            include_scores=True
        )
        
        if results:
            for idx, result in enumerate(results, 1):
                title = result.get("title", result.get("_id", f"Result {idx}"))
                score = result.get("_score", "N/A")
                print(f"{idx}. {title}")
                print(f"   Score: {score}")
                if "text" in result:
                    snippet = result["text"][:100] + "..." if len(result.get("text", "")) > 100 else result.get("text", "")
                    print(f"   Snippet: {snippet}")
                print()
        else:
            print("No results found.\n")
    
    print("=" * 80)


if __name__ == "__main__":
    main()

