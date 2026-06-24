from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=50_000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20_000)
    session_id: Optional[str] = Field(default=None, max_length=128)
    history: list[HistoryMessage] = Field(default_factory=list, max_length=50)


class Source(BaseModel):
    title: str = "Source"
    url: Optional[HttpUrl] = None
    score: Optional[float] = None
    snippet: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    session_id: str
    sources: list[Source] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
