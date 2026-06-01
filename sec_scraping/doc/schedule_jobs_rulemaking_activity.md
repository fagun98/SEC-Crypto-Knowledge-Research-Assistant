# Scheduled job: Rulemaking Activity

[← Schedule jobs index](schedule_jobs.md) · [Scraper doc](rulemaking_activity.md) · [Ingest](ingest.md)

| | |
|--|--|
| **CLI** | `python -m sec_scraping.schedule_jobs.rulemaking_activity` |
| **`sec_dataset`** | `rulemaking-activity` |
| **Parquet** | `dataframes/rulemaking_activity.parquet` |
| **Periods** | No — one full table scrape per run; `--year` / `--period` flags are ignored |

## Examples

```bash
# Scrape entire rulemaking table (no month filter)
python -m sec_scraping.schedule_jobs.rulemaking_activity --mode scrap

# Scrape then embed pending rows
python -m sec_scraping.schedule_jobs.rulemaking_activity --mode pipeline

# List-only scrape (faster)
python -m sec_scraping.schedule_jobs.rulemaking_activity --mode scrap --no-context

python -m sec_scraping.schedule_jobs.rulemaking_activity --mode embed --dry-run
```
