from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from urllib.parse import urlencode, urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

from cri_ontology.document_context import (
    _sec_headers,
    extract_title_and_text_from_html,
    extract_title_and_text_from_url,
)

SEC_BASE = "https://www.sec.gov"
DEFAULT_REQUEST_DELAY = 1.5

# region agent log
_DEBUG_LOG_PATH = Path(
    "/Users/fagun/Documents/Work - Num Infomatics/SEC-Crypto-UI/.cursor/debug-fedcd0.log"
)
_DEBUG_SESSION_ID = "fedcd0"


def _debug_log(*, run_id: str, hypothesis_id: str, location: str, message: str, data: Dict[str, Any]) -> None:
    try:
        payload = {
            "sessionId": _DEBUG_SESSION_ID,
            "runId": run_id,
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        _DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _DEBUG_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass

# Emit a one-time import log so we can confirm the
# module version actually running in the user's command.
_debug_log(
    run_id="pre-fix",
    hypothesis_id="H0",
    location="sec_scraping/core.py:import",
    message="Imported sec_scraping.core",
    data={
        "file": __file__,
        "cwd": os.getcwd(),
        "sys_path_0": sys.path[0] if sys.path else "",
        "python": sys.executable,
    },
)

# endregion agent log

_EXCLUDED_KEY_PARTS = frozenset(
    {
        "row_key",
        "context",
        "context_title",
        "date_normalized",
        "source_list_url",
        "scraped_at",
        "vectorized",
        "resources",
    }
)

_FALLBACK_TITLE_FIELDS = (
    "title",
    "written_input",
    "participants_associated_materials",
    "statement",
    "rulemaking",
)


def _slug_column(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", (name or "").strip().lower())
    return slug.strip("_") or "column"


def make_row_key(row: Dict[str, Any]) -> str:
    """Alphanumeric key from all non-URL row values."""
    parts: List[str] = []
    for key, value in sorted(row.items()):
        if key in _EXCLUDED_KEY_PARTS or key.endswith("_url"):
            continue
        if value is None:
            continue
        parts.append(str(value))
    combined = "".join(parts)
    return re.sub(r"[^a-zA-Z0-9]", "", combined)


def ensure_dataframe_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure standard scraper columns exist with correct defaults."""
    if df is None or df.empty:
        out = pd.DataFrame() if df is None else df.copy()
        if "vectorized" not in out.columns:
            out["vectorized"] = pd.Series(dtype=bool)
        return out
    out = df.copy()
    if "vectorized" not in out.columns:
        out["vectorized"] = False
    else:
        out["vectorized"] = out["vectorized"].fillna(False).astype(bool)
    return out


def resolve_sec_url(href: str) -> str:
    return urljoin(SEC_BASE, (href or "").strip())


def fetch_html(url: str, *, timeout: int = 20) -> str:
    """Fetch SEC HTML with standard headers and polite delay."""
    time.sleep(DEFAULT_REQUEST_DELAY)
    resp = requests.get(url, headers=_sec_headers(), timeout=timeout, allow_redirects=True)
    resp.raise_for_status()
    # region agent log
    _debug_log(
        run_id="pre-fix",
        hypothesis_id="H2",
        location="sec_scraping/core.py:fetch_html",
        message="Fetched list/detail HTML",
        data={
            "url": url,
            "final_url": str(resp.url or ""),
            "status_code": int(getattr(resp, "status_code", 0) or 0),
            "text_len": len(resp.text or ""),
        },
    )
    # endregion agent log
    return resp.text


def parse_html_table(
    html: str,
    *,
    expected_headers: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Parse the first table whose header row matches expected_headers (if given).
    Returns dicts with column keys and optional {column}_url fields.
    """
    soup = BeautifulSoup(html or "", "html.parser")
    expected = [h.strip().lower() for h in (expected_headers or [])]

    for table_root in soup.find_all("table"):
        rows = _parse_table_element(table_root, expected)
        if rows:
            return rows

    tbody = soup.find("tbody")
    if tbody is not None:
        rows = _parse_tr_block(list(tbody.find_all("tr")), expected)
        if rows:
            return rows

    all_trs = soup.find_all("tr")
    if len(all_trs) >= 2:
        return _parse_tr_block(all_trs, expected)
    return []


def _parse_table_element(table: Any, expected: List[str]) -> List[Dict[str, Any]]:
    trs = table.find_all("tr")
    if len(trs) < 2:
        return []
    return _parse_tr_block(trs, expected)


def _parse_tr_block(trs: List[Any], expected: List[str]) -> List[Dict[str, Any]]:
    header_cells = trs[0].find_all(["th", "td"])
    headers = [c.get_text(" ", strip=True) for c in header_cells]
    if not headers:
        return []

    if expected:
        normalized = [h.lower() for h in headers]
        if normalized[: len(expected)] != expected:
            return []

    col_keys = [_slug_column(h) for h in headers]
    out: List[Dict[str, Any]] = []

    for tr in trs[1:]:
        cells = tr.find_all(["td", "th"])
        if not cells:
            continue
        row: Dict[str, Any] = {}
        for i, cell in enumerate(cells):
            if i >= len(col_keys):
                break
            key = col_keys[i]
            row[key] = cell.get_text(" ", strip=True)
            anchor = cell.find("a", href=True)
            if anchor:
                row[f"{key}_url"] = resolve_sec_url(anchor["href"])
        if any(str(v).strip() for k, v in row.items() if not k.endswith("_url")):
            out.append(row)
    return out


def load_dataframe(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        return ensure_dataframe_schema(pd.DataFrame())
    if path.suffix == ".parquet":
        return ensure_dataframe_schema(pd.read_parquet(path))
    if path.suffix == ".csv":
        return ensure_dataframe_schema(pd.read_csv(path))
    raise ValueError(f"Unsupported dataframe format: {path}")


def save_dataframe(df: pd.DataFrame, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df = ensure_dataframe_schema(df)
    try:
        df.to_parquet(path, index=False)
        return path
    except Exception:
        csv_path = path.with_suffix(".csv")
        df.to_csv(csv_path, index=False)
        return csv_path


def primary_detail_url(row: Dict[str, Any]) -> Optional[str]:
    def _clean_url_value(v: Any) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip()
        if not s:
            return None
        if s.lower() == "nan":
            return None
        return s

    title_url = _clean_url_value(row.get("title_url"))
    if title_url:
        return title_url

    status_url = _clean_url_value(row.get("status_url"))
    if status_url:
        return status_url

    for key, value in row.items():
        if key.endswith("_url"):
            u = _clean_url_value(value)
            if u:
                return u
    return None


def row_fallback_title(row: Dict[str, Any]) -> str:
    for field in _FALLBACK_TITLE_FIELDS:
        value = row.get(field)
        if value and str(value).strip():
            return str(value).strip()
    return ""


def enrich_row_context_any(
    url: str, *, fallback_title: str = "", timeout: int = 20
) -> Tuple[str, str]:
    """Fetch HTML or PDF detail and return (context_title, context_text)."""
    try:
        time.sleep(DEFAULT_REQUEST_DELAY)
        title, text = extract_title_and_text_from_url(url, timeout=timeout, max_pdf_pages=0)
        if title == "PDF Document" and fallback_title:
            title = fallback_title
        # region agent log
        _debug_log(
            run_id="pre-fix",
            hypothesis_id="H6",
            location="sec_scraping/core.py:enrich_row_context_any",
            message="Enriched row context",
            data={
                "url": url,
                "title_len": len(title or ""),
                "text_len": len(text or ""),
            },
        )
        # endregion agent log
        return title, text
    except Exception as e:
        # region agent log
        _debug_log(
            run_id="pre-fix",
            hypothesis_id="H6",
            location="sec_scraping/core.py:enrich_row_context_any",
            message="Enrich row context failed",
            data={"url": url, "error": type(e).__name__},
        )
        # endregion agent log
        raise


def merge_scraped_rows(
    existing: pd.DataFrame,
    new_rows: List[Dict[str, Any]],
    *,
    source_list_url: str,
    fetch_context: bool = True,
) -> Tuple[pd.DataFrame, int]:
    """
    Append rows whose row_key is not already present; optionally enrich context.
    Returns (updated_df, count_added).
    """
    df = ensure_dataframe_schema(existing)
    if "context_title" not in df.columns:
        df["context_title"] = ""
    if "context" not in df.columns:
        df["context"] = ""

    if df is None or df.empty or "row_key" not in df.columns:
        key_to_index: Dict[str, int] = {}
    else:
        key_to_index = {
            str(k): int(idx)
            for idx, k in df["row_key"].astype(str).items()
        }

    added = 0
    now = datetime.now(timezone.utc).isoformat()

    for row in new_rows:
        row_key = make_row_key(row)
        if not row_key:
            continue

        record: Dict[str, Any] = dict(row)
        if row_key in key_to_index:
            # If we previously scraped without context, opportunistically fill it.
            if fetch_context:
                idx = key_to_index[row_key]
                current_context = df.at[idx, "context"] if idx in df.index else ""
                context_str = "" if current_context is None else str(current_context).strip()
                if (not context_str) or context_str.lower() == "nan":
                    try:
                        existing_row_dict = df.loc[idx].to_dict()
                        detail_url = primary_detail_url(existing_row_dict)
                        if detail_url:
                            fallback = row_fallback_title(existing_row_dict)
                            title, text = enrich_row_context_any(
                                detail_url, fallback_title=fallback
                            )
                            df.at[idx, "context_title"] = title
                            df.at[idx, "context"] = text
                    except Exception:
                        pass
            continue

        record["row_key"] = row_key
        record["source_list_url"] = source_list_url
        record["scraped_at"] = now
        record["vectorized"] = False
        record.setdefault("context_title", "")
        record.setdefault("context", "")

        if fetch_context:
            detail_url = primary_detail_url(record)
            if detail_url:
                try:
                    fallback = row_fallback_title(record)
                    title, text = enrich_row_context_any(
                        detail_url, fallback_title=fallback
                    )
                    record["context_title"] = title
                    record["context"] = text
                except Exception:
                    pass

        df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
        key_to_index[row_key] = len(df) - 1
        added += 1

    return df, added


def extract_side_resources(html: str) -> List[Dict[str, str]]:
    """Parse right-rail resource links from SEC detail pages."""
    soup = BeautifulSoup(html or "", "html.parser")
    panel = soup.select_one("div.side-resources")
    selector_used = "div.side-resources"

    # What's New / newsroom pages use a different right-rail layout.
    if panel is None:
        for cand in soup.select("div.rightrail-list"):
            heading = cand.find(["h2", "h3"])
            heading_text = " ".join((heading.get_text(" ", strip=True) if heading else "").split()).lower()
            if not heading_text or "resource" in heading_text:
                panel = cand
                selector_used = "div.rightrail-list"
                break

    # Fallback: Drupal field list used inside right rail.
    if panel is None:
        cand = soup.select_one("ul.field--name-field-see-also")
        if cand is not None:
            panel = cand
            selector_used = "ul.field--name-field-see-also"

    # region agent log
    _debug_log(
        run_id="pre-fix",
        hypothesis_id="H5",
        location="sec_scraping/core.py:extract_side_resources",
        message="Right-rail panel selector match",
        data={
            "selector_used": selector_used if panel is not None else "",
            "panel_found": bool(panel is not None),
        },
    )
    # endregion agent log

    if panel is None:
        return []

    seen: Set[str] = set()
    out: List[Dict[str, str]] = []
    for anchor in panel.find_all("a", href=True):
        href = (anchor.get("href") or "").strip()
        if not href or href.startswith("#"):
            continue
        url = resolve_sec_url(href)
        if url in seen:
            continue
        seen.add(url)
        label = " ".join(anchor.get_text(" ", strip=True).split())
        if not label:
            label = url
        out.append({"label": label, "url": url})
    # region agent log
    _debug_log(
        run_id="pre-fix",
        hypothesis_id="H5",
        location="sec_scraping/core.py:extract_side_resources",
        message="Extracted right-rail links",
        data={"selector_used": selector_used, "count": len(out)},
    )
    # endregion agent log
    return out


_FILES_PATH_EXTENSIONS = (
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".zip",
    ".txt",
    ".csv",
    ".xml",
)


def is_file_url(url: str) -> bool:
    """True when URL points to a downloadable file (PDF or other /files/ asset)."""
    if not url:
        return False
    u = str(url).strip().lower()
    if not u or u == "nan":
        return False
    path = u.split("?", 1)[0].split("#", 1)[0]
    if path.endswith(".pdf"):
        return True
    if "/files/" in path and any(path.endswith(ext) for ext in _FILES_PATH_EXTENSIONS):
        return True
    return False


def _enrich_html_detail_with_resources(
    final_url: str,
    html: str,
    *,
    fetch_resources: bool = True,
) -> Tuple[str, str, str]:
    """Extract main HTML context and optional side-resources JSON from detail HTML."""
    context_title, context = extract_title_and_text_from_html(final_url, html)

    resources_out: List[Dict[str, str]] = []
    if fetch_resources:
        for item in extract_side_resources(html):
            label = item.get("label", "")
            url = item.get("url", "")
            if not url:
                continue
            entry: Dict[str, str] = {
                "label": label,
                "url": url,
                "context_title": "",
                "context": "",
            }
            try:
                r_title, r_text = enrich_row_context_any(url, fallback_title=label)
                entry["context_title"] = r_title
                entry["context"] = r_text
            except Exception:
                pass
            resources_out.append(entry)

    return context_title, context, json.dumps(resources_out)


def enrich_rulemaking_detail(
    status_url: str,
    *,
    fetch_resources: bool = True,
    timeout: int = 20,
) -> Tuple[str, str, str]:
    """
    Fetch rulemaking detail page once; return (context_title, context, resources_json).
    resources_json is a JSON list of {label, url, context_title, context}.
    """
    try:
        time.sleep(DEFAULT_REQUEST_DELAY)
        resp = requests.get(
            status_url, headers=_sec_headers(), timeout=timeout, allow_redirects=True
        )
        resp.raise_for_status()
        final_url = str(resp.url or status_url)
        html = resp.text
        out = _enrich_html_detail_with_resources(final_url, html, fetch_resources=fetch_resources)
        # region agent log
        _debug_log(
            run_id="pre-fix",
            hypothesis_id="H7",
            location="sec_scraping/core.py:enrich_rulemaking_detail",
            message="Enriched HTML detail with resources",
            data={
                "url": status_url,
                "final_url": final_url,
                "html_len": len(html or ""),
                "context_len": len(out[1] or ""),
                "resources_len": len(out[2] or ""),
            },
        )
        # endregion agent log
        return out
    except Exception as e:
        # region agent log
        _debug_log(
            run_id="pre-fix",
            hypothesis_id="H7",
            location="sec_scraping/core.py:enrich_rulemaking_detail",
            message="Enrich HTML detail failed",
            data={"url": status_url, "error": type(e).__name__},
        )
        # endregion agent log
        raise


def enrich_whats_new_detail(
    title_url: str,
    *,
    fallback_title: str = "",
    fetch_resources: bool = True,
    timeout: int = 20,
) -> Tuple[str, str, str]:
    """
    Enrich What's New title_url: files -> context only; HTML -> context + side-resources.
    """
    try:
        file_branch = is_file_url(title_url)
        # region agent log
        _debug_log(
            run_id="pre-fix",
            hypothesis_id="H8",
            location="sec_scraping/core.py:enrich_whats_new_detail",
            message="WhatsNew detail branch",
            data={"title_url": title_url, "is_file": bool(file_branch)},
        )
        # endregion agent log
        if file_branch:
            title, text = enrich_row_context_any(title_url, fallback_title=fallback_title)
            return title, text, "[]"
        return enrich_rulemaking_detail(
            title_url, fetch_resources=fetch_resources, timeout=timeout
        )
    except Exception as e:
        # region agent log
        _debug_log(
            run_id="pre-fix",
            hypothesis_id="H8",
            location="sec_scraping/core.py:enrich_whats_new_detail",
            message="WhatsNew detail enrich failed",
            data={"title_url": title_url, "error": type(e).__name__},
        )
        # endregion agent log
        raise


def _needs_detail_enrichment(row_dict: Dict[str, Any]) -> bool:
    context = str(row_dict.get("context", "") or "").strip()
    if not context or context.lower() == "nan":
        return True
    resources_raw = str(row_dict.get("resources", "") or "").strip()
    if not resources_raw or resources_raw.lower() == "nan":
        return True
    if resources_raw in ("[]", "{}"):
        return True
    return False


def merge_rulemaking_rows(
    existing: pd.DataFrame,
    new_rows: List[Dict[str, Any]],
    *,
    source_list_url: str,
    fetch_context: bool = True,
) -> Tuple[pd.DataFrame, int]:
    """
    Append rulemaking rows with main context and side-resources JSON.
    Returns (updated_df, count_added).
    """
    df = ensure_dataframe_schema(existing)
    for col in ("context_title", "context", "resources"):
        if col not in df.columns:
            df[col] = ""

    if df is None or df.empty or "row_key" not in df.columns:
        key_to_index: Dict[str, int] = {}
    else:
        key_to_index = {
            str(k): int(idx)
            for idx, k in df["row_key"].astype(str).items()
        }

    added = 0
    now = datetime.now(timezone.utc).isoformat()

    for row in new_rows:
        row_key = make_row_key(row)
        if not row_key:
            continue

        record: Dict[str, Any] = dict(row)
        issue_date = record.get("issue_date")
        if issue_date:
            normalized = normalize_sec_date(str(issue_date))
            if normalized:
                record["date_normalized"] = normalized

        if row_key in key_to_index:
            if fetch_context:
                idx = key_to_index[row_key]
                existing_row_dict = df.loc[idx].to_dict()
                if _needs_detail_enrichment(existing_row_dict):
                    status_url = primary_detail_url(existing_row_dict)
                    if status_url:
                        try:
                            title, text, resources_json = enrich_rulemaking_detail(
                                status_url, fetch_resources=fetch_context
                            )
                            df.at[idx, "context_title"] = title
                            df.at[idx, "context"] = text
                            df.at[idx, "resources"] = resources_json
                        except Exception:
                            pass
            continue

        record["row_key"] = row_key
        record["source_list_url"] = source_list_url
        record["scraped_at"] = now
        record["vectorized"] = False
        record.setdefault("context_title", "")
        record.setdefault("context", "")
        record.setdefault("resources", "[]")

        if fetch_context:
            status_url = primary_detail_url(record)
            if status_url:
                try:
                    title, text, resources_json = enrich_rulemaking_detail(
                        status_url, fetch_resources=True
                    )
                    record["context_title"] = title
                    record["context"] = text
                    record["resources"] = resources_json
                except Exception:
                    pass

        df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
        key_to_index[row_key] = len(df) - 1
        added += 1

    return df, added


def merge_whats_new_rows(
    existing: pd.DataFrame,
    new_rows: List[Dict[str, Any]],
    *,
    source_list_url: str,
    fetch_context: bool = True,
) -> Tuple[pd.DataFrame, int]:
    """
    Append What's New rows: title_url enrichment with file vs HTML branching.
    Returns (updated_df, count_added).
    """
    df = ensure_dataframe_schema(existing)
    for col in ("context_title", "context", "resources"):
        if col not in df.columns:
            df[col] = ""

    if df is None or df.empty or "row_key" not in df.columns:
        key_to_index: Dict[str, int] = {}
    else:
        key_to_index = {
            str(k): int(idx)
            for idx, k in df["row_key"].astype(str).items()
        }

    added = 0
    now = datetime.now(timezone.utc).isoformat()

    for row in new_rows:
        row_key = make_row_key(row)
        if not row_key:
            continue

        record: Dict[str, Any] = dict(row)
        date_val = record.get("date")
        if date_val:
            normalized = normalize_sec_date(str(date_val))
            if normalized:
                record["date_normalized"] = normalized

        if row_key in key_to_index:
            if fetch_context:
                idx = key_to_index[row_key]
                existing_row_dict = df.loc[idx].to_dict()
                if _needs_detail_enrichment(existing_row_dict):
                    detail_url = primary_detail_url(existing_row_dict)
                    if detail_url:
                        try:
                            fallback = row_fallback_title(existing_row_dict)
                            title, text, resources_json = enrich_whats_new_detail(
                                detail_url,
                                fallback_title=fallback,
                                fetch_resources=fetch_context,
                            )
                            df.at[idx, "context_title"] = title
                            df.at[idx, "context"] = text
                            df.at[idx, "resources"] = resources_json
                        except Exception:
                            pass
            continue

        record["row_key"] = row_key
        record["source_list_url"] = source_list_url
        record["scraped_at"] = now
        record["vectorized"] = False
        record.setdefault("context_title", "")
        record.setdefault("context", "")
        record.setdefault("resources", "[]")

        if fetch_context:
            detail_url = primary_detail_url(record)
            if detail_url:
                try:
                    fallback = row_fallback_title(record)
                    title, text, resources_json = enrich_whats_new_detail(
                        detail_url,
                        fallback_title=fallback,
                        fetch_resources=True,
                    )
                    record["context_title"] = title
                    record["context"] = text
                    record["resources"] = resources_json
                except Exception:
                    pass

        df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
        key_to_index[row_key] = len(df) - 1
        added += 1

    return df, added


def list_page_has_no_results(html: str) -> bool:
    return "no results" in (html or "").lower()


def normalize_sec_date(raw: Optional[str]) -> Optional[str]:
    """
    Normalize SEC table date formats into ISO `YYYY-MM-DD`.
    """
    if raw is None:
        return None
    s = str(raw).replace("\xa0", " ").strip()
    if not s:
        return None
    s = " ".join(s.split())

    # Normalize month abbreviations like "Apr." -> "Apr"
    s_no_dot = re.sub(r"(?i)\b([a-z]{3})\.\s+", r"\1 ", s)

    candidates = [s, s_no_dot]
    formats = [
        "%Y-%m-%d",
        "%m/%d/%y",  # Crypto@SEC: 5/4/26
        "%B %d, %Y",  # Written input: April 23, 2026
        "%b %d, %Y",  # Newsroom / meetings without dot: Apr 21, 2026
        "%b. %d, %Y",  # Meetings with dot: Apr. 30, 2026
    ]

    for c in candidates:
        for fmt in formats:
            try:
                dt = datetime.strptime(c, fmt)
                return dt.date().isoformat()
            except Exception:
                continue
    return None


def filter_rows_by_month_year(
    rows: List[Dict[str, Any]],
    *,
    month: int,
    year: int,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    prefix = f"{year}-{month:02d}-"

    for row in rows:
        date_raw = row.get("date")
        date_normalized = normalize_sec_date(date_raw)
        if not date_normalized:
            continue
        if not str(date_normalized).startswith(prefix):
            continue
        row2 = dict(row)
        row2["date_normalized"] = date_normalized
        out.append(row2)
    return out


def normalize_and_filter_dataframe(
    df: pd.DataFrame,
    *,
    month: int,
    year: int,
) -> pd.DataFrame:
    df = ensure_dataframe_schema(df)
    if df is None or df.empty:
        if "date_normalized" not in df.columns:
            df["date_normalized"] = pd.Series(dtype=object)
        return df
    if "date" not in df.columns:
        df["date_normalized"] = pd.Series(dtype=object)
        return df.iloc[0:0]

    if "date_normalized" not in df.columns:
        df["date_normalized"] = df["date"].apply(normalize_sec_date)
    else:
        df["date_normalized"] = df["date_normalized"].apply(normalize_sec_date)

    prefix = f"{year}-{month:02d}-"
    df = df[df["date_normalized"].notna() & df["date_normalized"].astype(str).str.startswith(prefix)]
    return df.reset_index(drop=True)


def build_paginated_list_url(
    base_url: str,
    *,
    year: int,
    month: int,
    page: int = 0,
    search: str = "",
) -> str:
    params = {
        "search": search,
        "year": year,
        "month": month,
        "page": page,
    }
    return f"{base_url}?{urlencode(params)}"


def run_paginated_table_scraper(
    *,
    base_url: str,
    dataframe_path: str | Path,
    expected_headers: List[str],
    year: int = 2026,
    month: int = 3,
    max_pages: Optional[int] = None,
    fetch_context: bool = True,
    build_list_url: Optional[Callable[..., str]] = None,
    merge_fn: Optional[Callable[..., Tuple[pd.DataFrame, int]]] = None,
) -> pd.DataFrame:
    """Paginate list pages, dedupe rows, enrich context, persist after each page."""
    df = normalize_and_filter_dataframe(
        load_dataframe(dataframe_path),
        year=year,
        month=month,
    )
    # Persist normalized+filtered schema even if subsequent pages add nothing.
    save_dataframe(df, dataframe_path)
    page = 0
    url_builder = build_list_url or build_paginated_list_url
    merge_rows = merge_fn or merge_scraped_rows
    seen_signatures: Set[str] = set()

    while True:
        if max_pages is not None and page >= max_pages:
            break

        list_url = url_builder(base_url=base_url, year=year, month=month, page=page)
        print(f"[pagination] page={page} url={list_url}")
        # region agent log
        _debug_log(
            run_id="pre-fix",
            hypothesis_id="H1",
            location="sec_scraping/core.py:run_paginated_table_scraper",
            message="Built list URL",
            data={"page": page, "list_url": list_url},
        )
        # endregion agent log
        try:
            html = fetch_html(list_url)
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 404:
                break
            raise

        # region agent log
        _debug_log(
            run_id="pre-fix",
            hypothesis_id="H2",
            location="sec_scraping/core.py:run_paginated_table_scraper",
            message="Fetched list page HTML",
            data={"page": page, "html_len": len(html or "")},
        )
        # endregion agent log

        if list_page_has_no_results(html):
            # region agent log
            _debug_log(
                run_id="pre-fix",
                hypothesis_id="H2",
                location="sec_scraping/core.py:run_paginated_table_scraper",
                message="Stop: list page indicates no results",
                data={"page": page, "list_url": list_url},
            )
            # endregion agent log
            break

        rows = parse_html_table(html, expected_headers=expected_headers)
        # region agent log
        _debug_log(
            run_id="pre-fix",
            hypothesis_id="H3",
            location="sec_scraping/core.py:run_paginated_table_scraper",
            message="Parsed table rows",
            data={"page": page, "rows_count": len(rows)},
        )
        # endregion agent log
        if not rows:
            break

        rows = filter_rows_by_month_year(rows, year=year, month=month)
        # region agent log
        _debug_log(
            run_id="pre-fix",
            hypothesis_id="H4",
            location="sec_scraping/core.py:run_paginated_table_scraper",
            message="Filtered rows by month/year",
            data={"page": page, "filtered_count": len(rows), "year": year, "month": month},
        )
        # endregion agent log
        if not rows:
            break

        # Detect repeated pagination pages (SEC sometimes serves identical HTML for all pages).
        sig_parts: List[str] = []
        for r in rows:
            rk = make_row_key(r)
            if rk:
                sig_parts.append(rk)
        signature = "|".join(sorted(sig_parts))
        # region agent log
        _debug_log(
            run_id="pre-fix",
            hypothesis_id="H1",
            location="sec_scraping/core.py:run_paginated_table_scraper",
            message="Page signature",
            data={"page": page, "signature_len": len(signature), "row_keys": len(sig_parts)},
        )
        # endregion agent log
        if signature and signature in seen_signatures:
            # region agent log
            _debug_log(
                run_id="pre-fix",
                hypothesis_id="H1",
                location="sec_scraping/core.py:run_paginated_table_scraper",
                message="Stop: repeated page signature",
                data={"page": page},
            )
            # endregion agent log
            break
        if signature:
            seen_signatures.add(signature)

        df, added = merge_rows(
            df,
            rows,
            source_list_url=list_url,
            fetch_context=fetch_context,
        )
        # region agent log
        _debug_log(
            run_id="pre-fix",
            hypothesis_id="H1",
            location="sec_scraping/core.py:run_paginated_table_scraper",
            message="Merged rows",
            data={"page": page, "added": int(added), "df_len": int(len(df))},
        )
        # endregion agent log
        save_dataframe(df, dataframe_path)
        if added == 0 and not fetch_context:
            break
        page += 1

    return df


def run_single_page_table_scraper(
    *,
    list_url: str,
    dataframe_path: str | Path,
    expected_headers: List[str],
    fetch_context: bool = True,
    year: int = 2026,
    month: int = 3,
) -> pd.DataFrame:
    """Scrape a single list page (no pagination), dedupe, enrich, persist."""
    df = normalize_and_filter_dataframe(
        load_dataframe(dataframe_path),
        year=year,
        month=month,
    )
    # Persist normalized+filtered schema even if scraping adds nothing.
    save_dataframe(df, dataframe_path)
    html = fetch_html(list_url)
    rows = parse_html_table(html, expected_headers=expected_headers)
    rows = filter_rows_by_month_year(rows, year=year, month=month)
    if rows:
        df, _ = merge_scraped_rows(
            df,
            rows,
            source_list_url=list_url,
            fetch_context=fetch_context,
        )
        save_dataframe(df, dataframe_path)
    return df
