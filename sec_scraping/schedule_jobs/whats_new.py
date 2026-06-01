"""Scheduled job: What's New."""

from __future__ import annotations

from sec_scraping.pages.whats_new import DATAFRAME_PATH, scrape_whats_new
from sec_scraping.schedule_jobs._common import run_page_job

PAGE_NAME = "What's New"
DATASET = "whats-new"


def main(argv=None) -> int:
    return run_page_job(
        page_name=PAGE_NAME,
        dataset=DATASET,
        dataframe_path=DATAFRAME_PATH,
        scrape_fn=scrape_whats_new,
        supports_periods=True,
        argv=argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
