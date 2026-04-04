# Deploying MyBestFriend to Vercel (and backend)

- **Frontend**: Next.js → deploy on **Vercel** (native support).
- **Backend**: FastAPI (RAG, streaming, ChromaDB) → run on **Railway**, **Render**, or **Fly.io**. See "Can I use Vercel for the backend?" below.

---

## Can I use Vercel for the backend?

**Not recommended.** Vercel supports Python serverless functions, but this backend is a poor fit:

- **Size**: ChromaDB, LangChain, and other deps often exceed Vercel's serverless bundle limits (~50 MB compressed).
- **Timeouts**: Serverless has short timeouts (e.g. 10–60 s); RAG + streaming can exceed them.
- **State**: No long-lived process; each request is a new invocation. Your app uses in-memory state and persistent vector store in a way that fits a long-running server better.
- **Refactor cost**: You'd have to split the FastAPI app into per-route serverless handlers and possibly move heavy work to external services.

Use **Railway**, **Render**, or **Fly.io** for the backend and keep the frontend on Vercel.

---

## 1. Deploy the backend first

Your backend is a long-running FastAPI app with RAG and streaming. Python deps live under **`backend/`** (`backend/pyproject.toml`, `backend/uv.lock`). Deploy to one of these:

### Option A: Railway

Railway’s default image does not include `uv`. Use **Root Directory** `backend` and **pip** with the checked-in `backend/requirements.txt`.

1. Go to [railway.app](https://railway.app), sign in with GitHub.
2. **New Project** → **Deploy from GitHub repo** → select `MyBestFriend`.
3. **Root Directory**: **`backend`** (so the run directory has `src/` and `requirements.txt`).
4. **Build Command**: `pip install -r requirements.txt`
5. **Start Command**: `PYTHONPATH=.:src uvicorn src.api_server:app --host 0.0.0.0 --port ${PORT:-8080}` (Railway sets `PORT`; `${PORT:-8080}` falls back to 8080 if unset). `.:src` makes both `backend` and `backend/src` importable so `rag_retrieval` and `utils` resolve.
6. **Variables**: add env vars (e.g. `OPENAI_API_KEY`, Supabase keys). Use `backend/src/.env` as reference; do not commit secrets.
7. **Fix 502: set target port.** In Railway → your service → **Settings** → **Networking** (or **Public Networking**) → under your public domain, set **Target Port** to **8080** (or the port your logs show, e.g. "Uvicorn running on http://0.0.0.0:8080"). The proxy must forward to the same port the app listens on.
8. Deploy; note the public URL (e.g. `https://your-app.up.railway.app`).

Regenerate `backend/requirements.txt` after changing deps: `cd backend && uv pip compile pyproject.toml -o requirements.txt`.

**If you get 502 Bad Gateway:** (1) **Target port** (most common): Railway → service → **Settings** → **Networking** → set **Target Port** to **8080** so it matches the port in your logs ("Uvicorn running on http://0.0.0.0:8080"). (2) Ensure the app uses `$PORT` (start command uses `${PORT:-8080}`). (3) Open `https://your-app.up.railway.app/health`; if that works, the app is up. (4) Ensure **Generate Domain** was used for the service.

### Option B: Render

1. [render.com](https://render.com) → **New** → **Web Service**; connect GitHub and select `MyBestFriend`.
2. **Root Directory**: **`backend`**.
3. **Build Command**: `uv sync`.
4. **Start Command**: `uv run uvicorn src.api_server:app --host 0.0.0.0 --port $PORT`
5. **Environment**: add your env vars (OpenAI, Supabase, etc.).
6. Deploy and copy the service URL.

### Option C: Fly.io

1. Install [flyctl](https://fly.io/docs/hack/getting-started/), then `fly launch` in the repo root.
2. Use a Dockerfile that copies the repo, runs `uv sync` inside **`backend/`**, and starts `uv run uvicorn src.api_server:app --host 0.0.0.0 --port 8080` with `backend` as working directory.
3. Set secrets: `fly secrets set OPENAI_API_KEY=...` (and others).
4. Deploy; URL will be like `https://your-app.fly.dev`.

### Backend CORS

The backend allows the frontend origin via `CORS_ORIGINS`. Set it to your Vercel URL(s), e.g. `https://your-project.vercel.app` (comma-separated for multiple). Do not use `*` if you rely on credentials.

---

## 2. Deploy the frontend on Vercel

1. Go to [vercel.com](https://vercel.com), sign in with GitHub.
2. **Add New** → **Project** → import the `MyBestFriend` repo.
3. **Root Directory**: set to **`frontend`** (important).
4. **Framework Preset**: Next.js (auto-detected).
5. **Environment Variables**:
   - `BACKEND_URL` = your deployed backend URL (e.g. `https://your-app.up.railway.app`).  
   - No trailing slash.
6. **Deploy**. Your app will be at `https://your-project.vercel.app`.

The frontend uses `BACKEND_URL` (or `NEXT_PUBLIC_BACKEND_URL`) from `frontend/src/lib/backend.ts`; server-side API routes proxy to this URL.

**"Backend stream error: Not Found" / "couldn't connect to the backend":** (1) In Vercel go to **Project → Settings → Environment Variables**. Add **BACKEND_URL** = your Railway backend URL with **no trailing slash** (e.g. `https://your-app.up.railway.app`). Apply to Production (and Preview if you use it). (2) **Redeploy**: Deployments → ⋮ on latest deployment → **Redeploy**. Env vars are read at build/run time, so a redeploy is required. (3) Confirm the backend is up: open `https://your-railway-url/health` in a browser; you should see `{"status":"ok"}`.

**Where to see detailed logs on Vercel:**  
- **You must click a log row:** The "Messages" column in the list is often empty. **Click a row** in the log list (e.g. a `POST` to `/api/chat/stream`) to open the detail panel on the right — **Messages** (your `console.log` / `console.error` output) appear there.  
- **Filter to the API route:** In the search/filter box, type **`/api/chat/stream`** or **`api`** so you see API route invocations instead of only page requests (e.g. `GET /chat`). Look for **POST** requests when you send a message.  
- **Show errors:** Under "Contains Console Level", **check "Error"** to list only entries that have errors; those will show the "backend error" or "exception" logs.  
- **Tags:** Every log from the chat proxy is prefixed with **`[chat/stream]`** (e.g. "request start", "fetching backend", "backend error"). Search for that to find the right entries.

**"No response received" / empty bot reply:** The chat route streams the backend response. If the stream is empty or truncated (e.g. Vercel function timeout), the browser gets no SSE events. The route sets **`maxDuration = 60`**; on Hobby the limit may be 10s — raise it in **Settings → Functions → Max Duration**, or try shorter questions.

---

## 3. Checklist

- [ ] Backend deployed and `/health` returns `{"status":"ok"}`.
- [ ] Backend env vars set (OpenAI, Supabase, etc.).
- [ ] Backend `CORS_ORIGINS` includes your Vercel URL (e.g. `https://your-project.vercel.app`).
- [ ] Frontend on Vercel with **Root Directory** = `frontend`.
- [ ] Frontend env var `BACKEND_URL` = backend URL.
- [ ] Optional: add `backend/requirements.txt` for hosts that prefer pip: from repo root, `cd backend && uv pip compile pyproject.toml -o requirements.txt`.
- [ ] Optional: `agent_run_traces` table exists in Supabase (created automatically by migration).
- [ ] Optional: enable multi-agent mode via admin UI → Settings → `USE_MULTI_AGENT=true`.

---

## 4. Multi-Agent Mode

The multi-agent system is **off by default** (`USE_MULTI_AGENT=false`). Enable it via the admin UI at `/admin/settings` or directly in Supabase `app_config`.

### Key config flags

| Flag | Default | Description |
|------|---------|-------------|
| `USE_MULTI_AGENT` | `false` | Enable supervisor + specialist agent graph |
| `MULTI_AGENT_TOKEN_BUDGET` | `6000` | Max context tokens across all agents |
| `MULTI_AGENT_PARALLEL` | `true` | Parallel agent dispatch via LangGraph Send |
| `MULTI_AGENT_LOG_TRACES` | `true` | Log each run to `agent_run_traces` table |
| `HITL_ENABLED` | `false` | Human-in-the-loop review (pauses graph) |

### Verify it's working

```bash
# Check graph topology
curl https://your-backend/api/agent/graph

# Send a test message with multi-agent mode forced
curl -X POST https://your-backend/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me about your projects", "mode": "multi_agent"}'
```

### Agent traces

When `MULTI_AGENT_LOG_TRACES=true`, each run writes to the `agent_run_traces` Supabase table:

```bash
# View trace for a specific run
curl https://your-backend/api/agent/trace/<run_id>
```

---

## 5. MCP Server (Claude Desktop / external LLM integration)

The MCP server exposes 6 knowledge tools via stdio, making the twin's knowledge base composable with any MCP-compatible client.

### Local setup (Claude Desktop)

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mybestfriend": {
      "command": "uv",
      "args": [
        "run",
        "--project", "/absolute/path/to/MyBestFriend/backend",
        "python", "-m", "src.mcp_server"
      ],
      "env": {
        "OPENAI_API_KEY": "sk-...",
        "SUPABASE_URL": "https://...",
        "SUPABASE_SECRET_KEY": "..."
      }
    }
  }
}
```

Restart Claude Desktop. You can then ask Claude to `search_knowledge`, `list_domain_items`, etc.

### Test with MCP Inspector

```bash
cd backend
npx @modelcontextprotocol/inspector uv run python -m src.mcp_server
```

### Available tools

| Tool | Description |
|------|-------------|
| `search_knowledge` | Semantic + lexical search across the knowledge base |
| `get_time_period_summary` | All knowledge for a given year (e.g. "2023") |
| `list_domain_items` | List projects / jobs / skills / education / hobbies |
| `get_knowledge_scope` | Doc type counts + year range |
| `generate_structured_bio` | Bio in professional / casual / conference style |
| `extract_job_fit_signals` | Analyse a job description against the knowledge base |

---

## Optional: Dockerfile for backend

At repo root, you can use a Dockerfile that builds and runs from **`backend/`**:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY backend /app/backend
COPY README.md /app/README.md
WORKDIR /app/backend
RUN pip install uv && uv sync
EXPOSE 8080
CMD ["uv", "run", "uvicorn", "src.api_server:app", "--host", "0.0.0.0", "--port", "8080"]
```

Build from repo root: `docker build -t mybestfriend-backend .` Run with port 8080 or pass `$PORT` in `CMD`.
