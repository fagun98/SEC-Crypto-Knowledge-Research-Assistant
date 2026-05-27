from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from sec_scraping.core import run_single_page_table_scraper

BASE_URL = (
    "https://www.sec.gov/featured-topics/crypto-task-force/crypto-task-force-meetings"
)
_PACKAGE_DIR = Path(__file__).resolve().parent.parent
DATAFRAME_PATH = _PACKAGE_DIR / "dataframes" / "crypto_task_force_meetings.parquet"

EXPECTED_HEADERS = ["Date", "Participants & Associated Materials"]


def scrape_crypto_task_force_meetings(
    *,
    year: int = 2026,
    month: int = 3,
    fetch_context: bool = True,
) -> pd.DataFrame:
    """Scrape meetings table (single page, mostly PDF detail links)."""
    return run_single_page_table_scraper(
        list_url=BASE_URL,
        dataframe_path=DATAFRAME_PATH,
        expected_headers=EXPECTED_HEADERS,
        fetch_context=fetch_context,
        year=year,
        month=month,
    )
