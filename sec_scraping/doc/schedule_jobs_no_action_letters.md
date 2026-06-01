# Scheduled job: No-Action Letters

[← Schedule jobs index](schedule_jobs.md) · [Scraper doc](no_action_letters.md) · [Ingest](ingest.md)

| | |
|--|--|
| **CLI** | `python -m sec_scraping.schedule_jobs.no_action_letters` |
| **`sec_dataset`** | `no-action-letters` |
| **Parquet** | `dataframes/no_action_letters.parquet` |
| **Periods** | No — three division index pages; `--year` / `--period` flags are ignored |

In **`test`** mode, scrape passes `test_mode=True` (first 2 and last 2 list items per division).

## Examples

```bash
# Full scrape (all divisions)
python -m sec_scraping.schedule_jobs.no_action_letters --mode scrap

# Smoke: limited list items + one embed row
python -m sec_scraping.schedule_jobs.no_action_letters --mode test

# Scrape then embed
python -m sec_scraping.schedule_jobs.no_action_letters --mode pipeline

python -m sec_scraping.schedule_jobs.no_action_letters --mode embed
```
