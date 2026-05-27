from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

import pandas as pd

from sec_scraping.core import merge_whats_new_rows, run_paginated_table_scraper

BASE_URL = "https://www.sec.gov/newsroom/whats-new"
_PACKAGE_DIR = Path(__file__).resolve().parent.parent
DATAFRAME_PATH = _PACKAGE_DIR / "dataframes" / "whats_new.parquet"

EXPECTED_HEADERS = ["Date", "Title", "Division/Office"]


def build_whats_new_list_url(
    *,
    base_url: str,
    year: int,
    month: int,
    page: int = 0,
    search: str = "",
    division: str = "All",
    tag: str = "36696",
    type_param: str = "news,secarticle,link",
) -> str:
    params = {
        "search": search,
        "year": year,
        "month": month,
        "division": division,
        "tag": tag,
        "type": type_param,
        "page": page,
    }
    # print("="*50)
    # print(f"{base_url}?{urlencode(params)}")
    # print("="*50)
    return f"{base_url}?{urlencode(params)}"


def scrape_whats_new(
    *,
    year: int = 2026,
    month: int = 3,
    division: str = "All",
    tag: str = "36696",
    type_param: str = "news,secarticle,link",
    max_pages: Optional[int] = None,
    fetch_context: bool = True,
) -> pd.DataFrame:
    """Paginate What's New list, filter by month/year, enrich title_url detail pages."""
    build_url = partial(
        build_whats_new_list_url,
        division=division,
        tag=tag,
        type_param=type_param,
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
