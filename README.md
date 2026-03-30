# MyBestFriend – Personal Digital Twin

MyBestFriend is a production-grade *personal digital twin*: a RAG chatbot and admin console that answers questions about a single person (the “owner”) using only curated, versioned documents. It runs as a FastAPI backend, a Next.js frontend, and a Supabase-backed Postgres + vector store.

## Frontend showcase

Next.js UI: sidebar (Chatbot, Job Preparation, Admin), dark theme, quick prompts and streaming chat, job-description prep, and admin tools for knowledge, settings, prompts, and eval. Screenshots live under `frontend/docs/screenshots/` (paths below are repo-root–relative for GitHub and editor preview).

### Chatbot

Ethereal-style background, quick prompts, prompt box with optional voice (Web Speech API in supported browsers).

![Chatbot](/frontend/docs/screenshots/chat.png)

### Job preparation

Paste a job description, optional cover-letter word limit, then switch between cover letter, resume suggestions, and interview questions.

![Job preparation](/frontend/docs/screenshots/job-preparation.png)

### Admin — hub

Entry points for Knowledge Base, Settings, Prompts, and Eval.

![Admin hub](/frontend/docs/screenshots/admin.png)

### Admin — Knowledge Base

Inspect and manage documents in the vector store (with backend support for add/delete).

![Admin knowledge](/frontend/docs/screenshots/admin-knowledge.png)

### Admin — Settings

Runtime display and model-related options from config.

![Admin settings](/frontend/docs/screenshots/admin-settings.png)

### Admin — Prompts

Edit Supabase-backed LLM system prompts.

![Admin prompts](/frontend/docs/screenshots/admin-prompts.png)

### Admin — Eval

Run retrieval and LLM quality evaluation against the configured dataset.

![Admin eval](/frontend/docs/screenshots/admin-eval.png)

---

## 1. Core features

### 1.1 Chat experience

- **Owner-centric Q&A**: Answers questions about the owner (career, projects, education, hobbies, personality) using only ingested markdown documents.
- **Streaming UI**: Next.js 16 + React 19 chat interface with token streaming, desktop/mobile friendly, source citations, and optional **voice input** (Web Speech API where available; otherwise a fallback message).
- **Unknown-answer handling**: If the RAG stack can’t confidently answer, the backend sets `no_info` and the UI shows a dedicated fallback state plus a contact form.
- **Local history**: Conversation history is persisted in `localStorage` so refreshes don’t lose the thread.

### 1.2 RAG pipeline

- **Markdown-based knowledge base**:
  - Loads markdown documents from a configured data directory (via `ConfigLoader`) under `backend/`.
  - Supports YAML-style frontmatter (`--- ... ---`) with fields like `doc_type`, `type`, `year`, `importance`, `title`, etc.
- **Chunking & embeddings**:
  - Splits documents into section-level chunks using `##` / `###` headings and attaches lightweight labels (e.g. project title, section name) directly in chunk text.
  - Embeds chunks using the configured embedding model and stores them in a Supabase `document_chunks` table via `SupabaseVectorStore`.
- **Live reload**:
  - `/api/ingest` fully re-ingests documents, rebuilds the vector store, and keeps the in-memory retriever hot without restarting the backend.

### 1.3 Job preparation (LLM-based JD analysis)

- **LLM-first JD parsing**:
  - Backend uses `extract_job_requirements()` (small “rewrite” model) to turn arbitrary job descriptions into JSON:
    - `technical_requirements: string[]`
    - `culture: string[]`
    - `keywords: string[]`
  - A simple heuristic extractor is kept only as a fallback.
- **Tailored cover letters + guidance**:
  - `POST /api/job/cover-letter`: generates a concise cover letter using RAG context + structured JD analysis.
  - `POST /api/job/prepare`: runs the full flow once (cover letter, resume improvement suggestions, interview questions).
  - `JobPrepResponse` returns the cover letter and the structured `technical_requirements`, `culture`, and `keywords`.
- **Job-prep UI**:
  - The Job Preparation page first shows **Job analysis** (requirements, culture bullets, keyword tags) and then the generated cover letter, so you can inspect the analysis before using the output.

### 1.4 Knowledge management & admin UI

Admin panel (Next.js) with secure access via an admin key:

- **Knowledge base view**:
  - Tree of ingested documents, quick stats, and links to inspect content.
- **Document operations**:
  - Add markdown documents via the admin UI → backend `/api/documents` (write file, chunk, embed, sync to Supabase).
  - Delete documents via `/api/documents/{source}` (disk, vector store, and Supabase are all kept in sync).
- **Config management**:
  - `/api/config` + `/api/config/push` + `/api/config` `PUT` let you:
    - View effective runtime config (models, flags, owner/app name, retrieval options).
    - Push in-memory config back to Supabase.
    - Update selected fields from the admin settings page.
- **Prompt management**:
  - All major system prompts are stored in a Supabase `prompts` table and surfaced in the Prompts admin screen:
    - Core generator, reranker, evaluator, job-prep prompts…
    - **Eval dataset generator prompt** (`EVAL_DATASET_GENERATOR_PROMPT`) used to synthesize test cases from your ingested knowledge.

### 1.5 Evaluation & dataset management

#### 1.5.1 Eval runs

- **Backend APIs**:
  - `POST /api/evaluate` — runs an async evaluation over the current test set:
    - LLM answer quality (accuracy, relevance, completeness, confidence, score).
    - Retrieval metrics (MRR, keyword coverage).
  - `GET /api/evaluate/{job_id}` — poll job status.
  - `GET /api/evaluate/latest` — fetch last completed result from Supabase (`eval_results` table).
- **Admin eval UI** (`/admin/eval`):
  - Run evaluation with a single button.
  - Live status banner with elapsed time.
  - Cards for:
    - **LLM Evaluation** (scores + average feedback).
    - **Retrieval Metrics** (MRR, keyword coverage).
    - **Config at time of run** (frozen snapshot so you know which models/settings were used).

#### 1.5.2 Evaluation dataset manager (Supabase-backed)

The evaluation test set is now a first-class, Supabase-backed dataset, editable in the admin UI:

- **Data model**:
  - Supabase table `eval_dataset` (per-owner) with:
    - `question: text`
    - `ground_truth: text`
    - `category: text`
    - `keywords: jsonb` (string array)
    - `owner_id`, timestamps, etc.
- **Source-of-truth behavior**:
  - `load_test_questions()` in the backend:
    - Loads tests from `eval_dataset` for the current `owner_id`.
    - If empty, seeds from `backend/evaluation/eval_data.jsonl` **once** and writes them into Supabase.
    - Falls back to JSONL-only if Supabase is unavailable.
- **Eval Dataset tab (admin)**:
  - `/admin/eval` is split into two tabs:
    - **Run evaluation**
    - **Evaluation dataset**
  - **Dataset table** with columns:
    - `Question`
    - `Ground truth`
    - `Keywords`
    - `Category`
  - **Inline editing**:
    - Textareas for `question` and `ground_truth`.
    - Editable input for `category`.
    - Comma-separated string for `keywords` (mapped to a string array).
  - **Actions**:
    - **Add row** (new row at the top).
    - **Save changes** (writes the full table to Supabase via `PUT /api/eval/dataset`).
    - **Clear** (with confirmation; clears Supabase and UI via `POST /api/eval/dataset/clear`).
    - **Upload JSONL**:
      - Client-side parse of `.jsonl`/`.txt` file into rows.
      - Validates each line has `question` and `ground_truth`.
      - Only updates the UI; nothing hits Supabase until you press **Save changes**.
    - **Download JSONL**:
      - `GET /api/eval/dataset/download` returns canonical JSONL:
        - Each line is `{ "question", "ground_truth", "category", "keywords": [] }`.
    - **AI generate**:
      - Configurable **AI count** (default 20, min 1, max 200) sent as `n` to `/api/eval/dataset/generate`.
      - Appends new test cases to the existing dataset.
      - Shows a loader while generating and a message like `AI generated 20 test cases.` on success.

#### 1.5.3 AI-generated evaluation questions

- **Backend logic**:
  - `/api/eval/dataset/generate`:
    - Samples documents from Supabase `document_chunks` (`content` + `metadata`).
    - Builds a structured context with headers like `[project] LLM-Based Code Reviewer (2024)` followed by content.
    - Passes this context into the Supabase-managed prompt `EVAL_DATASET_GENERATOR_PROMPT`.
    - The LLM returns a JSON array of `{question, ground_truth, category, keywords[]}` objects.
    - Validates and appends them to `eval_dataset` for the current `owner_id`.
- **Prompt is configurable**:
  - `EVAL_DATASET_GENERATOR_PROMPT` lives in `utils/prompts.py` and is registered in `prompt_manager`.
  - You can edit it from the Prompts admin page to change style, categories, or difficulty of evaluation questions.

### 1.6 User contact & handoff

- When `no_info` is true from `/api/chat`:
  - The frontend shows a contact form (name, email, question).
  - `POST /api/contact` sends an email to the owner via SMTP using credentials and `RECIPIENT_EMAIL` from config.

### 1.7 Health & observability

- `GET /health` — simple health check.
- `GET /` — minimal JSON descriptor with service name and health URL.
- Frontend logs chat streaming calls with context to help debug connectivity/timeouts.

### 1.8 Tech stack

- **Backend**: Python 3.12, FastAPI, Uvicorn, LangChain, Supabase vector store, RAG evaluation tools.
- **Frontend**: Next.js 16 (App Router), React 19, Tailwind CSS v4, Lucide icons, Caveat + Quicksand typography (indigo-forward UI).
- **Storage & infra**: Supabase Postgres (documents, chunks, eval datasets, prompts, config); Vercel (default) for frontend; Railway/Render/Fly.io/Docker for the backend.

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

   - Copy `backend/src/.env` and set:
     - `SUPABASE_URL`, `SUPABASE_SECRET_KEY`
     - Model provider keys (e.g. OpenAI) used by `config.yaml`
     - SMTP settings if you want email handoff:
       - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`
   - Adjust `backend/config.yaml`:
     - `DATA_DIR` (where your markdown lives)
     - Model names (`EMBEDDING_MODEL`, `GENERATOR_MODEL`, etc.)
     - `frontend` section (`app_name`, `owner_name`)

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
   - Admin panel: `http://localhost:3000/admin` (requires admin key if configured)

---

### 2.2 Backend deployment (Railway / Render / Fly.io / Docker)

1. **Project root**

   - Set the deployment working directory to `backend/`.
   - Ensure `pyproject.toml`, `uv.lock`, and `src/` are present.

2. **Install dependencies**

   Examples:
   - Railway (pip): `pip install -r requirements.txt`
   - Render/Fly.io: `uv sync`

3. **Start command**

   Most platforms can use:

   ```bash
   PYTHONPATH=.:src uvicorn src.api_server:app --host 0.0.0.0 --port $PORT
   ```

   If your host doesn’t provide `PORT`, choose one (e.g. `8080`) and configure the service to route traffic to it.

4. **Environment variables**

   Set the same values as your local `.env` in the cloud provider:

   - `SUPABASE_URL`, `SUPABASE_SECRET_KEY`
   - Model provider keys
   - SMTP variables (optional but required for contact email)
   - Any extra config keys referenced by `config.yaml`

5. **Health check**

   - Visit `/health` on your backend URL, e.g.:

     ```text
     https://your-backend.example.com/health
     ```

   - Expect `{"status": "ok"}`.

---

### 2.3 Frontend deployment (Vercel)

1. **Import project**

   - In Vercel, import the Git repo.
   - Set the project root to `frontend/`.
   - Framework preset: **Next.js** (App Router).

2. **Configure environment**

   - Set **one** of:
     - `NEXT_PUBLIC_BACKEND_URL`
     - `BACKEND_URL`
   - Value: your backend base URL **without** trailing slash, e.g.:

     ```text
     https://your-backend.example.com
     ```

3. **Deploy**

   - Vercel builds and deploys automatically.
   - You’ll get a URL like `https://mybestfriend-yourname.vercel.app`.

4. **CORS**

   - Ensure the backend CORS config includes:
     - `http://localhost:3000` (for local dev)
     - Your Vercel URL (e.g. `https://mybestfriend-yourname.vercel.app`)

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

(If you don’t already have an `updated_at` trigger function, you can omit the trigger or add one later.)

---

### 2.5 Operational checklist

- Backend deployed, `/health` returns `{"status":"ok"}`.
- Supabase tables exist and are reachable: `document_chunks`, `documents`, `app_config`, `prompts`, `eval_results`, `eval_dataset`.
- `POST /api/ingest` completes successfully and `GET /api/knowledge` returns non-empty data.
- Frontend deployed on Vercel with `BACKEND_URL` pointing to the backend.
- CORS configured correctly on the backend.
- Admin panel reachable; prompts, settings, and evaluation dataset manager all work:
  - You can see/edit prompts.
  - You can edit the evaluation dataset table, upload/download JSONL, and run AI generation.
  - Evaluations run and visualize successfully on `/admin/eval`.
