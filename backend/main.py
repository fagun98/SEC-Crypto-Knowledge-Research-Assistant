from __future__ import annotations

import sys
from pathlib import Path

# Keep the documented `cd backend && uvicorn main:app` command working while
# preserving package imports when the app is launched from the repository root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI

from backend.api import chat, reports, search
from backend.core.config import get_settings
from backend.core.cors import configure_cors


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="API gateway for source-grounded SEC cryptocurrency research.",
)
configure_cors(app, settings)

app.include_router(chat.router, prefix=settings.api_prefix)
app.include_router(search.router, prefix=settings.api_prefix)
app.include_router(reports.router, prefix=settings.api_prefix)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}
