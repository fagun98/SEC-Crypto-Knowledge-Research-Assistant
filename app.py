import uuid
from typing import Dict, List, Any
import streamlit as st
from search_handler import search_pinecone
from langgraph_agent import run_agent

def init_session_state() -> None:
    """Initialize the high-level app session state."""
    if "sessions" not in st.session_state:
        st.session_state.sessions = {}  # type: ignore[attr-defined]
    if "active_session_id" not in st.session_state:
        st.session_state.active_session_id = None  # type: ignore[attr-defined]


def create_new_session(label: str | None = None) -> str:
    """Create a new logical RAG session and return its id."""
    if not label:
        label = "New Session"

    session_id = str(uuid.uuid4())[:8]
    st.session_state.sessions[session_id] = {
        "label": label,
        "search_history": [],
        "chat_history": [],
    }
    st.session_state.active_session_id = session_id
    return session_id


def get_active_session() -> Dict:
    """Return the currently active session dict, creating one if needed."""
    if not st.session_state.sessions:
        create_new_session("Session 1")

    active_id = st.session_state.active_session_id
    if active_id is None or active_id not in st.session_state.sessions:
        # Fallback to first available session
        active_id = next(iter(st.session_state.sessions.keys()))
        st.session_state.active_session_id = active_id

    return st.session_state.sessions[active_id]


def layout_page() -> None:
    """Top-level layout and styling."""
    st.set_page_config(
        page_title="RAG Studio",
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


def render_session_bar() -> None:
    """Horizontal list of sessions with ability to add new ones."""
    sessions: Dict[str, Dict] = st.session_state.sessions
    active_id = st.session_state.active_session_id

    st.markdown('<div class="section-label">Workspace</div>', unsafe_allow_html=True)

    cols = st.columns([6, 1.5])
    with cols[0]:
        session_items: List[str] = list(sessions.keys())
        pill_html = '<div class="session-bar">'
        for sid in session_items:
            cls = "session-pill active" if sid == active_id else "session-pill"
            label = sessions[sid]["label"]
            pill_html += f'<button class="{cls}" onclick="">{label}</button>'
        pill_html += "</div>"
        # Note: buttons are purely visual; real selection is below.
        st.markdown(pill_html, unsafe_allow_html=True)

    with cols[1]:
        if st.button("＋ New Session", use_container_width=True):
            create_new_session(f"Session {len(sessions) + 1}")

    # Real selector (clean, small)
    if sessions:
        labels = {v["label"]: k for k, v in sessions.items()}
        selected_label = st.selectbox(
            "Active session",
            options=list(labels.keys()),
            index=list(labels.values()).index(active_id) if active_id in labels.values() else 0,
            label_visibility="collapsed",
        )
        st.session_state.active_session_id = labels[selected_label]


def perform_search(query: str, alpha: float = 0.5, top_k: int = 20) -> List[Dict[str, Any]]:
    """
    Perform RAG search using Pinecone hybrid search.
    
    Args:
        query: Search query string
        alpha: Blend factor between dense (1.0) and sparse (0.0) search
        top_k: Maximum number of results to return
    
    Returns:
        List of search result dictionaries
    """
    try:
        results = search_pinecone(
            query=query,
            alpha=alpha,
            top_k=top_k,
            score_threshold=0.5,
            include_scores=True
        )
        
        # Filter out error results
        if results and len(results) == 1 and results[0].get("error"):
            return []
        
        return results
    except Exception as e:
        st.error(f"Search error: {str(e)}")
        return []


def perform_chat(message: str, history: List[Dict[str, str]]) -> str:
    """
    Perform chat using LangGraph agent with RAG tool.
    
    Args:
        message: User's message/query
        history: Previous conversation history
    
    Returns:
        Agent's response string
    """
    try:
        # Convert history format if needed
        conversation_history = []
        for msg in history:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                conversation_history.append(msg)
        
        # Run the agent
        response = run_agent(message, conversation_history=conversation_history if conversation_history else None)
        return response
    except Exception as e:
        return f"I encountered an error while processing your request: {str(e)}. Please try again or rephrase your question."


def render_search_ui(active_session: Dict, alpha: float = 0.5) -> None:
    """Search-only interaction panel."""
    query = st.text_input("Search query", placeholder="Ask a question or search for a topic...")

    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        run_search = st.button("Search", use_container_width=True)
    with col2:
        top_k = st.number_input("Results", min_value=5, max_value=50, value=20, step=5, label_visibility="collapsed")
    with col3:
        st.caption("Results will be ranked by semantic relevance.")

    if run_search and query.strip():
        with st.spinner("Searching SEC Crypto knowledge base..."):
            results = perform_search(query.strip(), alpha=alpha, top_k=top_k)

        if results:
            # Persist history
            active_session["search_history"].append({"query": query.strip(), "results": results})

            st.markdown("")
            st.markdown(f"**Found {len(results)} results**", help="Preview of top-ranked passages for this query.")

            for idx, item in enumerate(results, start=1):
                with st.container(border=True):
                    title = item.get("title", f"Result {idx}")
                    score = item.get("score", "0.00")
                    snippet = item.get("snippet", "No content available")
                    url = item.get("url", "")
                    
                    st.markdown(f"**{idx}. {title}**  ·  score: `{score}`")
                    st.markdown(f"<span style='color:#d1d5db;'>{snippet}</span>", unsafe_allow_html=True)
                    if url:
                        st.markdown(f"<a href='{url}' target='_blank'>Click to view full document</a>", unsafe_allow_html=True)
                    # Show metadata if available
                    metadata = item.get("metadata", {})
                    if metadata:
                        with st.expander("View metadata"):
                            st.json(metadata)
        else:
            st.warning("No results found. Try rephrasing your query or adjusting the search parameters.")

    if active_session["search_history"]:
        with st.expander("Search history", expanded=False):
            for entry in reversed(active_session["search_history"][-10:]):
                st.markdown(f"- **{entry['query']}** ({len(entry.get('results', []))} results)")


def render_chat_ui(active_session: Dict) -> None:
    """Chat-style interaction panel."""
    chat_container = st.container()
    with chat_container:
        for msg in active_session["chat_history"]:
            alignment = "flex-end" if msg["role"] == "user" else "flex-start"
            bg = "#0b1120" if msg["role"] == "assistant" else "#111827"
            role_label = "You" if msg["role"] == "user" else "Assistant"
            st.markdown(
                f"""
                <div style="display:flex; justify-content:{alignment}; margin-bottom:0.35rem;">
                    <div style="
                        max-width:72%;
                        background:{bg};
                        padding:0.65rem 0.9rem;
                        border-radius:14px;
                        border:1px solid rgba(148,163,184,0.45);
                        font-size:0.88rem;
                        line-height:1.45;
                    ">
                        <div style="font-size:0.65rem; text-transform:uppercase; letter-spacing:0.14em; color:#9ca3af; margin-bottom:0.2rem;">
                            {role_label}
                        </div>
                        <div>{msg["content"]}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with st.container():
        prompt = st.text_area(
            "Message",
            placeholder="Ask a question, request a summary, or refine previous results...",
            label_visibility="collapsed",
            height=80,
        )
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            send = st.button("Send", use_container_width=True)
        with col2:
            clear = st.button("Clear conversation", use_container_width=True)
        with col3:
            st.caption("")

    sid = st.session_state.active_session_id

    if clear:
        active_session["chat_history"].clear()
        st.rerun()

    if send and prompt.strip():
        # Add user message to history
        active_session["chat_history"].append({"role": "user", "content": prompt.strip()})
        
        # Get conversation history (excluding the just-added user message for the agent call)
        history_for_agent = active_session["chat_history"][:-1] if len(active_session["chat_history"]) > 1 else []
        
        # Show loading spinner
        with st.spinner("Researching SEC Crypto knowledge base and generating response..."):
            reply = perform_chat(prompt.strip(), history_for_agent)
        
        # Add assistant response to history
        active_session["chat_history"].append({"role": "assistant", "content": reply})
        st.rerun()


def main() -> None:
    init_session_state()
    layout_page()

    # Top hero / branding
    left, right = st.columns([3, 2])
    with left:
        st.markdown(
            """
            <div class="top-title">RAG Studio</div>
            <div style="color:#9ca3af; margin-top:0.15rem; font-size:0.86rem;">
                SEC Crypto Knowledge Research Assistant - Powered by RAG & LangGraph
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            """
            <div style="text-align:right; font-size:0.7rem; color:#9ca3af; margin-top:0.25rem;">
                Powered by LangGraph Agent & Pinecone RAG
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Session selector bar
    with st.container():
        render_session_bar()

    st.markdown("")

    # Main interaction panel with Search / Chat at the top
    with st.container():
        st.markdown('<div class="section-label">Interaction</div>', unsafe_allow_html=True)
        # Use a horizontal radio instead of segmented_control for wider compatibility
        mode = st.radio(
            "Mode",
            options=["Search", "Chat"],
            index=0,
            horizontal=True,
            label_visibility="collapsed",
        )

        active_session = get_active_session()

        with st.container():

            # Shared, calibrated header inside the glass panel
            if mode == "Search":
                st.markdown('<h4><div class="glass-panel">Search across your knowledge base</div></h4>', unsafe_allow_html=True)
            else:
                st.markdown('<h4><div class="glass-panel">Chat with your RAG assistant</div></h4>', unsafe_allow_html=True)

            st.markdown("---")

            if mode == "Search":
                # Contextual Search slider (0–1 mapped to 0–100% in UI)
                alpha = st.slider(
                    "Contextual Search",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.5,
                    step=0.01,
                    help="Blend between keyword-style and fully contextual semantic search.",
                )
                # `alpha` is now available for use in your search logic
                render_search_ui(active_session, alpha=alpha)
            else:
                render_chat_ui(active_session)

            st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()


