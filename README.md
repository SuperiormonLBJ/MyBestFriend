# MyBestFriend – Personal Digital Twin

MyBestFriend is a production-grade *personal digital twin*: a multi-agent RAG system and admin console that answers questions about a single person (the "owner") using only curated, versioned documents. It runs as a FastAPI backend, a Next.js frontend, and a Supabase-backed Postgres + vector store. The default execution mode is a **LangGraph supervisor + parallel domain specialist agents**, with MCP server support for external LLM integrations.

## Frontend showcase

Next.js UI: sidebar (Chatbot, Job Preparation, Admin), dark theme, quick prompts and streaming chat, job-description prep, and admin tools for knowledge, settings, prompts, and eval. Screenshots live under `frontend/docs/screenshots/` (paths below are repo-root–relative for GitHub and editor preview).

### Chatbot

Ethereal-style background, quick prompts, topic filter chips (Personal & Hobbies, Career & Work, CV, Projects), and a prompt box with optional voice input (Web Speech API in supported browsers).

![Chatbot](/frontend/docs/screenshots/chat.png)

### Job preparation

Paste a job description, optional cover-letter word limit, then generate tailored cover letter, resume suggestions, and interview questions.

![Job preparation](/frontend/docs/screenshots/job-preparation.png)

### Admin — hub

Entry points for Knowledge Base, Settings, Prompts, and Eval.

![Admin hub](/frontend/docs/screenshots/admin.png)

### Admin — Knowledge Base

Inspect and manage documents in the vector store (127 chunks across 4 categories: CV, career, personal, project). Add/delete documents; re-ingest all.

![Admin knowledge](/frontend/docs/screenshots/admin-knowledge.png)

### Admin — Settings

Edit identity (app name, owner name), notification email, and AI models — changes save to Supabase immediately.

![Admin settings](/frontend/docs/screenshots/admin-settings.png)

### Admin — Prompts

Edit all 21 Supabase-backed LLM system prompts, including agent-specific prompts for the multi-agent graph.

![Admin prompts](/frontend/docs/screenshots/admin-prompts.png)

### Admin — Eval (RAG evaluation)

Run retrieval and LLM quality evaluation against the configured dataset. Shows LLM scores (accuracy, relevance, completeness, confidence) and retrieval metrics (MRR, keyword coverage).

![Admin eval](/frontend/docs/screenshots/admin-eval.png)

### Admin — Eval (Multi-agent evaluation)

Dedicated multi-agent evaluation tab with orchestration metrics: Agent Routing Accuracy (ARA), Context Redundancy Ratio (ACRR), Synthesis Faithfulness, Parallel Efficiency, and per-agent MRR.

![Admin eval multi-agent](/frontend/docs/screenshots/admin-eval-multi-agent.png)

---

## 1. Core features

### 1.1 Chat experience

- **Owner-centric Q&A**: Answers questions about the owner (career, projects, education, hobbies, personality) using only ingested markdown documents.
- **Streaming UI**: Next.js + React chat interface with token streaming, topic filter chips, source citations, and optional **voice input** (Web Speech API where available).
- **Unknown-answer handling**: If the RAG stack can't confidently answer, the backend sets `no_info` and the UI shows a dedicated fallback state plus a contact form.
- **Local history**: Conversation history persisted in `localStorage` so refreshes don't lose the thread.
- **Agent status events**: In multi-agent mode, the stream emits `{"agent_status": "<name>"}` progress events before synthesis tokens begin, so the UI can show which specialist is active.

### 1.2 Multi-agent RAG pipeline (default)

The primary execution mode (`USE_MULTI_AGENT=true`) uses a **LangGraph supervisor + parallel ReAct specialist graph**:

```
intent_classifier → supervisor → [Send fan-out]
                                  ├─ career_agent    ─┐
                                  ├─ project_agent   ─┤
                                  ├─ skills_agent    ─┤ (parallel ReAct agents)
                                  ├─ personal_agent  ─┤
                                  ├─ job_prep_agent  ─┤
                                  └─ calendar_agent  ─┘
                                          ↓ [fan-in via operator.add reducers]
                              grounding_guard → rerank → synthesis → hitl_review → trace_log → END
```

**Key nodes:**
- **`intent_classifier`**: LLM structured output (`IntentResult`) classifies the query and activates only the relevant agents — a narrow question about one domain activates just one agent instead of all of them.
- **`supervisor`**: initialises token budget + run ID, dispatches agents via `Send` API.
- **ReAct specialist agents**: each runs a reason-act-observe loop with a curated tool set. Agents can call multiple tools in sequence (e.g. `list_domain_items("jobs")` then `search_knowledge` for details) and self-terminate when they have enough context.
- **`grounding_guard`**: merges and deduplicates docs across all agent branches, enforces `MULTI_AGENT_TOKEN_BUDGET`.
- **`rerank`**: single LLM rerank on the final merged, budget-trimmed doc set.
- **`synthesis`**: generates final answer with multi-source attribution (`SYNTHESIS_AGENT_PROMPT`), streams tokens via SSE.
- **`trace_log`**: fire-and-forget write to `agent_run_traces` Supabase table.

#### Skill-based agent definitions (`agent_skills.py`)

Each agent is declared as an `AgentSkill` — a data-only record of its prompt key, tool whitelist, tool defaults, iteration limit, and optional MCP server filter. Adding a new domain agent requires only a new entry in `AGENT_SKILLS`, no graph code changes.

| Agent | Tools | Max iterations | MCP filter |
|---|---|---|---|
| `career_agent` | `search_knowledge`, `get_time_period_summary`, `list_domain_items` | 3 | — |
| `project_agent` | `search_knowledge`, `list_domain_items`, `get_knowledge_scope` | 3 | — |
| `skills_agent` | `search_knowledge`, `list_domain_items` | 3 | — |
| `personal_agent` | `search_knowledge`, `get_time_period_summary` | 2 | — |
| `job_prep_agent` | `search_knowledge`, `fetch_job_description`, `score_job_fit`, `extract_job_fit_signals`, `search_recent_jobs` | 4 | — |
| `calendar_agent` | *(external only)* | 4 | `google-calendar` |

Tool access is **scoped** — `career_agent` cannot call `search_recent_jobs`, `calendar_agent` cannot call knowledge-base tools. `mcp_server_filter` limits each agent to specific external MCP servers.

**Fallback modes** (configured via flags):
- `USE_GRAPH=true` → `conversation_graph.py` (legacy 6-node LangGraph)
- default → `rag_retrieval.py::generate_answer_stream()` (direct RAG)

### 1.3 RAG pipeline internals

- **Markdown-based knowledge base**: Loads markdown documents from `backend/data/` with YAML frontmatter (`doc_type`, `type`, `year`, `importance`, `title`).
- **Chunking & embeddings**: Splits by `##`/`###` headers, attaches labels, embeds via `text-embedding-3-large`, stores in Supabase `document_chunks`.
- **Hybrid search**: Semantic + lexical search (`HYBRID_SEARCH_ENABLED=true`, `LEXICAL_WEIGHT=0.3`).
- **Live reload**: `/api/ingest` fully re-ingests documents without restarting the backend.

### 1.4 Job preparation (LLM-based JD analysis)

- **LLM-first JD parsing**: `extract_job_requirements()` (rewrite model) extracts `technical_requirements`, `culture`, and `keywords` from arbitrary job descriptions.
- **Tailored output**: `POST /api/job/cover-letter` and `POST /api/job/prepare` generate cover letter, resume improvement suggestions, and interview questions using RAG context + structured JD analysis.
- **Job-prep UI**: Shows job analysis (requirements, culture bullets, keyword tags) before the generated cover letter.

### 1.5 Unified tool registry (`tool_registry.py`)

All tool implementations live in a single registry as LangChain `@tool` functions. This is the **single source of truth** shared by three consumers — ReAct agents, the MCP server, and direct API endpoints — eliminating duplication.

| Tool | Wraps | Used by |
|------|-------|---------|
| `search_knowledge` | `fetch_context` + `rerank_documents` | All knowledge agents, MCP |
| `get_time_period_summary` | `twin_tools.summarize_time_period` | `career_agent`, `personal_agent`, MCP |
| `list_domain_items` | `twin_tools.list_domain_items` | `career_agent`, `project_agent`, `skills_agent`, MCP |
| `get_knowledge_scope` | `twin_tools.get_knowledge_scope` | `project_agent`, MCP |
| `generate_structured_bio` | `twin_tools.generate_bio` + retrieval | MCP |
| `extract_job_fit_signals` | `extract_job_requirements` + `get_job_context` | `job_prep_agent`, MCP |
| `fetch_job_description` | `agent_tools.scrape_job_description` | `job_prep_agent`, MCP |
| `score_job_fit` | `agent_tools.score_job_fit` | `job_prep_agent`, MCP |
| `search_recent_jobs` | `agent_tools.search_recent_jobs` | `job_prep_agent`, MCP |

### 1.6 MCP server (outbound) + MCP client (inbound)

#### Outbound — expose the twin as MCP tools

`mcp_server.py` imports directly from `tool_registry.py` and auto-generates MCP tool schemas from the LangChain `@tool` definitions. Run in stdio mode for Claude Desktop or any MCP-compatible client:

```bash
uv run python -m src.mcp_server
```

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

#### Inbound — consume external MCP servers inside agents

`mcp_client.py` connects to external MCP servers defined in `config.yaml` under `mcp_clients` and wraps their tools as LangChain tools for use inside ReAct agents. Each agent controls which servers it may access via `mcp_server_filter` in its `AgentSkill` definition.

**Example — Google Calendar integration:**

```yaml
# config.yaml
mcp_clients:
  - name: "google-calendar"
    command: "npx"
    args: ["-y", "@anthropic-community/mcp-server-google-calendar"]
    env:
      GOOGLE_CLIENT_ID: "your-client-id"
      GOOGLE_CLIENT_SECRET: "your-client-secret"
      GOOGLE_REFRESH_TOKEN: "your-refresh-token"
```

With this configured, queries like *"Is Beiji free on Friday afternoon?"* trigger `calendar_agent`, which calls the Google Calendar MCP tools (`list_events`, `get_freebusy`, etc.) and feeds the results into synthesis alongside knowledge-base context.

### 1.7 Knowledge management & admin UI

Admin panel (Next.js) with optional access control via `ADMIN_API_KEY`:

- **Knowledge base view**: Tree of ingested documents with chunk counts by category (CV, career, personal, project). Re-ingest all with one click.
- **Document operations**: Add markdown via admin UI → `/api/documents` (write, chunk, embed, sync to Supabase). Delete → disk, vector store, and Supabase kept in sync.
- **Config management**: `/api/config` — view effective runtime config; edit identity, notifications, and AI models from the Settings page.
- **Prompt management**: All system prompts stored in Supabase `prompts` table, editable from the Prompts admin screen. Includes all agent-specific prompts (`CAREER_AGENT_PROMPT`, `PROJECT_AGENT_PROMPT`, `SKILLS_AGENT_PROMPT`, `PERSONAL_AGENT_PROMPT`, `JOB_PREP_AGENT_PROMPT`, `CALENDAR_AGENT_PROMPT`, `SYNTHESIS_AGENT_PROMPT`, `INTENT_CLASSIFIER_PROMPT`, etc.).

### 1.8 Evaluation & dataset management

#### 1.8.1 RAG evaluation

- `POST /api/evaluate` — async RAGAS evaluation over the test set:
  - LLM answer quality: accuracy, relevance, completeness, confidence, overall score (3.9/5 on last run).
  - Retrieval metrics: MRR (0.630), keyword coverage (87.4%).
- `GET /api/evaluate/{job_id}` — poll job status.
- `GET /api/evaluate/latest` — fetch last completed result from Supabase.

#### 1.8.2 Multi-agent evaluation

- `POST /api/evaluate/multi-agent` — 5 new metrics:
  - **ARA** (Agent Routing Accuracy): fraction of queries routed to correct specialists.
  - **ACRR** (Context Redundancy Ratio): duplicate context across agents (lower = better).
  - **Synthesis Faithfulness**: grounded-answer fidelity score.
  - **Parallel Efficiency**: speedup vs sequential execution.
  - **Per-Agent MRR**: retrieval rank quality per specialist (career, skills, project, personal, job-prep).

#### 1.8.3 Evaluation dataset manager

- Supabase-backed `eval_dataset` table (per-owner): `question`, `ground_truth`, `category`, `keywords`.
- Admin UI dataset tab: inline editing, add/delete rows, upload JSONL, download JSONL, AI-generate test cases via `/api/eval/dataset/generate`.
- `load_test_questions()` seeds from `backend/evaluation/eval_data.jsonl` if the Supabase table is empty.

### 1.9 Human-in-the-loop (HITL)

Set `HITL_ENABLED=true` + build graph with checkpointing. Interrupted runs pause at the `hitl_review` node. Resume via `POST /api/agent/resume/{thread_id}`. Pending reviews listed at `GET /api/agent/pending-reviews`.

### 1.10 User contact & handoff

When `no_info` is true from `/api/chat`:
- Frontend shows a contact form (name, email, question).
- `POST /api/contact` sends email to owner via SMTP.

### 1.11 Tech stack

- **Backend**: Python 3.12, FastAPI, Uvicorn, LangChain, LangGraph, Supabase vector store, RAGAS evaluation.
- **Frontend**: Next.js (App Router), React 19, Tailwind CSS v4, Lucide icons.
- **Storage & infra**: Supabase Postgres (documents, chunks, eval datasets, prompts, config, agent traces); Vercel for frontend; Railway/Render/Fly.io/Docker for backend.
- **MCP**: mcp Python SDK (outbound server + inbound client); stdio transport for Claude Desktop and external MCP servers.

---

## 2. Architecture improvements over single-agent RAG

The previous system was a single-graph linear pipeline: one retrieval call, one generation call, no specialisation.

| Concern | Old (direct RAG) | New (ReAct multi-agent) |
|---|---|---|
| **Retrieval scope** | One `search_knowledge` call with the raw query | Each specialist filters by domain; `career_agent` searches only career docs, `skills_agent` searches skills, etc. |
| **Routing** | None — every query goes through the same path | LLM intent classifier activates only the relevant agents; narrow questions hit one agent instead of all |
| **Tool calling** | None — retrieval was hard-coded | Every agent runs a ReAct loop and can call any tool in its whitelist across multiple steps |
| **External integrations** | MCP server was outbound only; internal agents had no access | `mcp_client.py` lets any agent consume external MCP servers (Google Calendar, etc.) via `mcp_server_filter` |
| **Duplication** | `mcp_server.py` had its own hand-written implementations of tools also defined in `rag_retrieval.py` | `tool_registry.py` is the single source of truth; MCP server, agents, and API routes all import from it |
| **Streaming feedback** | Users saw a spinner until the full answer appeared | `agent_status` SSE events let the UI show a live per-agent progress indicator as each one runs |
| **Adding a new domain** | Required editing the retrieval query and synthesis prompt | Add one `AgentSkill` entry in `agent_skills.py`, one node wire-up in `multi_agent_graph.py` |
| **Calendar / real-time data** | Not possible | `calendar_agent` queries Google Calendar MCP and merges results into synthesis |

**Common multi-agent problems addressed:**

- **Fan-out / fan-in state corruption** — `Annotated[list, operator.add]` reducers on `agent_results` and `agent_trace` merge parallel branches without race conditions.
- **Token budget explosion** — `grounding_guard` deduplicates and trims the merged doc set to `MULTI_AGENT_TOKEN_BUDGET` before synthesis.
- **Unreliable routing** — replaced regex heuristics with LLM structured output (`IntentResult`); classifier emits confidence and entity hints alongside the agent list.
- **Tool scope creep** — each agent only receives the tools listed in its `AgentSkill.tools` whitelist; external MCP tools are additionally gated by `mcp_server_filter`.
- **Dead-loop prevention** — each ReAct agent has a `max_iterations` cap in its `AgentSkill`; the loop exits early if the model stops issuing tool calls.
- **Observability** — every run writes a structured trace (agents activated, per-agent latency, token budget used) to the `agent_run_traces` Supabase table.

---

## 3. Deployment

For provider-specific details, see `DEPLOYMENT.md`. This section covers the overall flow.

### 3.1 Local development

1. **Backend: install dependencies**

   ```bash
   cd backend
   uv sync
   ```

2. **Backend: configure environment**

   Copy `backend/src/.env` and set:
   - `OPENAI_API_KEY` — Required for LLM + embeddings
   - `SUPABASE_URL`, `SUPABASE_SECRET_KEY`
   - SMTP settings (optional, for contact email): `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`

   Adjust `backend/config.yaml`:
   - `DATA_DIR` — where your markdown knowledge base lives
   - Model names (`EMBEDDING_MODEL`, `GENERATOR_MODEL`, etc.)
   - `frontend` section (`app_name`, `owner_name`)
   - `USE_MULTI_AGENT: true` (default) to enable the supervisor + specialist agent graph

3. **Backend: run FastAPI**

   ```bash
   cd backend
   uv run uvicorn src.api_server:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Frontend: install & run**

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

   Point the UI at your API: set `BACKEND_URL` or `NEXT_PUBLIC_BACKEND_URL` in `frontend/.env.local` if the backend is not `http://127.0.0.1:8000`.

   **Regenerate showcase screenshots** (optional): with the dev server on port 3000, run `npm run playwright:install` once, then `npm run screenshots`. PNGs are written to `frontend/docs/screenshots/`.

5. **Open the app**

   - Chat: `http://localhost:3000/chat`
   - Job preparation: `http://localhost:3000/job-preparation`
   - Admin panel: `http://localhost:3000/admin`

6. **MCP server** (optional, for Claude Desktop)

   ```bash
   cd backend
   uv run python -m src.mcp_server
   ```

---

### 3.2 Backend deployment (Railway / Render / Fly.io / Docker)

1. Set deployment working directory to `backend/`.
2. Install: `uv sync` (or `pip install -r requirements.txt` for Railway).
3. Start command:
   ```bash
   PYTHONPATH=.:src uvicorn src.api_server:app --host 0.0.0.0 --port $PORT
   ```
4. Environment variables: `OPENAI_API_KEY`, `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, SMTP vars.
5. Health check: `GET /health` → `{"status": "ok"}`.

---

### 3.3 Frontend deployment (Vercel)

1. Import the Git repo in Vercel, set project root to `frontend/`, framework preset: **Next.js**.
2. Set `NEXT_PUBLIC_BACKEND_URL` (or `BACKEND_URL`) to your backend base URL (no trailing slash).
3. Ensure the backend CORS config includes `http://localhost:3000` and your Vercel URL.

---

### 3.4 Supabase setup

Use the Supabase SQL editor to create the core tables.

#### 3.4.1 Vector store, documents, config, prompts, eval results

```sql
-- Vector chunks used by SupabaseVectorStore
create table if not exists public.document_chunks (
  id uuid primary key default gen_random_uuid(),
  content text not null,
  metadata jsonb not null default '{}'::jsonb,
  embedding vector(1536)  -- text-embedding-3-large
);

-- Source documents (full markdown content + metadata)
create table if not exists public.documents (
  id uuid primary key default gen_random_uuid(),
  filename text not null,
  doc_type text not null,
  content text not null,
  inserted_at timestamptz not null default now(),
  unique (filename, doc_type)
);

-- App configuration key/value store
create table if not exists public.app_config (
  key text primary key,
  value jsonb not null
);

-- LLM prompts managed from the admin UI (21 total)
create table if not exists public.prompts (
  key text primary key,
  content text not null,
  description text not null
);

-- Latest RAG evaluation result snapshot
create table if not exists public.eval_results (
  id integer primary key,
  status text,
  finished_at timestamptz,
  result jsonb
);
```

#### 3.4.2 Evaluation dataset table

```sql
create table if not exists public.eval_dataset (
  id uuid primary key default gen_random_uuid(),
  owner_id text not null default 'default',
  question text not null,
  ground_truth text not null,
  category text not null default 'general',
  keywords jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_eval_dataset_owner_id
  on public.eval_dataset (owner_id);
```

#### 3.4.3 Agent run traces table

```sql
create table if not exists public.agent_run_traces (
  id uuid primary key default gen_random_uuid(),
  run_id text not null,
  owner_id text not null default 'default',
  agents_activated text[] not null default '{}',
  latencies jsonb not null default '{}'::jsonb,
  token_budget_used integer,
  result_summary jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_agent_run_traces_run_id
  on public.agent_run_traces (run_id);
```

---

### 3.5 Key config flags

| Flag | Default | Purpose |
|------|---------|---------|
| `USE_MULTI_AGENT` | `true` | Enable supervisor + ReAct specialist agent graph |
| `USE_GRAPH` | `false` | Enable legacy 6-node LangGraph (fallback) |
| `MULTI_AGENT_TOKEN_BUDGET` | `12000` | Max context tokens across all agents |
| `MULTI_AGENT_PARALLEL` | `true` | Run agents in parallel via LangGraph Send API |
| `MULTI_AGENT_LOG_TRACES` | `true` | Write traces to `agent_run_traces` table |
| `HYBRID_SEARCH_ENABLED` | `true` | Semantic + lexical search |
| `LEXICAL_WEIGHT` | `0.3` | Weight for lexical component in hybrid search |
| `TOP_K` | `5` | Docs retrieved per agent |
| `GENERATOR_MODEL` | `gpt-4o` | Answer synthesis model |
| `EMBEDDING_MODEL` | `text-embedding-3-large` | Embedding model |
| `HITL_ENABLED` | `false` | Human-in-the-loop review for sensitive answers |
| `ADMIN_API_KEY` | `""` | Empty = no auth (dev mode) |

---

### 3.6 New API endpoints (multi-agent)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET` | `/api/agent/graph` | Public | Graph topology JSON for visualisation |
| `GET` | `/api/agent/trace/{run_id}` | Public | Full agent trace for a run |
| `GET` | `/api/agent/pending-reviews` | Admin | HITL runs awaiting review |
| `POST` | `/api/agent/resume/{thread_id}` | Admin | Resume paused HITL graph |
| `POST` | `/api/evaluate/multi-agent` | Admin | Trigger multi-agent eval (ARA, ACRR, MRR) |

`ChatRequest` accepts optional `thread_id` (checkpointing) and `mode` (`"multi_agent"` / `"graph"` / `"direct"` to override config per-request).

---

### 3.7 Operational checklist

- Backend deployed, `/health` returns `{"status":"ok"}`.
- Supabase tables exist and are reachable: `document_chunks`, `documents`, `app_config`, `prompts`, `eval_results`, `eval_dataset`, `agent_run_traces`.
- `POST /api/ingest` completes successfully and `GET /api/knowledge` returns non-empty data.
- Frontend deployed on Vercel with `BACKEND_URL` pointing to the backend.
- CORS configured correctly on the backend.
- Admin panel reachable:
  - Knowledge base shows documents and chunk counts.
  - Settings edits save to Supabase.
  - Prompts (21 total) are viewable and editable.
  - RAG evaluation runs and displays LLM scores + retrieval metrics.
  - Multi-agent evaluation runs and displays ARA, ACRR, per-agent MRR.
  - Evaluation dataset manager works: edit, upload/download JSONL, AI generate.
