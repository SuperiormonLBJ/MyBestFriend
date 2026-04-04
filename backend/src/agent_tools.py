"""
Agent tool layer — domain-scoped retrieval primitives for the multi-agent graph.

Each specialist agent calls search_knowledge_by_domain() instead of fetch_context()
directly so that retrieval is scoped to a single doc_type. This prevents agents from
retrieving the same documents (which the grounding_guard's ACRR metric will catch).

All functions reuse existing rag_retrieval.py implementations — no new retrieval logic.
"""
import sys
import time
import utils.path_setup  # noqa: F401

from src.agent_state import AgentResult


# ---------------------------------------------------------------------------
# Token budget helpers
# ---------------------------------------------------------------------------

def estimate_token_count(text: str) -> int:
    """
    Approximate token count using word-count heuristic (words * 1.3).
    Avoids tiktoken import for speed inside parallel agent nodes.
    """
    return int(len(text.split()) * 1.3)


# ---------------------------------------------------------------------------
# Domain-scoped retrieval
# ---------------------------------------------------------------------------

DOMAIN_DOC_TYPES: dict[str, list[str]] = {
    "career_agent":   ["career", "work", "job"],
    "project_agent":  ["project"],
    "skills_agent":   ["cv", "skills", "education"],
    "personal_agent": ["personal", "hobby", "life"],
    "job_prep_agent": ["career", "project", "cv", "skills"],  # broad for job context
}


def search_knowledge_by_domain(
    query: str,
    agent_name: str,
    top_k: int = 5,
) -> list:
    """
    Run fetch_context with a soft metadata boost scoped to the agent's doc_types.
    Returns a list of Document objects (same type as fetch_context output).

    We call fetch_context normally (it uses the global hybrid search), then apply
    a metadata boost that promotes docs matching the agent's domain.
    This preserves the full hybrid search quality while adding domain focus.
    """
    from src.rag_retrieval import fetch_context, _apply_metadata_boost, rerank_documents

    doc_types = DOMAIN_DOC_TYPES.get(agent_name, [])

    # fetch_context uses TOP_K from config — call it then apply domain boost
    docs = fetch_context(query)

    # Apply soft boost toward this agent's domain
    if doc_types:
        # Use the first doc_type as the primary hint for the boost function
        intent = {"doc_type": doc_types[0], "year": None}
        docs = _apply_metadata_boost(docs, intent)

    # Rerank and trim to top_k
    reranked = rerank_documents(query, docs, top_k=top_k)
    return reranked


# ---------------------------------------------------------------------------
# AgentResult factory
# ---------------------------------------------------------------------------

def compute_confidence(docs: list) -> float:
    """
    Confidence score 0.0–1.0 based on number and quality of retrieved docs.
    Simple heuristic: full marks at top_k docs, penalty for fewer.
    """
    if not docs:
        return 0.0
    # Score is linearly proportional to number of docs found (max=5)
    return min(1.0, len(docs) / 5.0)


def build_agent_result(
    agent_name: str,
    docs: list,
    error: str | None = None,
) -> AgentResult:
    """
    Build an AgentResult from retrieved documents.
    Calls _extract_sources() from rag_retrieval — no duplication of source logic.
    """
    from src.rag_retrieval import _extract_sources

    if error is not None or not docs:
        return AgentResult(
            agent_name=agent_name,
            docs=[],
            context="",
            sources=[],
            token_count=0,
            error=error,
            confidence=0.0,
        )

    context = "\n\n".join(doc.page_content for doc in docs)
    sources = _extract_sources(docs)
    token_count = estimate_token_count(context)
    confidence = compute_confidence(docs)

    return AgentResult(
        agent_name=agent_name,
        docs=docs,
        context=context,
        sources=sources,
        token_count=token_count,
        error=None,
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# Loop guard
# ---------------------------------------------------------------------------

MAX_TRACE_STEPS = 10


def is_loop_detected(state: dict) -> bool:
    """
    Returns True if the graph has taken too many steps — prevents infinite loops.
    Called at the start of every node. If True, the node should set no_info=True
    and return immediately without doing further work.
    """
    return len(state.get("agent_trace", [])) >= MAX_TRACE_STEPS


# ---------------------------------------------------------------------------
# Context formatting for synthesis
# ---------------------------------------------------------------------------

def format_agent_summary(agent_results: list[AgentResult]) -> str:
    """
    Build a brief per-agent context summary to include in the synthesis prompt.
    Helps the synthesis model understand the provenance of each piece of information.
    """
    lines = []
    for result in agent_results:
        if result.get("error"):
            lines.append(f"[{result['agent_name']}] ERROR: {result['error']}")
        elif result.get("context"):
            doc_count = len(result.get("docs", []))
            lines.append(
                f"[{result['agent_name']}] ({doc_count} docs, "
                f"confidence={result['confidence']:.2f}):\n{result['context'][:500]}..."
            )
        else:
            lines.append(f"[{result['agent_name']}] No relevant information found.")
    return "\n\n".join(lines)
