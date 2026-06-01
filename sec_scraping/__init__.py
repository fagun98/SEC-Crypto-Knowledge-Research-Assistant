"""SEC.gov table scraping pipeline with deduplicated DataFrame persistence."""

from sec_scraping.ingest import run_ingest

__all__ = ["run_ingest"]
