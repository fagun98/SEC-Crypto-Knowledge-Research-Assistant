# Scheduled job: Crypto Written Input

[← Schedule jobs index](schedule_jobs.md) · [Scraper doc](crypto_written_input.md) · [Ingest](ingest.md)

| | |
|--|--|
| **CLI** | `python -m sec_scraping.schedule_jobs.crypto_written_input` |
| **`sec_dataset`** | `crypto-written-input` |
| **Parquet** | `dataframes/crypto_written_input.parquet` |
| **Periods** | Yes |

## Examples

```bash
python -m sec_scraping.schedule_jobs.crypto_written_input --mode scrap
python -m sec_scraping.schedule_jobs.crypto_written_input --mode scrap --year 2025
python -m sec_scraping.schedule_jobs.crypto_written_input --mode pipeline --period 2026-03
python -m sec_scraping.schedule_jobs.crypto_written_input --mode test
python -m sec_scraping.schedule_jobs.crypto_written_input --mode embed --limit-rows 5
```
