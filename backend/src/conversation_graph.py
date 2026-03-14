"""
LangGraph-based conversation orchestrator for MyBestFriend.

Activated when USE_GRAPH=true in config. Implements a Route → Retrieve →
(Expand?) → Answer state machine with session-level context accumulation.

Usage from api_server.py:
    from conversation_graph import run_graph
    answer, context_docs, no_info, sources = run_graph(query, history)
"""
import sys
from pathlib import Path
from typing import TypedDict

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from utils.config_loader import ConfigLoader
from utils.prompt_manager import get_prompt

config = ConfigLoader()


class ConversationState(TypedDict):
    query: str
    history: list
    rewritten_query: str
    context_docs: list
    context: str
    answer: str
    sources: list
    no_info: bool
    followup_queries: list
    is_complex: bool
    # Session-level context accumulated from history
    session_doc_type: str
    session_year: str


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------

def _rewrite_node(state: ConversationState) -> ConversationState:
    from src.rag_retrieval import rewrite_query
    state["rewritten_query"] = rewrite_query(state["query"], state["history"])
    return state


def _router_node(state: ConversationState) -> ConversationState:
    """Detect query complexity and extract session context from history."""
    from src.rag_retrieval import _is_complex_query, extract_query_intent

    state["is_complex"] = _is_complex_query(state["query"])
    state["followup_queries"] = []

    # Build session context: scan last 6 history messages for doc_type / year hints
    session_doc_type = ""
    session_year = ""
    for msg in state["history"][-6:]:
        if msg.get("role") != "user":
            continue
        intent = extract_query_intent(msg["content"])
        if intent["doc_type"] and not session_doc_type:
            session_doc_type = intent["doc_type"]
        if intent["year"] and not session_year:
            session_year = intent["year"]

    state["session_doc_type"] = session_doc_type
    state["session_year"] = session_year
    return state


def _retrieve_node(state: ConversationState) -> ConversationState:
    from src.rag_retrieval import (
        fetch_context, combine_all_user_questions, deduplicate_context,
        rerank_documents, _extract_sources, extract_query_intent, _apply_metadata_boost,
    )

    rewritten = state["rewritten_query"] or state["query"]
    combined_rewritten = combine_all_user_questions(rewritten, state["history"])
    combined_original = combine_all_user_questions(state["query"], state["history"])

    docs_r = fetch_context(combined_rewritten)
    docs_o = fetch_context(combined_original)
    all_docs = deduplicate_context(docs_r + docs_o)

    # Boost by session context (previously established doc_type / year)
    session_intent = {
        "doc_type": state.get("session_doc_type") or None,
        "year": state.get("session_year") or None,
    }
    if session_intent["doc_type"] or session_intent["year"]:
        all_docs = _apply_metadata_boost(all_docs, session_intent)

    top_k = config.get_top_k()
    reranked = rerank_documents(state["query"], all_docs, top_k=top_k)

    state["context_docs"] = reranked
    state["context"] = "\n".join(doc.page_content for doc in reranked)
    state["sources"] = _extract_sources(reranked)
    return state


def _expand_node(state: ConversationState) -> ConversationState:
    """Generate follow-up retrieval queries to fill gaps in the initial context."""
    from src.rag_retrieval import _generate_followup_queries
    followups = _generate_followup_queries(state["query"], state["context"])
    state["followup_queries"] = followups
    return state


def _expand_retrieve_node(state: ConversationState) -> ConversationState:
    """Fetch additional context using the follow-up queries and merge."""
    from src.rag_retrieval import (
        fetch_context, deduplicate_context, rerank_documents, _extract_sources,
    )

    all_docs = list(state["context_docs"])
    for fq in state.get("followup_queries", []):
        fq_docs = fetch_context(fq)
        all_docs = deduplicate_context(all_docs + fq_docs)

    top_k = config.get_top_k()
    reranked = rerank_documents(state["query"], all_docs, top_k=top_k)

    state["context_docs"] = reranked
    state["context"] = "\n".join(doc.page_content for doc in reranked)
    state["sources"] = _extract_sources(reranked)
    return state


def _answer_node(state: ConversationState) -> ConversationState:
    from langchain_core.messages import convert_to_messages

    llm = ChatOpenAI(model=config.get_generator_model())
    messages = [SystemMessage(content=get_prompt("SYSTEM_PROMPT_GENERATOR").format(context=state["context"]))]
    messages.extend(convert_to_messages(state["history"]))
    messages.append(HumanMessage(content=state["query"]))

    response = llm.invoke(messages)
    raw = response.content or ""
    state["no_info"] = "[[NO_INFO]]" in raw
    state["answer"] = raw.replace("[[NO_INFO]]", "").strip()
    return state


# ---------------------------------------------------------------------------
# Routing condition
# ---------------------------------------------------------------------------

def _should_expand(state: ConversationState) -> str:
    if state.get("is_complex") and config.get_multi_step_enabled():
        return "expand"
    return "answer"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_conversation_graph():
    graph = StateGraph(ConversationState)

    graph.add_node("rewrite", _rewrite_node)
    graph.add_node("router", _router_node)
    graph.add_node("retrieve", _retrieve_node)
    graph.add_node("expand", _expand_node)
    graph.add_node("expand_retrieve", _expand_retrieve_node)
    graph.add_node("answer", _answer_node)

    graph.set_entry_point("rewrite")
    graph.add_edge("rewrite", "router")
    graph.add_edge("router", "retrieve")
    graph.add_conditional_edges(
        "retrieve",
        _should_expand,
        {"expand": "expand", "answer": "answer"},
    )
    graph.add_edge("expand", "expand_retrieve")
    graph.add_edge("expand_retrieve", "answer")
    graph.add_edge("answer", END)

    return graph.compile()


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_conversation_graph()
    return _graph


def run_graph(query: str, history: list = []) -> tuple:
    """
    Run the full conversation graph.
    Returns (answer: str, context_docs: list, no_info: bool, sources: list).
    """
    g = get_graph()
    initial: ConversationState = {
        "query": query,
        "history": history,
        "rewritten_query": "",
        "context_docs": [],
        "context": "",
        "answer": "",
        "sources": [],
        "no_info": False,
        "followup_queries": [],
        "is_complex": False,
        "session_doc_type": "",
        "session_year": "",
    }
    result = g.invoke(initial)
    return result["answer"], result["context_docs"], result["no_info"], result["sources"]
