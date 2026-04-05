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
    Run fetch_context scoped to the agent's domain doc_types.
    Returns a list of Document objects (same type as fetch_context output).

    Strategy:
    1. Fetch globally (full hybrid search for quality).
    2. Hard-filter to docs matching the agent's domain doc_types.
    3. If fewer than 2 domain-specific docs survive, fall back to soft boost
       so the agent still returns something useful.
    4. Rerank and trim to top_k.
    """
    from src.rag_retrieval import fetch_context, _apply_metadata_boost

    doc_types = DOMAIN_DOC_TYPES.get(agent_name, [])
    docs = fetch_context(query)

    if doc_types:
        # Hard-filter: keep only docs whose doc_type matches this agent's domain
        domain_docs = [d for d in docs if d.metadata.get("doc_type") in doc_types]
        if len(domain_docs) >= 2:
            docs = domain_docs
        else:
            # Not enough domain docs — fall back to soft boost re-ordering
            intent = {"doc_type": doc_types[0], "year": None}
            docs = _apply_metadata_boost(docs, intent)

    # Skip LLM reranker per-agent: reranking happens once on the merged set in
    # grounding_guard, so we just trim to top_k by position (already ranked by
    # fetch_context's hybrid score + metadata boost).
    return docs[:top_k]


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
# Notification helper
# ---------------------------------------------------------------------------

def send_unknown_query_notification(query: str, run_id: str = "") -> None:
    """
    Send a system email notification when a query could not be answered.
    Uses SMTP config from environment variables (same as api_server.py contact form).
    Non-blocking: caller should run this in a background thread.
    """
    import os
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from utils.config_loader import ConfigLoader

    cfg = ConfigLoader()
    recipient = cfg.get_recipient_email()
    if not recipient:
        print("[notification_agent] RECIPIENT_EMAIL not configured — skipping notification")
        return

    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = cfg.get_smtp_user()
    smtp_password = cfg.get_smtp_password()

    if not smtp_user or not smtp_password:
        print("[notification_agent] SMTP credentials not configured — skipping notification")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "[MyBestFriend] Unknown query received"
    msg["From"] = smtp_user
    msg["To"] = recipient

    body = (
        f"Your digital twin could not answer a visitor's question.\n\n"
        f"Run ID: {run_id}\n\n"
        f"Question:\n{query}\n\n"
        f"Consider adding this topic to your knowledge base."
    )
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, recipient, msg.as_string())
        print(f"[notification_agent] Notification sent to {recipient}")
    except Exception as e:
        print(f"[notification_agent] Email send error (non-fatal): {e}")


# ---------------------------------------------------------------------------
# Context formatting for synthesis
# ---------------------------------------------------------------------------

def format_agent_summary(agent_results: list[AgentResult]) -> str:
    """
    Build a brief per-agent attribution header (no content truncation).
    Used only for provenance metadata — the full merged context from grounding_guard
    is passed separately to the synthesis prompt via state["context"].
    """
    lines = []
    for result in agent_results:
        if result.get("error"):
            lines.append(f"[{result['agent_name']}] ERROR: {result['error']}")
        elif result.get("context"):
            doc_count = len(result.get("docs", []))
            lines.append(
                f"[{result['agent_name']}] {doc_count} docs retrieved, "
                f"confidence={result.get('confidence', 0.0):.2f}"
            )
        else:
            lines.append(f"[{result['agent_name']}] No relevant information found.")
    return "\n".join(lines)
