"""Scheduled job: Press Releases."""

from __future__ import annotations

from sec_scraping.pages.press_releases import DATAFRAME_PATH, scrape_press_releases
from sec_scraping.schedule_jobs._common import run_page_job

PAGE_NAME = "Press Releases"
DATASET = "press-releases"


def main(argv=None) -> int:
    return run_page_job(
        page_name=PAGE_NAME,
        dataset=DATASET,
        dataframe_path=DATAFRAME_PATH,
        scrape_fn=scrape_press_releases,
        supports_periods=True,
        argv=argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
