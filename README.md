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

The primary execution mode (`USE_MULTI_AGENT=true`) uses a **LangGraph supervisor + parallel domain specialist graph**:

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

- **`intent_classifier`**: classifies query → decides which specialist agents to activate (structured output via `INTENT_CLASSIFIER_PROMPT`)
- **`supervisor`**: initialises token budget + run ID, dispatches via `Send` API
- **Specialist agents**: each calls `search_knowledge_by_domain()` → `rerank_documents()` → `build_agent_result()`
- **`grounding_guard`**: deduplicates docs, enforces `MULTI_AGENT_TOKEN_BUDGET`, runs self-check
- **`synthesis`**: generates final answer with multi-source attribution (`SYNTHESIS_AGENT_PROMPT`)
- **`trace_log`**: fire-and-forget write to `agent_run_traces` Supabase table

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

### 1.5 MCP server

Exposes the knowledge base as 6 tools for Claude Desktop and any MCP-compatible LLM client:

| Tool | Description |
|------|-------------|
| `search_knowledge` | Primary knowledge retrieval (hybrid search + rerank) |
| `get_time_period_summary` | All chunks for a given year |
| `list_domain_items` | Titles + years by domain |
| `get_knowledge_scope` | Doc type counts + year range |
| `generate_structured_bio` | Bio in professional/casual/conference style |
| `extract_job_fit_signals` | Job description analysis against knowledge base |

Run with:
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

### 1.6 Knowledge management & admin UI

Admin panel (Next.js) with optional access control via `ADMIN_API_KEY`:

- **Knowledge base view**: Tree of ingested documents with chunk counts by category (CV, career, personal, project). Re-ingest all with one click.
- **Document operations**: Add markdown via admin UI → `/api/documents` (write, chunk, embed, sync to Supabase). Delete → disk, vector store, and Supabase kept in sync.
- **Config management**: `/api/config` — view effective runtime config; edit identity, notifications, and AI models from the Settings page.
- **Prompt management**: All 21 system prompts stored in Supabase `prompts` table, editable from the Prompts admin screen. Includes agent-specific prompts (`CAREER_AGENT_PROMPT`, `GROUNDING_GUARD_PROMPT`, `SYNTHESIS_AGENT_PROMPT`, etc.).

### 1.7 Evaluation & dataset management

#### 1.7.1 RAG evaluation

- `POST /api/evaluate` — async RAGAS evaluation over the test set:
  - LLM answer quality: accuracy, relevance, completeness, confidence, overall score (3.9/5 on last run).
  - Retrieval metrics: MRR (0.630), keyword coverage (87.4%).
- `GET /api/evaluate/{job_id}` — poll job status.
- `GET /api/evaluate/latest` — fetch last completed result from Supabase.

#### 1.7.2 Multi-agent evaluation

- `POST /api/evaluate/multi-agent` — 5 new metrics:
  - **ARA** (Agent Routing Accuracy): fraction of queries routed to correct specialists.
  - **ACRR** (Context Redundancy Ratio): duplicate context across agents (lower = better).
  - **Synthesis Faithfulness**: grounded-answer fidelity score.
  - **Parallel Efficiency**: speedup vs sequential execution.
  - **Per-Agent MRR**: retrieval rank quality per specialist (career, skills, project, personal, job-prep).

#### 1.7.3 Evaluation dataset manager

- Supabase-backed `eval_dataset` table (per-owner): `question`, `ground_truth`, `category`, `keywords`.
- Admin UI dataset tab: inline editing, add/delete rows, upload JSONL, download JSONL, AI-generate test cases via `/api/eval/dataset/generate`.
- `load_test_questions()` seeds from `backend/evaluation/eval_data.jsonl` if the Supabase table is empty.

### 1.8 Human-in-the-loop (HITL)

Set `HITL_ENABLED=true` + build graph with checkpointing. Interrupted runs pause at the `hitl_review` node. Resume via `POST /api/agent/resume/{thread_id}`. Pending reviews listed at `GET /api/agent/pending-reviews`.

### 1.9 User contact & handoff

When `no_info` is true from `/api/chat`:
- Frontend shows a contact form (name, email, question).
- `POST /api/contact` sends email to owner via SMTP.

### 1.10 Tech stack

- **Backend**: Python 3.12, FastAPI, Uvicorn, LangChain, LangGraph, Supabase vector store, RAGAS evaluation.
- **Frontend**: Next.js (App Router), React 19, Tailwind CSS v4, Lucide icons.
- **Storage & infra**: Supabase Postgres (documents, chunks, eval datasets, prompts, config, agent traces); Vercel for frontend; Railway/Render/Fly.io/Docker for backend.

---

## 2. Deployment

For provider-specific details, see `DEPLOYMENT.md`. This section covers the overall flow.

### 2.1 Local development

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

### 2.2 Backend deployment (Railway / Render / Fly.io / Docker)

1. Set deployment working directory to `backend/`.
2. Install: `uv sync` (or `pip install -r requirements.txt` for Railway).
3. Start command:
   ```bash
   PYTHONPATH=.:src uvicorn src.api_server:app --host 0.0.0.0 --port $PORT
   ```
4. Environment variables: `OPENAI_API_KEY`, `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, SMTP vars.
5. Health check: `GET /health` → `{"status": "ok"}`.

---

### 2.3 Frontend deployment (Vercel)

1. Import the Git repo in Vercel, set project root to `frontend/`, framework preset: **Next.js**.
2. Set `NEXT_PUBLIC_BACKEND_URL` (or `BACKEND_URL`) to your backend base URL (no trailing slash).
3. Ensure the backend CORS config includes `http://localhost:3000` and your Vercel URL.

---

### 2.4 Supabase setup

Use the Supabase SQL editor to create the core tables.

#### 2.4.1 Vector store, documents, config, prompts, eval results

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

#### 2.4.2 Evaluation dataset table

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

#### 2.4.3 Agent run traces table

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

### 2.5 Key config flags

| Flag | Default | Purpose |
|------|---------|---------|
| `USE_MULTI_AGENT` | `true` | Enable supervisor + specialist agent graph |
| `USE_GRAPH` | `false` | Enable legacy 6-node LangGraph (fallback) |
| `MULTI_AGENT_TOKEN_BUDGET` | `12000` | Max context tokens across all agents |
| `MULTI_AGENT_LOG_TRACES` | `true` | Write traces to `agent_run_traces` table |
| `HYBRID_SEARCH_ENABLED` | `true` | Semantic + lexical search |
| `LEXICAL_WEIGHT` | `0.3` | Weight for lexical component in hybrid search |
| `TOP_K` | `5` | Docs retrieved per agent |
| `GENERATOR_MODEL` | `gpt-4o` | Answer synthesis model |
| `EMBEDDING_MODEL` | `text-embedding-3-large` | Embedding model |
| `HITL_ENABLED` | `false` | Human-in-the-loop review for sensitive answers |
| `ADMIN_API_KEY` | `""` | Empty = no auth (dev mode) |

---

### 2.6 New API endpoints (multi-agent)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET` | `/api/agent/graph` | Public | Graph topology JSON for visualisation |
| `GET` | `/api/agent/trace/{run_id}` | Public | Full agent trace for a run |
| `GET` | `/api/agent/pending-reviews` | Admin | HITL runs awaiting review |
| `POST` | `/api/agent/resume/{thread_id}` | Admin | Resume paused HITL graph |
| `POST` | `/api/evaluate/multi-agent` | Admin | Trigger multi-agent eval (ARA, ACRR, MRR) |

`ChatRequest` accepts optional `thread_id` (checkpointing) and `mode` (`"multi_agent"` / `"graph"` / `"direct"` to override config per-request).

---

### 2.7 Operational checklist

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
