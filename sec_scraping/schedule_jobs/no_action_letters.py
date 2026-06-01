"""Scheduled job: No-Action Letters."""

from __future__ import annotations

from sec_scraping.pages.no_action_letters import (
    DATAFRAME_PATH,
    scrape_no_action_letters,
)
from sec_scraping.schedule_jobs._common import run_page_job

PAGE_NAME = "No-Action Letters"
DATASET = "no-action-letters"


def main(argv=None) -> int:
    return run_page_job(
        page_name=PAGE_NAME,
        dataset=DATASET,
        dataframe_path=DATAFRAME_PATH,
        scrape_fn=scrape_no_action_letters,
        supports_periods=False,
        scrape_uses_test_mode=True,
        argv=argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
