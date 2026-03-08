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

---

## 3. Checklist

- [ ] Backend deployed and `/health` returns `{"status":"ok"}`.
- [ ] Backend env vars set (OpenAI, Supabase, etc.).
- [ ] Backend `CORS_ORIGINS` includes your Vercel URL (e.g. `https://your-project.vercel.app`).
- [ ] Frontend on Vercel with **Root Directory** = `frontend`.
- [ ] Frontend env var `BACKEND_URL` = backend URL.
- [ ] Optional: add `backend/requirements.txt` for hosts that prefer pip: from repo root, `cd backend && uv pip compile pyproject.toml -o requirements.txt`.

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
