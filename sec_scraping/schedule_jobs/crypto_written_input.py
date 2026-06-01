"""Scheduled job: Crypto Written Input."""

from __future__ import annotations

from sec_scraping.pages.crypto_written_input import (
    DATAFRAME_PATH,
    scrape_crypto_written_input,
)
from sec_scraping.schedule_jobs._common import run_page_job

PAGE_NAME = "Crypto Written Input"
DATASET = "crypto-written-input"


def main(argv=None) -> int:
    return run_page_job(
        page_name=PAGE_NAME,
        dataset=DATASET,
        dataframe_path=DATAFRAME_PATH,
        scrape_fn=scrape_crypto_written_input,
        supports_periods=True,
        argv=argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
