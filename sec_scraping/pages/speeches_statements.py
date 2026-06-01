from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

import pandas as pd

from sec_scraping.core import merge_whats_new_rows, run_paginated_table_scraper

BASE_URL = "https://www.sec.gov/newsroom/speeches-statements"
_PACKAGE_DIR = Path(__file__).resolve().parent.parent
DATAFRAME_PATH = _PACKAGE_DIR / "dataframes" / "speeches_statements.parquet"

EXPECTED_HEADERS = ["Date", "Title", "Speaker", "Type"]


def build_speeches_statements_list_url(
    *,
    base_url: str,
    year: int,
    month: int,
    page: int = 0,
    field_person_target_id: str = "",
    speaker: str = "",
    news_type: str = "All",
) -> str:
    params = {
        "field_person_target_id": field_person_target_id,
        "year": year,
        "month": month,
        "speaker": speaker,
        "news_type": news_type,
        "page": page,
    }
    return f"{base_url}?{urlencode(params)}"


def scrape_speeches_statements(
    *,
    year: int = 2026,
    month: int = 3,
    field_person_target_id: str = "",
    speaker: str = "",
    news_type: str = "All",
    max_pages: Optional[int] = None,
    fetch_context: bool = True,
) -> pd.DataFrame:
    """Paginate speeches and statements list, filter by month/year, enrich title_url detail pages."""
    build_url = partial(
        build_speeches_statements_list_url,
        field_person_target_id=field_person_target_id,
        speaker=speaker,
        news_type=news_type,
    )
    return run_paginated_table_scraper(
        base_url=BASE_URL,
        dataframe_path=DATAFRAME_PATH,
        expected_headers=EXPECTED_HEADERS,
        year=year,
        month=month,
        max_pages=max_pages,
        fetch_context=fetch_context,
        build_list_url=build_url,
        merge_fn=merge_whats_new_rows,
    )
