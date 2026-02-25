from typing import Any, Dict, List, Tuple

from pathlib import Path

import json
import streamlit as st
from chat_agent import answer_sec_query_v3_docs, answer_sec_query_v3_docs_with_progress


CACHE_PATH = Path(__file__).resolve().parent / "qa_cache.json"
SAMPLE_QUESTIONS_PATH = Path(__file__).resolve().parent / "sample_questions.txt"


def _normalise_query(query: str) -> str:
    return " ".join((query or "").strip().lower().split())


def _load_cache() -> Dict[str, str]:
    try:
        if not CACHE_PATH.exists():
            return {}
        raw = CACHE_PATH.read_text(encoding="utf-8")
        data = json.loads(raw) if raw.strip() else {}
        if isinstance(data, dict):
            out: Dict[str, str] = {}
            for k, v in data.items():
                if isinstance(k, str) and isinstance(v, str):
                    out[k] = v
            return out
    except Exception:
        return {}
    return {}


def _save_cache(cache: Dict[str, str]) -> None:
    try:
        tmp_path = CACHE_PATH.with_suffix(".json.tmp")
        tmp_path.write_text(
            json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        tmp_path.replace(CACHE_PATH)
    except Exception:
        # Cache is best-effort; never block answering on write failures.
        return


def get_cached_answer(query: str) -> str | None:
    key = _normalise_query(query)
    if not key:
        return None
    cache = _load_cache()
    ans = cache.get(key)
    return ans if isinstance(ans, str) and ans.strip() else None


def set_cached_answer(query: str, answer: str) -> None:
    key = _normalise_query(query)
    if not key:
        return
    cache = _load_cache()
    cache[key] = answer
    _save_cache(cache)


def _load_sample_questions(max_items: int = 10) -> List[str]:
    questions: List[str] = []
    try:
        if not SAMPLE_QUESTIONS_PATH.exists():
            return questions
        for line in SAMPLE_QUESTIONS_PATH.read_text(encoding="utf-8").splitlines():
            q = line.strip()
            if q:
                questions.append(q)
            if len(questions) >= max_items:
                break
    except Exception:
        return []
    return questions

def init_chat_state() -> None:
    """
    Ensure a single chat history list exists in session state.

    Each message is a dict with keys:
      - \"role\": \"user\" | \"assistant\"
      - \"content\": str
    """
    if "messages" not in st.session_state:
        st.session_state.messages: List[Dict[str, str]] = []
    if "queued_prompt" not in st.session_state:
        st.session_state.queued_prompt = None
    if "is_generating" not in st.session_state:
        st.session_state.is_generating = False


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


def perform_chat(
    message: str,
    history: List[Dict[str, str]],
    *,
    progress_cb: Any | None = None,
) -> str:
    """
    Call the document-level SEC Q&A chat agent with the current query.

    The underlying pipeline is single-turn; chat history is maintained only
    in the Streamlit UI for conversational context.
    """
    try:
        if progress_cb is not None:
            return answer_sec_query_v3_docs_with_progress(
                query=message, progress_cb=progress_cb
            )
        # Non-progress fast path, still using the same doc pipeline.
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

    is_generating = bool(st.session_state.get("is_generating", False))

    # Sample questions expander
    sample_questions = _load_sample_questions(max_items=12)
    if sample_questions:
        with st.expander("Sample questions to try"):
            for idx, q in enumerate(sample_questions):
                if st.button(q, key=f"sample-q-{idx}", disabled=is_generating):
                    st.session_state["queued_prompt"] = q
                    st.rerun()

    # Optional controls row (clear chat)
    controls_col, _ = st.columns([1, 5])
    with controls_col:
        if st.button("Clear chat", disabled=is_generating):
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

    # Single chat input for the current turn (or queued sample question).
    queued = st.session_state.pop("queued_prompt", None)
    if queued is not None:
        prompt = queued
        _ = st.chat_input("Ask a question about SEC crypto, custody, or enforcement...")
    else:
        prompt = st.chat_input(
            "Ask a question about SEC crypto, custody, or enforcement...",
            disabled=is_generating,
        )
    if prompt:
        prompt = prompt.strip()
        if not prompt:
            return

        if is_generating:
            st.info("An answer is already being generated. Please wait for it to complete.")
            return

        cached = get_cached_answer(prompt)
        if cached is not None:
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.session_state.messages.append({"role": "assistant", "content": cached})
            st.rerun()

        # Capture history before this turn (UI only).
        history_for_agent = list(st.session_state.messages)

        # Append the user message to the visible conversation.
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.is_generating = True

        try:
            with st.chat_message("assistant"):
                status_placeholder = st.empty()
                progress_bar = st.progress(0)
                details_placeholder = st.empty()

                stage_percent = {
                    "topics": 15,
                    "retrieval_queries": 25,
                    "retrieval_done": 40,
                    "candidates": 55,
                    "reranked": 65,
                    "fetch_doc": 75,
                    "doc_summarized": 85,
                }

                def _progress_cb(update: Dict[str, Any]) -> None:
                    stage = str(update.get("stage") or "").strip()
                    percent = stage_percent.get(stage, 10)

                    title = "Working…"
                    if stage == "topics":
                        title = "Generating topics"
                    elif stage == "retrieval_queries":
                        title = "Building retrieval queries"
                    elif stage == "retrieval_done":
                        title = "Retrieving SEC index matches"
                    elif stage == "candidates":
                        title = "Preparing candidate SEC URLs"
                    elif stage == "reranked":
                        title = "Selecting top SEC documents"
                    elif stage == "fetch_doc":
                        title = "Fetching and reading SEC documents"
                    elif stage == "doc_summarized":
                        title = "Summarising documents"

                    progress_bar.progress(min(max(int(percent), 0), 100))
                    status_placeholder.markdown(f"**{title}**")

                    topics = update.get("topics")
                    if isinstance(topics, list) and topics:
                        bullets = "\n".join(
                            f"- {t}" for t in topics[:10] if isinstance(t, str)
                        )
                        details_placeholder.markdown(f"**Topics**\n{bullets}")
                        return

                    selected_urls = update.get("selected_urls")
                    if isinstance(selected_urls, list) and selected_urls:
                        bullets = "\n".join(
                            f"- {u}" for u in selected_urls[:10] if isinstance(u, str)
                        )
                        details_placeholder.markdown(f"**Selected SEC URLs**\n{bullets}")
                        return

                    candidate_urls = update.get("candidate_urls")
                    if isinstance(candidate_urls, list) and candidate_urls:
                        bullets = "\n".join(
                            f"- {u}" for u in candidate_urls[:10] if isinstance(u, str)
                        )
                        details_placeholder.markdown(f"**Candidate SEC URLs**\n{bullets}")
                        return

                    url = update.get("url")
                    if isinstance(url, str) and url.strip():
                        cur = update.get("current")
                        total = update.get("total")
                        suffix = ""
                        if isinstance(cur, int) and isinstance(total, int) and total > 0:
                            suffix = f" ({cur}/{total})"
                        details_placeholder.markdown(f"**Current URL**{suffix}\n- {url}")

                reply = perform_chat(prompt, history_for_agent, progress_cb=_progress_cb)

                progress_bar.progress(100)
                status_placeholder.empty()
                details_placeholder.empty()
                st.markdown(reply)
        finally:
            st.session_state.is_generating = False

        st.session_state.messages.append({"role": "assistant", "content": reply})
        set_cached_answer(prompt, reply)
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