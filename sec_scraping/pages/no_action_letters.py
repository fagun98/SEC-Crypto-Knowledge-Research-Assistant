from __future__ import annotations

from pathlib import Path

import pandas as pd

from sec_scraping.core import run_no_action_list_scraper

DIVISIONS = [
    (
        "corporation_finance",
        "https://www.sec.gov/rules-regulations/no-action-interpretive-exemptive-letters/"
        "division-corporation-finance-no-action",
    ),
    (
        "investment_management",
        "https://www.sec.gov/rules-regulations/no-action-interpretive-exemptive-letters/"
        "division-investment-management-staff-no-action-interpretive-letters",
    ),
    (
        "trading_markets",
        "https://www.sec.gov/rules-regulations/no-action-interpretive-exemptive-letters/"
        "division-trading-markets-no-action",
    ),
]

_PACKAGE_DIR = Path(__file__).resolve().parent.parent
DATAFRAME_PATH = _PACKAGE_DIR / "dataframes" / "no_action_letters.parquet"


def scrape_no_action_letters(
    *,
    fetch_context: bool = True,
    test_mode: bool = False,
) -> pd.DataFrame:
    """Scrape no-action letter lists from three SEC divisions; dedupe by list_item_id."""
    return run_no_action_list_scraper(
        divisions=DIVISIONS,
        dataframe_path=DATAFRAME_PATH,
        fetch_context=fetch_context,
        test_mode=test_mode,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Scrape SEC no-action letter index pages.")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Only process first 2 and last 2 parseable list items per division.",
    )
    parser.add_argument(
        "--no-context",
        action="store_true",
        help="Skip fetching PDF/HTML detail content.",
    )
    args = parser.parse_args()
    scrape_no_action_letters(
        fetch_context=not args.no_context,
        test_mode=args.test,
    )
