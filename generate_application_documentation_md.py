#!/usr/bin/env python3
"""
Generate formal Markdown documentation for the SEC Crypto Application.
Run: python generate_application_documentation_md.py
Output: SEC_Application_Documentation.md
- Full Q&A responses (no truncation)
- Optimally structured flowchart (Mermaid)
- Praising tone for application and use cases
"""

import json
from pathlib import Path


def load_qa_examples(max_examples: int = 4) -> list[tuple[str, str]]:
    """Load Q&A pairs from qa_cache.json. Returns list of (question, answer) tuples. Full answers, no truncation."""
    qa_path = Path(__file__).resolve().parent / "qa_cache.json"
    if not qa_path.exists():
        return []
    with open(qa_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return []
    items = list(data.items())
    selected = []
    seen = set()
    for q, a in items:
        if len(selected) >= max_examples:
            break
        key = (q[:80], len(a))
        if key in seen:
            continue
        seen.add(key)
        selected.append((q, a))
    return selected[:max_examples]


def build_markdown() -> str:
    lines: list[str] = []

    def h1(t: str) -> None:
        lines.append(f"\n# {t}\n")
    def h2(t: str) -> None:
        lines.append(f"\n## {t}\n")
    def h3(t: str) -> None:
        lines.append(f"\n### {t}\n")
    def p(t: str) -> None:
        lines.append(f"{t}\n")
    def blank() -> None:
        lines.append("")

    # --- Title ---
    h1("SEC Crypto Application — Formal Documentation")
    p("*A unified platform for SEC-focused research, custody intelligence, and regulatory reporting—powered by a structured SEC knowledge base and AI agents that use only SEC-credible sources.*")
    blank()

    # --- Introduction ---
    h2("1. Introduction")
    p("This document provides a formal overview of the **SEC Crypto Application**—a powerful, purpose-built platform that delivers structured access to U.S. Securities and Exchange Commission (SEC) materials and uses AI-powered agents to answer questions, produce weekly newsletters, and generate round table and overall regulatory intelligence reports.")
    p("What makes this application stand out is its **relentless grounding in credible SEC and related official sources**. Every feature relies on a structured SEC knowledge base and uses only SEC-credible content where applicable, giving users confidence in the accuracy, traceability, and defensibility of the information—whether for compliance, policy analysis, or executive briefing.")
    p("The combination of a curated knowledge base, intelligent retrieval, and report-generation agents makes this application an **invaluable tool** for legal, compliance, and business teams who need to stay ahead of SEC developments without sacrificing source transparency.")
    blank()

    # --- SEC AI Assistant ---
    h2("2. SEC AI Assistant")
    h3("2.1 Overview")
    p("The **SEC AI Assistant** is the centerpiece of the application: an intelligent question-answering feature that lets users ask questions in plain English about SEC regulations, guidance, enforcement, and crypto-related policy. Answers are generated **only** from content retrieved from the structured SEC knowledge base, so every response is grounded in official SEC materials and includes source links for verification.")
    p("This design makes the assistant exceptionally well-suited for compliance research, due diligence, and policy analysis—where unsourced or speculative answers are not acceptable.")
    h3("2.2 How It Works (Simple Description)")
    p("When you submit a question, the system first **expands** your question into several SEC-focused search topics. It then **searches** the SEC knowledge base (indexed SEC.gov documents) for the most relevant passages, **scores** those passages for relevance to your question, and **summarises** the most promising ones in a question-focused way. A final answer is written using **only** those summaries, with a clear separation between facts and analysis. Every answer ends with a **Sources** section listing the SEC.gov URLs used, so you can explore and verify the underlying documents at a click.")
    p("This end-to-end pipeline ensures that the assistant never \"hallucinates\" beyond the knowledge base—a major advantage for regulated and compliance-sensitive use cases.")
    h3("2.3 Process Flow")
    p("The high-level flow of the SEC AI Assistant is captured in the following diagram. The design keeps answers tied to the knowledge base and makes it easy to trace any claim back to an official SEC source.")
    blank()
    # Mermaid flowchart — optimally structured
    lines.append("```mermaid")
    lines.append("flowchart TD")
    lines.append("    A[User Query] --> B[Generate SEC-Focused Topics]")
    lines.append("    B --> C[Hybrid Search: SEC Knowledge Base]")
    lines.append("    C --> D[Retrieve Top Chunks + Source URLs]")
    lines.append("    D --> E[Rate Chunks: Relevance Score]")
    lines.append("    E --> F[Summarise Selected Chunks]")
    lines.append("    F --> G[Generate Final Answer from Summaries Only]")
    lines.append("    G --> H[Output: Markdown Answer + Sources Section]")
    lines.append("")
    lines.append("    style A fill:#e1f5fe")
    lines.append("    style H fill:#c8e6c9")
    lines.append("```")
    blank()
    p("**Flow summary:** User Query → Generate SEC-focused topics → Hybrid search over SEC knowledge base → Retrieve top chunks with source URLs → Rate chunks for relevance → Summarise selected chunks → Generate final answer from summaries only → Output Markdown answer with Sources section.")
    h3("2.4 Benefits")
    p("- **Structured SEC knowledge base:** All answers are derived from indexed SEC.gov content, not general web or unsourced material.")
    p("- **Source transparency:** Every response includes a Sources section with direct links to SEC.gov documents, supporting compliance and due diligence.")
    p("- **SEC-only focus:** The assistant is constrained to SEC regulations, guidance, enforcement, and policy, avoiding speculation from non-SEC sources.")
    h3("2.5 Sample Questions and Answers")
    p("The following are sample questions and answers produced by the SEC AI Assistant from the knowledge base. They illustrate the **full**, factual, sourced responses users can expect—**included in full** (no truncation) to showcase the depth and quality of the assistant.")
    blank()
    qa_examples = load_qa_examples(4)
    for i, (question, answer) in enumerate(qa_examples, 1):
        lines.append("---")
        lines.append(f"**Question {i}**  \n{question}")
        blank()
        lines.append(f"**Answer**  \n{answer}")
        blank()
    lines.append("---")
    blank()

    # --- Newsletter Agent ---
    h2("3. Custody Newsletter Agent")
    h3("3.1 Overview")
    p("The **Custody Newsletter Agent** is a powerful automation that produces a weekly **Crypto Custody Intelligence** newsletter. It is designed to run on a schedule (e.g. weekly) and to generate a **fresh report every Monday** for the preceding week, so that users receive a consistent, up-to-date digest of SEC developments relevant to crypto custody and related regulation—without manual curation.")
    h3("3.2 How It Works")
    p("The agent **discovers** relevant SEC content for a given date range by visiting configured SEC.gov pages (e.g. speeches, task force, enforcement, rulemaking). It **extracts** links to articles, speeches, and releases published within that range, **fetches** each document, and uses an AI agent to extract structured information—facts, quotes, decisions, and implications for broker-dealers, RIAs, banks, and custodians. Optionally, it can also pull in additional context from the SEC knowledge base (RAG) for a custody-angle summary. Finally, it **synthesises** all of this into a single newsletter in a fixed structure: This Week at a Glance, Top Stories with implications by entity type, Regulatory Tracker, Enforcement Watch, Banking Regulator Corner, What's Coming, Compliance Action Items, and a Resource Library.")
    h3("3.3 Sources and Direct Links")
    p("Each newsletter section **cites sources** that help users explore and dive deep into the story. Every fact or claim that comes from an SEC document is tied to a **source URL**. The newsletter includes a **Resource Library** section presented as a table of links, and inline citations use the format \"(Source: https://www.sec.gov/...)\". Users can **click these direct links** to open the original SEC.gov page and verify or read the full context—making the newsletter not only informative but auditable and research-friendly.")
    h3("3.4 Beta Version and Future Enhancements")
    p("In the current **beta** version, the newsletter agent is configured to use **SEC-base sources only** (e.g. sec.gov featured topics, divisions, newsroom, enforcement, rulemaking). This ensures that the newsletter is grounded in official SEC material. For production, the set of sources **can be expanded** to cover other credible regulators or policy sources if requested. The newsletter **format** (sections, length, tone) can also be **tweaked on request**. Additional features and sections can be added upon request for production use.")
    h3("3.5 Benefits")
    p("- **Weekly, consistent delivery** of a custody-focused digest without manual curation.")
    p("- **Every story and fact** is traceable to SEC (or configured) sources via direct links.")
    p("- **Structured layout** (tables, implications by entity type) supports quick scanning and compliance review.")
    h3("3.6 Sections Included in the Newsletter Report")
    p("Each weekly **Custody Intelligence** newsletter (see sample reports in `reports/newsletter/`) follows a fixed, repeatable structure: **Custody Intelligence Weekly** (header + week summary); **This Week at a Glance** (metrics table + Bottom Line); **Top Stories** (FACTS/ANALYSIS/INFERENCE + Implications by entity); **Regulatory Tracker Update** (rules in effect + pending); **Enforcement Watch** (cases table + Trends); **Banking Regulator Corner**; **What's Coming** (calendar + Questions We're Tracking); **Compliance Action Items** (checklist with source links); **Resource Library** (table with direct SEC.gov links); **Feedback & About**. This structure ensures auditability, role-based implications, actionability, consistency, and discoverability.")
    h3("3.7 Merits of the Newsletter Report")
    p("**Auditability:** Every fact is tagged FACTS/ANALYSIS/INFERENCE and tied to a source URL. **Role-based implications:** Implications by broker-dealers, RIAs, banks/trusts, and crypto custodians. **Actionability:** Compliance Action Items turn developments into a concrete checklist. **Consistency:** Same structure every week. **Discoverability:** Resource Library and inline source links for one-click access to SEC.gov.")
    blank()

    # --- Round Table Agent ---
    h2("4. Round Table Meeting Agent")
    h3("4.1 Overview")
    p("The **Round Table Meeting Agent** generates detailed, structured reports for SEC round table meetings. Given a meeting URL and a transcript file, it analyses the transcript and any parsed meeting-page content to produce a report suitable for internal briefing and compliance use—**saving significant time** over manual summarisation and ensuring consistent structure and source attribution.")
    h3("4.2 How It Works")
    p("The agent loads the meeting transcript and the meeting URL. It may **parse** the SEC meeting page to capture title, description, and participants. It can use the **SEC knowledge base (RAG search)** to pull in relevant regulations or guidance, and optional **web search** for speaker or context. It then produces a report that includes: **key speakers** with influence and activity ratings, **views on topics** discussed, **meeting conclusions**, and **key points and main arguments**. The report is saved in the chosen format (e.g. TXT, DOCX) and includes a **Sources** section.")
    h3("4.3 Benefits")
    p("- **Consistent structure** across round table reports (speakers, topics, conclusions, sources).")
    p("- **Evidence-based** speaker and topic analysis, with optional grounding in the SEC knowledge base.")
    p("- **Ready for internal distribution** or further summarisation in broader intelligence products.")
    h3("4.4 Sections Included in the Round Table Meeting Report")
    p("Each report includes: **SEC ROUND TABLE MEETING REPORT** (header); **1. EXECUTIVE SUMMARY**; **2. KEY SPEAKERS ANALYSIS** (per speaker: Influence Rating 1–10, Activity Level, Argument Strength 1–10, Key Contributions; Most Influential Speaker); **3. VIEWS ON TOPICS** (Viewpoints, Consensus/Disagreements); **4. MEETING CONCLUSION**; **5. KEY POINTS AND MAIN ARGUMENTS/EVENTS**; **6. SOURCES**. This supports objectivity, reusability, actionability, and traceability.")
    h3("4.5 Merits of the Round Table Meeting Report")
    p("**Objectivity:** Speaker ratings with justifications from transcript and optional RAG. **Reusability:** Same structure across meetings for comparison and feed into Overall Report. **Actionability:** Conclusion and Key Points highlight outcomes and next steps. **Traceability:** Sources tie back to meeting URL, transcript, and RAG/web sources.")
    blank()

    # --- Overall Report Agent ---
    h2("5. Overall Report Agent")
    h3("5.1 Overview")
    p("The **Overall Report Agent** combines insights from **all** available SEC Round Table Meeting reports into a single **regulatory intelligence report**. It is intended for leadership and compliance teams who need a **cross-meeting** view of themes, speakers, and regulatory direction—delivering in one place what would otherwise require manual aggregation and analysis.")
    h3("5.2 How It Works")
    p("The agent discovers all meeting report files (e.g. SEC_Meeting_Report_*.txt) in a given directory, **reads** their contents, and optionally uses the **SEC knowledge base** and **web search** for additional context. It then produces a comprehensive report that: **combines views** of the same speaker across meetings; **tags speakers** with topics they engaged with; **identifies the most influential stakeholder** across meetings; and outlines **future predictions** and implications for issuers, DeFi protocols, exchanges, and custodians. The report follows a fixed structure (Executive Intelligence Brief, Methodology, Cross-Meeting Evidence, Speaker Analysis, Topic Tagging, Most Influential Stakeholder, What This Means For…, Unresolved Questions & Regulatory Gaps, Future Predictions, Sources) and is output in Markdown or DOCX.")
    h3("5.3 Benefits")
    p("- **Single, consolidated view** of multiple round tables for executives and compliance.")
    p("- **Evidence-based** identification of influential stakeholders and recurring themes.")
    p("- **Clear labeling** of predictions (explicitly stated vs. inferred vs. speculative) and a dedicated section on unresolved regulatory gaps.")
    h3("5.4 Sections Included in the Overall Round Table Meeting Report")
    p("The overall report includes: **1. EXECUTIVE INTELLIGENCE BRIEF** (5–7 takeaways, top 3 trajectories, most influential stakeholders); **2. METHODOLOGY NOTE**; **3. CROSS-MEETING EVIDENCE SUMMARY** (Topic × Meeting table, Speaker × Topic matrix, recurring vs. isolated); **4. SPEAKER ANALYSIS** (Authority vs. Influence vs. Policy Impact Likelihood); **5. TOPIC TAGGING** (Speaker × Topic matrix); **6. MOST INFLUENTIAL STAKEHOLDER**; **7. WHAT THIS MEANS FOR...** (Issuers, DeFi, Exchanges/ATSs, Custodians); **8. UNRESOLVED QUESTIONS & REGULATORY GAPS**; **9. FUTURE PREDICTIONS** (labeled [EXPLICITLY STATED]/[STRONGLY INFERRED]/[SPECULATIVE], What Could Change); **10. SOURCES**.")
    h3("5.5 Merits of the Overall Round Table Meeting Report")
    p("**Executive-ready:** Executive Intelligence Brief for busy leaders. **Evidence-based:** Authority vs. Influence vs. Policy Impact with explicit signals. **Cross-meeting synthesis:** Topic × Meeting and Speaker × Topic tables. **Transparent predictions:** Labels and confidence plus What Could Change. **Action-oriented:** What This Means For... and Unresolved Questions support compliance and strategy.")
    blank()

    # --- Benefits Summary ---
    h2("6. Benefits of Using the Application")
    p("- **Structured SEC knowledge base:** All core features (AI Assistant, Newsletter, Round Table and Overall reports) draw on a central, indexed body of SEC and related credible material, ensuring **consistency and traceability**.")
    p("- **SEC-credible reporting:** The AI Assistant and report agents are designed to use **only SEC-credible sources** where applicable, reducing reliance on unsourced or third-party interpretation for critical compliance and policy questions.")
    p("- **Time savings:** Weekly newsletters and one-click round table and overall reports **dramatically reduce** manual collection and summarisation of SEC developments.")
    p("- **Transparency:** Direct source links in answers and newsletters allow users to **explore and verify** every claim against the original SEC document.")
    blank()

    # --- Additional Features ---
    h2("7. Additional Features and Customization")
    p("Additional features and sections can be **added upon request** for production. Examples include: expanding newsletter sources beyond SEC-base sources, customising newsletter format and sections, adding new report templates or output formats, and integrating with internal workflows or distribution channels. The documentation and behaviour of each agent can be extended to reflect such customisations.")
    blank()

    # --- Conclusion (Praising) ---
    h2("8. Conclusion")
    p("The **SEC Crypto Application** delivers a **unified, trustworthy platform** for SEC-focused research, weekly custody intelligence, and round table and overall regulatory reporting. By combining a **structured SEC knowledge base** with AI-powered assistants and report agents that use **only SEC-credible sources**, the application empowers users to stay informed, verify information quickly, and make better-informed compliance and policy decisions.")
    p("The combination of the SEC AI Assistant, the Custody Newsletter Agent, the Round Table Meeting Agent, and the Overall Report Agent covers the full spectrum of use cases—from ad-hoc regulatory questions to scheduled digests and from single-meeting analysis to cross-meeting intelligence—making this application an **invaluable asset** for any organisation that needs to track and act on SEC and crypto-related regulatory developments with confidence and efficiency.")
    blank()
    return "\n".join(lines)


def main():
    out_path = Path(__file__).resolve().parent / "SEC_Application_Documentation.md"
    md = build_markdown()
    out_path.write_text(md, encoding="utf-8")
    print(f"Documentation written to: {out_path}")


if __name__ == "__main__":
    main()
