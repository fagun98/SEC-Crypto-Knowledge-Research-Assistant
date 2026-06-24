from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from backend.core.config import PROJECT_ROOT, get_settings
from backend.schemas.reports import ReportDetail, ReportSummary


SUPPORTED_SUFFIXES = {".txt", ".md", ".markdown"}


def _report_dir() -> Path:
    configured = get_settings().resolved_reports_dir
    if configured.exists():
        return configured
    # This repository's current scheduler writes Markdown newsletters here.
    newsletter_dir = PROJECT_ROOT / "reports" / "newsletter"
    return newsletter_dir if newsletter_dir.exists() else configured


def _date_from_name(path: Path) -> datetime:
    name = path.stem
    patterns = (
        (r"(\d{4})[_-](\d{2})[_-](\d{2})", "%Y-%m-%d"),
        (r"([A-Za-z]{3})_(\d{1,2})_(\d{4})", "%b-%d-%Y"),
        (r"([A-Za-z]{3})_(\d{1,2})_(\d{4})", "%b-%d-%Y"),
    )
    for pattern, date_format in patterns:
        matches = list(re.finditer(pattern, name))
        if matches:
            value = "-".join(matches[-1].groups())
            try:
                return datetime.strptime(value, date_format)
            except ValueError:
                continue
    return datetime.fromtimestamp(path.stat().st_mtime)


def _title_from_content(path: Path, content: str = "") -> str:
    if content:
        heading = next(
            (line.lstrip("# ").strip() for line in content.splitlines() if line.startswith("#")),
            "",
        )
        if heading:
            return heading
    return "Weekly SEC Report"


def _paths() -> list[Path]:
    directory = _report_dir()
    if not directory.exists():
        return []
    paths = [p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES]
    return sorted(paths, key=lambda path: (_date_from_name(path), path.stat().st_mtime), reverse=True)


def list_reports() -> list[ReportSummary]:
    return [
        ReportSummary(
            title="Weekly SEC Report",
            date=_date_from_name(path).date().isoformat(),
            filename=path.name,
        )
        for path in _paths()
    ]


def get_report(filename: str | None = None) -> ReportDetail | None:
    paths = _paths()
    if not paths:
        return None
    if filename:
        safe_name = Path(filename).name
        path = next((item for item in paths if item.name == safe_name), None)
        if path is None:
            return None
    else:
        path = paths[0]
    content = path.read_text(encoding="utf-8", errors="replace")
    return ReportDetail(
        title=_title_from_content(path, content),
        date=_date_from_name(path).date().isoformat(),
        filename=path.name,
        content=content,
    )
