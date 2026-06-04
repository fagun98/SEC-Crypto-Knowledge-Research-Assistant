from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from cri_ontology.constants import DOMAIN_CODES

logger = logging.getLogger(__name__)


def _as_str_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if v is not None and str(v).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def build_pinecone_filter(
    classification: Dict[str, Any],
    *,
    mode: str = "domain_primary",
) -> Optional[Dict[str, Any]]:
    """
    Build a Pinecone metadata filter from query classification.

    Modes:
      - domain_primary: filter on domain_primary only (v1 default)
      - full: OR across primary, secondary domains, and subdomains
    """
    normalized = classification.get("normalized") or classification
    domain_primary = (normalized.get("domain_primary") or "").strip()

    if not domain_primary or domain_primary not in DOMAIN_CODES:
        logger.warning(
            "Skipping Pinecone filter: invalid or missing domain_primary=%r",
            domain_primary,
        )
        return None

    if mode == "domain_primary":
        return {"domain_primary": {"$eq": domain_primary}}

    if mode == "full":
        clauses: List[Dict[str, Any]] = [
            {"domain_primary": {"$eq": domain_primary}},
        ]
        secondary = _as_str_list(normalized.get("domain_secondary"))
        if secondary:
            clauses.append({"domain_secondary": {"$in": secondary}})
        subdomains = _as_str_list(normalized.get("subdomain"))
        if subdomains:
            clauses.append({"subdomain": {"$in": subdomains}})
        if len(clauses) == 1:
            return clauses[0]
        return {"$or": clauses}

    logger.warning("Unknown filter mode %r; using domain_primary", mode)
    return {"domain_primary": {"$eq": domain_primary}}
