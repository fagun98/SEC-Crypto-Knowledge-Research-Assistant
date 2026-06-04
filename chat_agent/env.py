"""
Load project ``.env`` before OpenAI or Pinecone clients are constructed.

Import this module (or ``from chat_agent.env import load_dotenv_env``) at the top of
any ``chat_agent`` module that uses OpenAI / Pinecone / LangChain OpenAI wrappers.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

_loaded = False
_openai_key_logged = False
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_dotenv_env(*, override: bool = False) -> None:
    """Load ``.env`` from the repo root once (idempotent unless ``override=True``)."""
    global _loaded
    # region agent log
    from chat_agent.debug_log import agent_log, key_fingerprint

    pre = os.getenv("OPENAI_API_KEY") or ""
    agent_log(
        "B",
        "chat_agent/env.py:load_dotenv_env:entry",
        "before load_dotenv",
        {
            "override": override,
            "already_loaded": _loaded,
            "env_key_fp": key_fingerprint(pre),
            "dotenv_path": str(_PROJECT_ROOT / ".env"),
        },
    )
    # endregion agent log
    if _loaded and not override:
        return
    load_dotenv(_PROJECT_ROOT / ".env", override=override)
    _loaded = True
    # region agent log
    post = os.getenv("OPENAI_API_KEY") or ""
    agent_log(
        "B",
        "chat_agent/env.py:load_dotenv_env:exit",
        "after load_dotenv",
        {
            "override": override,
            "env_key_fp": key_fingerprint(post),
            "key_changed": key_fingerprint(pre) != key_fingerprint(post),
        },
    )
    # endregion agent log


# Eager load on import; override=True so project .env wins over stale shell vars.
load_dotenv_env(override=True)


def getenv(name: str, default: str = "") -> str:
    """Read env var after ``.env`` has been loaded."""
    load_dotenv_env()
    val = os.getenv(name)
    if val is None or not str(val).strip():
        return default
    return str(val).strip().strip('"').strip("'")


def setup_openai_api_key(*, log: bool = True) -> str:
    """
    Load ``OPENAI_API_KEY`` from ``.env`` / environment and set ``openai.api_key``.

    Mirrors local notebook usage::

        openai.api_key = os.getenv("OPENAI_API_KEY")

    Logs the key for debugging (full value when ``CHAT_DEBUG_LOG_OPENAI_KEY`` is set,
    otherwise a masked preview).
    """
    load_dotenv_env(override=True)
    key = os.getenv("OPENAI_API_KEY") or ""
    key = key.strip().strip('"').strip("'")
    # region agent log
    from chat_agent.debug_log import agent_log, key_fingerprint

    dotenv_file_key = ""
    try:
        for line in (_PROJECT_ROOT / ".env").read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith("OPENAI_API_KEY") and "=" in s and not s.startswith("#"):
                dotenv_file_key = s.split("=", 1)[1].strip().strip('"').strip("'")
                break
    except OSError:
        pass
    agent_log(
        "C",
        "chat_agent/env.py:setup_openai_api_key",
        "resolved OPENAI_API_KEY",
        {
            "os_env_fp": key_fingerprint(key),
            "dotenv_file_fp": key_fingerprint(dotenv_file_key),
            "matches_dotenv_file": key_fingerprint(key) == key_fingerprint(dotenv_file_key),
        },
    )
    # endregion agent log
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set. Add it to .env or the environment.")

    try:
        import openai as openai_module

        openai_module.api_key = key
        # region agent log
        agent_log(
            "D",
            "chat_agent/env.py:setup_openai_api_key",
            "openai.api_key set",
            {"openai_module_fp": key_fingerprint(getattr(openai_module, "api_key", "") or "")},
        )
        # endregion agent log
    except ImportError:
        pass

    global _openai_key_logged
    if log and not _openai_key_logged:
        debug_full = getenv("CHAT_DEBUG_LOG_OPENAI_KEY").lower() in (
            "1",
            "true",
            "yes",
        )
        if debug_full:
            logger.info("OPENAI_API_KEY=%s", key)
        else:
            masked = f"{key[:7]}...{key[-4:]}" if len(key) > 11 else "***"
            logger.info(
                "OPENAI_API_KEY=%s (set; full key if CHAT_DEBUG_LOG_OPENAI_KEY=1)",
                masked,
            )
        _openai_key_logged = True

    return key


def require_openai_api_key(*, log: bool = True) -> str:
    """Alias for :func:`setup_openai_api_key`."""
    return setup_openai_api_key(log=log)


def require_pinecone_config() -> tuple[str, str, str]:
    api_key = getenv("PINECONE_API_KEY")
    index_name = getenv("PINECONE_INDEX") or getenv("PINECONE_INDEX_NAME")
    namespace = getenv("PINECONE_NAMESPACE")
    if not api_key:
        raise RuntimeError("PINECONE_API_KEY is not set.")
    if not index_name:
        raise RuntimeError("PINECONE_INDEX or PINECONE_INDEX_NAME is not set.")
    return api_key, index_name, namespace
