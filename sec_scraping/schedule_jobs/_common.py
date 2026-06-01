"""Shared CLI, period parsing, logging, and job orchestration for schedule_jobs."""

from __future__ import annotations

import argparse
import logging
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, List, Optional, Sequence, Tuple

import pandas as pd
from tqdm import tqdm

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from sec_scraping.core import load_dataframe
from sec_scraping.ingest import IngestPageStats, run_ingest

logger = logging.getLogger("sec_scraping.schedule_jobs")

DEFAULT_YEAR = 2026
DEFAULT_MONTH = 3

ScrapeFn = Callable[..., pd.DataFrame]

_YEAR_MONTH_RE = re.compile(r"^(\d{4})-(\d{1,2})$")
_MONTH_NAME_RE = re.compile(
    r"^(january|february|march|april|may|june|july|august|september|october|november|december)"
    r"[-\s]+(\d{4})$",
    re.IGNORECASE,
)


@dataclass(frozen=True, order=True)
class YearMonth:
    year: int
    month: int

    def label(self) -> str:
        return f"{self.year}-{self.month:02d}"


@dataclass
class ScrapePeriodStats:
    period: Optional[YearMonth]
    rows_before: int
    rows_after: int

    @property
    def rows_added(self) -> int:
        return max(0, self.rows_after - self.rows_before)


@dataclass
class JobSummary:
    page_name: str
    dataset: str
    mode: str
    dataframe_path: Path
    periods_run: int = 0
    rows_added: int = 0
    total_rows: int = 0
    period_stats: List[ScrapePeriodStats] = field(default_factory=list)
    ingest_stats: Optional[IngestPageStats] = None

    def print_summary(self) -> None:
        print(f"\n=== Job summary: {self.dataset} ({self.mode}) ===")
        print(f"  page:            {self.page_name}")
        print(f"  dataframe:       {self.dataframe_path}")
        if self.period_stats or self.mode in ("scrap", "pipeline", "test"):
            print(f"  periods_run:     {self.periods_run}")
            print(f"  rows_added:      {self.rows_added}")
            print(f"  total_rows:      {self.total_rows}")
        for ps in self.period_stats:
            label = ps.period.label() if ps.period else "all"
            print(
                f"    {label}: +{ps.rows_added} rows "
                f"({ps.rows_before} -> {ps.rows_after})"
            )
        if self.ingest_stats is not None:
            s = self.ingest_stats
            if s.dry_run:
                print(
                    f"  ingest:          processed={s.rows_processed} "
                    f"chunks={s.chunks_upserted} failures={s.failures}"
                )
            else:
                print(
                    f"  ingest:          embedded={s.rows_embedded} "
                    f"chunks={s.chunks_upserted} skipped={s.rows_skipped} "
                    f"failures={s.failures}"
                )


def configure_logging(*, verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )


def parse_year_month(value: str) -> YearMonth:
    s = value.strip()
    m = _YEAR_MONTH_RE.match(s)
    if m:
        year, month = int(m.group(1)), int(m.group(2))
        if 1 <= month <= 12:
            return YearMonth(year, month)
        raise argparse.ArgumentTypeError(f"Invalid month in {value!r} (use 1-12)")

    m2 = _MONTH_NAME_RE.match(s.replace("_", "-"))
    if m2:
        month_name, year = m2.group(1), int(m2.group(2))
        try:
            month = datetime.strptime(month_name[:3].title(), "%b").month
        except ValueError as e:
            raise argparse.ArgumentTypeError(f"Invalid month name in {value!r}") from e
        return YearMonth(year, month)

    raise argparse.ArgumentTypeError(
        f"Invalid period {value!r}; use YYYY-MM (e.g. 2025-03) or march-2025"
    )


def _months_in_year(year: int) -> List[YearMonth]:
    return [YearMonth(year, m) for m in range(1, 13)]


def _months_in_range(start: YearMonth, end: YearMonth) -> List[YearMonth]:
    if (start.year, start.month) > (end.year, end.month):
        raise argparse.ArgumentTypeError(
            f"--from {start.label()} is after --to {end.label()}"
        )
    out: List[YearMonth] = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        out.append(YearMonth(y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


def resolve_periods(
    *,
    years: Sequence[int],
    periods: Sequence[YearMonth],
    from_period: Optional[YearMonth],
    to_period: Optional[YearMonth],
    default: YearMonth = YearMonth(DEFAULT_YEAR, DEFAULT_MONTH),
) -> List[YearMonth]:
    collected: List[YearMonth] = []
    for year in years:
        collected.extend(_months_in_year(year))
    collected.extend(periods)
    if from_period is not None and to_period is not None:
        collected.extend(_months_in_range(from_period, to_period))
    elif from_period is not None or to_period is not None:
        raise argparse.ArgumentTypeError("Both --from and --to are required for a range")

    if not collected:
        return [default]

    return sorted(set(collected))


def build_parser(*, page_name: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=f"Scheduled job for SEC {page_name} (scrape / embed / pipeline)."
    )
    parser.add_argument(
        "--mode",
        choices=("scrap", "embed", "test", "pipeline"),
        default="scrap",
        help="scrap: fetch list rows; embed: Pinecone ingest; test: smoke limits; "
        "pipeline: scrap then embed",
    )
    parser.add_argument(
        "--year",
        type=int,
        action="append",
        default=[],
        metavar="YYYY",
        help="Scrape every month in this year (repeatable)",
    )
    parser.add_argument(
        "--period",
        type=parse_year_month,
        action="append",
        default=[],
        metavar="YYYY-MM",
        help="Specific month to scrape (repeatable, e.g. 2025-03 or march-2025)",
    )
    parser.add_argument(
        "--from",
        dest="from_period",
        type=parse_year_month,
        metavar="YYYY-MM",
        help="Start of month range (requires --to)",
    )
    parser.add_argument(
        "--to",
        dest="to_period",
        type=parse_year_month,
        metavar="YYYY-MM",
        help="End of month range (requires --from)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Embed only: count chunks without Pinecone/OpenAI writes",
    )
    parser.add_argument(
        "--no-context",
        action="store_true",
        help="Scrape only: skip detail page / PDF text fetch",
    )
    parser.add_argument(
        "--limit-rows",
        type=int,
        default=None,
        help="Embed only: max pending rows (ignored in test mode)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="DEBUG logging",
    )
    return parser


def _row_count(path: Path) -> int:
    if not path.exists():
        return 0
    return len(load_dataframe(path))


def _run_scrape_periods(
    *,
    scrape_fn: ScrapeFn,
    dataframe_path: Path,
    periods: List[YearMonth],
    supports_periods: bool,
    scrape_uses_test_mode: bool,
    fetch_context: bool,
    scrape_test: bool,
) -> Tuple[List[ScrapePeriodStats], pd.DataFrame]:
    period_stats: List[ScrapePeriodStats] = []
    df: pd.DataFrame = load_dataframe(dataframe_path) if dataframe_path.exists() else pd.DataFrame()

    if supports_periods:
        iterator: Any = tqdm(periods, desc="scrape months", unit="month")
        for ym in iterator:
            iterator.set_postfix(period=ym.label())
            rows_before = _row_count(dataframe_path)
            logger.info("Scraping %s", ym.label())
            kwargs: dict[str, Any] = {
                "year": ym.year,
                "month": ym.month,
                "fetch_context": fetch_context,
            }
            if scrape_test:
                kwargs["max_pages"] = 1
            df = scrape_fn(**kwargs)
            rows_after = len(df)
            period_stats.append(
                ScrapePeriodStats(period=ym, rows_before=rows_before, rows_after=rows_after)
            )
            logger.info(
                "Period %s: +%d rows (total %d)",
                ym.label(),
                rows_after - rows_before,
                rows_after,
            )
    else:
        rows_before = _row_count(dataframe_path)
        logger.info("Scraping (no month filter)")
        kwargs = {"fetch_context": fetch_context}
        if scrape_uses_test_mode:
            kwargs["test_mode"] = scrape_test
        df = scrape_fn(**kwargs)
        rows_after = len(df)
        period_stats.append(
            ScrapePeriodStats(period=None, rows_before=rows_before, rows_after=rows_after)
        )
        logger.info("Scrape done: +%d rows (total %d)", rows_after - rows_before, rows_after)

    return period_stats, df


def run_page_job(
    *,
    page_name: str,
    dataset: str,
    dataframe_path: Path,
    scrape_fn: ScrapeFn,
    supports_periods: bool = True,
    scrape_uses_test_mode: bool = False,
    argv: Optional[List[str]] = None,
) -> int:
    parser = build_parser(page_name=page_name)
    args = parser.parse_args(argv)
    configure_logging(verbose=args.verbose)

    periods = resolve_periods(
        years=args.year,
        periods=args.period,
        from_period=args.from_period,
        to_period=args.to_period,
    )

    if not supports_periods and (
        args.year or args.period or args.from_period or args.to_period
    ):
        logger.warning(
            "%s does not use month/year filters; period flags are ignored.",
            page_name,
        )

    mode = args.mode
    scrape_test = mode == "test"
    if scrape_test and supports_periods and len(periods) > 1:
        logger.info("Test mode: using first period only (%s)", periods[0].label())
        periods = periods[:1]

    summary = JobSummary(
        page_name=page_name,
        dataset=dataset,
        mode=mode,
        dataframe_path=dataframe_path.resolve(),
    )

    fetch_context = not args.no_context
    do_scrape = mode in ("scrap", "pipeline", "test")
    do_embed = mode in ("embed", "pipeline", "test")

    if do_scrape:
        period_log = (
            [p.label() for p in periods] if supports_periods else ["n/a"]
        )
    else:
        period_log = ["n/a (embed only)"]

    logger.info(
        "Starting job page=%s dataset=%s mode=%s periods=%s",
        page_name,
        dataset,
        mode,
        period_log,
    )

    if do_scrape:
        scrape_periods = periods if supports_periods else [YearMonth(DEFAULT_YEAR, DEFAULT_MONTH)]
        period_stats, df = _run_scrape_periods(
            scrape_fn=scrape_fn,
            dataframe_path=dataframe_path,
            periods=scrape_periods,
            supports_periods=supports_periods,
            scrape_uses_test_mode=scrape_uses_test_mode,
            fetch_context=fetch_context,
            scrape_test=scrape_test,
        )
        summary.period_stats = period_stats
        summary.periods_run = len(period_stats)
        summary.rows_added = sum(ps.rows_added for ps in period_stats)
        summary.total_rows = len(df)

    if do_embed:
        ingest_test = mode == "test"
        limit_rows = None if ingest_test else args.limit_rows
        if ingest_test and args.limit_rows is not None:
            logger.info("--limit-rows ignored in test mode")
        logger.info(
            "Running ingest dataset=%s test=%s dry_run=%s",
            dataset,
            ingest_test,
            args.dry_run,
        )
        all_stats = run_ingest(
            dataset=dataset,
            test_mode=ingest_test,
            limit_rows=limit_rows,
            dry_run=args.dry_run,
        )
        if all_stats:
            summary.ingest_stats = all_stats[0]

    summary.print_summary()
    return 0


def main_entry(
    *,
    page_name: str,
    dataset: str,
    dataframe_path: Path,
    scrape_fn: ScrapeFn,
    supports_periods: bool = True,
    scrape_uses_test_mode: bool = False,
) -> None:
    raise SystemExit(
        run_page_job(
            page_name=page_name,
            dataset=dataset,
            dataframe_path=dataframe_path,
            scrape_fn=scrape_fn,
            supports_periods=supports_periods,
            scrape_uses_test_mode=scrape_uses_test_mode,
        )
    )
