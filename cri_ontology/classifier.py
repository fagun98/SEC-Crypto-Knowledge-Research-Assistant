from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Optional, Tuple

from openai import OpenAI

from cri_ontology.prompts import build_classifier_prompt, build_query_classifier_prompt
from cri_ontology.validate import validate_classification

from dotenv import load_dotenv

load_dotenv()

def _strip_code_fence(text: str) -> str:
    s = (text or "").strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", s, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return s


def _extract_balanced_json_object(s: str) -> str:
    """
    Slice from first ``{`` to the matching closing ``}``, respecting ``"`` strings.
    """
    start = s.find("{")
    if start == -1:
        raise ValueError("No JSON object found in response.")
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(s)):
        c = s[i]
        if not in_string:
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return s[start : i + 1]
            elif c == '"':
                in_string = True
        else:
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                in_string = False
    raise ValueError("Unbalanced JSON object braces in response.")


def _strip_trailing_commas_json(s: str) -> str:
    """Remove ``,`` immediately before ``}`` or ``]`` outside of quoted strings."""
    out: list[str] = []
    i = 0
    n = len(s)
    in_string = False
    escape = False
    while i < n:
        c = s[i]
        if not in_string:
            if c == '"':
                in_string = True
                out.append(c)
                i += 1
                continue
            if c == ",":
                j = i + 1
                while j < n and s[j] in " \t\n\r":
                    j += 1
                if j < n and s[j] in "}]":
                    i += 1
                    continue
            out.append(c)
            i += 1
        else:
            out.append(c)
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                in_string = False
            i += 1
    return "".join(out)


def _extract_json_object(text: str) -> str:
    """
    Extract the most likely JSON object from a model response.
    Tolerates markdown fences, extra leading/trailing text, and mispaired ``}``
    inside strings vs. ``rfind("}")``.
    """
    if not text:
        raise ValueError("Empty model response text.")
    s = _strip_code_fence(text)
    try:
        return _extract_balanced_json_object(s)
    except ValueError:
        start = s.find("{")
        end = s.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("No JSON object found in response.") from None
        return s[start : end + 1]


def _loads_classifier_json(json_str: str) -> Dict[str, Any]:
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e_first:
        repaired = _strip_trailing_commas_json(json_str)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError as e_second:
            raise e_second from e_first


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


def _safe_int(x: Any, default: int = 0) -> int:
    try:
        if x is None:
            return default
        return int(x)
    except Exception:
        return default


def _gpt5_mini_cost_usd(
    uncached_input_tokens: int, cached_input_tokens: int, output_tokens: int
) -> float:
    """GPT-5-mini USD estimate; uncached_input_tokens is total input minus cached (OpenAI usage semantics)."""
    return (
        uncached_input_tokens / 1_000_000 * 0.25
        + cached_input_tokens / 1_000_000 * 0.025
        + output_tokens / 1_000_000 * 2.00
    )


def _usage_cached_input_tokens(usage: Any) -> int:
    if usage is None:
        return 0
    details = getattr(usage, "input_tokens_details", None) or getattr(
        usage, "prompt_tokens_details", None
    )
    if details is None:
        return 0
    if isinstance(details, dict):
        return _safe_int(details.get("cached_tokens"))
    return _safe_int(getattr(details, "cached_tokens", None))


def _usage_input_tokens_int(usage: Any) -> int:
    if usage is None:
        return 0
    v = getattr(usage, "input_tokens", None) or getattr(usage, "prompt_tokens", None)
    return _safe_int(v)


def _usage_output_tokens_int(usage: Any) -> int:
    if usage is None:
        return 0
    v = getattr(usage, "output_tokens", None) or getattr(
        usage, "completion_tokens", None
    )
    return _safe_int(v)


def _call_openai_classifier(
    *,
    prompt: str,
    model: str,
    max_output_tokens: int,
    client: Optional[OpenAI] = None,
    track_usage_cost: bool = False,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Returns (parsed_json, debug_info).

    If ``track_usage_cost`` is True, ``debug_info`` also contains ``cached_input_tokens``,
    ``uncached_input_tokens``, and ``gpt_5_mini_cost_usd``.
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
    try:
        data = _loads_classifier_json(json_str)
    except json.JSONDecodeError as e:
        head = json_str[:800] + ("…" if len(json_str) > 800 else "")
        raise ValueError(
            f"Classifier model returned invalid JSON ({e}). First 800 chars:\n{head}"
        ) from e

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
    if track_usage_cost:
        tin = _usage_input_tokens_int(usage)
        cached = _usage_cached_input_tokens(usage)
        uncached = max(0, tin - cached)
        tout = _usage_output_tokens_int(usage)
        debug["cached_input_tokens"] = cached
        debug["uncached_input_tokens"] = uncached
        debug["gpt_5_mini_cost_usd"] = _gpt5_mini_cost_usd(uncached, cached, tout)
    return data, debug


def classify_chunk(
    chunk_text: str,
    document_context: Optional[Dict[str, Any]] = None,
    *,
    client: Optional[OpenAI] = None,
    track_usage_cost: bool = False,
) -> Dict[str, Any]:
    """
    Classify a chunk under the CRI Regulatory Ontology.

    When ``track_usage_cost`` is True, ``_debug`` includes GPT-5-mini token breakdown
    and ``gpt_5_mini_cost_usd`` (uncached input uses total input minus cached).

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

    model = os.getenv("CRI_CLASSIFIER_MODEL", "gpt-5.4-nano")
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
        track_usage_cost=track_usage_cost,
    )

    return _normalize_classifier_output(data, debug)


def _normalize_classifier_output(data: Dict[str, Any], debug: Dict[str, Any]) -> Dict[str, Any]:
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


def classify_query(
    query: str,
    *,
    client: Optional[OpenAI] = None,
    track_usage_cost: bool = False,
) -> Dict[str, Any]:
    """
    Classify a user research question under the CRI Regulatory Ontology.

    Returns raw classifier fields plus ``normalized`` and ``validation_errors``
    from ``validate_classification``.
    """
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string.")

    try:
        from chat_agent.models import get_query_classifier_model

        model = get_query_classifier_model()
    except ImportError:
        model = (
            os.getenv("CRI_QUERY_CLASSIFIER_MODEL")
            or os.getenv("CHAT_NANO_MODEL")
            or os.getenv("CRI_CLASSIFIER_MODEL", "gpt-5.4-nano")
        )
    max_output_tokens = _get_env_int("CRI_CLASSIFIER_MAX_OUTPUT_TOKENS", 1200)

    prompt = build_query_classifier_prompt(query=query.strip())

    data, debug = _call_openai_classifier(
        prompt=prompt,
        model=model,
        max_output_tokens=max_output_tokens,
        client=client,
        track_usage_cost=track_usage_cost,
    )

    out = _normalize_classifier_output(data, debug)
    normalized, errors = validate_classification(out)
    out["normalized"] = normalized
    out["validation_errors"] = errors
    return out


if __name__ == "__main__":
    # Minimal local smoke test.
    #
    # Prereqs:
    # - OPENAI_API_KEY set in your environment
    # - (optional) CRI_CLASSIFIER_MODEL / CRI_CLASSIFIER_MAX_OUTPUT_TOKENS
    example_chunk = """Remarks at the 13th Annual Conference on Financial Market Regulation
        Commissioner Mark T. Uyeda Washington D.C. May 7, 2026 Thank you, Kathleen [Hanley], for that kind introduction. Good afternoon and welcome to the SEC’s Annual Conference on Financial Market Regulation. [1] Thank you to the staff of the Division of Economic and Risk Analysis, especially Vlad Ivanov, for your work in putting together this conference. Thank you to our partners at Lehigh University’s Center for Financial Services and the University of Virginia’s Darden School of Business for their assistance in hosting this conference. Introduction This is the 13 th annual edition organized by the SEC. I am pleased that it is still going strong, because I attended the very first edition of this conference back in May 2014. At the time, I served as counsel to then-Commissioner Michael S. Piwowar. As far as we know, Commissioner Piwowar is only the 2 nd Ph.D. economist to ever serve as an SEC commissioner. His perspectives, based on his academic and empirical research, served the Commission well during discussions about financial market policy – particularly when the voices of lawyers often dominate regulatory agencies. In his remarks at the inaugural conference in 2014, Commissioner Piwowar stated: Academic research is critically important to the SEC’s mission of protecting investors, maintaining fair, orderly, and efficient markets, and facilitating capital formation. Other financial regulators have long benefitted from holding academic research conferences on issues of importance to their agencies and it is high time for the Commission to do likewise. So it is quite exciting for me to be part of your activities today. [2] I could not agree more. Conferences like this one, where empirical analysis is applied to regulatory practice, are the type of forum that can help inform policy. Of course, that discussion cannot occur unless people are willing to submit papers and others are willing to analyze the papers and serve as discussants. To those individuals, thank you for your contributions. Over the next two days, a number of important topics over five tracks will be covered at the conference. For my remarks this afternoon, I would like to briefly touch upon two topics that caught my interest. Broken Windows and SEC Enforcement One panel during the enforcement track will discuss a paper on the application and effectiveness of the broken windows policy in the securities enforcement context. [3] The broken windows hypothesis, as described in a seminal article published in The Atlantic by James Q. Wilson and George Kelling, posits that visible signs of disorder, when left unaddressed, create an environment that encourages more serious crime. [4] The empirical literature on this theory remains contested, but its migration into securities is not merely academic. The paper focuses on a period in the past when the Commission explicitly implemented a broken windows policy, about which concerns have been expressed. [5] Whether the broken windows theory translates effectively in the securities enforcement context is an interesting question, particularly as this theory was implemented by prior Commission leadership. This particular paper asserts that it “provides the first empirical evidence consistent with a broken windows securities enforcement policy reducing the incidence of severe financial misconduct.” The paper does, however, recognize that such a policy may not be effective overall in a white-collar setting because enforcing minor violations could divert limited resources and attention away from pursuing the more serious violations. I appreciate the efforts to use various metrics in empirical studies in this field. My reactions to the paper are based on nearly twenty years of service at the SEC, half of which has been spent on the executive staff. During that period, I have reviewed thousands of recommendations from the Division of Enforcement. When it comes to “broken windows,” Wilson and Kelling identify two separate, but related, fears. The first is the fear of being a victim of crime, especially crime involving a sudden, violent attack by a stranger. The second is the fear of being bothered by disorderly people. As Wilson and Kelling describe this group, they are “not violent people, nor, necessarily, criminals, but disreputable or obstreperous or unpredictable people.” Wilson and Kelling further describe a neighborhood as being made up of “regulars” and “strangers.” Rules regulating order were defined and enforced in collaboration with the “regulars” on the street – and not necessarily by the rules established exclusively by law. In other words, to achieve order, there was a set of regularly expected behaviors among participants in a neighborhood. In a certain sense, that regular expectation of rules and norms exists in the securities markets as well. Leaking material non-public information to a golfing buddy with the expectation that your friend can trade profitably on such information – definitely prohibited behavior. But requiring monitoring and retention of all texts on personal mobile devices by persons working for broker-dealers and investment advisers? Is that a violation of the technical meaning of the laws and regulations? Perhaps. However, given the reaction to the SEC’s sweep effort on off-channel communications, communicating on personal devices was not the type of behavior that was viewed as unambiguously impermissible. When it comes to regulatory enforcement, one should also be considering the incentives and metrics designated by agency leadership for that program. If the metrics being stressed focus on the number of enforcement actions being brought and the amount of dollars collected in the form of disgorgement and civil penalties, then agency personnel will act in accordance with such instructions and incentives. The SEC’s rulebook has expanded dramatically in volume and complexity over the decades, which leaves significant ground for the Commission staff to exercise discretion in making and recommending enforcement decisions. Without limitations on the exercise of such discretion, there are many violations and novel legal interpretations that can be asserted as the basis for sanctions against virtually any asset class or market participant. However, random acts of regulatory enforcement dressed up as broken windows enforcement are unlikely to succeed at achieving behavioral conformity with widely-accepted norms intended to protect investors, maintain fair, orderly, and efficient markets, and facilitate capital formation. Abusing our discretionary authority undermines the regulatory predictability that efficient markets require or chills market activity that may be socially valuable. The author finds that sweep investigations opened during the broken windows era were 8-9% more likely to result in an enforcement action, which can be partially explained by strict liability violations that do not require proving negligence or scienter. [6] The author also divides SEC enforcement actions based on the tenure of various SEC chairman. However, the paper does not appear to make adjustments to reflect that SEC enforcement investigations, particularly for complex accounting cases, can take years between initiation and the bringing of any actual action. Thus, the enforcement actions taken during the early tenure of any chairman often reflects investigations initiated under the prior chairman – and enforcement initiatives undertaken by one chairman may only come to fruition, if at all, during the tenure of his or her successor. Nonetheless, I appreciate the efforts of researchers to study the actions of regulatory agencies. Their efforts play a role in holding the government accountable to the people. Active ETFs Another paper that caught my attention was regarding active exchange-traded funds (ETFs). [7] The first ETF launched in 1993, as a passive, index-tracking tool designed for low-cost, broad market exposure, combining mutual fund diversification with stock-like intraday trading. The ETF space has since experienced exponential growth. In 2005, the ICI Fact Book reported that mutual funds held nearly $8.9 trillion in assets as compared to a mere $296 billion for ETFs. [8] Thus, ETFs represented about 3.2% of assets in SEC-registered open-end fund assets. By 2025, mutual funds held $31.4 trillion in assets while ETFs had grown to $13.4 trillion – with ETFs now representing almost 30% of open-end fund assets. [9] Among other trends, there is an emerging market of active ETFs. The paper on active ETFs that will be presented tomorrow during the asset management track finds that the growth in the active ETF space is driven by a shift in investor base and expansion of the retail clientele. The authors conclude that active ETF managers benefit from chasing extreme performance, in either direction, which incentivizes asset managers to pursue high-volatility strategies. As we continue to see innovation and growth in the ETF space, ongoing empirical research such as this is essential for understanding market implications and informing sound policymaking. Conclusion I have mentioned only two examples from the array of thoughtful and relevant topics in the program. There are many other interesting topics, including with respect to crypto regulation, nocturnal trading of U.S.-listed equities, and corporate loan ratings. Thank you again to the economists for your work and your participation in this conference. Your work helps to understand the markets and ensure that economic analysis contributes to sound policy development. [1] My remarks reflect solely my individual views as a commissioner and do not necessarily reflect the views of the full U.S. Securities and Exchange Commission or my fellow Commissioners. [2] Commissioner Michael S. Piwowar, Remarks to the First Annual Conference on the Regulation of Financial Markets (May 16, 2014), available at https://www.sec.gov/newsroom/speeches-statements/2014-spch051614msp . [3] Nathan Herrmann, Broken Windows Securities Enforcement (Oct. 2025). [4] James Q. Wilson & George L. Kelling, Broken Windows , Atlantic Monthly (1982). [5] Michael S. Piwowar, Remarks to the Securities Enforcement Forum 2014 (Oct. 14, 2014), available at https://www.sec.gov/newsroom/speeches-statements/2014-spch101414msp . [6] Herrmann, supra note 3, at 29. [7] Da Huang, Vasudha Nair, Christopher Schwarz, Active ETFs as Attention Assets: Retail Trading Meets Managed Funds (Apr. 2026), available at https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5426275 . [8] Investment Company Institute, 2006 Investment Company Fact Book, at 7, available at https://www.ici.org/system/files/attachments/2006_factbook.pdf . [9] Investment Company Institute, 2026 Investment Company Fact Book, at 13, available at https://www.icifactbook.org/pdf/2026-factbook.pdf . Last Reviewed or Updated: May 7, 2026"""
    example_context = {
        "document_title": "Remarks at the 13th Annual Conference on Financial Market Regulation",
        "source_url": "https://www.sec.gov/",
        "publication_date": "2025-05-01",
        "source_type": "faq",
        "regulatory_body": ["SEC"],
    }

    raw = classify_chunk(
        example_chunk, example_context, track_usage_cost=True
    )
    normalized, errors = validate_classification(raw)

    dbg = raw.get("_debug") or {}
    print("\n=== Usage (gpt-5-mini estimate) ===")
    print(
        "input_total="
        f"{dbg.get('input_tokens')} uncached={dbg.get('uncached_input_tokens')} "
        f"cached={dbg.get('cached_input_tokens')} output={dbg.get('output_tokens')} "
        f"cost_usd={dbg.get('gpt_5_mini_cost_usd')}"
    )

    print("\n=== Raw classifier output ===")
    print(json.dumps(raw, ensure_ascii=False, indent=2))

    print("\n=== Validated / normalized ===")
    print(json.dumps(normalized, ensure_ascii=False, indent=2))

    if errors:
        print("\n=== Validation errors (pending_review) ===")
        for e in errors:
            print(f"- {e}")

