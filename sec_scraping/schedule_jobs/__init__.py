"""Scheduled scrape and embed jobs for SEC scraping pages."""

from sec_scraping.schedule_jobs._common import YearMonth, run_page_job

__all__ = ["YearMonth", "run_page_job"]
