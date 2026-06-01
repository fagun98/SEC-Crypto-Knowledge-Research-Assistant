from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

import pandas as pd

from sec_scraping.core import merge_whats_new_rows, run_paginated_table_scraper

BASE_URL = "https://www.sec.gov/newsroom/press-releases"
_PACKAGE_DIR = Path(__file__).resolve().parent.parent
DATAFRAME_PATH = _PACKAGE_DIR / "dataframes" / "press_releases.parquet"

EXPECTED_HEADERS = ["Date", "Headline", "Release No."]


def build_press_releases_list_url(
    *,
    base_url: str,
    year: int,
    month: int,
    page: int = 0,
    combine: str = "",
    field_person_target_id: str = "",
    speaker: str = "",
) -> str:
    params = {
        "combine": combine,
        "year": year,
        "month": month,
        "field_person_target_id": field_person_target_id,
        "speaker": speaker,
        "page": page,
    }
    return f"{base_url}?{urlencode(params)}"


def scrape_press_releases(
    *,
    year: int = 2026,
    month: int = 3,
    combine: str = "",
    field_person_target_id: str = "",
    speaker: str = "",
    max_pages: Optional[int] = None,
    fetch_context: bool = True,
) -> pd.DataFrame:
    """Paginate press releases list, filter by month/year, enrich headline_url detail pages."""
    build_url = partial(
        build_press_releases_list_url,
        combine=combine,
        field_person_target_id=field_person_target_id,
        speaker=speaker,
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
