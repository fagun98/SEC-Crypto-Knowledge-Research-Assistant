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

MODES = ("Chat", "Search", "Instructions")


def _init_session() -> None:
    if "sessions" not in st.session_state:
        st.session_state.sessions = {"default": {"chat_history": [], "retrieval_logs": []}}
    if "active_session" not in st.session_state:
        st.session_state.active_session = "default"
    if "mode" not in st.session_state:
        st.session_state.mode = "Instructions"


def _active_session() -> Dict[str, Any]:
    sid = st.session_state.active_session
    return st.session_state.sessions[sid]


def _render_sidebar() -> None:
    st.sidebar.title("SEC Crypto RAG")
    st.session_state.mode = st.sidebar.radio(
        "Mode",
        MODES,
        index=MODES.index(st.session_state.mode) if st.session_state.mode in MODES else 2,
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

    trigger_search = False
    if st.session_state.get("trigger_search"):
        st.session_state.trigger_search = False
        trigger_search = True

    if (st.button("Search", type="primary") or trigger_search) and query.strip():
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

    # Render st.chat_input so it always displays
    chat_prompt = st.chat_input("Ask about SEC crypto regulation…")

    # Resolve active prompt: check for pending prefilled prompt first
    prompt = None
    if st.session_state.get("pending_chat_prompt"):
        prompt = st.session_state.pop("pending_chat_prompt")
    elif chat_prompt:
        prompt = chat_prompt

    if prompt:
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


def _render_instructions_page() -> None:
    st.header("Instructions & About")
    st.caption("Learn about the SEC Crypto Knowledge Base, how to navigate it, and try out sample research/compliance questions.")

    tab1, tab2, tab3 = st.tabs(["ℹ️ About", "📖 How to Use", "❓ Sample Questions"])

    with tab1:
        st.markdown("""
        ### ℹ️ SEC Crypto Knowledge Research Assistant

        Welcome to the **SEC Crypto Knowledge Research Assistant**, a powerful **Retrieval-Augmented Generation (RAG)** platform designed to streamline compliance, research, and analysis of SEC cryptocurrency regulations, policies, guidance, enforcement actions, and stakeholder discussions.

        By integrating state-of-the-art AI agents with high-fidelity document retrieval, this assistant acts as an intelligent companion for legal teams, compliance officers, and regulatory researchers seeking to navigate the complex landscape of digital asset supervision.

        ---

        #### 🌟 Key Capabilities
        * **🧠 LangGraph-Powered Conversational Agent**: Engages in multi-turn dialogues, synthesizes complex regulatory history, and provides evidence-backed answers.
        * **🔍 Hybrid Sparse & Dense Retrieval**: Combines semantic embeddings (OpenAI `text-embedding-3-small`) with keyword-matching (SPLADE sparse vectors) through Pinecone to ensure high-precision results.
        * **🏷️ CRI Ontology Classification**: Classifies and structures retrieved documents according to relevant regulatory domains, giving context-rich answers.
        * **📂 Session Isolation**: Creates separate research workspaces so you can organize different inquiries without overlap.
        * **🔗 Active Citations & Proofs**: Provides direct links to the official sources and details of the exact files/sections retrieved during the search.
        """)

    with tab2:
        st.markdown("""
        ### 📖 How to Navigate the Assistant

        This app provides two primary modes of interaction to support different workflows:

        ---

        #### 💬 Chat Mode
        * **When to use**: Best for open-ended questions, policy evolution, summarizing complex rules, or synthesizing multiple documents.
        * **How it works**: Simply enter your question in the chat input. The LangGraph agent will decide whether it needs to search the knowledge base, retrieve relevant content, and draft a response.
        * **Key Features**:
          * **Citations**: Clickable links to sources are provided directly inside responses.
          * **Retrieval Details**: Below each response, expand the *Retrieval details* tab to see raw scores and namespaces retrieved by the system.
          * **Sidebar Controls**: Use **"Clear conversation"** to reset the history for the active session.

        ---

        #### 🔍 Search Mode
        * **When to use**: Best for locating specific sections, regulatory filings, press releases, or verifying the occurrence of key phrases.
        * **How it works**: Enter a keyword or query, configure your parameters, and hit the **Search** button.
        * **Adjustable Parameters**:
          * **Contextual Search (alpha)**: 
            * `0.0` is pure keyword matching (lexical SPLADE search).
            * `1.0` is pure contextual matching (semantic OpenAI embeddings).
            * `0.5` (default) blends both for the best hybrid performance.
          * **Results**: Limit the number of retrieved documents (5 to 50).
          * **Min Score**: Filter out low-confidence matches.

        ---

        #### 💼 Workspace & Session Management
        * Use **"＋ New Session"** in the sidebar to spawn a clean session workspace.
        * Switch between sessions using the **"Session"** dropdown to keep different lines of research separated.
        """)

    with tab3:
        st.markdown("### 🛠️ Practice & Compliance-Focused Questions")
        st.caption("These questions help firms evaluate registration requirements, custody guidelines, compliance paths, and jurisdiction limits. Click a button below any question to execute it in Chat or Search mode.")

        compliance_questions = [
            {
                "question": "When should a crypto asset or crypto transaction be treated as a securities transaction?",
                "goal": "Helps firms decide whether they must register, disclose, restrict trading, or avoid offering a product—and helps SEC staff see where clearer guidance is needed."
            },
            {
                "question": "What exact compliance path should a crypto trading platform, ATS, exchange, or broker-dealer follow?",
                "tag": "Highest Priority",
                "goal": "Surfaces registration options (exchange, ATS, broker-dealer, custodian, etc.) and where existing rules may not fit 24/7 trading, wallets, on-chain settlement, and tokenized assets."
            },
            {
                "question": "How should custody rules apply to crypto assets, tokenized securities, and stablecoins?",
                "goal": "Addresses a major operational blocker—who may hold customer crypto, segregation, control, bankruptcy treatment, and whether broker-dealer custody rules need updates."
            },
            {
                "question": "What rules are needed for tokenized securities to work in real markets?",
                "goal": "Clarifies legal vs. technical treatment (token as security, receipt, claim, or wrapper) across clearing, settlement, transfer agents, and investor rights."
            },
            {
                "question": "Where do SEC and CFTC rules need to be harmonized for crypto products and venues?",
                "goal": "Helps firms avoid duplicated or conflicting obligations when products sit between securities and commodities regulation."
            }
        ]

        for idx, item in enumerate(compliance_questions):
            with st.container():
                tag_str = " 🏷️ **(Highest Priority)**" if item.get("tag") else ""
                st.markdown(f"**{idx+1}. {item['question']}**{tag_str}")
                st.markdown(f"*{item['goal']}*")
                col1, col2, _ = st.columns([1.2, 1.4, 5])
                with col1:
                    if st.button("💬 Ask in Chat", key=f"comp_chat_{idx}"):
                        st.session_state.pending_chat_prompt = item["question"]
                        st.session_state.mode = "Chat"
                        st.rerun()
                with col2:
                    if st.button("🔍 Query in Search", key=f"comp_search_{idx}"):
                        st.session_state.search_query = item["question"]
                        st.session_state.trigger_search = True
                        st.session_state.mode = "Search"
                        st.rerun()
                st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

        st.markdown("---")

        st.markdown("### 📚 Research-Style Questions")
        st.caption("These questions track historical policy shifts, SEC staff statements, stakeholder meeting outputs, and agency coordination. Click a button below any question to execute it in Chat or Search mode.")

        research_questions = [
            {
                "question": "Which 2025 topics moved from private stakeholder meetings into public SEC staff statements or no-action positions?",
                "goal": "Connects Task Force meetings with public outputs (custody FAQs, stablecoin/staking statements, ETP disclosures, no-action letters)."
            },
            {
                "question": "How did the SEC’s 2025 withdrawal of the 2019 broker-dealer custody statement change the regulatory direction for crypto custody?",
                "goal": "Tracks a concrete policy shift (May 15, 2025 withdrawal of the joint SEC/FINRA staff statement)."
            },
            {
                "question": "How did the SEC’s 2025 staff statements separate meme coins, proof-of-work mining, protocol staking, and liquid staking from securities transactions?",
                "goal": "Summarizes staff positions across Feb–Aug 2025 on products often treated as securities by default."
            },
            {
                "question": "Did 2025 meeting participants mostly ask for new crypto-specific rules, or no-action relief, safe harbors, and reinterpretation of existing securities laws?",
                "goal": "Reveals whether industry is seeking new rulemaking vs. relief under current law."
            },
            {
                "question": "What crypto market problems require SEC-CFTC harmonization rather than separate agency action?",
                "goal": "Aligns with the Sept 2025 joint statement on product/venue definitions, reporting, capital/margin, and coordinated innovation exemptions."
            }
        ]

        for idx, item in enumerate(research_questions):
            with st.container():
                st.markdown(f"**{idx+1}. {item['question']}**")
                st.markdown(f"*{item['goal']}*")
                col1, col2, _ = st.columns([1.2, 1.4, 5])
                with col1:
                    if st.button("💬 Ask in Chat", key=f"res_chat_{idx}"):
                        st.session_state.pending_chat_prompt = item["question"]
                        st.session_state.mode = "Chat"
                        st.rerun()
                with col2:
                    if st.button("🔍 Query in Search", key=f"res_search_{idx}"):
                        st.session_state.search_query = item["question"]
                        st.session_state.trigger_search = True
                        st.session_state.mode = "Search"
                        st.rerun()
                st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)


def main() -> None:
    _init_session()
    _render_sidebar()
    if st.session_state.mode == "Search":
        _render_search_mode()
    elif st.session_state.mode == "Instructions":
        _render_instructions_page()
    else:
        _render_chat_mode()


if __name__ == "__main__":
    main()
