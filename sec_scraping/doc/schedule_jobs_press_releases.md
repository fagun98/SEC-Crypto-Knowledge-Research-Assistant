# Scheduled job: Press Releases

[← Schedule jobs index](schedule_jobs.md) · [Scraper doc](press_releases.md) · [Ingest](ingest.md)

| | |
|--|--|
| **CLI** | `python -m sec_scraping.schedule_jobs.press_releases` |
| **`sec_dataset`** | `press-releases` |
| **Parquet** | `dataframes/press_releases.parquet` |
| **Periods** | Yes |

## Examples

```bash
python -m sec_scraping.schedule_jobs.press_releases --mode scrap
python -m sec_scraping.schedule_jobs.press_releases --mode scrap --year 2025
python -m sec_scraping.schedule_jobs.press_releases --mode pipeline --from 2025-03 --to 2025-09
python -m sec_scraping.schedule_jobs.press_releases --mode embed --dry-run
```
