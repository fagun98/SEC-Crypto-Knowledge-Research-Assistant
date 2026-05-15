#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
for p in (_REPO_ROOT, _SCRIPT_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from sec_crawl_handler import (
    add_crawl_arguments,
    crawl_config_from_args,
    run_crawl_job,
)


def parse_time_hhmm(value: str) -> tuple[int, int]:
    parts = value.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid time {value!r}; expected HH:MM")
    hour, minute = int(parts[0]), int(parts[1])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"Invalid time {value!r}; hour/minute out of range")
    return hour, minute


def seconds_until_next(at: str, *, now: datetime | None = None) -> float:
    """Seconds until the next local-time occurrence of HH:MM."""
    hour, minute = parse_time_hhmm(at)
    current = now or datetime.now()
    target = current.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= current:
        target += timedelta(days=1)
    return (target - current).total_seconds()


def next_run_at(at: str, *, now: datetime | None = None) -> datetime:
    current = now or datetime.now()
    delta = seconds_until_next(at, now=current)
    return current + timedelta(seconds=delta)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Schedule SEC crawl ingest daily at a fixed local time (default 10:00 AM).",
        epilog=(
            "Examples:\n"
            "  python scripts/sec_crawl_scheduler_handler.py\n"
            "  python scripts/sec_crawl_scheduler_handler.py --at 09:30\n"
            "  python scripts/sec_crawl_scheduler_handler.py --run-once\n"
            "\n"
            "Cron (daily at 10:00):\n"
            "  0 10 * * * cd /path/to/SEC-Crypto-UI && python scripts/sec_crawl_scheduler_handler.py --run-once\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--at",
        type=str,
        default="10:00",
        help="Daily run time in local timezone (HH:MM, 24-hour).",
    )
    ap.add_argument(
        "--run-once",
        action="store_true",
        help="Run the crawl job once immediately and exit (for cron/launchd).",
    )
    add_crawl_arguments(ap)
    args = ap.parse_args()

    try:
        parse_time_hhmm(args.at)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    config = crawl_config_from_args(args)

    if args.run_once:
        print("Running crawl job once (run-once mode).")
        return run_crawl_job(config)

    print(
        f"SEC crawl scheduler started. Daily run at {args.at} (local), "
        f"max_pages={config.max_pages}, batch_size={config.batch_size}."
    )
    print("Press Ctrl+C to stop.\n")

    while True:
        nxt = next_run_at(args.at)
        wait_s = seconds_until_next(args.at)
        print(f"Next crawl scheduled at {nxt.strftime('%Y-%m-%d %H:%M:%S')} "
              f"(sleeping {wait_s:.0f}s).")
        time.sleep(wait_s)

        started = datetime.now()
        print(f"\n=== Crawl job starting at {started.strftime('%Y-%m-%d %H:%M:%S')} ===")
        exit_code = run_crawl_job(config)
        finished = datetime.now()
        elapsed = finished - started
        print(
            f"=== Crawl job finished at {finished.strftime('%Y-%m-%d %H:%M:%S')} "
            f"(exit={exit_code}, elapsed={elapsed}) ===\n"
        )


if __name__ == "__main__":
    raise SystemExit(main())
