"""Demo entry point for SEC table scraping."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from sec_scraping.pages.crypto_newsroom import (
    DATAFRAME_PATH as NEWSROOM_PATH,
    scrape_crypto_newsroom,
)
from sec_scraping.pages.crypto_task_force_meetings import (
    DATAFRAME_PATH as MEETINGS_PATH,
    scrape_crypto_task_force_meetings,
)
from sec_scraping.pages.crypto_written_input import (
    DATAFRAME_PATH as WRITTEN_INPUT_PATH,
    scrape_crypto_written_input,
)
from sec_scraping.pages.cryptosec import DATAFRAME_PATH as CRYPTOSEC_PATH, scrape_cryptosec
from sec_scraping.pages.rulemaking_activity import (
    DATAFRAME_PATH as RULEMAKING_PATH,
    scrape_rulemaking_activity,
)
from sec_scraping.pages.press_releases import (
    DATAFRAME_PATH as PRESS_RELEASES_PATH,
    scrape_press_releases,
)
from sec_scraping.pages.speeches_statements import (
    DATAFRAME_PATH as SPEECHES_STATEMENTS_PATH,
    scrape_speeches_statements,
)
from sec_scraping.pages.no_action_letters import (
    DATAFRAME_PATH as NO_ACTION_LETTERS_PATH,
    scrape_no_action_letters,
)
from sec_scraping.pages.whats_new import DATAFRAME_PATH as WHATS_NEW_PATH, scrape_whats_new

RECORD_SEPARATOR = "*" * 50
CONTEXT_PREVIEW_LEN = 100

_TITLE_FIELDS = (
    "title",
    "headline",
    "written_input",
    "participants_associated_materials",
    "statement",
    "rulemaking",
)
_SPEAKER_FIELDS = ("speaker", "speaker_division")


def _detail_url_from_row(row: Any) -> str:
    # Prefer the "main" detail link per table.
    for key in (
        "title_url",
        "written_input_url",
        "participants_associated_materials_url",
        "statement_url",
        "status_url",
    ):
        if key in row.index and row.get(key):
            return str(row.get(key))

    # Fallback: any other *_url except `source_list_url`.
    for key in row.index:
        if key.endswith("_url") and key != "source_list_url" and row.get(key):
            return str(row.get(key))
    return ""


def _is_pdf_url(url: str) -> bool:
    if not url:
        return False
    u = str(url).strip().lower()
    if not u or u == "nan":
        return False
    u = u.split("?", 1)[0].split("#", 1)[0]
    return u.endswith(".pdf") or ".pdf" in u


def _resolved_path(path: Path) -> Path:
    if path.exists():
        return path
    csv_path = path.with_suffix(".csv")
    if csv_path.exists():
        return csv_path
    return path


def _parse_resources(raw: Any) -> list:
    if raw is None:
        return []
    s = str(raw).strip()
    if not s or s.lower() == "nan":
        return []
    try:
        data = json.loads(s)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _row_label(row: Any, fields: tuple[str, ...]) -> str:
    for field in fields:
        if field in row.index:
            value = row.get(field)
            if value is not None and str(value).strip():
                return str(value).strip()
    return ""


def _print_records(df, *, section: str, path: Path) -> None:
    print(f"\n=== {section} ===")
    print(f"Rows: {len(df)}, saved to {_resolved_path(path)}\n")
    if df.empty:
        return
    for idx, (_, row) in enumerate(df.iterrows()):
        if idx > 0:
            print(RECORD_SEPARATOR)
        label = _row_label(row, _TITLE_FIELDS)
        speaker = _row_label(row, _SPEAKER_FIELDS)
        context = str(row.get("context", "") or "")
        detail_url = _detail_url_from_row(row)
        is_file = _is_pdf_url(detail_url)

        preview_start = context[:CONTEXT_PREVIEW_LEN]
        preview_end = context[-CONTEXT_PREVIEW_LEN:] if len(context) > 0 else ""
        is_context_small = len(context) <= (CONTEXT_PREVIEW_LEN * 2)

        vectorized = bool(row.get("vectorized", False))
        print(f"title: {label}")
        if speaker:
            print(f"speaker: {speaker}")
        print(f"vectorized: {vectorized}")
        if is_file:
            # For file-based rows (PDFs), show the first and last 100 chars.
            if is_context_small:
                print(f"context_start: {context}")
                print(f"context_end: {context}")
            else:
                print(f"context_start: {preview_start}")
                print(f"context_end: {preview_end}")
        else:
            preview = preview_start
            if len(context) > CONTEXT_PREVIEW_LEN:
                preview += "..."
            print(f"context: {preview}")

        resources = _parse_resources(row.get("resources"))
        print(f"resources_count: {len(resources)}")
        if resources:
            first = resources[0]
            print(f"resource[0] label: {first.get('label', '')}")
            print(f"resource[0] url: {first.get('url', '')}")
            r_ctx = str(first.get("context", "") or "")
            if r_ctx:
                preview = r_ctx[:CONTEXT_PREVIEW_LEN]
                if len(r_ctx) > CONTEXT_PREVIEW_LEN:
                    preview += "..."
                print(f"resource[0] context: {preview}")


def main() -> None:
    scrapers = [
        # ("Crypto Newsroom", NEWSROOM_PATH, lambda: scrape_crypto_newsroom(year=2026, month=3)),
        # (
        #     "Crypto Written Input",
        #     WRITTEN_INPUT_PATH,
        #     lambda: scrape_crypto_written_input(year=2026, month=3),
        # ),
        # (
        #     "Crypto Task Force Meetings",
        #     MEETINGS_PATH,
        #     lambda: scrape_crypto_task_force_meetings(year=2026, month=3),
        # ),
        # ("Crypto@SEC", CRYPTOSEC_PATH, lambda: scrape_cryptosec(year=2026, month=3)),
        # ("Rulemaking Activity", RULEMAKING_PATH, scrape_rulemaking_activity),
        # (
        #     "What's New",
        #     WHATS_NEW_PATH,
        #     lambda: scrape_whats_new(year=2026, month=3),
        # ),
        # (
        #     "Press Releases",
        #     PRESS_RELEASES_PATH,
        #     lambda: scrape_press_releases(year=2026, month=3),
        # ),
        # (
        #     "Speeches and Statements",
        #     SPEECHES_STATEMENTS_PATH,
        #     lambda: scrape_speeches_statements(year=2026, month=3),
        # ),
        (
            "No-Action Letters",
            NO_ACTION_LETTERS_PATH,
            lambda: scrape_no_action_letters(test_mode=True),
        ),
    ]

    for section, path, run in scrapers:
        df = run()
        _print_records(df, section=section, path=path)


if __name__ == "__main__":
    main()
