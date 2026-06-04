from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from chat_agent.answer_agent import ChatAnswer, generate_answer
from chat_agent.data_collector import RetrievalContext, collect_context


class ChatState(TypedDict, total=False):
    query: str
    history: List[Dict[str, str]]
    retrieval: RetrievalContext
    html: str
    sources: List[Dict[str, Any]]
    retrieval_debug: Dict[str, Any]
    error: Optional[str]


def _collect_node(state: ChatState) -> ChatState:
    query = (state.get("query") or "").strip()
    retrieval = collect_context(query)
    return {"retrieval": retrieval}


def _answer_node(state: ChatState) -> ChatState:
    query = state.get("query") or ""
    retrieval = state.get("retrieval")
    if retrieval is None:
        return {
            "html": "<article><p>Retrieval failed.</p></article>",
            "sources": [],
            "error": "missing_retrieval",
        }
    answer = generate_answer(query, retrieval, history=state.get("history"))
    return {
        "html": answer.html,
        "sources": answer.sources,
        "retrieval_debug": answer.retrieval_debug,
        "error": answer.error,
    }


_graph: Any = None


def _build_graph() -> Any:
    global _graph
    if _graph is not None:
        return _graph
    workflow = StateGraph(ChatState)
    workflow.add_node("collect", _collect_node)
    workflow.add_node("answer", _answer_node)
    workflow.set_entry_point("collect")
    workflow.add_edge("collect", "answer")
    workflow.add_edge("answer", END)
    _graph = workflow.compile()
    return _graph


def run_chat_turn(
    query: str,
    history: Optional[List[Dict[str, str]]] = None,
) -> ChatAnswer:
    """
    Run one chat turn: classify, retrieve, rerank, and generate HTML answer.
    """
    graph = _build_graph()
    result = graph.invoke(
        {
            "query": query.strip(),
            "history": history or [],
        }
    )
    return ChatAnswer(
        html=result.get("html") or "",
        sources=result.get("sources") or [],
        retrieval_debug=result.get("retrieval_debug") or {},
        error=result.get("error"),
    )
