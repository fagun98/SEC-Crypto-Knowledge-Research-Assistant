from __future__ import annotations

from typing import Dict, FrozenSet, Set

# -----------------------------
# Primary domains (top-level)
# -----------------------------

DOMAIN_CODES: FrozenSet[str] = frozenset(
    {
        "AC",  # Asset Classification
        "RO",  # Registration & Offering
        "MS",  # Market Structure
        "CU",  # Custody & Safeguarding
        "SC",  # Stablecoin Regulation
        "DP",  # DeFi & Protocol Governance
        "CB",  # Cross-Border & International
        "EL",  # Enforcement & Litigation
        "SP",  # Systemic Risk & Prudential
        "IP",  # Investor Protection & Disclosure
    }
)

# -----------------------------
# Lifecycle stages
# -----------------------------

LIFECYCLE_STAGES: FrozenSet[str] = frozenset(
    {
        "PRE",
        "PROP",
        "INTPR",
        "FINAL",
        "ENFORCED",
        "SUPER",
    }
)

# -----------------------------
# Durability tiers
# -----------------------------

DURABILITY_TIERS: FrozenSet[str] = frozenset({"T1", "T2", "T3", "T4", "T5"})

# -----------------------------
# Subdomains (by domain)
# -----------------------------

SUBDOMAINS_BY_DOMAIN: Dict[str, FrozenSet[str]] = {
    # 7.1 Asset Classification — AC
    "AC": frozenset(
        {
            "AC-HOW",
            "AC-REV",
            "AC-TAX",
            "AC-DEC",
            "AC-SEC",
            "AC-NFT",
            "AC-MEM",
        }
    ),
    # 7.2 Registration & Offering — RO
    "RO": frozenset(
        {
            "RO-REG",
            "RO-EXM",
            "RO-DIS",
            "RO-AIR",
            "RO-ICA",
        }
    ),
    # 7.3 Market Structure — MS
    "MS": frozenset(
        {
            "MS-ATS",
            "MS-BDR",
            "MS-DEX",
            "MS-CLE",
            "MS-WAC",
        }
    ),
    # 7.4 Custody & Safeguarding — CU
    "CU": frozenset(
        {
            "CU-IAC",
            "CU-BDC",
            "CU-SPB",
            "CU-TEC",
            "CU-UCC",
            "CU-BNK",
            "CU-SIP",
        }
    ),
    # 7.5 Stablecoin Regulation — SC
    "SC": frozenset(
        {
            "SC-GEN",
            "SC-RES",
            "SC-YLD",
            "SC-THR",
            "SC-SEC",
            "SC-TOK",
        }
    ),
    # 7.6 DeFi & Protocol Governance — DP
    "DP": frozenset(
        {
            "DP-FEE",
            "DP-GOV",
            "DP-DAO",
            "DP-STK",
            "DP-WRP",
            "DP-LEN",
        }
    ),
    # 7.7 Cross-Border & International — CB
    "CB": frozenset(
        {
            "CB-MCA",
            "CB-FCA",
            "CB-EQV",
            "CB-TRL",
            "CB-COM",
        }
    ),
    # 7.8 Enforcement & Litigation — EL
    "EL": frozenset(
        {
            "EL-SEC",
            "EL-CFT",
            "EL-LIT",
            "EL-DIS",
            "EL-STL",
        }
    ),
    # 7.9 Systemic Risk & Prudential — SP
    "SP": frozenset(
        {
            "SP-AML",
            "SP-SYS",
            "SP-BNK",
            "SP-PRI",
        }
    ),
    # 7.10 Investor Protection & Disclosure — IP
    "IP": frozenset(
        {
            "IP-PER",
            "IP-SUI",
            "IP-RET",
            "IP-MKT",
        }
    ),
}

# Flattened set of all subdomains.
ALL_SUBDOMAINS: FrozenSet[str] = frozenset(
    sd for sds in SUBDOMAINS_BY_DOMAIN.values() for sd in sds
)

# Reverse lookup for validation: subdomain -> owning domain.
SUBDOMAIN_TO_DOMAIN: Dict[str, str] = {}
for dom, sds in SUBDOMAINS_BY_DOMAIN.items():
    for sd in sds:
        SUBDOMAIN_TO_DOMAIN[sd] = dom


def is_valid_domain(code: str) -> bool:
    return code in DOMAIN_CODES


def is_valid_lifecycle(code: str) -> bool:
    return code in LIFECYCLE_STAGES


def is_valid_durability(code: str) -> bool:
    return code in DURABILITY_TIERS


def is_valid_subdomain(code: str) -> bool:
    return code in ALL_SUBDOMAINS


def infer_domains_for_subdomains(subdomains: Set[str]) -> Set[str]:
    """Return the set of owning domains for a set of subdomains."""
    out: Set[str] = set()
    for sd in subdomains:
        dom = SUBDOMAIN_TO_DOMAIN.get(sd)
        if dom:
            out.add(dom)
    return out

