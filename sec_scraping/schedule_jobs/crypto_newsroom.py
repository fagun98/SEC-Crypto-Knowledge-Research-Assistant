"""Scheduled job: Crypto Newsroom."""

from __future__ import annotations

from sec_scraping.pages.crypto_newsroom import DATAFRAME_PATH, scrape_crypto_newsroom
from sec_scraping.schedule_jobs._common import run_page_job

PAGE_NAME = "Crypto Newsroom"
DATASET = "crypto-newsroom"


def main(argv=None) -> int:
    return run_page_job(
        page_name=PAGE_NAME,
        dataset=DATASET,
        dataframe_path=DATAFRAME_PATH,
        scrape_fn=scrape_crypto_newsroom,
        supports_periods=True,
        argv=argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
