from __future__ import annotations

import os
from typing import Any, Optional

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from pinecone_text.sparse import SpladeEncoder

from chat_agent.env import load_dotenv_env

load_dotenv_env(override=True)


def _get_secret(key: str, default: str = "") -> str:
    """Prefer environment variables; fall back to Streamlit secrets when available."""
    val = os.getenv(key)
    source = "os.environ" if val is not None and str(val).strip() else None
    if source:
        out = str(val).strip()
    else:
        out = default
        try:
            import streamlit as st

            if key in st.secrets:
                s = st.secrets[key]
                if s is not None and str(s).strip():
                    out = str(s).strip()
                    source = "st.secrets"
        except Exception:
            pass
    if key == "OPENAI_API_KEY":
        # region agent log
        try:
            from chat_agent.debug_log import agent_log, key_fingerprint

            agent_log(
                "D",
                "utils.py:_get_secret",
                "OPENAI_API_KEY source",
                {"source": source or "default", "key_fp": key_fingerprint(out)},
            )
        except Exception:
            pass
        # endregion agent log
    return out


def get_dense_embedder() -> OpenAIEmbeddings:
    embedder = OpenAIEmbeddings(
        model=_get_secret("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        api_key=_get_secret("OPENAI_API_KEY"),
    )
    return embedder


def get_sparse_embedder() -> SpladeEncoder:
    return SpladeEncoder()


def embed_dense_documents(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    embedder = get_dense_embedder()
    return embedder.embed_documents(texts)


def embed_sparse_documents(texts: list[str]) -> list[dict[str, list[float]]]:
    if not texts:
        return []
    embedder = get_sparse_embedder()
    return embedder.encode_documents(texts)


def get_brain_model() -> str:
    """Chat answer / synthesis model (default: gpt-5.4-mini)."""
    return (
        _get_secret("CHAT_BRAIN_MODEL")
        or _get_secret("OPENAI_LLM_MODEL")
        or "gpt-5.4-mini"
    )


def get_nano_model() -> str:
    """Classification, rerank, structured JSON (default: gpt-5.4-nano)."""
    return _get_secret("CHAT_NANO_MODEL") or "gpt-5.4-nano"


def get_llm(
    *,
    streaming: bool = False,
    temperature: Optional[float] = None,
    model: Optional[str] = None,
    log_openai_key: bool = False,
) -> ChatOpenAI:
    from chat_agent.env import setup_openai_api_key

    api_key = setup_openai_api_key(log=log_openai_key)
    temp_raw = _get_secret("CHAT_LLM_TEMPERATURE") or _get_secret("OPENAI_TEMPERATURE", "0.2")
    if temperature is None:
        try:
            temperature = float(temp_raw)
        except (TypeError, ValueError):
            temperature = 0.2
    return ChatOpenAI(
        model=model or get_brain_model(),
        api_key=api_key,
        temperature=temperature,
        streaming=streaming,
    )


def get_env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def get_env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default
