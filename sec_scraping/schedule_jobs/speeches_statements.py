"""Scheduled job: Speeches and Statements."""

from __future__ import annotations

from sec_scraping.pages.speeches_statements import (
    DATAFRAME_PATH,
    scrape_speeches_statements,
)
from sec_scraping.schedule_jobs._common import run_page_job

PAGE_NAME = "Speeches and Statements"
DATASET = "speeches-statements"


def main(argv=None) -> int:
    return run_page_job(
        page_name=PAGE_NAME,
        dataset=DATASET,
        dataframe_path=DATAFRAME_PATH,
        scrape_fn=scrape_speeches_statements,
        supports_periods=True,
        argv=argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
