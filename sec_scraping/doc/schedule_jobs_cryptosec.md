# Scheduled job: Crypto@SEC

[← Schedule jobs index](schedule_jobs.md) · [Scraper doc](cryptosec.md) · [Ingest](ingest.md)

| | |
|--|--|
| **CLI** | `python -m sec_scraping.schedule_jobs.cryptosec` |
| **`sec_dataset`** | `cryptosec` |
| **Parquet** | `dataframes/cryptosec.parquet` |
| **Periods** | Yes |

## Examples

```bash
python -m sec_scraping.schedule_jobs.cryptosec --mode scrap
python -m sec_scraping.schedule_jobs.cryptosec --mode scrap --year 2025
python -m sec_scraping.schedule_jobs.cryptosec --mode embed
python -m sec_scraping.schedule_jobs.cryptosec --mode pipeline --period 2026-03 --period 2026-04
```
