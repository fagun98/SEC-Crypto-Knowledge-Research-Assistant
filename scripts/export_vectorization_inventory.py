#!/usr/bin/env python3
"""Export a combined vectorization inventory from data/ CSVs and sec_scraping parquet files."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

# Large HTML fields in some legacy CSVs
csv.field_size_limit(sys.maxsize)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sec_scraping.core import primary_detail_url

DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_PARQUET_DIR = PROJECT_ROOT / "sec_scraping" / "dataframes"
DEFAULT_OUTPUT = PROJECT_ROOT / "vectorization_inventory.csv"

URL_FALLBACK_COLUMNS = (
    "page_url",
    "url",
    "written-input-url",
    "title_url",
    "material_url",
)

OUTPUT_COLUMNS = ("name", "file-type", "URL", "Vectorized")


def _find_vectorized_column(columns: List[str]) -> Optional[str]:
    return next((c for c in columns if c.strip().lower() == "vectorized"), None)


def _normalize_vectorized(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "FALSE"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    return "TRUE" if str(value).strip().upper() == "TRUE" else "FALSE"


def _resolve_url(row: Dict[str, Any]) -> str:
    url = primary_detail_url(row)
    if url:
        return url

    for col in URL_FALLBACK_COLUMNS:
        raw = row.get(col)
        if raw is None or (isinstance(raw, float) and pd.isna(raw)):
            continue
        cleaned = str(raw).strip()
        if cleaned and cleaned.lower() != "nan":
            return cleaned
    return ""


def _rows_from_dataframe(
    df: pd.DataFrame,
    *,
    filename: str,
    file_type: str,
) -> List[Dict[str, str]]:
    vectorized_col = _find_vectorized_column(list(df.columns))
    records: List[Dict[str, str]] = []

    for row in df.to_dict(orient="records"):
        row_dict = {str(k): v for k, v in row.items()}
        vectorized_value = row_dict.get(vectorized_col) if vectorized_col else None
        records.append(
            {
                "name": filename,
                "file-type": file_type,
                "URL": _resolve_url(row_dict),
                "Vectorized": _normalize_vectorized(vectorized_value),
            }
        )
    return records


def _collect_csv_rows(data_dir: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for path in sorted(data_dir.glob("*.csv")):
        df = pd.read_csv(path, low_memory=False)
        rows.extend(_rows_from_dataframe(df, filename=path.name, file_type="csv"))
    return rows


def _collect_parquet_rows(parquet_dir: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for path in sorted(parquet_dir.glob("*.parquet")):
        if path.name.startswith("embed_"):
            continue
        df = pd.read_parquet(path)
        rows.extend(_rows_from_dataframe(df, filename=path.name, file_type="parquet"))
    return rows


def export_inventory(
    *,
    data_dir: Path,
    parquet_dir: Path,
    output_path: Path,
) -> pd.DataFrame:
    rows = _collect_csv_rows(data_dir) + _collect_parquet_rows(parquet_dir)
    out = pd.DataFrame(rows, columns=list(OUTPUT_COLUMNS))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)
    return out


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Combine data/*.csv and sec_scraping/dataframes/*.parquet into a "
            "single vectorization inventory CSV."
        )
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output CSV path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"Directory containing source CSV files (default: {DEFAULT_DATA_DIR})",
    )
    parser.add_argument(
        "--parquet-dir",
        type=Path,
        default=DEFAULT_PARQUET_DIR,
        help=f"Directory containing parquet dataframes (default: {DEFAULT_PARQUET_DIR})",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    out = export_inventory(
        data_dir=args.data_dir,
        parquet_dir=args.parquet_dir,
        output_path=args.output,
    )

    csv_files = len(list(args.data_dir.glob("*.csv")))
    parquet_files = len(
        [p for p in args.parquet_dir.glob("*.parquet") if not p.name.startswith("embed_")]
    )
    true_count = int((out["Vectorized"] == "TRUE").sum())

    print(f"Wrote {len(out)} rows to {args.output}")
    print(f"  CSV files processed:     {csv_files}")
    print(f"  Parquet files processed: {parquet_files}")
    print(f"  Vectorized=TRUE:         {true_count}")


if __name__ == "__main__":
    main()
