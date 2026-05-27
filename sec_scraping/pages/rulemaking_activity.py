from __future__ import annotations

from pathlib import Path

import pandas as pd

from sec_scraping.core import (
    fetch_html,
    load_dataframe,
    merge_rulemaking_rows,
    parse_html_table,
    save_dataframe,
)

BASE_URL = "https://www.sec.gov/rules-regulations/rulemaking-activity"
_PACKAGE_DIR = Path(__file__).resolve().parent.parent
DATAFRAME_PATH = _PACKAGE_DIR / "dataframes" / "rulemaking_activity.parquet"

EXPECTED_HEADERS = ["Issue Date", "File Number", "Rulemaking", "Status"]


def scrape_rulemaking_activity(*, fetch_context: bool = True) -> pd.DataFrame:
    """Scrape rulemaking activity table and enrich rows from Status detail URLs."""
    df = load_dataframe(DATAFRAME_PATH)
    html = fetch_html(BASE_URL)
    rows = parse_html_table(html, expected_headers=EXPECTED_HEADERS)
    if rows:
        df, _ = merge_rulemaking_rows(
            df,
            rows,
            source_list_url=BASE_URL,
            fetch_context=fetch_context,
        )
        save_dataframe(df, DATAFRAME_PATH)
    return df
