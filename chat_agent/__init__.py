"""RAG chat agent: retrieval, rerank, and HTML answer generation."""

from chat_agent import env as _env  # noqa: F401 — load .env before OpenAI/Pinecone

from chat_agent.answer_agent import ChatAnswer, generate_answer
from chat_agent.data_collector import RetrievalContext, collect_context
from chat_agent.types import RetrievedChunk

__all__ = [
    "ChatAnswer",
    "RetrievalContext",
    "collect_context",
    "generate_answer",
]
