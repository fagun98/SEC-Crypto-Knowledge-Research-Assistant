# CRI Ontology (`cri_ontology/`)

This folder contains the **Crypto Regulatory Insight (CRI) chunk-level ontology classifier** and related utilities.

The goal is to attach regulatory ontology metadata to each Pinecone chunk so retrieval can use:

`semantic search + metadata filtering`

## What gets written to Pinecone metadata

After classification, each vector/chunk is updated with (at minimum):

- **`domain_primary`**: string (one of the domain codes)
- **`domain_secondary`**: list[string] (0+ domain codes)
- **`subdomain`**: list[string] (1+ subdomain codes)
- **`lifecycle_stage`**: string (`PRE|PROP|INTPR|FINAL|ENFORCED|SUPER`)
- **`durability_tier`**: string (`T1|T2|T3|T4|T5`)

Plus additional review/debug fields:

- **`classification_confidence`**: object with scores in `[0,1]`
- **`classification_reason`**: short text summary for why the labels were chosen
- **`validation_status`**: `auto` or `pending_review`
- **`classification_validation_errors`** (optional): list of validation errors (when present)
- **`ontology_version`** (optional): e.g. `"v1"`
- **`classified_at`** (optional): ISO timestamp

## Modules

### `constants.py`
Canonical allowlists for:

- domain codes (`AC, RO, MS, CU, SC, DP, CB, EL, SP, IP`)
- lifecycle stages (`PRE, PROP, INTPR, FINAL, ENFORCED, SUPER`)
- durability tiers (`T1..T5`)
- all subdomain codes

Also includes:

- `SUBDOMAIN_TO_DOMAIN`: reverse mapping used for alignment checks.

### `prompts.py`
`build_classifier_prompt(chunk_text, document_context)` builds the LLM prompt (based on the source spec).

### `classifier.py`
`classify_chunk(chunk_text: str, document_context: dict | None = None) -> dict`

- Calls `OpenAI().responses.create(...)`
- Extracts/loads a JSON object from the model output
- Normalizes the returned shape and confidence keys

Environment variables:

- `CRI_CLASSIFIER_MODEL` (default: `gpt-5-mini`)
- `CRI_CLASSIFIER_MAX_OUTPUT_TOKENS` (default: `1200`)

### `validate.py`
`validate_classification(result: dict) -> tuple[dict, list[str]]`

Validates and normalizes classifier output:

- required fields exist and are correct types
- `domain_primary` and `domain_secondary` contain only allowed domain codes
- `lifecycle_stage` and `durability_tier` are allowed values
- `subdomain` contains only allowed subdomain codes
- **subdomain-domain alignment**: each subdomain must belong to `domain_primary` or a listed secondary domain
- confidence values are coerced into floats and clamped to `[0,1]`

Sets:

- `validation_status` to `auto` when all required confidence scores are high enough (else `pending_review`)

### `document_context.py`
Helpers used to enrich / infer document-level context:

- `infer_source_type_from_url(url, doc_type=None)` (SEC-centric URL heuristics)
- `extract_publication_date_from_html(html)` (best-effort meta/time/date parsing)
- `build_document_context_from_metadata(meta)` (normalizes Pinecone metadata into LLM context)

## Scripts that use this package

These scripts live in `scripts/` and are intended to be run in this order.

### 1) Enrich document context in Pinecone

This script adds (or fills missing) document-level metadata fields used as classifier context:

- `publication_date`
- `source_type`
- `regulatory_body`

Run:

```bash
python scripts/enrich_pinecone_document_context.py --only-missing --max-records 200
```

Required environment variables:

- `PINECONE_API_KEY`
- `PINECONE_NAMESPACE`
- `PINECONE_INDEX_NAME` **or** `PINECONE_INDEX`

### 2) Backfill CRI ontology metadata for existing vectors

Classifies each Pinecone record and updates metadata with ontology fields + confidence + validation.

Run:

```bash
python scripts/backfill_cri_ontology_metadata.py --max-records 200
```

Outputs:

- `cri_backfill_log.jsonl`
- `cri_pending_review_ids.json`
- `cri_backfill_failures.json`

## Optional: classify on ingestion

`crypto_ingest.py` supports classifying chunks during `upsert_chunks(...)` when enabled:

```bash
export CRI_CLASSIFY_ON_INGEST=1
```

Notes:

- Ingest-time classification uses best-effort context (URL/title/type). For best accuracy, run the context enrichment + backfill scripts across the corpus.

## Minimal “document context” recommended shape

The classifier prompt accepts a free-form JSON object; in this repo we typically pass:

```json
{
  "document_title": "…",
  "source_url": "https://www.sec.gov/…",
  "publication_date": "YYYY-MM-DD",
  "source_type": "speech_or_statement | press_release | rulemaking | …",
  "regulatory_body": ["SEC"],
  "source_doc_type": "html|pdf",
  "page": 3
}
```

