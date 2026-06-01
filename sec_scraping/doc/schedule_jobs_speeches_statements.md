# Scheduled job: Speeches and Statements

[← Schedule jobs index](schedule_jobs.md) · [Scraper doc](speeches_statements.md) · [Ingest](ingest.md)

| | |
|--|--|
| **CLI** | `python -m sec_scraping.schedule_jobs.speeches_statements` |
| **`sec_dataset`** | `speeches-statements` |
| **Parquet** | `dataframes/speeches_statements.parquet` |
| **Periods** | Yes |

## Examples

```bash
python -m sec_scraping.schedule_jobs.speeches_statements --mode scrap
python -m sec_scraping.schedule_jobs.speeches_statements --mode pipeline --year 2025
python -m sec_scraping.schedule_jobs.speeches_statements --mode scrap --period 2025-03 --period 2026-04
python -m sec_scraping.schedule_jobs.speeches_statements --mode test
```
