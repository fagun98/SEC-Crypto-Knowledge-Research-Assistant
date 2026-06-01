# Scheduled job: Crypto Newsroom

[← Schedule jobs index](schedule_jobs.md) · [Scraper doc](crypto_newsroom.md) · [Ingest](ingest.md)

| | |
|--|--|
| **CLI** | `python -m sec_scraping.schedule_jobs.crypto_newsroom` |
| **`sec_dataset`** | `crypto-newsroom` |
| **Parquet** | `dataframes/crypto_newsroom.parquet` |
| **Periods** | Yes (month/year list filter) |

## Examples

```bash
# Default: scrape March 2026
python -m sec_scraping.schedule_jobs.crypto_newsroom --mode scrap

# Full year 2025, then embed pending rows
python -m sec_scraping.schedule_jobs.crypto_newsroom --mode pipeline --year 2025

# March–September 2025 only
python -m sec_scraping.schedule_jobs.crypto_newsroom --mode scrap --from 2025-03 --to 2025-09

# Smoke test
python -m sec_scraping.schedule_jobs.crypto_newsroom --mode test

# Embed dry-run
python -m sec_scraping.schedule_jobs.crypto_newsroom --mode embed --dry-run
```
