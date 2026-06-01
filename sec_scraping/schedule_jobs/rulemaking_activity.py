"""Scheduled job: Rulemaking Activity."""

from __future__ import annotations

from sec_scraping.pages.rulemaking_activity import (
    DATAFRAME_PATH,
    scrape_rulemaking_activity,
)
from sec_scraping.schedule_jobs._common import run_page_job

PAGE_NAME = "Rulemaking Activity"
DATASET = "rulemaking-activity"


def main(argv=None) -> int:
    return run_page_job(
        page_name=PAGE_NAME,
        dataset=DATASET,
        dataframe_path=DATAFRAME_PATH,
        scrape_fn=scrape_rulemaking_activity,
        supports_periods=False,
        argv=argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
