# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**MyBestFriend** is a personal digital twin — a multi-agent RAG system that answers questions about its owner using only curated, versioned markdown documents. It strictly refuses to answer questions outside the knowledge base to prevent hallucinations. The system is built on LangGraph with a supervisor + domain specialist agent architecture, and exposes the knowledge base as MCP tools for external integrations.

## Commands

### Frontend (`frontend/`)
```bash
npm install          # Install dependencies
npm run dev          # Dev server on :3000
npm run build        # Production build
npm run lint         # ESLint
npm run test:e2e     # Playwright E2E tests
npm run screenshots  # Generate screenshots (tests/screenshots.spec.ts)
```

### Backend (`backend/`)
```bash
uv sync              # Install dependencies from uv.lock
uv run uvicorn src.api_server:app --reload --host 0.0.0.0 --port 8000  # Dev server
uv run python -m src.mcp_server   # Run MCP server (stdio mode, for Claude Desktop)
```

Backend uses `uv` (not pip/poetry). Always `uv sync` to install, `uv run` to execute.

## Architecture

### Two-Service Structure
- `frontend/` — Next.js 16 (App Router), React 19, Tailwind CSS v4, deployed on Vercel
- `backend/` — FastAPI + Python 3.12+, deployed on Railway/Render/Fly.io

### Request Flow
1. Frontend `POST /api/chat/stream` → Next.js API route (`frontend/src/app/api/chat/stream/`)
2. Next.js API route proxies to backend at `BACKEND_URL` (env var, defaults to `http://127.0.0.1:8000`)
3. Backend routes based on execution mode (three-way flag):
   - `USE_MULTI_AGENT=true` → `multi_agent_graph.py` (supervisor + parallel domain agents)
   - `USE_GRAPH=true` → `conversation_graph.py` (single-graph flow)
   - default → `rag_retrieval.py::generate_answer_stream()` (direct RAG)
4. Tokens stream back through Next.js to browser via SSE

All frontend routes under `src/app/api/` are proxy routes — they forward to the FastAPI backend.

### Backend Core Files
- `src/api_server.py` — All FastAPI routes + app setup
- `src/rag_retrieval.py` — RAG pipeline: hybrid search (semantic + lexical), optional reranking, streaming generation
- `src/rag_ingestion.py` — Markdown chunking via `MarkdownHeaderTextSplitter` + embedding into Supabase
- `src/eval.py` + `src/eval_dataset_store.py` — RAGAS-based evaluation framework (async, runs in background thread)
- `src/conversation_graph.py` — Basic 6-node LangGraph graph (legacy, `USE_GRAPH=true`)
- `utils/config_loader.py` — Loads `config.yaml`, syncs to/from Supabase `app_config` table at startup
- `utils/prompt_manager.py` — Supabase-backed prompt registry (editable from admin UI)

### Multi-Agent System Files (new)
- `src/multi_agent_graph.py` — Full supervisor + domain specialist graph (activated by `USE_MULTI_AGENT=true`)
- `src/agent_state.py` — `MultiAgentState` TypedDict with `Annotated[list, operator.add]` fan-in reducers
- `src/agent_tools.py` — Domain-scoped retrieval, `build_agent_result`, token budget helpers
- `src/mcp_server.py` — MCP stdio server exposing 6 knowledge tools for Claude Desktop / external LLMs
- `src/multi_agent_eval.py` — 5 new evaluation metrics (ARA, ACRR, per-agent MRR, faithfulness, parallel efficiency)

### Database (Supabase Postgres + pgvector)
- `document_chunks` — Vector embeddings (1536-dim, `text-embedding-3-large`)
- `documents` — Full markdown source files
- `app_config` — Runtime config (key-value, seeds from `config.yaml`)
- `prompts` — LLM prompts editable via admin UI (21 total, including 8 new agent prompts)
- `eval_results` — Latest evaluation run result
- `eval_dataset` — Test question bank for RAGAS evaluation
- `agent_run_traces` — Per-run multi-agent execution trace (agents activated, latencies, token budget)

### Config System
`config.yaml` → loaded at startup → synced to Supabase `app_config` (source of truth at runtime). Admin UI edits update Supabase, not the filesystem.

Key settings:

| Flag | Default | Purpose |
|------|---------|---------|
| `GENERATOR_MODEL` | `gpt-4o` | Answer synthesis model |
| `EMBEDDING_MODEL` | `text-embedding-3-large` | Embedding model |
| `TOP_K` | `5` | Docs retrieved per agent |
| `HYBRID_SEARCH_ENABLED` | `true` | Semantic + lexical search |
| `USE_GRAPH` | `false` | Enable legacy 6-node graph |
| `USE_MULTI_AGENT` | `false` | Enable supervisor + specialist agents |
| `MULTI_AGENT_TOKEN_BUDGET` | `6000` | Max context tokens across all agents |
| `MULTI_AGENT_PARALLEL` | `true` | Run agents in parallel via LangGraph Send |
| `MULTI_AGENT_LOG_TRACES` | `true` | Write traces to `agent_run_traces` table |
| `HITL_ENABLED` | `false` | Human-in-the-loop review for sensitive answers |

### Knowledge Base
- Documents live in `backend/data/` as markdown with YAML frontmatter (`doc_type`, `type`, `year`, `importance`, `title`)
- Chunked by `##`/`###` headers, stored as embeddings in Supabase
- Adding a doc via admin UI → `POST /api/documents` → `rag_ingestion.py` → Supabase

### Admin Auth
`ADMIN_API_KEY` in `config.yaml`: empty = no auth (dev mode). When set, frontend must send `X-Admin-Key: <key>` header. Viewing admin pages is always allowed; edits require the key.

## Environment Variables

**Backend** (`.env` in `backend/src/`):
- `OPENAI_API_KEY` — Required for LLM + embeddings
- `SUPABASE_URL`, `SUPABASE_SECRET_KEY` — Required for vector store
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` — For contact form email

**Frontend** (Vercel env / `.env.local`):
- `BACKEND_URL` — FastAPI backend URL (server-side Next.js routes)
- `NEXT_PUBLIC_BACKEND_URL` — Same, exposed to browser if needed

## Frontend Structure

- `src/app/(routes)/` — Pages: `/chat`, `/job-preparation`, `/admin`, `/admin/knowledge`, `/admin/settings`, `/admin/prompts`, `/admin/eval`
- `src/app/api/` — Next.js API routes (all proxy to FastAPI)
- `src/components/` — `chat-message.tsx`, `chat-input.tsx`, `sidebar.tsx`, `admin-login.tsx`, `ui/`
- `src/lib/backend.ts` — `BACKEND_URL` resolution logic
- `src/contexts/` — React context providers (config, etc.)

## Key Patterns

- **Streaming:** Backend yields SSE tokens; frontend consumes via `useEffect` + `ReadableStream`. In multi-agent mode, agents emit optional `{"agent_status": "<name>"}` progress events before synthesis tokens begin.
- **Evaluation:** `POST /api/evaluate` returns job ID immediately; frontend polls `GET /api/evaluate/{jobId}`; RAGAS metrics run in background thread. Multi-agent eval: `POST /api/evaluate/multi-agent`.
- **TypeScript paths:** `@/*` maps to `frontend/src/*`
- **Tailwind v4:** Uses `@tailwindcss/postcss` plugin (not the v3 config pattern)
- **Multi-agent fan-out:** `LangGraph Send API` dispatches specialist agents in parallel. `Annotated[list, operator.add]` reducers on `agent_results`/`agent_trace` merge results safely at fan-in.
- **MCP server:** `uv run python -m src.mcp_server` exposes 6 tools via stdio. Register in Claude Desktop config to query the twin's knowledge from any MCP-compatible client.
- **HITL:** Set `HITL_ENABLED=true` + build graph with checkpointing. Interrupted runs pause at `hitl_review` node. Resume via `POST /api/agent/resume/{thread_id}`.

## Multi-Agent Graph Topology

```
intent_classifier → supervisor → [Send fan-out]
                                  ├─ career_agent    ─┐
                                  ├─ project_agent   ─┤ (parallel)
                                  ├─ skills_agent    ─┤
                                  ├─ personal_agent  ─┤
                                  └─ job_prep_agent  ─┘
                                          ↓ [fan-in via operator.add reducers]
                              grounding_guard → synthesis → hitl_review → trace_log → END
```

- `intent_classifier`: classifies query → decides which agents to activate (uses `INTENT_CLASSIFIER_PROMPT`, structured output)
- `supervisor`: initialises token budget + run ID, dispatches via `Send`
- Specialist agents: each calls `search_knowledge_by_domain()` → `rerank_documents()` → `build_agent_result()`
- `grounding_guard`: deduplicates docs, enforces `MULTI_AGENT_TOKEN_BUDGET`, runs self-check
- `synthesis`: generates final answer with multi-source attribution (`SYNTHESIS_AGENT_PROMPT`)
- `trace_log`: fire-and-forget write to `agent_run_traces` Supabase table

## MCP Server Tools

Run with `uv run python -m src.mcp_server`. Wraps existing functions — no new retrieval logic:

| Tool | Wraps | Description |
|------|-------|-------------|
| `search_knowledge` | `fetch_context` + `rerank_documents` | Primary knowledge retrieval |
| `get_time_period_summary` | `twin_tools.summarize_time_period` | All chunks for a given year |
| `list_domain_items` | `twin_tools.list_domain_items` | Titles + years by domain |
| `get_knowledge_scope` | `twin_tools.get_knowledge_scope` | Doc type counts + year range |
| `generate_structured_bio` | `search_knowledge` + `generate_bio` | Bio in professional/casual/conference style |
| `extract_job_fit_signals` | `extract_job_requirements` + `get_job_context` | Job description analysis |

Register with Claude Desktop:
```json
{
  "mcpServers": {
    "mybestfriend": {
      "command": "uv",
      "args": ["run", "--project", "/path/to/backend", "python", "-m", "src.mcp_server"]
    }
  }
}
```

## New API Endpoints (multi-agent)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET` | `/api/agent/graph` | Public | Graph topology JSON (for visualisation) |
| `GET` | `/api/agent/trace/{run_id}` | Public | Full agent trace for a run |
| `GET` | `/api/agent/pending-reviews` | Admin | HITL runs awaiting review |
| `POST` | `/api/agent/resume/{thread_id}` | Admin | Resume paused HITL graph |
| `POST` | `/api/evaluate/multi-agent` | Admin | Trigger multi-agent eval (ARA, ACRR, MRR) |

`ChatRequest` now accepts optional `thread_id` (for checkpointing) and `mode` (`"multi_agent"` / `"graph"` / `"direct"` to override config flags per-request).
