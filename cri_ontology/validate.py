from __future__ import annotations

from typing import Any, Dict, List, Tuple

from cri_ontology.constants import (
    DOMAIN_CODES,
    DURABILITY_TIERS,
    LIFECYCLE_STAGES,
    SUBDOMAIN_TO_DOMAIN,
    is_valid_subdomain,
)


def _as_str(x: Any) -> str:
    return x if isinstance(x, str) else ""


def _as_list_of_str(x: Any) -> List[str]:
    if x is None:
        return []
    if isinstance(x, list):
        out: List[str] = []
        for item in x:
            if isinstance(item, str) and item.strip():
                out.append(item.strip())
        return out
    if isinstance(x, str) and x.strip():
        return [x.strip()]
    return []


def _as_confidence_dict(x: Any) -> Dict[str, float]:
    if not isinstance(x, dict):
        return {}
    out: Dict[str, float] = {}
    for k in ("domain_primary", "subdomain", "lifecycle_stage", "durability_tier"):
        try:
            v = float(x.get(k, 0.0))
        except Exception:
            v = 0.0
        # Clamp into [0, 1]
        if v < 0.0:
            v = 0.0
        if v > 1.0:
            v = 1.0
        out[k] = v
    return out


def _determine_validation_status(
    confidence: Dict[str, float],
    errors: List[str],
    *,
    auto_threshold: float = 0.85,
    review_threshold: float = 0.65,
) -> str:
    if errors:
        return "pending_review"

    required_keys = ("domain_primary", "subdomain", "lifecycle_stage", "durability_tier")
    scores = [float(confidence.get(k, 0.0)) for k in required_keys]
    min_score = min(scores) if scores else 0.0

    if min_score >= auto_threshold:
        return "auto"
    if min_score >= review_threshold:
        return "pending_review"
    return "pending_review"


def validate_classification(result: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """
    Validate and normalize classifier output.

    Returns:
      (normalized_result, errors)
    """
    errors: List[str] = []
    if not isinstance(result, dict):
        return (
            {
                "domain_primary": "",
                "domain_secondary": [],
                "subdomain": [],
                "lifecycle_stage": "",
                "durability_tier": "",
                "confidence": {},
                "reasoning_summary": "",
                "validation_status": "pending_review",
            },
            ["Result is not a dict."],
        )

    domain_primary = _as_str(result.get("domain_primary")).strip()
    domain_secondary = _as_list_of_str(result.get("domain_secondary"))
    subdomain = _as_list_of_str(result.get("subdomain"))
    lifecycle_stage = _as_str(result.get("lifecycle_stage")).strip()
    durability_tier = _as_str(result.get("durability_tier")).strip()
    confidence = _as_confidence_dict(result.get("confidence"))
    reasoning_summary = _as_str(result.get("reasoning_summary")).strip()

    # Required fields
    if not domain_primary:
        errors.append("domain_primary missing/empty.")
    if not subdomain:
        errors.append("subdomain missing/empty (must be a list, can be broad but not empty).")
    if not lifecycle_stage:
        errors.append("lifecycle_stage missing/empty.")
    if not durability_tier:
        errors.append("durability_tier missing/empty.")

    # Allowed values
    if domain_primary and domain_primary not in DOMAIN_CODES:
        errors.append(f"domain_primary invalid: {domain_primary!r}.")

    # De-dup and normalize secondary domains
    cleaned_secondary: List[str] = []
    seen = set()
    for d in domain_secondary:
        if d not in DOMAIN_CODES:
            errors.append(f"domain_secondary contains invalid code: {d!r}.")
            continue
        if d == domain_primary:
            continue
        if d in seen:
            continue
        seen.add(d)
        cleaned_secondary.append(d)

    if lifecycle_stage and lifecycle_stage not in LIFECYCLE_STAGES:
        errors.append(f"lifecycle_stage invalid: {lifecycle_stage!r}.")

    if durability_tier and durability_tier not in DURABILITY_TIERS:
        errors.append(f"durability_tier invalid: {durability_tier!r}.")

    # Subdomain validation
    cleaned_subdomains: List[str] = []
    seen_sd = set()
    for sd in subdomain:
        if not is_valid_subdomain(sd):
            errors.append(f"subdomain contains invalid code: {sd!r}.")
            continue
        if sd in seen_sd:
            continue
        seen_sd.add(sd)
        cleaned_subdomains.append(sd)

    # Subdomain-domain alignment
    allowed_domains_for_subdomains = set([domain_primary] if domain_primary else []) | set(
        cleaned_secondary
    )
    for sd in cleaned_subdomains:
        owner = SUBDOMAIN_TO_DOMAIN.get(sd)
        if owner and owner not in allowed_domains_for_subdomains:
            errors.append(
                f"subdomain {sd!r} belongs to domain {owner!r}, but primary/secondary domains are {sorted(allowed_domains_for_subdomains)!r}."
            )

    validation_status = _determine_validation_status(confidence, errors)

    normalized: Dict[str, Any] = {
        "domain_primary": domain_primary,
        "domain_secondary": cleaned_secondary,
        "subdomain": cleaned_subdomains,
        "lifecycle_stage": lifecycle_stage,
        "durability_tier": durability_tier,
        "confidence": confidence,
        "reasoning_summary": reasoning_summary,
        "validation_status": validation_status,
    }

    return normalized, errors

