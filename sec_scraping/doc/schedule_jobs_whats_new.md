# Scheduled job: What's New

[← Schedule jobs index](schedule_jobs.md) · [Scraper doc](whats_new.md) · [Ingest](ingest.md)

| | |
|--|--|
| **CLI** | `python -m sec_scraping.schedule_jobs.whats_new` |
| **`sec_dataset`** | `whats-new` |
| **Parquet** | `dataframes/whats_new.parquet` |
| **Periods** | Yes |

## Examples

```bash
python -m sec_scraping.schedule_jobs.whats_new --mode scrap
python -m sec_scraping.schedule_jobs.whats_new --mode scrap --from 2025-03 --to 2025-09
python -m sec_scraping.schedule_jobs.whats_new --mode pipeline --year 2025
python -m sec_scraping.schedule_jobs.whats_new --mode test --verbose
```
