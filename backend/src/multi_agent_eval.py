"""
Multi-agent evaluation metrics for MyBestFriend.

Adds 5 new metrics beyond single-turn RAGAS to measure multi-agent system quality:

1. Agent Routing Accuracy (ARA) — are the right agents activated?
2. Agent Context Redundancy Ratio (ACRR) — are agents retrieving diverse docs?
3. Per-Agent MRR — which agent is the weakest retriever?
4. Synthesis Faithfulness — is the final answer grounded in merged context?
5. Parallel Efficiency — how well does parallelism reduce latency?

Usage:
    from src.multi_agent_eval import evaluate_multi_agent_all
    report = evaluate_multi_agent_all(test_questions)
"""
import sys
import time
import utils.path_setup  # noqa: F401

from utils.base_models import TestQuestion, MultiAgentEvalResult, AgentRoutingEval
from src.multi_agent_graph import run_multi_agent_graph
from src.agent_state import MultiAgentState


# ---------------------------------------------------------------------------
# Agent domain → expected agent mapping for routing accuracy
# ---------------------------------------------------------------------------

CATEGORY_TO_EXPECTED_AGENTS: dict[str, list[str]] = {
    "career": ["career_agent"],
    "work": ["career_agent"],
    "job": ["career_agent"],
    "project": ["project_agent"],
    "frontend": ["project_agent", "skills_agent"],
    "ai_engineering": ["project_agent", "skills_agent", "career_agent"],
    "platform_engineering": ["project_agent", "career_agent"],
    "education": ["skills_agent"],
    "skills": ["skills_agent"],
    "research": ["project_agent", "skills_agent"],
    "personality": ["personal_agent"],
    "personal": ["personal_agent"],
    "hobbies": ["personal_agent"],
}


def _get_expected_agents(question: TestQuestion) -> list[str]:
    """Return expected agent names based on question category."""
    category = (question.category or "").lower()
    for key, agents in CATEGORY_TO_EXPECTED_AGENTS.items():
        if key in category:
            return agents
    # Default: all four domain agents for uncategorised questions
    return ["career_agent", "project_agent", "skills_agent", "personal_agent"]


# ---------------------------------------------------------------------------
# Individual metric functions
# ---------------------------------------------------------------------------

def evaluate_agent_routing(
    tests: list[TestQuestion],
    traces: list[dict],
) -> tuple[float, list[AgentRoutingEval]]:
    """
    Agent Routing Accuracy (ARA):
    Fraction of test questions where at least one expected agent was activated.

    Returns (ARA_score, per_question_details).
    """
    details: list[AgentRoutingEval] = []
    correct = 0

    for test, trace in zip(tests, traces):
        expected = _get_expected_agents(test)
        activated = trace.get("active_agents", [])
        # Routing is correct if any expected agent was activated
        routing_correct = any(a in activated for a in expected)
        if routing_correct:
            correct += 1
        details.append(AgentRoutingEval(
            question=test.question,
            expected_agents=expected,
            activated_agents=activated,
            routing_correct=routing_correct,
        ))

    ara = correct / len(tests) if tests else 0.0
    return ara, details


def evaluate_agent_redundancy(traces: list[dict]) -> float:
    """
    Agent Context Redundancy Ratio (ACRR):
    |union(agent_docs)| / sum(|agent_docs_i|)

    Higher = more diverse (agents retrieved different documents).
    Lower = redundant (all agents retrieved the same docs).
    Target: > 0.60
    """
    if not traces:
        return 0.0

    acrr_values = []
    for trace in traces:
        agent_results = trace.get("agent_results", [])
        if not agent_results:
            continue

        all_docs: list[str] = []
        per_agent_counts: list[int] = []

        for result in agent_results:
            if result.get("error"):
                continue
            # Use source as doc identifier
            sources = result.get("sources", [])
            per_agent_counts.append(len(sources))
            all_docs.extend(sources)

        total = sum(per_agent_counts)
        unique = len(set(str(s) for s in all_docs))

        if total > 0:
            acrr_values.append(unique / total)

    return sum(acrr_values) / len(acrr_values) if acrr_values else 0.0


def evaluate_per_agent_mrr(
    tests: list[TestQuestion],
    traces: list[dict],
) -> dict[str, float]:
    """
    Per-agent MRR: for each agent, compute MRR across test questions.
    Measures how well each specialist's retrieved docs contain the answer keywords.

    Returns dict mapping agent_name → MRR score.
    """
    agent_mrr_scores: dict[str, list[float]] = {}

    for test, trace in zip(tests, traces):
        keywords = [kw.lower() for kw in (test.keywords or [])]
        if not keywords:
            continue

        agent_results = trace.get("agent_results", [])
        for result in agent_results:
            if result.get("error"):
                continue
            agent_name = result.get("agent_name", "unknown")
            context = result.get("context", "").lower()

            # Find rank of first keyword match in context paragraphs
            paragraphs = [p.strip() for p in context.split("\n\n") if p.strip()]
            rank = None
            for i, para in enumerate(paragraphs, start=1):
                if any(kw in para for kw in keywords):
                    rank = i
                    break

            mrr = 1.0 / rank if rank else 0.0
            if agent_name not in agent_mrr_scores:
                agent_mrr_scores[agent_name] = []
            agent_mrr_scores[agent_name].append(mrr)

    return {
        agent: sum(scores) / len(scores)
        for agent, scores in agent_mrr_scores.items()
        if scores
    }


def evaluate_synthesis_faithfulness(
    tests: list[TestQuestion],
    answers: list[str],
    contexts: list[str],
) -> float:
    """
    Synthesis faithfulness: keyword overlap between answer and merged context.
    Approximation of RAGAS faithfulness without requiring the full RAGAS pipeline.
    Returns a score 0.0–1.0.
    """
    if not tests:
        return 0.0

    scores = []
    for answer, context in zip(answers, contexts):
        if not answer or not context:
            scores.append(0.0)
            continue

        answer_words = set(answer.lower().split())
        context_words = set(context.lower().split())
        # Jaccard-based overlap: fraction of answer words found in context
        overlap = len(answer_words & context_words)
        score = overlap / max(len(answer_words), 1)
        scores.append(min(1.0, score))

    return sum(scores) / len(scores) if scores else 0.0


def evaluate_parallel_efficiency(traces: list[dict]) -> float:
    """
    Parallel efficiency: max(agent_latencies) / sum(agent_latencies).
    For N perfectly parallel agents, this approaches 1/N.
    Higher = better parallelism (agents running concurrently).
    Returns average across all traces.
    """
    if not traces:
        return 0.0

    efficiencies = []
    for trace in traces:
        agent_trace = trace.get("agent_trace", [])
        latencies = [t.get("latency_ms", 0) for t in agent_trace if t.get("latency_ms", 0) > 0]
        if len(latencies) >= 2:
            max_lat = max(latencies)
            sum_lat = sum(latencies)
            if sum_lat > 0:
                efficiencies.append(max_lat / sum_lat)

    return sum(efficiencies) / len(efficiencies) if efficiencies else 0.0


# ---------------------------------------------------------------------------
# Full evaluation suite
# ---------------------------------------------------------------------------

def evaluate_multi_agent_run(
    query: str,
    history: list = [],
) -> dict:
    """
    Run a single test through the multi-agent graph and return a trace dict
    with all information needed for metric computation.
    """
    from src.agent_state import build_initial_multi_agent_state
    from src.multi_agent_graph import get_multi_agent_graph

    g = get_multi_agent_graph()
    initial = build_initial_multi_agent_state(query, history)
    result = g.invoke(initial)

    return {
        "answer": result.get("answer", ""),
        "no_info": result.get("no_info", True),
        "sources": result.get("sources", []),
        "context": result.get("context", ""),
        "active_agents": result.get("active_agents", []),
        "agent_results": [
            {k: v for k, v in r.items() if k != "docs"}
            for r in result.get("agent_results", [])
        ],
        "agent_trace": result.get("agent_trace", []),
        "token_budget_used": result.get("token_budget_used", 0),
    }


def evaluate_multi_agent_all(tests: list[TestQuestion]) -> MultiAgentEvalResult:
    """
    Run the full multi-agent evaluation suite against all test questions.

    For each question: runs the multi-agent graph and collects traces.
    Then computes all 5 metrics and returns a MultiAgentEvalResult.
    """
    print(f"[multi_agent_eval] Running evaluation on {len(tests)} questions...")

    traces: list[dict] = []
    answers: list[str] = []
    contexts: list[str] = []

    for i, test in enumerate(tests):
        print(f"[multi_agent_eval] Question {i+1}/{len(tests)}: {test.question[:60]}...")
        try:
            trace = evaluate_multi_agent_run(test.question)
            traces.append(trace)
            answers.append(trace.get("answer", ""))
            contexts.append(trace.get("context", ""))
        except Exception as e:
            print(f"[multi_agent_eval] Error on question {i+1}: {e}")
            traces.append({})
            answers.append("")
            contexts.append("")

    # Compute all metrics
    ara, routing_details = evaluate_agent_routing(tests, traces)
    acrr = evaluate_agent_redundancy(traces)
    per_agent_mrr = evaluate_per_agent_mrr(tests, traces)
    faithfulness = evaluate_synthesis_faithfulness(tests, answers, contexts)
    parallel_efficiency = evaluate_parallel_efficiency(traces)

    print(f"[multi_agent_eval] Complete:")
    print(f"  ARA={ara:.3f} | ACRR={acrr:.3f} | Faithfulness={faithfulness:.3f}")
    print(f"  Per-agent MRR: {per_agent_mrr}")
    print(f"  Parallel efficiency: {parallel_efficiency:.3f}")

    return MultiAgentEvalResult(
        agent_routing_accuracy=round(ara, 4),
        agent_context_redundancy_ratio=round(acrr, 4),
        per_agent_mrr={k: round(v, 4) for k, v in per_agent_mrr.items()},
        synthesis_faithfulness=round(faithfulness, 4),
        parallel_efficiency=round(parallel_efficiency, 4),
        total_questions=len(tests),
        routing_details=routing_details,
    )
