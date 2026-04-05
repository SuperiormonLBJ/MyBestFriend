"""
Multi-agent state schema for MyBestFriend.

MultiAgentState extends ConversationState with fan-in reducers for parallel agent execution.
The Annotated[list, operator.add] reducer is the critical mechanism that makes LangGraph's
Send-based parallelism safe: each parallel agent appends to agent_results/agent_trace
instead of overwriting.

Usage:
    from src.agent_state import MultiAgentState, AgentResult
"""
import operator
from typing import Annotated, TypedDict
from pydantic import BaseModel, Field


class AgentResult(TypedDict):
    """Result from a single domain specialist agent."""
    agent_name: str          # e.g. "career_agent", "project_agent"
    docs: list               # retrieved Document objects
    context: str             # concatenated chunk text
    summary: str             # 2-3 sentence LLM-generated domain summary (Option B)
    sources: list            # _extract_sources() output
    token_count: int         # estimated token count of context
    error: str | None        # failure reason if agent raised an exception
    confidence: float        # 0.0–1.0, weighted by reranker position


class IntentResult(BaseModel):
    """Structured LLM output from the intent classifier node."""
    primary_domain: str = Field(
        description="The single most relevant domain: career, project, skills, personal, or general"
    )
    requires_agents: list[str] = Field(
        description="List of agent names to activate, e.g. ['career_agent', 'project_agent']"
    )
    entities: dict = Field(
        default_factory=dict,
        description="Extracted entities: year (str), doc_type (str), job_context (bool)",
    )
    confidence: float = Field(
        description="Classifier confidence 0.0–1.0",
        ge=0.0,
        le=1.0,
    )


class MultiAgentState(TypedDict):
    """
    Full state for the multi-agent conversation graph.

    Backward-compatible: all ConversationState fields are preserved so the existing
    run_graph() call signature is unchanged when USE_MULTI_AGENT=false.

    Parallel-safe: agent_results, agent_trace, and agent_errors use
    Annotated[list, operator.add] so LangGraph concatenates results from
    parallel branches rather than applying last-writer-wins semantics.
    """
    # ── Existing ConversationState fields (must not be removed) ─────────────
    query: str
    history: list
    rewritten_query: str
    context_docs: list          # final merged docs (used by synthesis + frontend)
    context: str                # final merged context text
    answer: str
    sources: list
    no_info: bool
    followup_queries: list
    is_complex: bool
    session_doc_type: str
    session_year: str

    # ── Multi-agent orchestration fields ────────────────────────────────────
    intent: dict                # IntentResult serialised to dict
    active_agents: list[str]    # agent names the supervisor dispatched

    # Job mode — set by the frontend toggle, gates job_prep_agent activation
    job_mode: bool              # True = user explicitly selected Job Mode

    # Job URL scraping (populated by fast_router when a job URL is detected)
    job_url: str                # original URL from the user's query
    scraped_job_text: str       # full JD text scraped from the URL

    # Fan-in reducers: parallel agents append; LangGraph concatenates at merge
    agent_results: Annotated[list[AgentResult], operator.add]
    agent_trace: Annotated[list[dict], operator.add]    # {agent, latency_ms, doc_count}
    agent_errors: Annotated[list[str], operator.add]    # names of failed agents

    # Token budget tracking
    token_budget_used: int
    token_budget_limit: int

    # Grounding guard output
    grounding_passed: bool
    grounding_issues: list[str]

    # Synthesis metadata
    synthesis_model: str

    # Checkpointing / HITL
    graph_run_id: str
    checkpoint_thread_id: str
    human_intervention_requested: bool

    # Notification agent
    notification_sent: bool       # True if unknown-query notification was dispatched


def build_initial_multi_agent_state(
    query: str,
    history: list,
    thread_id: str = "",
    job_mode: bool = False,
) -> MultiAgentState:
    """Factory for initial MultiAgentState with safe defaults."""
    import uuid
    run_id = str(uuid.uuid4())
    return MultiAgentState(
        # Existing fields
        query=query,
        history=history,
        rewritten_query="",
        context_docs=[],
        context="",
        answer="",
        sources=[],
        no_info=False,
        followup_queries=[],
        is_complex=False,
        session_doc_type="",
        session_year="",
        # Multi-agent fields
        intent={},
        active_agents=[],
        job_mode=job_mode,
        job_url="",
        scraped_job_text="",
        agent_results=[],
        agent_trace=[],
        agent_errors=[],
        token_budget_used=0,
        token_budget_limit=6000,
        grounding_passed=True,
        grounding_issues=[],
        synthesis_model="",
        graph_run_id=run_id,
        checkpoint_thread_id=thread_id or run_id,
        human_intervention_requested=False,
        notification_sent=False,
    )
