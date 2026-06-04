"""
OpenAI model IDs and role mapping for the RAG chat agent.

Brain: gpt-5.4-mini — answer synthesis
Nano: gpt-5.4-nano — query classify, rerank, ingest classify

See chat_agent/MODELS.md for pricing vs gpt-5-mini / gpt-5-nano.
"""

from __future__ import annotations

from chat_agent.env import getenv, load_dotenv_env

load_dotenv_env()

from utils import get_brain_model, get_nano_model

GPT_54_MINI = "gpt-5.4-mini"
GPT_54_NANO = "gpt-5.4-nano"
GPT_5_MINI = "gpt-5-mini"
GPT_5_NANO = "gpt-5-nano"


def get_rerank_model() -> str:
    return getenv("CHAT_RERANK_MODEL") or get_nano_model()


def get_query_classifier_model() -> str:
    return getenv("CRI_QUERY_CLASSIFIER_MODEL") or get_nano_model()
