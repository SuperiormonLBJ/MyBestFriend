# MyBestFriend – Personal Digital Twin

MyBestFriend is a production-grade RAG chatbot and admin API that answers questions about a single person (the "owner") using only curated, versioned documents. It runs as a FastAPI backend with a Next.js chat UI and a Supabase-backed vector store.

## 1. Functionalities

### Chat experience

- Streaming chat UI in the `frontend/` app, optimized for desktop and mobile.
- Answers questions about the owner using only ingested markdown documents.
- Shows an unknown-answer state: if the RAG stack cannot confidently answer, the backend flags `no_info` and the UI offers a follow-up contact form.
- Persists conversation history in the browser via `localStorage` so users can refresh without losing the thread.

### RAG pipeline

- Loads all markdown documents from the configured data directory (via `ConfigLoader`) under the backend project root.
- Supports simple YAML-style frontmatter (`--- ... ---`) to attach metadata such as `type`, `doc_type`, `year`, `importance`, and `title`.
- Normalizes metadata and writes one `Document` per source file.
- Splits markdown into section-level chunks using `##` / `###` headings and prepends lightweight labels (project title, section name) into the chunk text.
- Embeds chunks with OpenAI embeddings (model configured via `ConfigLoader`) and stores them in a Supabase `document_chunks` table via `SupabaseVectorStore`.
- Provides a `reload_vectorstore` hook so a full re-ingest can rebuild the live vector store without restarting the app.

### Knowledge management & admin APIs

The FastAPI backend exposes a small admin surface:

- `POST /api/ingest` — re-ingest all documents from disk, rebuild the vector store, and sync source documents into a Supabase `documents` table.
- `GET /api/knowledge` — return a tree of ingested documents and chunk counts for admin UIs.
- `POST /api/documents` — add a single markdown document (saves to disk, chunks, embeds, stores, and syncs to Supabase).
- `DELETE /api/documents/{source}` — delete a document by filename from disk, the vector store, and Supabase.
- `GET /api/config` — fetch the current runtime configuration (app name, owner name, model choices, routing, etc.) from the combined file/Supabase config.
- `PUT /api/config` — update and persist editable config fields back to `config.yaml`.
- `POST /api/config/push` — one-time “force push” of the current in-memory config into Supabase so hosted environments start from the same defaults.
- `GET /api/prompts` — list all managed system prompts with their current Supabase-backed content.
- `PUT /api/prompts/{key}` — update a single prompt by key.
- `POST /api/prompts/{key}/reset` — reset a prompt back to its hard-coded default template.

### User contact & handoff

When the model cannot answer a question:

- The chat backend returns a `no_info` flag from `/api/chat/stream`.
- The frontend opens a contact form that collects the user’s name, email, and original question.
- `POST /api/contact` sends an email to the configured recipient using SMTP credentials (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`) plus a recipient email configured via `ConfigLoader`.

### Evaluation

The backend includes a lightweight evaluation harness:

- `POST /api/evaluate` — kicks off an async evaluation job over a fixed set of test questions, running both generation and retrieval evaluations.
- `GET /api/evaluate/{job_id}` — poll the in-memory status/result of a specific job.
- `GET /api/evaluate/latest` — fetch the last persisted evaluation result from Supabase (survives restarts).
- Evaluation results are stored in an `eval_results` table in Supabase so you can build dashboards or compare runs over time.

### Health & observability

- `GET /health` — simple health check for load balancers and uptime monitors.
- `GET /` — returns a minimal JSON descriptor with service name and health URL.
- Frontend proxy logs all `/api/chat/stream` requests with contextual tags in Vercel logs to help trace backend connectivity and timeout issues.

### Tech stack

- **Backend**: Python 3.12, FastAPI, Uvicorn, LangChain, Supabase vector store, RAGAS-style evaluation.
- **Frontend**: Next.js 16 (App Router), React 19, Tailwind CSS 4, Lucide icons.
- **Storage & infra**: Supabase Postgres for documents, vector embeddings, and config; Vercel for the Next.js app; Railway/Render/Fly.io (or Docker) for the FastAPI backend.

## 2. Deployment flow

For detailed provider-specific instructions, see `DEPLOYMENT.md`. Below is the high-level flow.

### 2.1 Local development

1. **Clone and install backend**

   ```bash
   cd backend
   uv sync
   ```

2. **Configure backend environment**

   - Copy `backend/src/.env` and fill in:
     - `SUPABASE_URL`, `SUPABASE_SECRET_KEY`.
     - Model provider API keys (OpenAI, Anthropic, etc.) and any other secrets referenced by `config.yaml`.
     - SMTP settings if you want the contact-form email handoff.
   - Adjust `config.yaml` (data directory, models, app/owner name, etc.) as needed.

3. **Run backend**

   ```bash
   cd backend
   uv run uvicorn src.api_server:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Install and run frontend**

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

5. Open `http://localhost:3000/chat` and chat with your digital twin.

### 2.2 Backend deployment (Railway / Render / Fly.io)

1. **Choose a backend host** that supports a long-running FastAPI server (Railway, Render, or Fly.io are tested options).
2. **Set the project root to `backend/`** so that `pyproject.toml`, `uv.lock`, and `src/` are in the working directory.
3. **Install dependencies**, for example:
   - Railway with `requirements.txt`: `pip install -r requirements.txt`.
   - Render/Fly.io: `uv sync`.
4. **Start command** (adapt for each host):

   ```bash
   PYTHONPATH=.:src uvicorn src.api_server:app --host 0.0.0.0 --port $PORT
   ```

   Some platforms (like Railway) expose `PORT`; others expect you to pick a fixed port such as `8080` and configure the service to route traffic to it.

5. **Configure environment variables on the host** (same values as your local `.env`, but set via the provider’s dashboard or secrets manager).
6. **Verify health** by opening your backend URL at `/health` (e.g. `https://your-backend.example.com/health` should return `{"status":"ok"}`).

More detailed, provider-specific steps (including Railway’s target-port configuration, Render service settings, Fly.io Dockerfile, and a sample Dockerfile) are documented in `DEPLOYMENT.md`.

### 2.3 Frontend deployment (Vercel)

1. **Import the repo into Vercel** and set the project root to `frontend/`.
2. Ensure the framework preset is **Next.js** and keep the default build/start commands.
3. In the Vercel project settings, set:

   - `BACKEND_URL` (or `NEXT_PUBLIC_BACKEND_URL`) to your deployed backend base URL, **without** a trailing slash (e.g. `https://your-backend.example.com`).

4. Deploy the project; Vercel will provide a URL like `https://your-project.vercel.app`.
5. In the backend, configure CORS origins (via config) to include your Vercel URL so the browser can call the API.

### 2.4 Operational checklist

- Backend is deployed, `/health` returns `{"status":"ok"}`.
- Backend environment variables (Supabase, model provider, SMTP) are correctly set in the hosting provider.
- Supabase tables (`document_chunks`, `documents`, `eval_results`, and config/prompt tables) are created and reachable from the backend.
- Frontend is deployed on Vercel with `BACKEND_URL` pointing at the backend.
- CORS origins include both `http://localhost:3000` for local dev and your production Vercel URL.
- Running `POST /api/ingest` succeeds and `GET /api/knowledge` returns non-empty documents.

### 2.5 Supabase SQL initialization

Create the core tables in Supabase (SQL editor → New query):

```sql
-- Vector chunks used by SupabaseVectorStore
create table if not exists public.document_chunks (
  id uuid primary key default gen_random_uuid(),
  content text not null,
  metadata jsonb not null default '{}'::jsonb,
  embedding vector(1536)  -- adjust dimension if your embedding model differs
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

-- LLM prompts managed from the admin UI
create table if not exists public.prompts (
  key text primary key,
  content text not null,
  description text not null
);

-- Latest evaluation result snapshot
create table if not exists public.eval_results (
  id integer primary key,
  status text,
  finished_at timestamptz,
  result jsonb
);
```
