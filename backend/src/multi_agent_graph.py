"""
Multi-agent conversation graph for MyBestFriend.

Activated when USE_MULTI_AGENT=true in config. Implements:
  fast_router → supervisor → [parallel domain agents: A+B+C] → grounding_guard → rerank → synthesis → trace_log

Key design principles:
- Strict DAG: supervisor dispatches once, no backward edges, no cycles.
- Parallel execution via LangGraph Send API (fan-out) + Annotated[list, operator.add] (fan-in).
- Only the synthesis node streams tokens; all other nodes run synchronously before streaming begins.
- All existing rag_retrieval.py functions are reused unchanged.
- Feature-flagged: USE_MULTI_AGENT=false (default) falls back to existing run_graph() / generate_answer().

Usage from api_server.py:
    from src.multi_agent_graph import run_multi_agent_graph, run_multi_agent_graph_stream
    answer, context_docs, no_info, sources = run_multi_agent_graph(query, history)
    # or for SSE streaming:
    for event in run_multi_agent_graph_stream(query, history):
        yield event
"""
import json
import time
import uuid
import threading
import queue as queue_module
from typing import Callable
import utils.path_setup  # noqa: F401

from langgraph.graph import StateGraph, END
from langgraph.types import Send
from langchain_core.messages import HumanMessage, SystemMessage, convert_to_messages
from langchain_openai import ChatOpenAI

from utils.config_loader import ConfigLoader
from utils.prompt_manager import get_prompt
from src.agent_state import MultiAgentState, AgentResult, build_initial_multi_agent_state
from src.agent_tools import (
    expand_query_for_domain,
    generate_domain_summary,
    retrieve_job_prep_docs,
    extract_job_url,
    scrape_job_description,
    build_agent_result,
    is_loop_detected,
    format_agent_summaries,
    estimate_token_count,
    send_unknown_query_notification,
)

config = ConfigLoader()

# Thread-local: the streaming synthesis node reads from here so the graph
# can be compiled once and reused across all streaming calls.
_tl = threading.local()

SPECIALIST_AGENT_NAMES = [
    "career_agent",
    "project_agent",
    "skills_agent",
    "personal_agent",
    "job_prep_agent",
]


# ---------------------------------------------------------------------------
# Node: Fast Router (replaces LLM intent classifier)
# ---------------------------------------------------------------------------

# Maps doc_type from extract_query_intent → agent names to activate
_DOMAIN_AGENT_MAP: dict[str | None, list[str]] = {
    "career":   ["career_agent"],
    "project":  ["project_agent"],
    "cv":       ["skills_agent"],
    "personal": ["personal_agent"],
    None:       ["career_agent", "project_agent", "skills_agent", "personal_agent"],
}


def _fast_router_node(state: MultiAgentState) -> MultiAgentState:
    """
    Lightweight routing node — no LLM call.

    Uses the existing regex-based extract_query_intent() to classify the query
    into a domain, then maps it to the appropriate agent(s). For general/unknown
    queries all four core agents are activated.

    Also rewrites the query (1 LLM call). Each specialist agent then expands
    the rewritten query with domain-specific terms before calling fetch_context().
    """
    from src.rag_retrieval import extract_query_intent, rewrite_query

    print(f"[fast_router] query: {state['query']!r}")
    if is_loop_detected(state):
        state["no_info"] = True
        return state

    # ── Job Mode: scrape URL (if present) and force-activate job_prep_agent ──
    if state.get("job_mode"):
        job_url = extract_job_url(state["query"])
        if job_url:
            print(f"[fast_router] job_mode + URL detected: {job_url} — scraping...")
            scraped = scrape_job_description(job_url)
            if scraped:
                state["job_url"] = job_url
                state["scraped_job_text"] = scraped
                print(f"[fast_router] scraped {len(scraped)} chars from {job_url}")
            else:
                print(f"[fast_router] scrape returned empty (login-gated or failed)")

    rewritten = rewrite_query(state["query"], state["history"])
    state["rewritten_query"] = rewritten
    print(f"[fast_router] rewritten: {rewritten!r}")

    intent = extract_query_intent(state["query"])
    doc_type = intent.get("doc_type")  # str or None
    agents = list(_DOMAIN_AGENT_MAP.get(doc_type, _DOMAIN_AGENT_MAP[None]))

    # Activate job_prep_agent ONLY when the user explicitly toggled Job Mode
    if state.get("job_mode") and "job_prep_agent" not in agents:
        agents.append("job_prep_agent")
        doc_type = "job_prep"

    state["intent"] = {
        "primary_domain": doc_type or "general",
        "requires_agents": agents,
        "entities": {"year": intent.get("year")},
        "confidence": 1.0,  # deterministic regex — always 1.0
    }
    print(f"[fast_router] domain={doc_type!r} agents={agents}")
    return state


# ---------------------------------------------------------------------------
# Node: Supervisor
# ---------------------------------------------------------------------------

def _route_to_agents(state: MultiAgentState):
    """
    Conditional edge function: returns list[Send] for parallel execution
    or routes directly to grounding_guard if no agents are needed.
    """
    requires_agents = state.get("intent", {}).get("requires_agents", [])
    valid_agents = [a for a in requires_agents if a in SPECIALIST_AGENT_NAMES]

    if not valid_agents:
        # No agents to run — skip directly to grounding guard
        return "grounding_guard"

    if config.get_multi_agent_parallel():
        # Fan-out: dispatch each agent concurrently via Send
        return [Send(agent_name, state) for agent_name in valid_agents]
    else:
        # Sequential: set active_agents and let supervisor handle routing
        state["active_agents"] = valid_agents
        return valid_agents[0] if valid_agents else "grounding_guard"


def _supervisor_node(state: MultiAgentState) -> MultiAgentState:
    """
    Initialise multi-agent tracking fields.
    In parallel mode, this node's output goes to _route_to_agents (conditional edge).
    In sequential mode, it sets active_agents for ordered dispatch.
    """
    if is_loop_detected(state):
        state["no_info"] = True
        return state

    active = state.get("intent", {}).get("requires_agents", [])
    run_id = str(uuid.uuid4())
    print(f"[supervisor] run_id={run_id} dispatching {len(active)} agents: {active}")
    state["token_budget_limit"] = config.get_multi_agent_token_budget()
    state["token_budget_used"] = 0
    state["agent_results"] = []
    state["agent_trace"] = []
    state["agent_errors"] = []
    state["active_agents"] = active
    state["graph_run_id"] = run_id
    return state


# ---------------------------------------------------------------------------
# Specialist agent factory  (Options A + B + C)
# ---------------------------------------------------------------------------

def _make_specialist_agent(agent_name: str) -> Callable[[MultiAgentState], MultiAgentState]:
    """
    Returns a node function for a domain specialist agent.

    Each agent runs three steps in sequence (all fast, called in parallel across agents):

    A) Domain query expansion (template, no LLM):
       Appends domain-specific terms to the rewritten query so each agent retrieves
       a diverse, focused candidate set rather than all hitting the same generic query.

    B) Targeted fetch_context() + mini-summary (1 cheap LLM call per agent):
       Calls fetch_context() with the domain-expanded query, then generates a 2-3
       sentence domain summary. Because agents run in parallel via LangGraph Send,
       wall-clock cost = max(agent_latency), not sum — same as a single LLM call.

    C*) job_prep_agent only: detects job-description context, extracts requirements
       via extract_job_requirements(), and searches with those keywords for targeted
       fit-signal retrieval instead of the generic domain-suffix expansion.

    Wrapped in try/except so a single agent failure never kills the whole graph.
    """
    is_job_prep = agent_name == "job_prep_agent"

    def _agent_node(state: MultiAgentState) -> dict:
        if is_loop_detected(state):
            return {"agent_results": [], "agent_trace": [], "agent_errors": []}

        t0 = time.time()
        top_k = config.get_top_k()
        query = state.get("rewritten_query") or state["query"]
        original_query = state["query"]

        try:
            if is_job_prep:
                # Option C: job-description-aware retrieval
                # Prefer scraped text from URL over raw query text
                docs, _fit_note = retrieve_job_prep_docs(
                    original_query,
                    top_k=top_k,
                    scraped_job_text=state.get("scraped_job_text", ""),
                )
            else:
                # Option A: domain-expanded query → targeted fetch_context
                from src.rag_retrieval import fetch_context, deduplicate_context
                domain_query = expand_query_for_domain(query, agent_name)
                docs = fetch_context(domain_query)
                # Also fetch with original rewritten query and merge for coverage
                if domain_query != query:
                    docs = deduplicate_context(docs + fetch_context(query))
                docs = docs[:top_k * 3]

            # Option B: generate mini-summary in parallel with other agents
            # For job_prep, enrich the summary query with scraped JD text if available
            summary_query = original_query
            if is_job_prep and state.get("scraped_job_text"):
                summary_query = state["scraped_job_text"][:1500]
            summary = generate_domain_summary(summary_query, agent_name, docs[:top_k])
            result = build_agent_result(agent_name, docs[:top_k * 2], summary=summary)
            errors = []
        except Exception as e:
            print(f"[{agent_name}] Agent error: {e}")
            result = build_agent_result(agent_name, [], error=str(e))
            errors = [agent_name]

        latency_ms = int((time.time() - t0) * 1000)
        print(f"[{agent_name}] {len(result.get('docs', []))} docs, summary={bool(result.get('summary'))} in {latency_ms}ms")
        return {
            "agent_results": [result],
            "agent_trace": [{
                "agent": agent_name,
                "latency_ms": latency_ms,
                "doc_count": len(result.get("docs", [])),
                "confidence": result.get("confidence", 0.0),
                "error": result.get("error"),
            }],
            "agent_errors": errors,
        }

    _agent_node.__name__ = agent_name
    return _agent_node


career_agent = _make_specialist_agent("career_agent")
project_agent = _make_specialist_agent("project_agent")
skills_agent = _make_specialist_agent("skills_agent")
personal_agent = _make_specialist_agent("personal_agent")
job_prep_agent = _make_specialist_agent("job_prep_agent")


# ---------------------------------------------------------------------------
# Node: Grounding Guard
# ---------------------------------------------------------------------------

def _grounding_guard_node(state: MultiAgentState) -> MultiAgentState:
    """
    Fan-in node: receives merged agent_results from all parallel scorers.

    1. Merge and deduplicate documents across scorers
    2. Enforce token budget (drop from tail)
    3. Build intermediate context_docs for the rerank node

    NOTE: LLM reranking has been moved to _rerank_node (runs after this node)
    so there is exactly one rerank call per request — same as direct mode.
    """
    from src.rag_retrieval import deduplicate_context, _extract_sources

    agent_results: list[AgentResult] = state.get("agent_results", [])
    successful = [r for r in agent_results if not r.get("error")]

    print(f"[grounding_guard] fan-in: {len(agent_results)} scorer(s), {len(successful)} successful")
    if not successful:
        print("[grounding_guard] all scorers failed — no_info=True")
        state["no_info"] = True
        state["grounding_passed"] = False
        state["context_docs"] = []
        state["context"] = ""
        state["sources"] = []
        return state

    # Merge all docs, sorted by confidence (highest first)
    all_docs = []
    for result in sorted(successful, key=lambda r: r.get("confidence", 0.0), reverse=True):
        all_docs.extend(result.get("docs", []))

    # Deduplicate
    merged_docs = deduplicate_context(all_docs)

    # Enforce token budget: drop from the tail
    budget = state.get("token_budget_limit", config.get_multi_agent_token_budget())
    kept_docs = []
    token_sum = 0
    for doc in merged_docs:
        doc_tokens = estimate_token_count(doc.page_content)
        if token_sum + doc_tokens <= budget:
            kept_docs.append(doc)
            token_sum += doc_tokens
        else:
            break

    state["token_budget_used"] = token_sum
    print(f"[grounding_guard] merged {len(merged_docs)} docs → kept {len(kept_docs)} within budget ({token_sum}/{budget} tokens)")

    state["context_docs"] = kept_docs
    state["sources"] = _extract_sources(kept_docs)
    state["grounding_passed"] = True
    return state


# ---------------------------------------------------------------------------
# Node: Rerank (single LLM rerank after grounding_guard — same as direct mode)
# ---------------------------------------------------------------------------

def _rerank_node(state: MultiAgentState) -> MultiAgentState:
    """
    Single LLM rerank on the final merged, deduplicated, budget-trimmed doc set.

    Positioned after grounding_guard so there is exactly one rerank call per
    request regardless of how many scorers ran — matching direct mode's cost.
    """
    from src.rag_retrieval import rerank_documents, _extract_sources

    kept_docs = state.get("context_docs", [])
    if not kept_docs or state.get("no_info"):
        state["context"] = ""
        return state

    query = state.get("rewritten_query") or state.get("query", "")
    top_k = config.get_top_k()

    if len(kept_docs) > 1 and query:
        try:
            kept_docs = rerank_documents(query, kept_docs, top_k=top_k)
            state["context_docs"] = kept_docs
            state["sources"] = _extract_sources(kept_docs)
        except Exception as e:
            print(f"[rerank] warning (non-fatal): {e}")

    state["context"] = "\n\n".join(doc.page_content for doc in kept_docs)
    print(f"[rerank] final context: {len(kept_docs)} docs")
    return state


# ---------------------------------------------------------------------------
# Node: Synthesis
# ---------------------------------------------------------------------------

def _build_synthesis_inputs(state: MultiAgentState) -> tuple[str, str]:
    """
    Returns (synthesis_prompt_str, human_message_content).

    When job_mode is active and the user sent a URL (or raw JD), the raw query is
    not useful to pass to the LLM — it can't browse URLs and a pasted JD is already
    in scraped_job_text / merged_context.  We replace it with a plain-language task.
    We also append the scraped JD to the merged_context so synthesis sees the full JD.
    """
    raw_query = state["query"]
    scraped = state.get("scraped_job_text", "")
    job_mode = state.get("job_mode", False)

    # Build effective question shown to the LLM
    if job_mode and scraped:
        effective_query = (
            "Based on the scraped job description below and my background, "
            "assess how well I fit this role and highlight the most relevant experience."
        )
    elif job_mode and len(raw_query) > 200:
        # User pasted a raw JD without a URL
        effective_query = (
            "Based on the job description I provided and my background, "
            "assess how well I fit this role and highlight the most relevant experience."
        )
    else:
        effective_query = raw_query

    # Merged context: knowledge base docs (already in state["context"])
    # For job mode, prepend the scraped JD so synthesis can reason about requirements
    merged_context = state.get("context", "")
    if job_mode and scraped:
        merged_context = f"=== Job Description (scraped) ===\n{scraped[:3000]}\n\n=== Candidate Knowledge Base ===\n{merged_context}"

    agent_summaries = format_agent_summaries(state.get("agent_results", []))
    synthesis_prompt = get_prompt("SYNTHESIS_AGENT_PROMPT").format(
        agent_summaries=agent_summaries,
        merged_context=merged_context,
        query=effective_query,
    )
    return synthesis_prompt, effective_query


def _synthesis_node(state: MultiAgentState) -> MultiAgentState:
    """
    Non-streaming synthesis: generates the final answer from merged multi-agent context.
    Used for the non-streaming /api/chat endpoint path.
    """
    if state.get("no_info") or not state.get("context"):
        state["no_info"] = True
        state["answer"] = ""
        return state

    synthesis_prompt, human_msg = _build_synthesis_inputs(state)

    llm = ChatOpenAI(model=config.get_generator_model())
    messages = [SystemMessage(content=synthesis_prompt)]
    messages.extend(convert_to_messages(state["history"]))
    messages.append(HumanMessage(content=human_msg))

    try:
        response = llm.invoke(messages)
        raw = response.content or ""
        state["no_info"] = "[[NO_INFO]]" in raw
        state["answer"] = raw.replace("[[NO_INFO]]", "").strip()
        state["synthesis_model"] = config.get_generator_model()
    except Exception as e:
        print(f"[synthesis] Error: {e}")
        state["no_info"] = True
        state["answer"] = ""

    # Self-check now that we have an actual answer
    if config.get_self_check_enabled() and state.get("answer") and state.get("context"):
        try:
            from src.rag_retrieval import _self_check_answer
            check_result = _self_check_answer(state["answer"], state["context"])
            if check_result.get("severity") == "high":
                state["grounding_passed"] = False
                state["grounding_issues"] = check_result.get("issues", [])
        except Exception:
            pass

    return state


def _synthesis_tl_node(state: MultiAgentState) -> MultiAgentState:
    """
    Streaming synthesis node that reads its token queue from thread-local storage.
    This allows the streaming graph to be compiled once and cached as a singleton:
    each call sets _tl.token_queue before invoking the graph, then this node picks it up.
    """
    token_queue: queue_module.Queue | None = getattr(_tl, "token_queue", None)
    if token_queue is None:
        # No queue set — fall back to non-streaming synthesis (safety guard)
        return _synthesis_node(state)

    if state.get("no_info") or not state.get("context"):
        print("[synthesis] no context available — skipping")
        state["no_info"] = True
        state["answer"] = ""
        token_queue.put(None)
        return state

    print(f"[synthesis] generating answer with model={config.get_generator_model()}")
    synthesis_prompt, human_msg = _build_synthesis_inputs(state)

    llm = ChatOpenAI(model=config.get_generator_model())
    messages = [SystemMessage(content=synthesis_prompt)]
    messages.extend(convert_to_messages(state["history"]))
    messages.append(HumanMessage(content=human_msg))

    full_text = ""
    try:
        for chunk in llm.stream(messages):
            token = chunk.content or ""
            full_text += token
            if token:
                token_queue.put({"token": token})
    except Exception as e:
        print(f"[synthesis_stream] Error: {e}")
        state["no_info"] = True

    state["no_info"] = "[[NO_INFO]]" in full_text
    state["answer"] = full_text.replace("[[NO_INFO]]", "").strip()
    state["synthesis_model"] = config.get_generator_model()
    print(f"[synthesis] done — {len(state['answer'])} chars, no_info={state['no_info']}")
    token_queue.put(None)  # sentinel
    return state


# ---------------------------------------------------------------------------
# Node: Trace Logger
# ---------------------------------------------------------------------------

def _trace_log_node(state: MultiAgentState) -> MultiAgentState:
    """
    Non-blocking trace logger. Writes to agent_run_traces Supabase table if
    MULTI_AGENT_LOG_TRACES=true. Always runs last in the graph.
    """
    if not config.get_multi_agent_log_traces():
        return state

    def _write_trace():
        try:
            from utils.supabase_client import supabase_client as sb
            trace = {
                "run_id": state.get("graph_run_id", str(uuid.uuid4())),
                "thread_id": state.get("checkpoint_thread_id"),
                "query": state.get("query", ""),
                "active_agents": json.dumps(state.get("active_agents", [])),
                "agent_results": json.dumps([
                    {k: v for k, v in r.items() if k != "docs"}
                    for r in state.get("agent_results", [])
                ]),
                "grounding_passed": state.get("grounding_passed", True),
                "synthesis_model": state.get("synthesis_model", ""),
                "token_budget_used": state.get("token_budget_used", 0),
                "no_info": state.get("no_info", False),
            }
            sb.table("agent_run_traces").insert(trace).execute()
        except Exception as e:
            print(f"[trace_log] Non-fatal write error: {e}")

    threading.Thread(target=_write_trace, daemon=True).start()
    return state


# ---------------------------------------------------------------------------
# Node: Notification Agent
# ---------------------------------------------------------------------------

def _notification_agent_node(state: MultiAgentState) -> MultiAgentState:
    """
    Fire-and-forget notification node. Sends an email to the owner whenever a query
    could not be answered (no_info=True) — either because the knowledge base lacks
    the information or because the evaluator rejected the generated answer.

    Always runs last (after trace_log) so it has the final state.
    Non-blocking: email send happens in a background thread.
    """
    if not state.get("no_info"):
        return state

    query = state.get("query", "")
    run_id = state.get("graph_run_id", "")

    def _send():
        send_unknown_query_notification(query=query, run_id=run_id)

    threading.Thread(target=_send, daemon=True).start()
    state["notification_sent"] = True
    return state


# ---------------------------------------------------------------------------
# HITL: Human-in-the-loop interrupt node
# ---------------------------------------------------------------------------

def _await_human_review_node(state: MultiAgentState) -> MultiAgentState:
    """
    Optional interrupt node for human review. Only activates when HITL_ENABLED=true
    and the answer contains personal details flagged for review.
    Uses LangGraph interrupt() to pause the graph and persist state to checkpoint.
    """
    if not config.get_hitl_enabled():
        return state

    answer = state.get("answer", "")
    # Heuristic: flag answers that mention personal information and are longer than 100 chars
    personal_keywords = {"home", "address", "phone", "salary", "age", "birthday", "relationship"}
    answer_lower = answer.lower()
    if len(answer) > 100 and any(kw in answer_lower for kw in personal_keywords):
        try:
            from langgraph.types import interrupt
            state["human_intervention_requested"] = True
            interrupt({
                "type": "human_review",
                "answer_preview": answer[:300],
                "thread_id": state.get("checkpoint_thread_id"),
                "run_id": state.get("graph_run_id"),
            })
        except ImportError:
            pass  # LangGraph interrupt not available in this version

    return state


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_multi_agent_graph(use_checkpointing: bool = False):
    """
    Build and compile the full multi-agent StateGraph.

    Graph topology (A+B+C pattern):
        fast_router → supervisor →[Send fan-out]→ [specialist agents: domain fetch + summary]
                                                → grounding_guard → rerank → synthesis
                                                → [hitl] → trace_log → END

    LLM calls per request: rewrite (fast_router) + N×mini-summary (parallel) + rerank + synthesis
    Wall-clock: rewrite + max(agent_latency) + rerank + synthesis — same serial depth as direct mode.
    """
    graph = StateGraph(MultiAgentState)

    # Register all nodes
    graph.add_node("fast_router", _fast_router_node)
    graph.add_node("supervisor", _supervisor_node)
    graph.add_node("career_agent", career_agent)
    graph.add_node("project_agent", project_agent)
    graph.add_node("skills_agent", skills_agent)
    graph.add_node("personal_agent", personal_agent)
    graph.add_node("job_prep_agent", job_prep_agent)
    graph.add_node("grounding_guard", _grounding_guard_node)
    graph.add_node("rerank", _rerank_node)
    graph.add_node("synthesis", _synthesis_node)
    graph.add_node("hitl_review", _await_human_review_node)
    graph.add_node("trace_log", _trace_log_node)
    graph.add_node("notification_agent", _notification_agent_node)

    # Entry: fast_router → supervisor
    graph.set_entry_point("fast_router")
    graph.add_edge("fast_router", "supervisor")

    # Fan-out: supervisor → parallel scorers via Send, or directly to grounding_guard
    graph.add_conditional_edges(
        "supervisor",
        _route_to_agents,
        {
            "career_agent": "career_agent",
            "project_agent": "project_agent",
            "skills_agent": "skills_agent",
            "personal_agent": "personal_agent",
            "job_prep_agent": "job_prep_agent",
            "grounding_guard": "grounding_guard",
        },
    )

    # Fan-in: all scorers converge at grounding_guard
    for agent_name in SPECIALIST_AGENT_NAMES:
        graph.add_edge(agent_name, "grounding_guard")

    # Linear tail: grounding_guard → rerank → synthesis → hitl → trace → notify → END
    graph.add_edge("grounding_guard", "rerank")
    graph.add_edge("rerank", "synthesis")
    graph.add_edge("synthesis", "hitl_review")
    graph.add_edge("hitl_review", "trace_log")
    graph.add_edge("trace_log", "notification_agent")
    graph.add_edge("notification_agent", END)

    checkpointer = None
    if use_checkpointing:
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver
            checkpointer = SqliteSaver.from_conn_string(":memory:")
        except ImportError:
            print("[multi_agent_graph] langgraph-checkpoint-sqlite not available — skipping checkpointer")

    return graph.compile(checkpointer=checkpointer)


# Cached singletons — compiled once per process, not per request
_graph: object = None
_graph_with_checkpointing: object = None
_streaming_graph: object = None  # streaming variant with token-queue synthesis node


def _build_streaming_graph() -> object:
    """
    Build the streaming variant of the multi-agent graph.
    Uses _synthesis_tl_node which reads its token_queue from thread-local storage,
    so this graph can be compiled once and reused across all streaming calls.
    Each call sets _tl.token_queue before invoking the graph (see run_multi_agent_graph_stream).
    """
    graph = StateGraph(MultiAgentState)
    graph.add_node("fast_router", _fast_router_node)
    graph.add_node("supervisor", _supervisor_node)
    graph.add_node("career_agent", career_agent)
    graph.add_node("project_agent", project_agent)
    graph.add_node("skills_agent", skills_agent)
    graph.add_node("personal_agent", personal_agent)
    graph.add_node("job_prep_agent", job_prep_agent)
    graph.add_node("grounding_guard", _grounding_guard_node)
    graph.add_node("rerank", _rerank_node)
    graph.add_node("synthesis", _synthesis_tl_node)  # reads queue from _tl.token_queue
    graph.add_node("hitl_review", _await_human_review_node)
    graph.add_node("trace_log", _trace_log_node)
    graph.add_node("notification_agent", _notification_agent_node)

    graph.set_entry_point("fast_router")
    graph.add_edge("fast_router", "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        _route_to_agents,
        {a: a for a in SPECIALIST_AGENT_NAMES} | {"grounding_guard": "grounding_guard"},
    )
    for agent_name in SPECIALIST_AGENT_NAMES:
        graph.add_edge(agent_name, "grounding_guard")
    graph.add_edge("grounding_guard", "rerank")
    graph.add_edge("rerank", "synthesis")
    graph.add_edge("synthesis", "hitl_review")
    graph.add_edge("hitl_review", "trace_log")
    graph.add_edge("trace_log", "notification_agent")
    graph.add_edge("notification_agent", END)
    return graph.compile()


def get_multi_agent_graph():
    """Return cached compiled graph (no checkpointing)."""
    global _graph
    if _graph is None:
        _graph = build_multi_agent_graph(use_checkpointing=False)
    return _graph


def get_multi_agent_graph_with_checkpointing():
    """Return cached compiled graph with SQLite checkpointing for HITL."""
    global _graph_with_checkpointing
    if _graph_with_checkpointing is None:
        _graph_with_checkpointing = build_multi_agent_graph(use_checkpointing=True)
    return _graph_with_checkpointing


def get_streaming_graph():
    """Return cached streaming graph (uses _synthesis_tl_node, compiled once)."""
    global _streaming_graph
    if _streaming_graph is None:
        _streaming_graph = _build_streaming_graph()
    return _streaming_graph


# ---------------------------------------------------------------------------
# Public interfaces
# ---------------------------------------------------------------------------

def run_multi_agent_graph(
    query: str,
    history: list = [],
    thread_id: str | None = None,
    job_mode: bool = False,
) -> tuple:
    """
    Run the multi-agent graph (non-streaming).
    Returns (answer, context_docs, no_info, sources) — same signature as run_graph().
    """
    use_hitl = config.get_hitl_enabled()
    g = get_multi_agent_graph_with_checkpointing() if use_hitl else get_multi_agent_graph()
    initial = build_initial_multi_agent_state(query, history, thread_id or str(uuid.uuid4()), job_mode=job_mode)
    run_config = {"configurable": {"thread_id": initial["checkpoint_thread_id"]}} if use_hitl else {}
    result = g.invoke(initial, config=run_config)
    return result["answer"], result["context_docs"], result["no_info"], result["sources"]


def run_multi_agent_graph_stream(
    query: str,
    history: list = [],
    thread_id: str | None = None,
    job_mode: bool = False,
):
    """
    Generator that yields SSE-compatible dicts for the multi-agent graph.

    Uses a cached streaming graph (compiled once). Each call injects a fresh
    token_queue into thread-local storage; _synthesis_tl_node reads from there.
    No graph rebuild per request.

    Event types:
      {"token": str}                                                     — synthesis tokens
      {"done": True, "no_info": bool, "final": str, "sources": list,
       "agent_trace": list}                                              — terminal event
    """
    token_queue: queue_module.Queue = queue_module.Queue()
    result_container: dict = {}
    initial = build_initial_multi_agent_state(query, history, thread_id or str(uuid.uuid4()), job_mode=job_mode)

    def _run_graph():
        # Set queue on the background thread's thread-local before invoking
        _tl.token_queue = token_queue
        try:
            result = get_streaming_graph().invoke(initial)
            result_container["state"] = result
        finally:
            _tl.token_queue = None

    bg_thread = threading.Thread(target=_run_graph, daemon=True)
    bg_thread.start()

    while True:
        item = token_queue.get(timeout=120)
        if item is None:
            break
        yield item

    bg_thread.join(timeout=5)
    final_state = result_container.get("state", {})
    yield {
        "done": True,
        "no_info": final_state.get("no_info", True),
        "final": final_state.get("answer", ""),
        "sources": final_state.get("sources", []),
        "agent_trace": final_state.get("agent_trace", []),
    }


def get_graph_topology() -> dict:
    """
    Return the multi-agent graph topology as a JSON-serialisable dict.
    Used by GET /api/agent/graph for visualisation and interview demos.
    """
    return {
        "nodes": [
            {"id": "fast_router", "type": "classifier", "description": "Regex-based domain routing (no LLM) + query rewrite (1 LLM call)"},
            {"id": "supervisor", "type": "orchestrator", "description": "Initialises run and dispatches agents in parallel"},
            {"id": "career_agent", "type": "specialist", "domain": "career", "description": "A: domain query expansion → fetch_context; B: mini-summary via cheap LLM (parallel)"},
            {"id": "project_agent", "type": "specialist", "domain": "project", "description": "A: domain query expansion → fetch_context; B: mini-summary via cheap LLM (parallel)"},
            {"id": "skills_agent", "type": "specialist", "domain": "skills", "description": "A: domain query expansion → fetch_context; B: mini-summary via cheap LLM (parallel)"},
            {"id": "personal_agent", "type": "specialist", "domain": "personal", "description": "A: domain query expansion → fetch_context; B: mini-summary via cheap LLM (parallel)"},
            {"id": "job_prep_agent", "type": "specialist", "domain": "job_prep", "description": "C: extract_job_requirements → requirement-targeted fetch; B: fit-signal summary"},
            {"id": "grounding_guard", "type": "guard", "description": "Merge agent doc sets, dedup, token budget enforcement"},
            {"id": "rerank", "type": "reranker", "description": "Single LLM rerank on merged final set"},
            {"id": "synthesis", "type": "generator", "description": "Structured synthesis from per-domain summaries + merged context"},
            {"id": "hitl_review", "type": "interrupt", "description": "Human-in-the-loop review (when HITL_ENABLED=true)"},
            {"id": "trace_log", "type": "logger", "description": "Async trace write to agent_run_traces"},
            {"id": "notification_agent", "type": "notifier", "description": "Fire-and-forget email notification to owner when query is unanswerable"},
        ],
        "edges": [
            {"from": "fast_router", "to": "supervisor", "type": "always"},
            {"from": "supervisor", "to": "career_agent", "type": "conditional_fan_out"},
            {"from": "supervisor", "to": "project_agent", "type": "conditional_fan_out"},
            {"from": "supervisor", "to": "skills_agent", "type": "conditional_fan_out"},
            {"from": "supervisor", "to": "personal_agent", "type": "conditional_fan_out"},
            {"from": "supervisor", "to": "job_prep_agent", "type": "conditional_fan_out"},
            {"from": "supervisor", "to": "grounding_guard", "type": "fallback"},
            {"from": "career_agent", "to": "grounding_guard", "type": "fan_in"},
            {"from": "project_agent", "to": "grounding_guard", "type": "fan_in"},
            {"from": "skills_agent", "to": "grounding_guard", "type": "fan_in"},
            {"from": "personal_agent", "to": "grounding_guard", "type": "fan_in"},
            {"from": "job_prep_agent", "to": "grounding_guard", "type": "fan_in"},
            {"from": "grounding_guard", "to": "rerank", "type": "always"},
            {"from": "rerank", "to": "synthesis", "type": "always"},
            {"from": "synthesis", "to": "hitl_review", "type": "always"},
            {"from": "hitl_review", "to": "trace_log", "type": "always"},
            {"from": "trace_log", "to": "notification_agent", "type": "always"},
            {"from": "notification_agent", "to": "END", "type": "always"},
        ],
        "config": {
            "parallel_enabled": config.get_multi_agent_parallel(),
            "token_budget": config.get_multi_agent_token_budget(),
            "hitl_enabled": config.get_hitl_enabled(),
            "log_traces": config.get_multi_agent_log_traces(),
        },
    }
