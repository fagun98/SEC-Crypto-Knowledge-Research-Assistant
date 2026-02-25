from typing import Dict, List, Tuple

from pathlib import Path

import streamlit as st
from chat_agent import answer_sec_query_v3_docs

def init_chat_state() -> None:
    """
    Ensure a single chat history list exists in session state.

    Each message is a dict with keys:
      - \"role\": \"user\" | \"assistant\"
      - \"content\": str
    """
    if "messages" not in st.session_state:
        st.session_state.messages: List[Dict[str, str]] = []


def layout_page() -> None:
    """Top-level layout and styling."""
    st.set_page_config(
        page_title="SEC Crypto Research Assistant (Beta)",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Global dark theme styling
    st.markdown(
        """
        <style>
        body {
            background-color: #000000;
        }
        .stApp {
            background: radial-gradient(circle at top left, #101010 0, #000000 45%, #050505 100%);
            color: #f5f5f5;
        }
        header[data-testid="stHeader"] {
            background: rgba(0, 0, 0, 0.4);
        }
        .session-pill {
            padding: 0.25rem 0.75rem;
            border-radius: 999px;
            border: 1px solid #333;
            background: linear-gradient(90deg, #111 0, #181818 50%, #111 100%);
            color: #f5f5f5;
            font-size: 0.8rem;
            cursor: pointer;
            margin-right: 0.35rem;
            white-space: nowrap;
        }
        .session-pill.active {
            border-color: #54a3ff;
            box-shadow: 0 0 0 1px rgba(84, 163, 255, 0.3);
            background: linear-gradient(90deg, #0f172a 0, #111827 50%, #020617 100%);
        }
        .session-bar {
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.25rem;
        }
        .glass-panel {
            background: rgba(15, 23, 42, 0.9);
            border-radius: 16px;
            border: 1px solid rgba(148, 163, 184, 0.35);
            box-shadow: 0 24px 80px rgba(15, 23, 42, 0.9);
            padding: 1.25rem 1.5rem;
        }
        .section-label {
            letter-spacing: 0.12em;
            text-transform: uppercase;
            font-size: 0.7rem;
            color: #9ca3af;
        }
        .top-title {
            font-size: 1.4rem;
            font-weight: 600;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _split_answer_and_sources(answer: str) -> Tuple[str, List[Dict[str, str]]]:
    """
    Split an assistant answer into main body and a structured sources list.

    The SEC chat agent returns Markdown with a trailing \"Sources\" section.
    We parse that section into a list of {\"description\", \"url\"} entries
    so it can be rendered in a structured way.
    """
    if not answer:
        return "", []

    lower = answer.lower()
    idx = lower.rfind("\nsources")
    if idx == -1:
        return answer.strip(), []

    body = answer[:idx].strip()
    sources_block = answer[idx:].splitlines()

    sources: List[Dict[str, str]] = []
    # Skip the first line (\"Sources\" / \"Sources:\")
    for line in sources_block[1:]:
        line = line.strip()
        if not line.startswith("-"):
            continue
        # Try to find a URL in the line.
        url_start = line.find("http")
        if url_start == -1:
            continue
        url = line[url_start:].strip(" .)")
        # Description is whatever precedes the URL after the bullet.
        desc = line[1:url_start].strip(" -—:\t")
        if not desc:
            desc = url
        sources.append({"description": desc, "url": url})

    return (body if body else answer.strip()), sources


def perform_chat(message: str, history: List[Dict[str, str]]) -> str:
    """
    Call the document-level SEC Q&A chat agent with the current query.

    The underlying pipeline is single-turn; chat history is maintained only
    in the Streamlit UI for conversational context.
    """
    try:
        return answer_sec_query_v3_docs(query=message)
    except Exception as e:
        return (
            "I encountered an error while processing your request: "
            f"{e}. Please try again or rephrase your question."
        )


def render_chat_ui() -> None:
    """Single chat interface for the SEC Q&A agent."""
    st.markdown(
        """
        <div class="top-title">SEC Crypto Chat Agent</div>
        <div style="color:#9ca3af; margin-top:0.15rem; font-size:0.86rem;">
            Ask questions about SEC crypto, custody, and enforcement.
            Answers are generated from current sec.gov material with clear sources.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # Optional controls row (clear chat)
    controls_col, _ = st.columns([1, 5])
    with controls_col:
        if st.button("Clear chat"):
            st.session_state.messages = []
            st.rerun()

    # Render existing chat history.
    for msg in st.session_state.messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if role == "assistant":
            body, sources = _split_answer_and_sources(content)
            with st.chat_message("assistant"):
                if body:
                    st.markdown(body)
                if sources:
                    st.markdown("**Sources**")
                    for src in sources:
                        desc = src.get("description", "")
                        url = src.get("url", "")
                        if url:
                            st.markdown(f"- {desc} — [{url}]({url})")
        else:
            with st.chat_message("user"):
                st.markdown(content)

    # Single chat input for the current turn.
    prompt = st.chat_input("Ask a question about SEC crypto, custody, or enforcement...")
    if prompt:
        prompt = prompt.strip()
        if not prompt:
            return

        # Capture history before this turn to send as `messages` (chat history).
        history_for_agent = list(st.session_state.messages)

        # Append the user message to the visible conversation.
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Loader animation while the agent is working.
        with st.spinner(
            "Running SEC document pipeline and generating an evidence-backed answer..."
        ):
            reply = perform_chat(prompt, history_for_agent)

        # Append assistant response.
        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.rerun()


def _render_report_section(title: str, relative_dir: str) -> None:
    base_dir = Path(__file__).resolve().parent
    section_dir = base_dir / relative_dir

    st.subheader(title)

    if not section_dir.exists() or not section_dir.is_dir():
        st.info("No reports are available in this section yet.")
        return

    files = sorted(
        p
        for p in section_dir.iterdir()
        if p.is_file() and p.suffix.lower() in {".md", ".txt"}
    )

    if not files:
        st.info("No reports are available in this section yet.")
        return

    for file_path in files:
        label = file_path.stem.replace("_", " ").replace("-", " ")
        pretty_label = label.strip() or file_path.name

        try:
            text = file_path.read_text(encoding="utf-8")
        except Exception:
            continue

        mime = "text/markdown" if file_path.suffix.lower() == ".md" else "text/plain"

        st.download_button(
            label=pretty_label,
            data=text,
            file_name=file_path.name,
            mime=mime,
            key=f"download-{file_path.relative_to(base_dir)}",
        )


def render_reports_tab() -> None:
    st.markdown(
        "Use the buttons below to download generated newsletters and round-table reports."
    )
    st.markdown("---")

    _render_report_section("Newsletters", "reports/newsletter")
    _render_report_section("Round-table reports", "reports/round_table")
    _render_report_section(
        "Cross-round-table / overall reports", "reports/overall_round_table"
    )


def main() -> None:
    layout_page()
    init_chat_state()
    chat_tab, reports_tab = st.tabs(["Chat", "Reports"])

    with chat_tab:
        render_chat_ui()

    with reports_tab:
        render_reports_tab()

    st.markdown("---")
    st.markdown(
        """
        <div style="text-align:center; color:#9ca3af; font-size:0.8rem; margin-top:0.75rem;">
            This interface is a beta prototype for SEC-related research and content exploration.
            A production-ready version with regular and weekly content updates and an expanded feature set is planned.
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()