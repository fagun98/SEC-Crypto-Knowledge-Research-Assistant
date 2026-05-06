#!/usr/bin/env python3
"""
Generate formal DOCX documentation for the SEC Crypto Application.
Run: python generate_application_documentation.py
Output: SEC_Application_Documentation.docx
"""

import json
from pathlib import Path

from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE


def load_qa_examples(max_examples: int = 4) -> list[tuple[str, str]]:
    """Load Q&A pairs from qa_cache.json. Returns list of (question, answer) tuples."""
    qa_path = Path(__file__).resolve().parent / "qa_cache.json"
    if not qa_path.exists():
        return []
    with open(qa_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return []
    items = list(data.items())
    # Select a diverse subset: first, one short Q; include Howey, newsletter-relevant, etc.
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


def add_heading(doc: Document, text: str, level: int = 1):
    p = doc.add_heading(text, level=level)
    for run in p.runs:
        run.font.size = Pt(14 if level == 1 else 12)
    return p


def add_para(doc: Document, text: str, bold: bool = False):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run(text)
    run.bold = bold
    run.font.size = Pt(11)
    run.font.name = "Calibri"
    return p


def add_flowchart_text(doc: Document, lines: list[str]):
    """Add a simple text-based flowchart (monospace-style block)."""
    for line in lines:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.5)
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run(line)
        run.font.size = Pt(10)
        run.font.name = "Consolas"
    return


def build_document() -> Document:
    doc = Document()
    # Title
    title = doc.add_heading("SEC Crypto Application — Formal Documentation", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph()

    # --- Introduction ---
    add_heading(doc, "1. Introduction", 1)
    add_para(
        doc,
        "This document provides a formal overview of the SEC Crypto Application. The application delivers "
        "structured access to U.S. Securities and Exchange Commission (SEC) materials and uses AI-powered agents "
        "to answer questions, produce weekly newsletters, and generate round table and overall regulatory intelligence "
        "reports—all grounded in credible SEC and related official sources."
    )
    add_para(
        doc,
        "All features rely on a structured SEC knowledge base and use only SEC-credible content where applicable, "
        "giving users confidence in the accuracy and traceability of the information."
    )
    doc.add_paragraph()

    # --- SEC AI Assistant ---
    add_heading(doc, "2. SEC AI Assistant", 1)
    add_heading(doc, "2.1 Overview", 2)
    add_para(
        doc,
        "The SEC AI Assistant is an intelligent question-answering feature that lets users ask questions in plain "
        "English about SEC regulations, guidance, enforcement, and crypto-related policy. Answers are generated "
        "using only content retrieved from the structured SEC knowledge base, so responses are grounded in official "
        "SEC materials and include source links for verification."
    )
    add_heading(doc, "2.2 How It Works (Simple Description)", 2)
    add_para(
        doc,
        "When you submit a question, the system first expands your question into several SEC-focused search topics. "
        "It then searches the SEC knowledge base (which contains indexed SEC.gov documents) for the most relevant "
        "passages. Those passages are scored for relevance to your question, and the most relevant ones are summarized "
        "in a question-focused way. A final answer is then written using only those summaries, with a clear separation "
        "between facts and analysis. Every answer ends with a “Sources” section listing the SEC.gov URLs used, so you "
        "can explore and verify the underlying documents."
    )
    add_heading(doc, "2.3 Process Flow", 2)
    add_para(doc, "The high-level flow of the SEC AI Assistant is as follows:")
    flowchart = [
        "┌─────────────────────────────────────────────────────────────────┐",
        "│  USER QUERY (e.g. “How does the SEC apply the Howey test to     │",
        "│  crypto tokens?”)                                               │",
        "└───────────────────────────────┬───────────────────────────────┘",
        "                                 ▼",
        "┌─────────────────────────────────────────────────────────────────┐",
        "│  STEP 1: Generate SEC-focused search topics from the query       │",
        "│  (e.g. Howey Test, crypto tokens, SEC guidance)                 │",
        "└───────────────────────────────┬───────────────────────────────┘",
        "                                 ▼",
        "┌─────────────────────────────────────────────────────────────────┐",
        "│  STEP 2: Search the SEC knowledge base (hybrid search) per topic  │",
        "│  → Retrieve top relevant document chunks with source URLs         │",
        "└───────────────────────────────┬───────────────────────────────┘",
        "                                 ▼",
        "┌─────────────────────────────────────────────────────────────────┐",
        "│  STEP 3: Rate each chunk for relevance to the question           │",
        "│  (high / medium / low) and keep the most promising chunks         │",
        "└───────────────────────────────┬───────────────────────────────┘",
        "                                 ▼",
        "┌─────────────────────────────────────────────────────────────────┐",
        "│  STEP 4: Summarise selected chunks in a question-focused way      │",
        "└───────────────────────────────┬───────────────────────────────┘",
        "                                 ▼",
        "┌─────────────────────────────────────────────────────────────────┐",
        "│  STEP 5: Generate final answer from summaries only               │",
        "│  → Markdown answer + “Sources” section with SEC.gov URLs         │",
        "└─────────────────────────────────────────────────────────────────┘",
    ]
    add_flowchart_text(doc, flowchart)
    add_para(
        doc,
        "This design keeps answers tied to the knowledge base and makes it easy to trace any claim back to an "
        "official SEC source."
    )
    add_heading(doc, "2.4 Benefits", 2)
    add_para(
        doc,
        "• Structured SEC knowledge base: All answers are derived from indexed SEC.gov content, not general web or "
        "unsourced material."
    )
    add_para(
        doc,
        "• Source transparency: Every response includes a Sources section with direct links to SEC.gov documents, "
        "supporting compliance and due diligence."
    )
    add_para(
        doc,
        "• SEC-only focus: The assistant is constrained to SEC regulations, guidance, enforcement, and policy, "
        "avoiding speculation from non-SEC sources."
    )
    add_heading(doc, "2.5 Sample Questions and Answers", 2)
    add_para(
        doc,
        "The following are sample questions and answers produced by the SEC AI Assistant from the knowledge base. "
        "They illustrate the kind of factual, sourced responses users can expect."
    )
    qa_examples = load_qa_examples(4)
    for i, (question, answer) in enumerate(qa_examples, 1):
        add_para(doc, f"Question {i}:", bold=True)
        add_para(doc, question)
        add_para(doc, "Answer:", bold=True)
        # Truncate very long answers for readability in the doc; keep first ~1200 chars + "... [truncated]"
        display_answer = answer if len(answer) <= 1400 else answer[:1400].rsplit(" ", 1)[0] + "… [Answer truncated for documentation.]"
        add_para(doc, display_answer)
        doc.add_paragraph()
    doc.add_paragraph()

    # --- Newsletter Agent ---
    add_heading(doc, "3. Custody Newsletter Agent", 1)
    add_heading(doc, "3.1 Overview", 2)
    add_para(
        doc,
        "The Custody Newsletter Agent produces a weekly Crypto Custody Intelligence newsletter. It is designed to "
        "run on a schedule (e.g. weekly) and to generate a fresh report every Monday for the preceding week, "
        "so that users receive a consistent, up-to-date digest of SEC developments relevant to crypto custody and "
        "related regulation."
    )
    add_heading(doc, "3.2 How It Works", 2)
    add_para(
        doc,
        "The agent discovers relevant SEC content for a given date range by visiting configured SEC.gov pages "
        "(e.g. speeches, task force, enforcement, rulemaking). It extracts links to articles, speeches, and releases "
        "published within that range, fetches each document, and uses an AI agent to extract structured information "
        "—facts, quotes, decisions, and implications for broker-dealers, RIAs, banks, and custodians. Optionally, "
        "it can also pull in additional context from the SEC knowledge base (RAG) for a custody-angle summary. "
        "Finally, it synthesizes all of this into a single newsletter in a fixed structure: This Week at a Glance, "
        "Top Stories with implications by entity type, Regulatory Tracker, Enforcement Watch, Banking Regulator "
        "Corner, What’s Coming, Compliance Action Items, and a Resource Library."
    )
    add_heading(doc, "3.3 Sources and Direct Links", 2)
    add_para(
        doc,
        "Each newsletter section cites sources that help users explore and dive deep into the story. Every fact or "
        "claim that comes from an SEC document is tied to a source URL. The newsletter includes a Resource Library "
        "section presented as a table of links, and inline citations use the format “(Source: https://www.sec.gov/...)”. "
        "Users can click these direct links to open the original SEC.gov page and verify or read the full context."
    )
    add_heading(doc, "3.4 Beta Version and Future Enhancements", 2)
    add_para(
        doc,
        "In the current beta version, the newsletter agent is configured to use SEC-base sources only (e.g. "
        "sec.gov featured topics, divisions, newsroom, enforcement, rulemaking). This ensures that the newsletter "
        "is grounded in official SEC material. For production, the set of sources can be expanded to cover other "
        "credible regulators or policy sources if requested. The newsletter format (sections, length, tone) can also "
        "be tweaked on request. Additional features and sections can be added upon request for production use."
    )
    add_heading(doc, "3.5 Benefits", 2)
    add_para(
        doc,
        "• Weekly, consistent delivery of a custody-focused digest without manual curation.\n"
        "• Every story and fact is traceable to SEC (or configured) sources via direct links.\n"
        "• Structured layout (tables, implications by entity type) supports quick scanning and compliance review."
    )
    doc.add_paragraph()

    # --- Round Table Agent ---
    add_heading(doc, "4. Round Table Meeting Agent", 1)
    add_heading(doc, "4.1 Overview", 2)
    add_para(
        doc,
        "The Round Table Meeting Agent generates detailed reports for SEC round table meetings. Given a meeting URL "
        "and a transcript file, it analyzes the transcript and any parsed meeting-page content to produce a structured "
        "report suitable for internal briefing and compliance use."
    )
    add_heading(doc, "4.2 How It Works", 2)
    add_para(
        doc,
        "The agent loads the meeting transcript and the meeting URL. It may parse the SEC meeting page to capture "
        "title, description, and participants. It can use the SEC knowledge base (RAG search) to pull in relevant "
        "regulations or guidance, and optional web search for speaker or context. It then produces a report that "
        "includes: key speakers with influence and activity ratings, views on topics discussed, meeting conclusions, "
        "and key points and main arguments. The report is saved in the chosen format (e.g. TXT, DOCX) and includes a "
        "Sources section."
    )
    add_heading(doc, "4.3 Benefits", 2)
    add_para(
        doc,
        "• Consistent structure across round table reports (speakers, topics, conclusions, sources).\n"
        "• Evidence-based speaker and topic analysis, with optional grounding in the SEC knowledge base.\n"
        "• Ready for internal distribution or further summarization in broader intelligence products."
    )
    doc.add_paragraph()

    # --- Overall Report Agent ---
    add_heading(doc, "5. Overall Report Agent", 1)
    add_heading(doc, "5.1 Overview", 2)
    add_para(
        doc,
        "The Overall Report Agent combines insights from all available SEC Round Table Meeting reports into a single "
        "regulatory intelligence report. It is intended for leadership and compliance teams who need a cross-meeting "
        "view of themes, speakers, and regulatory direction."
    )
    add_heading(doc, "5.2 How It Works", 2)
    add_para(
        doc,
        "The agent discovers all meeting report files (e.g. SEC_Meeting_Report_*.txt) in a given directory, reads "
        "their contents, and optionally uses the SEC knowledge base and web search for additional context. It then "
        "produces a comprehensive report that: combines views of the same speaker across meetings; tags speakers "
        "with topics they engaged with; identifies the most influential stakeholder across meetings; and outlines "
        "future predictions and implications for issuers, DeFi protocols, exchanges, and custodians. The report "
        "follows a fixed structure (Executive Intelligence Brief, Methodology, Cross-Meeting Evidence, Speaker "
        "Analysis, Topic Tagging, Most Influential Stakeholder, What This Means For…, Unresolved Questions & "
        "Regulatory Gaps, Future Predictions, Sources) and is output in Markdown or DOCX."
    )
    add_heading(doc, "5.3 Benefits", 2)
    add_para(
        doc,
        "• Single, consolidated view of multiple round tables for executives and compliance.\n"
        "• Evidence-based identification of influential stakeholders and recurring themes.\n"
        "• Clear labeling of predictions (explicitly stated vs. inferred vs. speculative) and a dedicated section "
        "on unresolved regulatory gaps."
    )
    doc.add_paragraph()

    # --- Benefits Summary ---
    add_heading(doc, "6. Benefits of Using the Application", 1)
    add_para(
        doc,
        "• Structured SEC knowledge base: All core features (AI Assistant, Newsletter, Round Table and Overall "
        "reports) draw on a centralized, indexed body of SEC and related credible material, ensuring consistency and "
        "traceability."
    )
    add_para(
        doc,
        "• SEC-credible reporting: The AI Assistant and report agents are designed to use only SEC-credible sources "
        "where applicable, reducing reliance on unsourced or third-party interpretation for critical compliance and "
        "policy questions."
    )
    add_para(
        doc,
        "• Time savings: Weekly newsletters and one-click round table and overall reports reduce manual collection "
        "and summarization of SEC developments."
    )
    add_para(
        doc,
        "• Transparency: Direct source links in answers and newsletters allow users to explore and verify every claim "
        "against the original SEC document."
    )
    doc.add_paragraph()

    # --- Additional Features ---
    add_heading(doc, "7. Additional Features and Customization", 1)
    add_para(
        doc,
        "Additional features and sections can be added upon request for production. Examples include: expanding "
        "newsletter sources beyond SEC-base sources, customizing newsletter format and sections, adding new report "
        "templates or output formats, and integrating with internal workflows or distribution channels. The "
        "documentation and behaviour of each agent can be extended to reflect such customizations."
    )
    doc.add_paragraph()

    # --- Conclusion ---
    add_heading(doc, "8. Conclusion", 1)
    add_para(
        doc,
        "The SEC Crypto Application provides a unified platform for SEC-focused research, weekly custody intelligence, "
        "and round table and overall regulatory reporting. By combining a structured SEC knowledge base with "
        "AI-powered assistants and report agents that use only SEC-credible sources, the application helps users "
        "stay informed, verify information quickly, and make better-informed compliance and policy decisions."
    )

    return doc


def main():
    out_path = Path(__file__).resolve().parent / "SEC_Application_Documentation.docx"
    doc = build_document()
    doc.save(out_path)
    print(f"Documentation written to: {out_path}")


if __name__ == "__main__":
    main()
