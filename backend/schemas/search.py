from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, HttpUrl


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=20_000)
    alpha: float = Field(default=0.5, ge=0.0, le=1.0)
    top_k: int = Field(default=10, ge=1, le=50)
    score_threshold: float = Field(default=0.0, ge=0.0, le=1.0)


class SearchResult(BaseModel):
    title: str
    url: Optional[HttpUrl] = None
    score: float = 0.0
    snippet: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult] = Field(default_factory=list)
