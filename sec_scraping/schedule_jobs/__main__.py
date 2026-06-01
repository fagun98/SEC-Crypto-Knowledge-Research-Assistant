"""List or run schedule jobs by module name."""

from __future__ import annotations

import argparse
import importlib
import sys

JOBS = (
    "crypto_newsroom",
    "crypto_written_input",
    "crypto_task_force_meetings",
    "cryptosec",
    "whats_new",
    "press_releases",
    "speeches_statements",
    "rulemaking_activity",
    "no_action_letters",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="SEC schedule jobs: list available jobs or run one by name."
    )
    parser.add_argument(
        "job",
        nargs="?",
        help=f"Job module name. One of: {', '.join(JOBS)}",
    )
    parser.add_argument(
        "job_args",
        nargs=argparse.REMAINDER,
        help="Arguments passed to the job module",
    )
    args, _ = parser.parse_known_args(argv)

    if not args.job:
        print("Available schedule jobs:")
        for name in JOBS:
            print(f"  python -m sec_scraping.schedule_jobs.{name}")
        return 0

    if args.job not in JOBS:
        print(f"Unknown job {args.job!r}. Choose from: {', '.join(JOBS)}", file=sys.stderr)
        return 1

    mod = importlib.import_module(f"sec_scraping.schedule_jobs.{args.job}")
    return mod.main(args.job_args)


if __name__ == "__main__":
    raise SystemExit(main())
