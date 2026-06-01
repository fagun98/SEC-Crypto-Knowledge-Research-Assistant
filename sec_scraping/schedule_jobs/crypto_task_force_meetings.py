"""Scheduled job: Crypto Task Force Meetings."""

from __future__ import annotations

from sec_scraping.pages.crypto_task_force_meetings import (
    DATAFRAME_PATH,
    scrape_crypto_task_force_meetings,
)
from sec_scraping.schedule_jobs._common import run_page_job

PAGE_NAME = "Crypto Task Force Meetings"
DATASET = "crypto-task-force-meetings"


def main(argv=None) -> int:
    return run_page_job(
        page_name=PAGE_NAME,
        dataset=DATASET,
        dataframe_path=DATAFRAME_PATH,
        scrape_fn=scrape_crypto_task_force_meetings,
        supports_periods=True,
        argv=argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
