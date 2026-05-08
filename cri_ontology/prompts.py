from __future__ import annotations

import json
from typing import Any, Dict, Optional

from cri_ontology.constants import DOMAIN_CODES, SUBDOMAINS_BY_DOMAIN


def _to_cdata(text: str) -> str:
    """
    Wrap text in CDATA, safely handling the CDATA terminator.
    """
    # Split the CDATA terminator to avoid ending the section early.
    safe = (text or "").replace("]]>", "]]]]><![CDATA[>")
    return f"<![CDATA[{safe}]]>"


DOMAIN_LABELS: Dict[str, str] = {
    "AC": "Asset Classification",
    "RO": "Registration & Offering",
    "MS": "Market Structure",
    "CU": "Custody & Safeguarding",
    "SC": "Stablecoin Regulation",
    "DP": "DeFi & Protocol Governance",
    "CB": "Cross-Border & International",
    "EL": "Enforcement & Litigation",
    "SP": "Systemic Risk & Prudential",
    "IP": "Investor Protection & Disclosure",
}


SUBDOMAIN_LABELS: Dict[str, str] = {
    # AC
    "AC-HOW": "Howey Investment Contract Analysis",
    "AC-REV": "Reves Note Analysis",
    "AC-TAX": "Joint SEC-CFTC Taxonomy (March 2026)",
    "AC-DEC": "Sufficient Decentralization",
    "AC-SEC": "Secondary Market Status",
    "AC-NFT": "NFT / Collectible Classification",
    "AC-MEM": "Memecoin / Non-Utility Token Status",
    # RO
    "RO-REG": "Full Registration Pathways",
    "RO-EXM": "Exemptive Relief & Safe Harbors",
    "RO-DIS": "Offering Disclosure Requirements",
    "RO-AIR": "Airdrops, Mining & Staking Receipts",
    "RO-ICA": "Investment Company Act Implications",
    # MS
    "MS-ATS": "ATS Registration & Operation",
    "MS-BDR": "Broker-Dealer Obligations",
    "MS-DEX": "DEX / AMM Regulatory Status",
    "MS-CLE": "Clearing & Settlement",
    "MS-WAC": "Williams Act & Aggregation",
    # CU
    "CU-IAC": "Investment Adviser Custody Rule",
    "CU-BDC": "Broker-Dealer Customer Protection",
    "CU-SPB": "SPBD Framework (Legacy)",
    "CU-TEC": "Custody Technology Standards",
    "CU-UCC": "UCC Treatment",
    "CU-BNK": "Banking Custody & SAB 121 Reversal",
    "CU-SIP": "SIPA/SIPC Coverage",
    # SC
    "SC-GEN": "GENIUS Act Framework",
    "SC-RES": "Reserve & Redemption Requirements",
    "SC-YLD": "Yield Restriction",
    "SC-THR": "$10 Billion Threshold",
    "SC-SEC": "Stablecoin Securities Status",
    "SC-TOK": "Tokenized Deposits",
    # DP
    "DP-FEE": "Fee-Switch & Revenue Accrual",
    "DP-GOV": "Governance Token Classification",
    "DP-DAO": "DAO Legal Liability",
    "DP-STK": "Staking & Restaking",
    "DP-WRP": "Wrapping & Bridging",
    "DP-LEN": "DeFi Lending & Borrowing",
    # CB
    "CB-MCA": "EU MiCA Framework",
    "CB-FCA": "UK FCA Crypto Regime",
    "CB-EQV": "Equivalence & Mutual Recognition",
    "CB-TRL": "Travel Rule (International)",
    "CB-COM": "Comparative Analysis",
    # EL
    "EL-SEC": "SEC Enforcement Actions",
    "EL-CFT": "CFTC Enforcement Actions",
    "EL-LIT": "Private Litigation",
    "EL-DIS": "Enforcement Dismissals & Withdrawals",
    "EL-STL": "Settlement Terms & Conditions",
    # SP
    "SP-AML": "AML / KYC / Sanctions",
    "SP-SYS": "FSOC Systemic Risk Assessment",
    "SP-BNK": "Banking Guardrails",
    "SP-PRI": "Privacy & Surveillance",
    # IP
    "IP-PER": "Periodic Disclosure Obligations",
    "IP-SUI": "Suitability & Conduct Standards",
    "IP-RET": "Retail Investor Protections",
    "IP-MKT": "Marketing & Advertising Standards",
}


LIFECYCLE_LABELS: Dict[str, str] = {
    "PRE": "Pre-Regulatory / Concept",
    "PROP": "Proposed",
    "INTPR": "Interpretive / Guidance",
    "FINAL": "Final / Adopted",
    "ENFORCED": "Enforced / Litigated",
    "SUPER": "Superseded / Revoked",
}


DURABILITY_LABELS: Dict[str, str] = {
    "T1": "Statutory",
    "T2": "Commission-Level",
    "T3": "Judicial Precedent",
    "T4": "Staff Guidance",
    "T5": "Informal / Transitional",
}


def build_classifier_prompt(*, chunk_text: str, document_context: Optional[Dict[str, Any]]) -> str:
    """
    Build the CRI ontology classifier prompt, returning a single string input
    suitable for OpenAI Responses API.
    """
    doc_ctx = document_context or {}
    # Keep it compact and deterministic for stable model behavior.
    ctx_str = json.dumps(doc_ctx, ensure_ascii=False, sort_keys=True)

    # Stable ordering helps model and tests.
    ordered_domains = [d for d in ("AC", "RO", "MS", "CU", "SC", "DP", "CB", "EL", "SP", "IP") if d in DOMAIN_CODES]
    ordered_lifecycle = ["PRE", "PROP", "INTPR", "FINAL", "ENFORCED", "SUPER"]
    ordered_tiers = ["T1", "T2", "T3", "T4", "T5"]

    domains_xml = "\n".join(
        f'      <domain code="{d}">{DOMAIN_LABELS.get(d, d)}</domain>' for d in ordered_domains
    )

    subdomains_xml_parts = []
    for dom in ordered_domains:
        sds = sorted(SUBDOMAINS_BY_DOMAIN.get(dom, frozenset()))
        if not sds:
            continue
        subdomains_xml_parts.append(f'      <domain code="{dom}">')
        for sd in sds:
            subdomains_xml_parts.append(
                f'        <subdomain code="{sd}">{SUBDOMAIN_LABELS.get(sd, sd)}</subdomain>'
            )
        subdomains_xml_parts.append("      </domain>")
    subdomains_xml = "\n".join(subdomains_xml_parts)

    lifecycle_xml = "\n".join(
        f'      <stage code="{s}">{LIFECYCLE_LABELS.get(s, s)}</stage>' for s in ordered_lifecycle
    )
    tiers_xml = "\n".join(
        f'      <tier code="{t}">{DURABILITY_LABELS.get(t, t)}</tier>' for t in ordered_tiers
    )

    output_schema = {
        "domain_primary": "",
        "domain_secondary": [],
        "subdomain": [],
        "lifecycle_stage": "",
        "durability_tier": "",
        "confidence": {
            "domain_primary": 0.0,
            "subdomain": 0.0,
            "lifecycle_stage": 0.0,
            "durability_tier": 0.0,
        },
        "reasoning_summary": "",
    }
    output_schema_str = json.dumps(output_schema, ensure_ascii=False, sort_keys=False, indent=2)

    return f"""
    <cri_classifier_request>
      <role>You are a regulatory ontology classifier for Crypto Regulatory Insight (CRI).</role>
      <task>Classify a document chunk according to the CRI Regulatory Ontology.</task>

      <allowed_values>
        <domains>
          {domains_xml}
        </domains>

        <subdomains>
          {subdomains_xml}
        </subdomains>

        <lifecycle_stages>
          {lifecycle_xml}
        </lifecycle_stages>

        <durability_tiers>
          {tiers_xml}
        </durability_tiers>
      </allowed_values>

      <rules>
        <rule>domain_primary must be exactly one domain code.</rule>
        <rule>domain_secondary must be a JSON array of zero or more domain codes.</rule>
        <rule>subdomain must be a JSON array of one or more valid subdomain codes.</rule>
        <rule>lifecycle_stage must be exactly one of: PRE, PROP, INTPR, FINAL, ENFORCED, SUPER.</rule>
        <rule>durability_tier must be exactly one of: T1, T2, T3, T4, T5.</rule>
        <rule>Do not invent new labels or keys. Use only the allowed codes.</rule>
        <rule>If the chunk is vague, use document-level context. If still uncertain, choose the most likely class and lower confidence.</rule>
        <rule>Prefer the actual legal authority of the source over the chunk’s phrasing.</rule>
        <rule>Heuristics: staff FAQ is usually lifecycle_stage=INTPR and durability_tier=T4; final rule/statute is usually FINAL with T1 or T2; court opinion is usually ENFORCED with T3; roundtable or written input is usually PRE with T5; superseded/revoked documents should be SUPER.</rule>
        <rule>Output must be a single JSON object only (no markdown, no backticks, no extra text).</rule>
      </rules>

      <document_context_json>{_to_cdata(ctx_str)}</document_context_json>
      <chunk_text>{_to_cdata(chunk_text)}</chunk_text>

      <output_schema_json>{_to_cdata(output_schema_str)}</output_schema_json>
    </cri_classifier_request>
    """

