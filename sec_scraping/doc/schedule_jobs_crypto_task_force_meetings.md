# Scheduled job: Crypto Task Force Meetings

[← Schedule jobs index](schedule_jobs.md) · [Scraper doc](crypto_task_force_meetings.md) · [Ingest](ingest.md)

| | |
|--|--|
| **CLI** | `python -m sec_scraping.schedule_jobs.crypto_task_force_meetings` |
| **`sec_dataset`** | `crypto-task-force-meetings` |
| **Parquet** | `dataframes/crypto_task_force_meetings.parquet` |
| **Periods** | Yes (single list page; rows filtered by month/year) |

## Examples

```bash
python -m sec_scraping.schedule_jobs.crypto_task_force_meetings --mode scrap
python -m sec_scraping.schedule_jobs.crypto_task_force_meetings --mode scrap --period april-2026
python -m sec_scraping.schedule_jobs.crypto_task_force_meetings --mode pipeline --from 2025-01 --to 2025-12
python -m sec_scraping.schedule_jobs.crypto_task_force_meetings --mode test
```
