from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from sec_scraping.core import run_paginated_table_scraper

BASE_URL = "https://www.sec.gov/featured-topics/crypto-task-force/cryptosec"
_PACKAGE_DIR = Path(__file__).resolve().parent.parent
DATAFRAME_PATH = _PACKAGE_DIR / "dataframes" / "cryptosec.parquet"

EXPECTED_HEADERS = ["Date", "Speaker/Division", "Statement", "Summary"]


def scrape_cryptosec(
    *,
    year: int = 2026,
    month: int = 3,
    max_pages: Optional[int] = None,
    fetch_context: bool = True,
) -> pd.DataFrame:
    """Paginate Crypto@SEC list, dedupe by row_key, enrich HTML and PDF detail links."""
    return run_paginated_table_scraper(
        base_url=BASE_URL,
        dataframe_path=DATAFRAME_PATH,
        expected_headers=EXPECTED_HEADERS,
        year=year,
        month=month,
        max_pages=max_pages,
        fetch_context=fetch_context,
    )
