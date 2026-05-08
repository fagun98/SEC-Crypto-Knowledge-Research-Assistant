from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional, Tuple

from openai import OpenAI

from cri_ontology.prompts import build_classifier_prompt
from cri_ontology.validate import validate_classification

from dotenv import load_dotenv

load_dotenv()

def _extract_json_object(text: str) -> str:
    """
    Extract the most likely JSON object from a model response.
    Tolerates extra leading/trailing text.
    """
    if not text:
        raise ValueError("Empty model response text.")
    s = text.strip()
    start = s.find("{") 
    end = s.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in response.")
    return s[start : end + 1]


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _get_env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return int(raw)
    except Exception:
        return default


def _call_openai_classifier(
    *,
    prompt: str,
    model: str,
    max_output_tokens: int,
    client: Optional[OpenAI] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Returns (parsed_json, debug_info).
    """
    c = client or OpenAI()
    resp = c.responses.create(
        model=model,
        input=prompt,
        text={"format": {"type": "text"}},
        max_output_tokens=max_output_tokens,
    )
    raw = (resp.output_text or "").strip()
    json_str = _extract_json_object(raw)
    data = json.loads(json_str)

    usage = getattr(resp, "usage", None)
    debug = {
        "model": model,
        "max_output_tokens": max_output_tokens,
        "raw_text_len": len(raw),
        "input_tokens": getattr(usage, "input_tokens", None)
        or getattr(usage, "prompt_tokens", None),
        "output_tokens": getattr(usage, "output_tokens", None)
        or getattr(usage, "completion_tokens", None),
    }
    return data, debug


def classify_chunk(
    chunk_text: str,
    document_context: Optional[Dict[str, Any]] = None,
    *,
    client: Optional[OpenAI] = None,
) -> Dict[str, Any]:
    """
    Classify a chunk under the CRI Regulatory Ontology.

    Returns a dict matching the schema from the source document:
    {
      domain_primary, domain_secondary, subdomain,
      lifecycle_stage, durability_tier,
      confidence: {...},
      reasoning_summary
    }
    """
    if not isinstance(chunk_text, str) or not chunk_text.strip():
        raise ValueError("chunk_text must be a non-empty string.")

    model = os.getenv("CRI_CLASSIFIER_MODEL", "gpt-5-mini")
    max_output_tokens = _get_env_int("CRI_CLASSIFIER_MAX_OUTPUT_TOKENS", 1200)

    prompt = build_classifier_prompt(
        chunk_text=chunk_text.strip(),
        document_context=document_context or {},
    )

    data, debug = _call_openai_classifier(
        prompt=prompt,
        model=model,
        max_output_tokens=max_output_tokens,
        client=client,
    )

    # Normalize minimal shape defensively; strict validation occurs later.
    out: Dict[str, Any] = {
        "domain_primary": data.get("domain_primary", ""),
        "domain_secondary": data.get("domain_secondary") or [],
        "subdomain": data.get("subdomain") or [],
        "lifecycle_stage": data.get("lifecycle_stage", ""),
        "durability_tier": data.get("durability_tier", ""),
        "confidence": data.get("confidence") or {},
        "reasoning_summary": data.get("reasoning_summary") or "",
        "_debug": debug,
    }

    conf = out["confidence"]
    if isinstance(conf, dict):
        out["confidence"] = {
            "domain_primary": _safe_float(conf.get("domain_primary"), 0.0),
            "subdomain": _safe_float(conf.get("subdomain"), 0.0),
            "lifecycle_stage": _safe_float(conf.get("lifecycle_stage"), 0.0),
            "durability_tier": _safe_float(conf.get("durability_tier"), 0.0),
        }
    else:
        out["confidence"] = {
            "domain_primary": 0.0,
            "subdomain": 0.0,
            "lifecycle_stage": 0.0,
            "durability_tier": 0.0,
        }

    return out


if __name__ == "__main__":
    # Minimal local smoke test.
    #
    # Prereqs:
    # - OPENAI_API_KEY set in your environment
    # - (optional) CRI_CLASSIFIER_MODEL / CRI_CLASSIFIER_MAX_OUTPUT_TOKENS
    example_chunk = (
        "The SEC Division of Trading and Markets clarified broker-dealer custody "
        "obligations for customer digital asset securities, including possession or control."
    )
    example_context = {
        "document_title": "SEC Trading and Markets FAQ on Crypto Broker-Dealer Activities",
        "source_url": "https://www.sec.gov/",
        "publication_date": "2025-05-01",
        "source_type": "faq",
        "regulatory_body": ["SEC"],
    }

    raw = classify_chunk(example_chunk, example_context)
    normalized, errors = validate_classification(raw)

    print("\n=== Raw classifier output ===")
    print(json.dumps(raw, ensure_ascii=False, indent=2))

    print("\n=== Validated / normalized ===")
    print(json.dumps(normalized, ensure_ascii=False, indent=2))

    if errors:
        print("\n=== Validation errors (pending_review) ===")
        for e in errors:
            print(f"- {e}")

