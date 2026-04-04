"""
Multi-agent conversation graph for MyBestFriend.

Activated when USE_MULTI_AGENT=true in config. Implements:
  intent_classifier → supervisor → [parallel domain agents] → grounding_guard → synthesis → trace_log

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
    search_knowledge_by_domain,
    build_agent_result,
    is_loop_detected,
    format_agent_summary,
    estimate_token_count,
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
# Node: Intent Classifier
# ---------------------------------------------------------------------------

def _intent_classifier_node(state: MultiAgentState) -> MultiAgentState:
    """
    Classify the user's query into domains and decide which agents to activate.
    Uses structured output (IntentResult) to ensure parseable JSON response.
    """
    from src.agent_state import IntentResult
    from src.rag_retrieval import rewrite_query

    if is_loop_detected(state):
        state["no_info"] = True
        return state

    # Reuse existing query rewriting for better search
    rewritten = rewrite_query(state["query"], state["history"])
    state["rewritten_query"] = rewritten

    llm = ChatOpenAI(model=config.get_rewrite_model(), temperature=0)
    llm_structured = llm.with_structured_output(IntentResult)

    prompt = get_prompt("INTENT_CLASSIFIER_PROMPT").format(query=state["query"])
    try:
        result: IntentResult = llm_structured.invoke([HumanMessage(content=prompt)])
        state["intent"] = {
            "primary_domain": result.primary_domain,
            "requires_agents": result.requires_agents,
            "entities": result.entities,
            "confidence": result.confidence,
        }
    except Exception as e:
        print(f"[intent_classifier] Error: {e} — defaulting to all domain agents")
        state["intent"] = {
            "primary_domain": "general",
            "requires_agents": ["career_agent", "project_agent", "skills_agent", "personal_agent"],
            "entities": {},
            "confidence": 0.5,
        }

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

    state["token_budget_limit"] = config.get_multi_agent_token_budget()
    state["token_budget_used"] = 0
    state["agent_results"] = []
    state["agent_trace"] = []
    state["agent_errors"] = []
    state["active_agents"] = state.get("intent", {}).get("requires_agents", [])
    state["graph_run_id"] = str(uuid.uuid4())
    return state


# ---------------------------------------------------------------------------
# Specialist agent factory
# ---------------------------------------------------------------------------

def _make_specialist_agent(agent_name: str) -> Callable[[MultiAgentState], MultiAgentState]:
    """
    Returns a node function for a domain specialist agent.
    Each agent: retrieves domain-scoped docs → reranks → builds AgentResult → appends to state.
    Wrapped in try/except so a single agent failure never kills the whole graph.
    """
    def _agent_node(state: MultiAgentState) -> MultiAgentState:
        if is_loop_detected(state):
            return state

        t0 = time.time()
        query = state.get("rewritten_query") or state["query"]
        top_k = config.get_top_k()

        try:
            docs = search_knowledge_by_domain(query, agent_name, top_k=top_k)
            result = build_agent_result(agent_name, docs)
        except Exception as e:
            print(f"[{agent_name}] Retrieval error: {e}")
            result = build_agent_result(agent_name, [], error=str(e))
            state["agent_errors"] = [agent_name]

        latency_ms = int((time.time() - t0) * 1000)
        state["agent_results"] = [result]
        state["agent_trace"] = [{
            "agent": agent_name,
            "latency_ms": latency_ms,
            "doc_count": len(result.get("docs", [])),
            "confidence": result.get("confidence", 0.0),
            "error": result.get("error"),
        }]
        return state

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
    Fan-in node: receives merged agent_results from all parallel agents.

    1. Merge and deduplicate documents across agents
    2. Enforce token budget (drop lowest-confidence docs first)
    3. Run self-check on merged context
    4. Build final context_docs, context, sources for synthesis
    """
    from src.rag_retrieval import deduplicate_context, _extract_sources

    agent_results: list[AgentResult] = state.get("agent_results", [])
    successful = [r for r in agent_results if not r.get("error")]

    if not successful:
        # All agents failed — no context available
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

    # Deduplicate using existing function
    merged_docs = deduplicate_context(all_docs)

    # Enforce token budget: drop from the tail (lowest confidence / relevance)
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

    # Build final context
    merged_context = "\n\n".join(doc.page_content for doc in kept_docs)
    state["context_docs"] = kept_docs
    state["context"] = merged_context
    state["sources"] = _extract_sources(kept_docs)

    # Optional: run self-check on merged context if SELF_CHECK_ENABLED
    if config.get_self_check_enabled() and merged_context:
        try:
            from src.rag_retrieval import _self_check_answer
            check_result = _self_check_answer("", merged_context)
            if check_result.get("severity") == "high":
                state["grounding_passed"] = False
                state["grounding_issues"] = check_result.get("issues", [])
            else:
                state["grounding_passed"] = True
        except Exception:
            state["grounding_passed"] = True
    else:
        state["grounding_passed"] = True

    return state


# ---------------------------------------------------------------------------
# Node: Synthesis
# ---------------------------------------------------------------------------

def _synthesis_node(state: MultiAgentState) -> MultiAgentState:
    """
    Non-streaming synthesis: generates the final answer from merged multi-agent context.
    Used for the non-streaming /api/chat endpoint path.
    """
    if state.get("no_info") or not state.get("context"):
        state["no_info"] = True
        state["answer"] = ""
        return state

    agent_context = format_agent_summary(state.get("agent_results", []))
    synthesis_prompt = get_prompt("SYNTHESIS_AGENT_PROMPT").format(
        agent_context=agent_context,
        query=state["query"],
    )

    llm = ChatOpenAI(model=config.get_generator_model())
    messages = [SystemMessage(content=synthesis_prompt)]
    messages.extend(convert_to_messages(state["history"]))
    messages.append(HumanMessage(content=state["query"]))

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
        state["no_info"] = True
        state["answer"] = ""
        token_queue.put(None)
        return state

    agent_context = format_agent_summary(state.get("agent_results", []))
    synthesis_prompt = get_prompt("SYNTHESIS_AGENT_PROMPT").format(
        agent_context=agent_context,
        query=state["query"],
    )

    llm = ChatOpenAI(model=config.get_generator_model())
    messages = [SystemMessage(content=synthesis_prompt)]
    messages.extend(convert_to_messages(state["history"]))
    messages.append(HumanMessage(content=state["query"]))

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

    Graph topology:
        intent_classifier → supervisor →[Send fan-out]→ [specialist agents]
                                                       → grounding_guard
                                                       → synthesis → [hitl] → trace_log → END
    """
    graph = StateGraph(MultiAgentState)

    # Register all nodes
    graph.add_node("intent_classifier", _intent_classifier_node)
    graph.add_node("supervisor", _supervisor_node)
    graph.add_node("career_agent", career_agent)
    graph.add_node("project_agent", project_agent)
    graph.add_node("skills_agent", skills_agent)
    graph.add_node("personal_agent", personal_agent)
    graph.add_node("job_prep_agent", job_prep_agent)
    graph.add_node("grounding_guard", _grounding_guard_node)
    graph.add_node("synthesis", _synthesis_node)
    graph.add_node("hitl_review", _await_human_review_node)
    graph.add_node("trace_log", _trace_log_node)

    # Entry point
    graph.set_entry_point("intent_classifier")
    graph.add_edge("intent_classifier", "supervisor")

    # Fan-out: supervisor → parallel agents via Send, or directly to grounding_guard
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

    # Fan-in: all agents converge at grounding_guard
    for agent_name in SPECIALIST_AGENT_NAMES:
        graph.add_edge(agent_name, "grounding_guard")

    # Linear tail
    graph.add_edge("grounding_guard", "synthesis")
    graph.add_edge("synthesis", "hitl_review")
    graph.add_edge("hitl_review", "trace_log")
    graph.add_edge("trace_log", END)

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
    graph.add_node("intent_classifier", _intent_classifier_node)
    graph.add_node("supervisor", _supervisor_node)
    graph.add_node("career_agent", career_agent)
    graph.add_node("project_agent", project_agent)
    graph.add_node("skills_agent", skills_agent)
    graph.add_node("personal_agent", personal_agent)
    graph.add_node("job_prep_agent", job_prep_agent)
    graph.add_node("grounding_guard", _grounding_guard_node)
    graph.add_node("synthesis", _synthesis_tl_node)  # reads queue from _tl.token_queue
    graph.add_node("hitl_review", _await_human_review_node)
    graph.add_node("trace_log", _trace_log_node)

    graph.set_entry_point("intent_classifier")
    graph.add_edge("intent_classifier", "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        _route_to_agents,
        {a: a for a in SPECIALIST_AGENT_NAMES} | {"grounding_guard": "grounding_guard"},
    )
    for agent_name in SPECIALIST_AGENT_NAMES:
        graph.add_edge(agent_name, "grounding_guard")
    graph.add_edge("grounding_guard", "synthesis")
    graph.add_edge("synthesis", "hitl_review")
    graph.add_edge("hitl_review", "trace_log")
    graph.add_edge("trace_log", END)
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
) -> tuple:
    """
    Run the multi-agent graph (non-streaming).
    Returns (answer, context_docs, no_info, sources) — same signature as run_graph().
    """
    use_hitl = config.get_hitl_enabled()
    g = get_multi_agent_graph_with_checkpointing() if use_hitl else get_multi_agent_graph()
    initial = build_initial_multi_agent_state(query, history, thread_id or str(uuid.uuid4()))
    run_config = {"configurable": {"thread_id": initial["checkpoint_thread_id"]}} if use_hitl else {}
    result = g.invoke(initial, config=run_config)
    return result["answer"], result["context_docs"], result["no_info"], result["sources"]


def run_multi_agent_graph_stream(
    query: str,
    history: list = [],
    thread_id: str | None = None,
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
    initial = build_initial_multi_agent_state(query, history, thread_id or str(uuid.uuid4()))

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
            {"id": "intent_classifier", "type": "classifier", "description": "Classifies query intent and selects agents"},
            {"id": "supervisor", "type": "orchestrator", "description": "Initialises run and dispatches agents"},
            {"id": "career_agent", "type": "specialist", "domain": "career", "description": "Career and work history retrieval"},
            {"id": "project_agent", "type": "specialist", "domain": "project", "description": "Software project retrieval"},
            {"id": "skills_agent", "type": "specialist", "domain": "skills", "description": "Skills, CV, and education retrieval"},
            {"id": "personal_agent", "type": "specialist", "domain": "personal", "description": "Personal background retrieval"},
            {"id": "job_prep_agent", "type": "specialist", "domain": "job_prep", "description": "Job preparation context retrieval"},
            {"id": "grounding_guard", "type": "guard", "description": "Dedup, token budget, self-check, fan-in"},
            {"id": "synthesis", "type": "generator", "description": "Multi-source synthesis with source attribution"},
            {"id": "hitl_review", "type": "interrupt", "description": "Human-in-the-loop review (when HITL_ENABLED=true)"},
            {"id": "trace_log", "type": "logger", "description": "Async trace write to agent_run_traces"},
        ],
        "edges": [
            {"from": "intent_classifier", "to": "supervisor", "type": "always"},
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
            {"from": "grounding_guard", "to": "synthesis", "type": "always"},
            {"from": "synthesis", "to": "hitl_review", "type": "always"},
            {"from": "hitl_review", "to": "trace_log", "type": "always"},
            {"from": "trace_log", "to": "END", "type": "always"},
        ],
        "config": {
            "parallel_enabled": config.get_multi_agent_parallel(),
            "token_budget": config.get_multi_agent_token_budget(),
            "hitl_enabled": config.get_hitl_enabled(),
            "log_traces": config.get_multi_agent_log_traces(),
        },
    }
