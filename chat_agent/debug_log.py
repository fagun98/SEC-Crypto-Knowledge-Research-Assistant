"""NDJSON debug logging for agent debug mode (session 3af00c)."""

from __future__ import annotations

import json
import time
from typing import Any, Dict

_LOG_PATH = "/Users/fagun/Documents/Work - Num Infomatics/SEC-Crypto-UI/.cursor/debug-3af00c.log"
_SESSION_ID = "3af00c"


def key_fingerprint(key: str) -> str:
    if not key:
        return "empty"
    return f"{key[:7]}...{key[-4:]} len={len(key)}"


def agent_log(
    hypothesis_id: str,
    location: str,
    message: str,
    data: Dict[str, Any] | None = None,
    *,
    run_id: str = "pre-fix",
) -> None:
    # region agent log
    payload = {
        "sessionId": _SESSION_ID,
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data or {},
        "timestamp": int(time.time() * 1000),
    }
    try:
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except OSError:
        pass
    # endregion agent log
