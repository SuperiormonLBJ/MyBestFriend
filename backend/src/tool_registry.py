"""
Unified tool registry for the multi-agent system.

Single source of truth for all tool definitions — used by:
  - ReAct specialist agents (via LangChain tool-calling)
  - MCP server (exposed via stdio protocol)
  - API endpoints (direct invocation)

Each tool wraps existing functions from rag_retrieval.py, twin_tools.py, and agent_tools.py.
"""
import json
import utils.path_setup  # noqa: F401

from langchain_core.tools import tool


# ---------------------------------------------------------------------------
# Knowledge retrieval tools
# ---------------------------------------------------------------------------

@tool
def search_knowledge(query: str, doc_type: str = "", top_k: int = 5) -> str:
    """Search the knowledge base for information about the owner.
    Returns relevant document chunks with source attribution.
    Use this as the primary retrieval tool for any question.

    Args:
        query: The search query or question.
        doc_type: Optional filter: career, project, cv, personal, education, or empty for all.
        top_k: Number of results to return (default 5, max 10).
    """
    from src.rag_retrieval import fetch_context, _apply_metadata_boost, rerank_documents

    top_k = min(int(top_k), 10)
    docs = fetch_context(query)

    if doc_type:
        docs = _apply_metadata_boost(docs, {"doc_type": doc_type, "year": None})

    reranked = rerank_documents(query, docs, top_k=top_k)

    results = []
    for doc in reranked:
        meta = doc.metadata or {}
        results.append({
            "content": doc.page_content,
            "source": meta.get("source", ""),
            "doc_type": meta.get("doc_type", ""),
            "year": str(meta.get("year", "")),
            "section": meta.get("section", ""),
            "title": meta.get("title", ""),
        })

    return json.dumps({"query": query, "results": results, "count": len(results)})


@tool
def get_time_period_summary(year: str) -> str:
    """Get a summary of everything known about a specific year.
    Useful for 'what did you do in 2023?' style queries.

    Args:
        year: 4-digit year string, e.g. '2023'.
    """
    from src.twin_tools import summarize_time_period
    summary = summarize_time_period(str(year))
    return json.dumps({"year": year, "summary": summary})


@tool
def list_domain_items(domain: str) -> str:
    """List all items (titles and years) in a specific knowledge domain.
    Useful for 'list all projects' or 'what jobs have you had?' queries.

    Args:
        domain: Domain to list. One of: projects, jobs, skills, education, hobbies, personal.
    """
    from src.twin_tools import list_domain_items as _list_domain_items
    items = _list_domain_items(domain)
    return json.dumps({"domain": domain, "items": items, "count": len(items)})


@tool
def get_knowledge_scope() -> str:
    """Get an overview of what topics and time periods the knowledge base covers.
    Returns document type counts and year range.
    Use this to understand what knowledge is available before making specific queries."""
    from src.twin_tools import get_knowledge_scope as _get_knowledge_scope
    return json.dumps(_get_knowledge_scope())


# ---------------------------------------------------------------------------
# Bio generation tool
# ---------------------------------------------------------------------------

@tool
def generate_structured_bio(style: str = "professional", focus_area: str = "") -> str:
    """Generate a short bio in the specified style.
    Retrieves relevant context automatically and returns a bio prompt.

    Args:
        style: Bio style — professional, casual, or conference.
        focus_area: Optional focus area to emphasise, e.g. 'AI engineering'.
    """
    from src.twin_tools import generate_bio

    query = "professional background experience skills"
    if focus_area:
        query = f"{focus_area} {query}"

    context_result = json.loads(search_knowledge.invoke({"query": query, "top_k": 5}))
    context = "\n\n".join(r["content"] for r in context_result.get("results", []))

    bio_prompt = generate_bio(context, style)
    return json.dumps({"style": style, "bio_prompt": bio_prompt, "context_used": len(context)})


# ---------------------------------------------------------------------------
# Job tools
# ---------------------------------------------------------------------------

@tool
def fetch_job_description(url: str) -> str:
    """Scrape and extract job description text from a job posting URL.
    Supports LinkedIn, Greenhouse, Lever, Workday, and most public job boards.
    Returns empty text if the page requires login.

    Args:
        url: Full URL of the job posting.
    """
    from src.agent_tools import scrape_job_description
    text = scrape_job_description(url)
    return json.dumps({"url": url, "text": text, "char_count": len(text), "success": len(text) > 100})


@tool
def extract_job_fit_signals(job_description: str) -> str:
    """Analyse a job description against the knowledge base.
    Returns technical requirements, culture signals, keywords,
    and relevant experience from the knowledge base.

    Args:
        job_description: The full job description text.
    """
    from src.rag_retrieval import extract_job_requirements, get_job_context

    reqs = extract_job_requirements(job_description)
    _, context = get_job_context(job_description, reqs)

    return json.dumps({
        "technical_requirements": reqs.get("technical_requirements", []),
        "culture": reqs.get("culture", []),
        "keywords": reqs.get("keywords", []),
        "relevant_experience_context": context[:3000] if context else "",
    })


@tool
def score_job_fit(job_description: str, top_k: int = 5) -> str:
    """Score how well the owner fits a given job description.
    Extracts requirements, retrieves matching experience, and returns a 0-100 fit score.

    Args:
        job_description: The full job description text.
        top_k: Number of KB docs to retrieve for matching (default 5).
    """
    from src.agent_tools import score_job_fit as _score_job_fit
    result = _score_job_fit(job_description=job_description, top_k=int(top_k))
    return json.dumps(result)


@tool
def search_recent_jobs(keywords: list[str], hours: int = 24) -> str:
    """Search for recent job postings from public job boards (Arbeitnow, RemoteOK).
    No API key required. Filter by keywords and time window.

    Args:
        keywords: Search keywords, e.g. ['machine learning', 'python'].
        hours: Only return jobs posted within this many hours (default 24).
    """
    from src.agent_tools import search_recent_jobs as _search_recent_jobs
    jobs = _search_recent_jobs(keywords=keywords, hours=int(hours))
    return json.dumps({"jobs": jobs, "count": len(jobs)})


# ---------------------------------------------------------------------------
# Registry helpers
# ---------------------------------------------------------------------------

ALL_TOOLS = [
    search_knowledge,
    get_time_period_summary,
    list_domain_items,
    get_knowledge_scope,
    generate_structured_bio,
    fetch_job_description,
    extract_job_fit_signals,
    score_job_fit,
    search_recent_jobs,
]

TOOL_MAP: dict[str, object] = {t.name: t for t in ALL_TOOLS}


def get_tools_by_names(names: list[str]) -> list:
    """Return a subset of tools by name."""
    return [TOOL_MAP[n] for n in names if n in TOOL_MAP]
