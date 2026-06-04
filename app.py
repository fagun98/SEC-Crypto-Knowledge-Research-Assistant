"""
SEC Crypto RAG UI — Search and Chat modes.
"""

from __future__ import annotations

from typing import Any, Dict, List

# region agent log
def _app_debug_log_pre_imports() -> None:
    import os

    from chat_agent.debug_log import agent_log, key_fingerprint

    agent_log(
        "A",
        "app.py:module",
        "before heavy imports",
        {"env_key_fp": key_fingerprint(os.getenv("OPENAI_API_KEY") or "")},
    )


_app_debug_log_pre_imports()
# endregion agent log

import streamlit as st

from chat_agent.env import load_dotenv_env

load_dotenv_env(override=True)

from langgraph_agent import run_chat_turn
from search_handler import format_results_for_display, search_pinecone

# region agent log
def _app_debug_log_post_dotenv() -> None:
    import os

    from chat_agent.debug_log import agent_log, key_fingerprint

    agent_log(
        "A",
        "app.py:module",
        "after load_dotenv_env(override=True) before graph imports",
        {"env_key_fp": key_fingerprint(os.getenv("OPENAI_API_KEY") or "")},
        run_id="post-fix",
    )


_app_debug_log_post_dotenv()
# endregion agent log

st.set_page_config(
    page_title="SEC Crypto Knowledge Base",
    page_icon="📊",
    layout="wide",
)

MODES = ("Search", "Chat")


def _init_session() -> None:
    if "sessions" not in st.session_state:
        st.session_state.sessions = {"default": {"chat_history": [], "retrieval_logs": []}}
    if "active_session" not in st.session_state:
        st.session_state.active_session = "default"
    if "mode" not in st.session_state:
        st.session_state.mode = "Chat"


def _active_session() -> Dict[str, Any]:
    sid = st.session_state.active_session
    return st.session_state.sessions[sid]


def _render_sidebar() -> None:
    st.sidebar.title("SEC Crypto RAG")
    st.session_state.mode = st.sidebar.radio(
        "Mode",
        MODES,
        index=MODES.index(st.session_state.mode) if st.session_state.mode in MODES else 1,
    )

    if st.sidebar.button("＋ New Session"):
        n = len(st.session_state.sessions) + 1
        name = f"session_{n}"
        st.session_state.sessions[name] = {"chat_history": [], "retrieval_logs": []}
        st.session_state.active_session = name
        st.rerun()

    session_names = list(st.session_state.sessions.keys())
    st.session_state.active_session = st.sidebar.selectbox(
        "Session",
        session_names,
        index=session_names.index(st.session_state.active_session),
    )

    if st.session_state.mode == "Chat":
        if st.sidebar.button("Clear conversation"):
            sess = _active_session()
            sess["chat_history"] = []
            sess["retrieval_logs"] = []
            st.rerun()


def _render_search_mode() -> None:
    st.header("Search")
    query = st.text_input("Search query", key="search_query")
    col1, col2, col3 = st.columns(3)
    with col1:
        alpha = st.slider("Contextual search (alpha)", 0.0, 1.0, 0.5, 0.1)
    with col2:
        top_k = st.number_input("Results", min_value=5, max_value=50, value=10)
    with col3:
        score_threshold = st.slider("Min score", 0.0, 1.0, 0.5, 0.05)

    if st.button("Search", type="primary") and query.strip():
        with st.spinner("Searching Pinecone…"):
            results = search_pinecone(
                query=query.strip(),
                alpha=alpha,
                top_k=int(top_k),
                score_threshold=score_threshold,
            )
        results = format_results_for_display(results, max_results=int(top_k))
        if results and results[0].get("error"):
            st.error(results[0].get("snippet", "Search failed"))
            return
        for i, r in enumerate(results, 1):
            with st.expander(f"{i}. {r['title']} (score {r['score']})"):
                if r.get("url"):
                    st.markdown(f"[Open source]({r['url']})")
                st.write(r.get("snippet", ""))


def _render_chat_mode() -> None:
    st.header("Chat")
    st.caption(
        "Answers use CRI ontology classification, dual Pinecone retrieval, LLM reranking, "
        "and cited HTML responses."
    )

    sess = _active_session()
    history: List[Dict[str, str]] = sess["chat_history"]

    for turn in history:
        with st.chat_message(turn["role"]):
            if turn["role"] == "assistant":
                st.markdown(turn["content"], unsafe_allow_html=True)
            else:
                st.write(turn["content"])
            if turn.get("retrieval_debug"):
                with st.expander("Retrieval details"):
                    st.json(turn["retrieval_debug"])

    if prompt := st.chat_input("Ask about SEC crypto regulation…"):
        history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Searching knowledge base and generating answer…"):
                try:
                    # region agent log
                    import os

                    from chat_agent.debug_log import agent_log, key_fingerprint
                    from chat_agent.env import setup_openai_api_key

                    agent_log(
                        "E",
                        "app.py:_render_chat_mode",
                        "before run_chat_turn",
                        {
                            "env_key_fp": key_fingerprint(
                                os.getenv("OPENAI_API_KEY") or ""
                            ),
                        },
                        run_id="post-fix",
                    )
                    setup_openai_api_key(log=False)
                    agent_log(
                        "E",
                        "app.py:_render_chat_mode",
                        "after setup_openai_api_key",
                        {
                            "setup_fp": key_fingerprint(
                                os.getenv("OPENAI_API_KEY") or ""
                            ),
                        },
                        run_id="post-fix",
                    )
                    # endregion agent log
                    answer = run_chat_turn(
                        prompt,
                        history=[
                            {"role": t["role"], "content": t["content"]}
                            for t in history[:-1]
                            if t["role"] in ("user", "assistant")
                        ],
                    )
                    st.markdown(answer.html, unsafe_allow_html=True)
                    if answer.error:
                        st.warning(f"Partial error: {answer.error}")
                    with st.expander("Retrieval details"):
                        st.json(answer.retrieval_debug)
                    history.append(
                        {
                            "role": "assistant",
                            "content": answer.html,
                            "retrieval_debug": answer.retrieval_debug,
                        }
                    )
                    sess["retrieval_logs"].append(answer.retrieval_debug)
                except Exception as e:
                    st.error(f"Chat failed: {e}")
                    history.append(
                        {
                            "role": "assistant",
                            "content": f"<article><p>Error: {e}</p></article>",
                        }
                    )

        sess["chat_history"] = history


def main() -> None:
    _init_session()
    _render_sidebar()
    if st.session_state.mode == "Search":
        _render_search_mode()
    else:
        _render_chat_mode()


if __name__ == "__main__":
    main()
