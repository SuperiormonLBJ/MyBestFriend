"""
MCP server for MyBestFriend digital twin.

Exposes the twin's knowledge base as 6 typed MCP tools, making it composable
with any MCP-compatible client (Claude Desktop, other LLMs, MCP inspector).

Run in stdio mode:
    uv run python -m src.mcp_server

Register with Claude Desktop by adding to claude_desktop_config.json:
    {
      "mcpServers": {
        "mybestfriend": {
          "command": "uv",
          "args": ["run", "--project", "/path/to/backend", "python", "-m", "src.mcp_server"]
        }
      }
    }

All tools wrap existing functions from rag_retrieval.py and twin_tools.py —
no new retrieval logic is introduced here.
"""
import asyncio
import json
import utils.path_setup  # noqa: F401

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

server = Server("mybestfriend-twin")


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="search_knowledge",
            description=(
                "Search the twin's knowledge base using semantic + lexical hybrid search. "
                "Returns relevant document chunks with source attribution. "
                "Use this as the primary retrieval tool for any question about the twin."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query or question",
                    },
                    "doc_type": {
                        "type": "string",
                        "description": "Optional filter hint: career, project, cv, personal, education",
                        "enum": ["career", "project", "cv", "personal", "education", ""],
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return (default 5, max 10)",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="get_time_period_summary",
            description=(
                "Return all knowledge base content for a specific year. "
                "Useful for 'what did you do in 2023?' style queries."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "year": {
                        "type": "string",
                        "description": "4-digit year, e.g. '2023'",
                        "pattern": "^\\d{4}$",
                    },
                },
                "required": ["year"],
            },
        ),
        types.Tool(
            name="list_domain_items",
            description=(
                "List all items (titles + years) in a specific knowledge domain. "
                "Useful for 'list all projects' or 'what jobs have you had?' queries."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "Domain to list",
                        "enum": ["projects", "jobs", "skills", "education", "hobbies", "personal"],
                    },
                },
                "required": ["domain"],
            },
        ),
        types.Tool(
            name="get_knowledge_scope",
            description=(
                "Return metadata about the twin's knowledge base: "
                "document type counts and year range. "
                "Use this before making queries to understand what knowledge is available."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        types.Tool(
            name="generate_structured_bio",
            description=(
                "Generate a short bio in the specified style "
                "(professional, casual, or conference speaker). "
                "Retrieves relevant context automatically."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "style": {
                        "type": "string",
                        "description": "Bio style",
                        "enum": ["professional", "casual", "conference"],
                        "default": "professional",
                    },
                    "focus_area": {
                        "type": "string",
                        "description": "Optional focus area to emphasise, e.g. 'AI engineering'",
                    },
                },
                "required": [],
            },
        ),
        types.Tool(
            name="extract_job_fit_signals",
            description=(
                "Analyse a job description against the twin's knowledge base. "
                "Returns technical requirements, culture signals, keywords, "
                "and relevant experience from the knowledge base."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "job_description": {
                        "type": "string",
                        "description": "The full job description text",
                    },
                },
                "required": ["job_description"],
            },
        ),
        types.Tool(
            name="fetch_job_description",
            description=(
                "Scrape and extract the job description text from a job posting URL. "
                "Supports LinkedIn, Greenhouse, Lever, Workday, and most public job boards. "
                "Returns empty text if the page requires login."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Full URL of the job posting (https://...)",
                    },
                },
                "required": ["url"],
            },
        ),
        types.Tool(
            name="score_job_fit",
            description=(
                "Score how well the twin's owner fits a given job description. "
                "Extracts requirements from the JD, retrieves matching experience from the "
                "knowledge base, and returns a 0-100 fit score with matched/missing requirement lists."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "job_description": {
                        "type": "string",
                        "description": "The full job description text",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of KB docs to retrieve for matching (default 5)",
                        "default": 5,
                    },
                },
                "required": ["job_description"],
            },
        ),
        types.Tool(
            name="search_recent_jobs",
            description=(
                "Search for recent job postings from public job boards (Arbeitnow, RemoteOK). "
                "No API key required. Filter by keywords and time window. "
                "Use to find similar roles for the twin's owner."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Search keywords, e.g. ['machine learning', 'python', 'NLP']",
                    },
                    "hours": {
                        "type": "integer",
                        "description": "Only return jobs posted within this many hours (default 24)",
                        "default": 24,
                    },
                    "sources": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Job board sources to include: 'arbeitnow', 'remoteok'. Defaults to both.",
                        "default": ["linkedin","indeed"],
                    },
                },
                "required": ["keywords"],
            },
        ),
    ]


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    loop = asyncio.get_event_loop()

    if name == "search_knowledge":
        result = await loop.run_in_executor(None, _search_knowledge, arguments)
    elif name == "get_time_period_summary":
        result = await loop.run_in_executor(None, _get_time_period_summary, arguments)
    elif name == "list_domain_items":
        result = await loop.run_in_executor(None, _list_domain_items, arguments)
    elif name == "get_knowledge_scope":
        result = await loop.run_in_executor(None, _get_knowledge_scope, arguments)
    elif name == "generate_structured_bio":
        result = await loop.run_in_executor(None, _generate_structured_bio, arguments)
    elif name == "extract_job_fit_signals":
        result = await loop.run_in_executor(None, _extract_job_fit_signals, arguments)
    elif name == "fetch_job_description":
        result = await loop.run_in_executor(None, _fetch_job_description, arguments)
    elif name == "score_job_fit":
        result = await loop.run_in_executor(None, _score_job_fit, arguments)
    elif name == "search_recent_jobs":
        result = await loop.run_in_executor(None, _search_recent_jobs, arguments)
    else:
        result = {"error": f"Unknown tool: {name}"}

    return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


# ---------------------------------------------------------------------------
# Tool implementations (synchronous, run in executor)
# ---------------------------------------------------------------------------

def _search_knowledge(args: dict) -> dict:
    from src.rag_retrieval import fetch_context, _apply_metadata_boost, rerank_documents

    query = args["query"]
    doc_type = args.get("doc_type", "")
    top_k = min(int(args.get("top_k", 5)), 10)

    # fetch_context uses TOP_K from config; we apply domain boost then rerank to top_k
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

    return {"query": query, "results": results, "count": len(results)}


def _get_time_period_summary(args: dict) -> dict:
    from src.twin_tools import summarize_time_period
    year = str(args["year"])
    summary = summarize_time_period(year)
    return {"year": year, "summary": summary}


def _list_domain_items(args: dict) -> dict:
    from src.twin_tools import list_domain_items
    domain = args["domain"]
    items = list_domain_items(domain)
    return {"domain": domain, "items": items, "count": len(items)}


def _get_knowledge_scope(args: dict) -> dict:
    from src.twin_tools import get_knowledge_scope
    return get_knowledge_scope()


def _generate_structured_bio(args: dict) -> dict:
    from src.twin_tools import generate_bio
    style = args.get("style", "professional")
    focus_area = args.get("focus_area", "")

    # Build query for retrieval
    query = f"professional background experience skills"
    if focus_area:
        query = f"{focus_area} {query}"

    context_result = _search_knowledge({"query": query, "top_k": 5})
    context = "\n\n".join(r["content"] for r in context_result.get("results", []))

    bio_prompt = generate_bio(context, style)
    return {"style": style, "bio_prompt": bio_prompt, "context_used": len(context)}


def _extract_job_fit_signals(args: dict) -> dict:
    from src.rag_retrieval import extract_job_requirements, get_job_context
    job_description = args["job_description"]

    reqs = extract_job_requirements(job_description)
    _, context = get_job_context(job_description, reqs)

    return {
        "technical_requirements": reqs.get("technical_requirements", []),
        "culture": reqs.get("culture", []),
        "keywords": reqs.get("keywords", []),
        "relevant_experience_context": context[:3000] if context else "",
    }


def _fetch_job_description(args: dict) -> dict:
    from src.agent_tools import scrape_job_description
    url = args["url"]
    text = scrape_job_description(url)
    return {"url": url, "text": text, "char_count": len(text), "success": len(text) > 100}


def _score_job_fit(args: dict) -> dict:
    from src.agent_tools import score_job_fit
    return score_job_fit(
        job_description=args["job_description"],
        top_k=int(args.get("top_k", 5)),
    )


def _search_recent_jobs(args: dict) -> dict:
    from src.agent_tools import search_recent_jobs
    jobs = search_recent_jobs(
        keywords=args["keywords"],
        hours=int(args.get("hours", 24)),
        sources=args.get("sources") or None,
    )
    return {"jobs": jobs, "count": len(jobs)}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
