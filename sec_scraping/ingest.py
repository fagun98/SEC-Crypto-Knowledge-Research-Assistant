"""Ingest SEC scraping dataframes into Pinecone with per-segment CRI classification and embed_* backups."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone
from tqdm import tqdm

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from cri_ontology.classifier import classify_chunk
from cri_ontology.document_context import _cap_text, infer_source_type_from_url
from cri_ontology.validate import validate_classification

from crypto_ingest import (
    PINECONE_INDEX_NAME,
    PINECONE_NAMESPACE,
    DocumentChunk,
    chunk_text,
    ensure_index_exists,
    make_chunk_id,
)
from scripts.sec_crawl_ingestion import (
    BufferedVector,
    buffered_to_pinecone_vectors,
    sanitize_metadata_for_pinecone,
    upsert_vector_batch,
)
from sec_scraping.core import (
    load_dataframe,
    primary_detail_url,
    row_fallback_title,
    save_dataframe,
)

load_dotenv()

_DATAFRAMES_DIR = Path(__file__).resolve().parent / "dataframes"

EMBED_STATUS_SUCCESS = "Success"
EMBED_STATUS_FAILURE = "Failure"
ROW_STATUS_CONTENT_PART = "_row_status"
_REASON_MAX_LEN = 500

EMBED_COLUMNS = [
    "id",
    "row_key",
    "sec_dataset",
    "source_url",
    "content_part",
    "chunk_index",
    "domain_primary",
    "domain_secondary",
    "subdomain",
    "lifecycle_stage",
    "durability_tier",
    "classification_confidence",
    "classification_reason",
    "validation_status",
    "classification_validation_errors",
    "classification_error",
    "classified_at",
    "ingested_at",
    "status",
    "reason",
]


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_resources(raw: Any) -> list:
    if raw is None:
        return []
    s = str(raw).strip()
    if not s or s.lower() == "nan":
        return []
    try:
        data = json.loads(s)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _is_pdf_url(url: str) -> bool:
    if not url:
        return False
    u = str(url).strip().lower().split("?", 1)[0].split("#", 1)[0]
    return u.endswith(".pdf") or ".pdf" in u


def _clean_str(value: Any) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    return "" if s.lower() == "nan" else s


def embed_table_path(source_path: Path) -> Path:
    return source_path.parent / f"embed_{source_path.stem}.parquet"


@dataclass(frozen=True)
class TableConfig:
    source_filename: str
    sec_dataset: str
    extra_metadata_columns: Tuple[str, ...] = ()
    date_columns: Tuple[str, ...] = ("date_normalized", "date", "issue_date")

    @property
    def source_path(self) -> Path:
        return _DATAFRAMES_DIR / self.source_filename

    @property
    def embed_path(self) -> Path:
        return embed_table_path(self.source_path)


TABLE_REGISTRY: Tuple[TableConfig, ...] = (
    TableConfig("crypto_newsroom.parquet", "crypto-newsroom", ("date", "title", "speaker")),
    TableConfig(
        "crypto_task_force_meetings.parquet",
        "crypto-task-force-meetings",
        ("date", "participants_associated_materials"),
    ),
    TableConfig(
        "crypto_written_input.parquet",
        "crypto-written-input",
        ("date", "written_input", "topic_s", "key_points"),
    ),
    TableConfig(
        "cryptosec.parquet",
        "cryptosec",
        ("date", "speaker_division", "statement", "summary"),
    ),
    TableConfig("no_action_letters.parquet", "no-action-letters", ("date", "title", "division")),
    TableConfig("press_releases.parquet", "press-releases", ("date", "headline", "release_no")),
    TableConfig(
        "rulemaking_activity.parquet",
        "rulemaking-activity",
        ("issue_date", "file_number", "rulemaking", "status"),
    ),
    TableConfig(
        "speeches_statements.parquet",
        "speeches-statements",
        ("date", "title", "speaker", "type"),
    ),
    TableConfig("whats_new.parquet", "whats-new", ("date", "title", "division_office")),
)


@dataclass
class TextSegment:
    content_part: str
    source_url: str
    text: str
    resource_label: str = ""


@dataclass
class IngestPageStats:
    sec_dataset: str
    source_table: str
    embed_backup: str
    pending_rows: int = 0
    rows_processed: int = 0
    rows_embedded: int = 0
    rows_skipped: int = 0
    chunks_upserted: int = 0
    backup_rows_added: int = 0
    failures: int = 0
    rows_already_failed: int = 0
    dry_run: bool = False

    def print_summary(self) -> None:
        print(f"\n=== Ingest summary: {self.sec_dataset} ===")
        print(f"  source_table:      {self.source_table}")
        print(f"  embed_backup:      {self.embed_backup}")
        print(f"  pending_rows:      {self.pending_rows}")
        print(f"  rows_already_failed: {self.rows_already_failed}")
        print(f"  rows_processed:    {self.rows_processed}")
        print(f"  rows_embedded:     {self.rows_embedded}")
        print(f"  rows_skipped:      {self.rows_skipped}")
        print(f"  chunks_upserted:   {self.chunks_upserted}")
        print(f"  backup_rows_added: {self.backup_rows_added}")
        print(f"  failures:          {self.failures}")
        if self.dry_run:
            print("  (dry-run: no Pinecone/OpenAI writes, vectorized unchanged)")


def _registry_by_dataset(slug: str) -> Optional[TableConfig]:
    for cfg in TABLE_REGISTRY:
        if cfg.sec_dataset == slug:
            return cfg
    return None


def _publication_date(row: pd.Series, cfg: TableConfig) -> str:
    for col in cfg.date_columns:
        if col in row.index:
            v = _clean_str(row.get(col))
            if v:
                return v
    return ""


def _row_extra_metadata(row: pd.Series, cfg: TableConfig) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for col in cfg.extra_metadata_columns:
        if col in row.index:
            v = _clean_str(row.get(col))
            if v:
                out[col] = v
    if "source_list_url" in row.index:
        v = _clean_str(row.get("source_list_url"))
        if v:
            out["source_list_url"] = v
    return out


def build_segments(row: pd.Series) -> List[TextSegment]:
    segments: List[TextSegment] = []
    main_url = primary_detail_url(row.to_dict()) or ""
    main_text = _clean_str(row.get("context"))
    if main_text and main_url:
        segments.append(TextSegment("main", main_url, main_text))

    for item in _parse_resources(row.get("resources")):
        if not isinstance(item, dict):
            continue
        r_text = _clean_str(item.get("context"))
        r_url = _clean_str(item.get("url")) or main_url
        if r_text and r_url:
            segments.append(
                TextSegment(
                    "resource",
                    r_url,
                    r_text,
                    resource_label=_clean_str(item.get("label")),
                )
            )
    return segments


def _chunk_id(row_key: str, segment: TextSegment, chunk_index: int) -> str:
    base = f"{row_key}|{segment.content_part}|{segment.source_url}"
    return make_chunk_id(base, None, chunk_index)


def _document_context(
    *,
    title: str,
    source_url: str,
    doc_type: str,
    sec_dataset: str,
) -> Dict[str, Any]:
    return {
        "document_title": title,
        "source_url": source_url,
        "source_type": infer_source_type_from_url(source_url, doc_type=doc_type),
        "regulatory_body": ["SEC"],
        "sec_dataset": sec_dataset,
    }


def _classify_segment(
    segment_text: str,
    doc_ctx: Dict[str, Any],
    *,
    client: Optional[OpenAI],
    max_chars: int,
    retry_chars: int = 4_000,
) -> Dict[str, Any]:
    """Classify full segment text once; retry with a shorter excerpt on classifier failure."""
    capped = _cap_text(segment_text, max_chars=max_chars)
    attempts = [capped]
    shorter = _cap_text(capped, max_chars=min(retry_chars, len(capped)))
    if shorter != capped:
        attempts.append(shorter)

    last_error: Optional[Exception] = None
    for text in attempts:
        try:
            classified = classify_chunk(
                chunk_text=text,
                document_context=doc_ctx,
                client=client,
            )
            normalized, errors = validate_classification(classified)
            meta: Dict[str, Any] = {
                "domain_primary": normalized["domain_primary"],
                "domain_secondary": normalized["domain_secondary"],
                "subdomain": normalized["subdomain"],
                "lifecycle_stage": normalized["lifecycle_stage"],
                "durability_tier": normalized["durability_tier"],
                "classification_confidence": normalized["confidence"],
                "classification_reason": normalized.get("reasoning_summary", ""),
                "validation_status": normalized["validation_status"],
            }
            if errors:
                meta["classification_validation_errors"] = errors[:50]
            return meta
        except Exception as e:
            last_error = e

    return {
        "validation_status": "pending_review",
        "classification_error": str(last_error)[:500] if last_error else "classification failed",
    }


def _classification_to_embed_record(
    *,
    vector_id: str,
    row_key: str,
    sec_dataset: str,
    source_url: str,
    content_part: str,
    chunk_index: int,
    classified_meta: Dict[str, Any],
    ingested_at: str,
) -> Dict[str, Any]:
    conf = classified_meta.get("classification_confidence")
    if isinstance(conf, dict):
        conf_str = json.dumps(conf, ensure_ascii=False)
    else:
        conf_str = _clean_str(conf)

    err_list = classified_meta.get("classification_validation_errors")
    if isinstance(err_list, list):
        err_str = json.dumps(err_list, ensure_ascii=False)
    else:
        err_str = _clean_str(err_list)

    domain_secondary = classified_meta.get("domain_secondary") or []
    subdomain = classified_meta.get("subdomain") or []

    return {
        "id": vector_id,
        "row_key": row_key,
        "sec_dataset": sec_dataset,
        "source_url": source_url,
        "content_part": content_part,
        "chunk_index": chunk_index,
        "domain_primary": _clean_str(classified_meta.get("domain_primary")),
        "domain_secondary": json.dumps(domain_secondary, ensure_ascii=False)
        if isinstance(domain_secondary, list)
        else _clean_str(domain_secondary),
        "subdomain": json.dumps(subdomain, ensure_ascii=False)
        if isinstance(subdomain, list)
        else _clean_str(subdomain),
        "lifecycle_stage": _clean_str(classified_meta.get("lifecycle_stage")),
        "durability_tier": _clean_str(classified_meta.get("durability_tier")),
        "classification_confidence": conf_str,
        "classification_reason": _clean_str(classified_meta.get("classification_reason")),
        "validation_status": _clean_str(classified_meta.get("validation_status")),
        "classification_validation_errors": err_str,
        "classification_error": _clean_str(classified_meta.get("classification_error")),
        "classified_at": _utc_now_iso(),
        "ingested_at": ingested_at,
        "status": EMBED_STATUS_SUCCESS,
        "reason": None,
    }


def _truncate_reason(reason: str) -> str:
    s = (reason or "").strip()
    if len(s) <= _REASON_MAX_LEN:
        return s
    return s[: _REASON_MAX_LEN - 3] + "..."


def _failure_row_id(row_key: str) -> str:
    return make_chunk_id(f"{row_key}|{ROW_STATUS_CONTENT_PART}", None, 0)


def _failure_embed_record(
    *,
    row_key: str,
    sec_dataset: str,
    source_url: str,
    reason: str,
) -> Dict[str, Any]:
    now = _utc_now_iso()
    return {
        "id": _failure_row_id(row_key),
        "row_key": row_key,
        "sec_dataset": sec_dataset,
        "source_url": source_url or "",
        "content_part": ROW_STATUS_CONTENT_PART,
        "chunk_index": -1,
        "domain_primary": "",
        "domain_secondary": "",
        "subdomain": "",
        "lifecycle_stage": "",
        "durability_tier": "",
        "classification_confidence": "",
        "classification_reason": "",
        "validation_status": "",
        "classification_validation_errors": "",
        "classification_error": "",
        "classified_at": "",
        "ingested_at": now,
        "status": EMBED_STATUS_FAILURE,
        "reason": _truncate_reason(reason),
    }


def failed_row_keys(embed_df: pd.DataFrame) -> Set[str]:
    """Row keys with a prior Failure status in the embed backup (case-insensitive)."""
    if embed_df.empty or "status" not in embed_df.columns or "row_key" not in embed_df.columns:
        return set()
    mask = embed_df["status"].astype(str).str.strip().str.lower() == "failure"
    if not mask.any():
        return set()
    return set(embed_df.loc[mask, "row_key"].astype(str).str.strip()) - {""}


def filter_pending_indices(
    df: pd.DataFrame,
    pending_idx: List[Any],
    failed_keys: Set[str],
) -> List[Any]:
    if not failed_keys:
        return list(pending_idx)
    out: List[Any] = []
    for idx in pending_idx:
        rk = _clean_str(df.loc[idx].get("row_key"))
        if rk and rk in failed_keys:
            continue
        out.append(idx)
    return out


def load_embed_table(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=EMBED_COLUMNS)
    df = load_dataframe(path)
    for col in EMBED_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[EMBED_COLUMNS]


def append_embed_records(path: Path, records: List[Dict[str, Any]]) -> int:
    if not records:
        return 0
    existing = load_embed_table(path)
    new_df = pd.DataFrame(records)
    for col in EMBED_COLUMNS:
        if col not in new_df.columns:
            new_df[col] = ""
    new_df = new_df[EMBED_COLUMNS]

    failure_mask = new_df["content_part"].astype(str) == ROW_STATUS_CONTENT_PART
    failure_df = new_df[failure_mask]
    chunk_df = new_df[~failure_mask]

    if not existing.empty:
        if not chunk_df.empty:
            new_ids = set(chunk_df["id"].astype(str))
            existing = existing[~existing["id"].astype(str).isin(new_ids)]
        for _, fail_row in failure_df.iterrows():
            rk = str(fail_row.get("row_key", "")).strip()
            if not rk:
                continue
            row_match = existing["row_key"].astype(str).str.strip() == rk
            status_fail = existing["status"].astype(str).str.strip().str.lower() == "failure"
            part_match = existing["content_part"].astype(str) == ROW_STATUS_CONTENT_PART
            drop = row_match & (status_fail | part_match)
            existing = existing[~drop]

    parts = [existing] if not existing.empty else []
    if not chunk_df.empty:
        parts.append(chunk_df)
    if not failure_df.empty:
        parts.append(failure_df)
    combined = pd.concat(parts, ignore_index=True) if parts else new_df
    save_dataframe(combined, path)
    return len(records)


def record_row_failure(
    path: Path,
    row: pd.Series,
    cfg: TableConfig,
    reason: str,
) -> int:
    row_key = _clean_str(row.get("row_key"))
    if not row_key:
        return 0
    source_url = primary_detail_url(row.to_dict()) or ""
    record = _failure_embed_record(
        row_key=row_key,
        sec_dataset=cfg.sec_dataset,
        source_url=source_url,
        reason=reason,
    )
    return append_embed_records(path, [record])


def _row_title(row: pd.Series) -> str:
    t = _clean_str(row.get("context_title"))
    if t:
        return t
    return row_fallback_title(row.to_dict())


def row_to_buffered_vectors(
    row: pd.Series,
    cfg: TableConfig,
    *,
    client: Optional[OpenAI],
    max_tokens: int,
    overlap_tokens: int,
    dry_run: bool,
    classify_max_chars: int = 12_000,
) -> Tuple[List[BufferedVector], List[Dict[str, Any]], int]:
    """
    Build chunks for one row. Returns (buffered_vectors, embed_backup_records, chunk_count).

    Each segment (main or resource) is classified once on capped full text, then chunked;
    all chunks from that segment share the same CRI metadata.
    dry_run: chunk count only, no classification or vectors.
    """
    row_key = _clean_str(row.get("row_key"))
    if not row_key:
        return [], [], 0

    segments = build_segments(row)
    if not segments:
        return [], [], 0

    title = _row_title(row)
    pub_date = _publication_date(row, cfg)
    extra = _row_extra_metadata(row, cfg)
    buffered: List[BufferedVector] = []
    backup_records: List[Dict[str, Any]] = []
    chunk_count = 0

    for segment in segments:
        doc_type = "pdf" if _is_pdf_url(segment.source_url) else "html"
        doc_ctx = _document_context(
            title=title,
            source_url=segment.source_url,
            doc_type=doc_type,
            sec_dataset=cfg.sec_dataset,
        )
        classified_meta: Dict[str, Any] = {}
        if not dry_run:
            classified_meta = _classify_segment(
                segment.text,
                doc_ctx,
                client=client,
                max_chars=classify_max_chars,
            )

        texts = chunk_text(segment.text, max_tokens=max_tokens, overlap_tokens=overlap_tokens)
        for chunk_index, text in enumerate(texts):
            chunk_count += 1
            if dry_run:
                continue

            vector_id = _chunk_id(row_key, segment, chunk_index)
            base_meta: Dict[str, Any] = {
                "source_url": segment.source_url,
                "title": title or "N/A",
                "page": "N/A",
                "type": doc_type,
                "document_text": text,
                "sec_dataset": cfg.sec_dataset,
                "row_key": row_key,
                "chunk_index": chunk_index,
                "content_part": segment.content_part,
                "publication_date": pub_date,
                **extra,
            }
            if segment.resource_label:
                base_meta["resource_label"] = segment.resource_label

            full_meta = sanitize_metadata_for_pinecone({**base_meta, **classified_meta})
            ingested_at = _utc_now_iso()
            backup_records.append(
                _classification_to_embed_record(
                    vector_id=vector_id,
                    row_key=row_key,
                    sec_dataset=cfg.sec_dataset,
                    source_url=segment.source_url,
                    content_part=segment.content_part,
                    chunk_index=chunk_index,
                    classified_meta=classified_meta,
                    ingested_at=ingested_at,
                )
            )
            chunk = DocumentChunk(
                id=vector_id,
                text=text,
                source_url=segment.source_url,
                title=title,
                page=None,
                doc_type=doc_type,
            )
            buffered.append(BufferedVector(chunk=chunk, metadata=full_meta))

    return buffered, backup_records, chunk_count


def _upsert_buffered(
    buffered: List[BufferedVector],
    index: Any,
    namespace: str,
    vector_batch_size: int,
) -> int:
    upserted = 0
    for i in range(0, len(buffered), vector_batch_size):
        batch = buffered[i : i + vector_batch_size]
        vectors = buffered_to_pinecone_vectors(batch)
        upsert_vector_batch(vectors, index, namespace)
        upserted += len(batch)
    return upserted


def ingest_one_table(
    cfg: TableConfig,
    *,
    test_mode: bool = False,
    limit_rows: Optional[int] = None,
    dry_run: bool = False,
    row_batch_size: Optional[int] = None,
    vector_batch_size: Optional[int] = None,
    client: Optional[OpenAI] = None,
    index: Any = None,
    namespace: Optional[str] = None,
) -> IngestPageStats:
    stats = IngestPageStats(
        sec_dataset=cfg.sec_dataset,
        source_table=cfg.source_filename,
        embed_backup=cfg.embed_path.name,
        dry_run=dry_run,
    )

    if not cfg.source_path.exists():
        print(f"Skipping {cfg.sec_dataset}: missing {cfg.source_path}")
        return stats

    df = load_dataframe(cfg.source_path)
    embed_df = load_embed_table(cfg.embed_path)
    failed_keys = failed_row_keys(embed_df)

    pending_mask = ~df["vectorized"].fillna(False).astype(bool)
    pending_idx = list(df.index[pending_mask])
    stats.pending_rows = len(pending_idx)

    if failed_keys:
        before = len(pending_idx)
        pending_idx = filter_pending_indices(df, pending_idx, failed_keys)
        stats.rows_already_failed = before - len(pending_idx)
        if stats.rows_already_failed:
            print(
                f"  Skipping {stats.rows_already_failed} row(s) with prior Failure "
                f"in {cfg.embed_path.name}"
            )

    if not pending_idx:
        stats.print_summary()
        return stats

    if test_mode:
        pending_idx = pending_idx[:1]
    elif limit_rows is not None:
        pending_idx = pending_idx[: max(0, limit_rows)]

    row_batch = row_batch_size or _env_int("SEC_INGEST_ROW_BATCH_SIZE", 10)
    vec_batch = vector_batch_size or _env_int("SEC_INGEST_VECTOR_BATCH_SIZE", 32)
    max_tokens = _env_int("SEC_CHUNK_MAX_TOKENS", 500)
    overlap_tokens = _env_int("SEC_CHUNK_OVERLAP_TOKENS", 100)
    classify_max_chars = _env_int("SEC_CLASSIFY_MAX_CHARS", 12_000)
    ns = namespace or PINECONE_NAMESPACE

    if not dry_run and index is None:
        ensure_index_exists()
        pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
        index = pc.Index(PINECONE_INDEX_NAME)

    if not dry_run and client is None:
        client = OpenAI()

    progress = tqdm(
        total=len(pending_idx),
        desc=f"ingest {cfg.sec_dataset}",
        unit="row",
    )
    for batch_start in range(0, len(pending_idx), row_batch):
        batch_indices = pending_idx[batch_start : batch_start + row_batch]
        batch_backup: List[Dict[str, Any]] = []

        for idx in batch_indices:
            stats.rows_processed += 1
            progress.update(1)
            progress.set_postfix(
                embedded=stats.rows_embedded,
                failures=stats.failures,
                refresh=False,
            )
            row = df.loc[idx]
            try:
                buffered, backup_records, chunk_count = row_to_buffered_vectors(
                    row,
                    cfg,
                    client=client,
                    max_tokens=max_tokens,
                    overlap_tokens=overlap_tokens,
                    dry_run=dry_run,
                    classify_max_chars=classify_max_chars,
                )
            except Exception as e:
                stats.failures += 1
                print(f"  ERROR row_key={row.get('row_key')}: {e}")
                if not dry_run:
                    rk = _clean_str(row.get("row_key"))
                    if rk:
                        batch_backup.append(
                            _failure_embed_record(
                                row_key=rk,
                                sec_dataset=cfg.sec_dataset,
                                source_url=primary_detail_url(row.to_dict()) or "",
                                reason=str(e),
                            )
                        )
                continue

            if chunk_count == 0:
                stats.rows_skipped += 1
                print(f"  SKIP row_key={row.get('row_key')}: no embeddable text")
                if not dry_run:
                    rk = _clean_str(row.get("row_key"))
                    if rk:
                        batch_backup.append(
                            _failure_embed_record(
                                row_key=rk,
                                sec_dataset=cfg.sec_dataset,
                                source_url=primary_detail_url(row.to_dict()) or "",
                                reason="no embeddable text",
                            )
                        )
                continue

            if dry_run:
                stats.chunks_upserted += chunk_count
                continue

            try:
                upserted = _upsert_buffered(buffered, index, ns, vec_batch)
                stats.chunks_upserted += upserted
                batch_backup.extend(backup_records)
                df.at[idx, "vectorized"] = True
                stats.rows_embedded += 1
            except Exception as e:
                stats.failures += 1
                print(f"  ERROR upsert row_key={row.get('row_key')}: {e}")
                if not dry_run:
                    rk = _clean_str(row.get("row_key"))
                    if rk:
                        batch_backup.append(
                            _failure_embed_record(
                                row_key=rk,
                                sec_dataset=cfg.sec_dataset,
                                source_url=primary_detail_url(row.to_dict()) or "",
                                reason=str(e),
                            )
                        )

        if batch_backup and not dry_run:
            added = append_embed_records(cfg.embed_path, batch_backup)
            stats.backup_rows_added += added

        if not dry_run:
            save_dataframe(df, cfg.source_path)

    progress.close()
    stats.print_summary()
    return stats


def run_ingest(
    *,
    dataset: Optional[str] = None,
    test_mode: bool = False,
    limit_rows: Optional[int] = None,
    dry_run: bool = False,
) -> List[IngestPageStats]:
    if dataset:
        cfg = _registry_by_dataset(dataset)
        if cfg is None:
            known = ", ".join(c.sec_dataset for c in TABLE_REGISTRY)
            raise SystemExit(f"Unknown dataset {dataset!r}. Known: {known}")
        configs: Sequence[TableConfig] = (cfg,)
    else:
        configs = TABLE_REGISTRY

    all_stats: List[IngestPageStats] = []
    client: Optional[OpenAI] = None
    index: Any = None
    ns = PINECONE_NAMESPACE

    if not dry_run:
        ensure_index_exists()
        pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
        index = pc.Index(PINECONE_INDEX_NAME)
        client = OpenAI()

    for cfg in configs:
        stats = ingest_one_table(
            cfg,
            test_mode=test_mode,
            limit_rows=limit_rows,
            dry_run=dry_run,
            client=client,
            index=index,
            namespace=ns,
        )
        all_stats.append(stats)

    if len(all_stats) > 1:
        total_rows = sum(s.rows_embedded for s in all_stats)
        total_processed = sum(s.rows_processed for s in all_stats)
        total_chunks = sum(s.chunks_upserted for s in all_stats)
        print("\n=== Ingest job complete ===")
        for s in all_stats:
            if s.dry_run:
                print(
                    f"  {s.sec_dataset:<32} rows_processed={s.rows_processed}  "
                    f"chunks={s.chunks_upserted}"
                )
            else:
                print(
                    f"  {s.sec_dataset:<32} rows_embedded={s.rows_embedded}  "
                    f"chunks={s.chunks_upserted}"
                )
        if dry_run:
            print(
                f"  {'TOTAL':<32} rows_processed={total_processed}  chunks={total_chunks}"
            )
        else:
            print(f"  {'TOTAL':<32} rows_embedded={total_rows}  chunks={total_chunks}")

    return all_stats


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Embed SEC scraping dataframes into Pinecone (vectorized=False rows only)."
    )
    parser.add_argument(
        "--dataset",
        help="Process one table by sec_dataset slug (e.g. crypto-newsroom)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Ingest at most one pending row per table",
    )
    parser.add_argument(
        "--limit-rows",
        type=int,
        default=None,
        help="Max pending rows per table (ignored when --test is set)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Chunk and summarize only; no Pinecone/OpenAI writes or vectorized updates",
    )
    args = parser.parse_args(argv)

    if args.test and args.limit_rows is not None:
        print("Note: --limit-rows is ignored when --test is set.")

    run_ingest(
        dataset=args.dataset,
        test_mode=args.test,
        limit_rows=args.limit_rows,
        dry_run=args.dry_run,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
