"""
FastAPI server for the MyBestFriend chatbot.
Run with: uvicorn api_server:app --reload --host 0.0.0.0 --port 8000
"""
import threading
import time
import uuid
import smtplib
import os
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .rag_retrieval import (
    generate_answer,
    generate_answer_stream,
    get_knowledge_tree,
    reload_vectorstore,
    extract_job_requirements,
    get_job_context,
)
from utils.config_loader import ConfigLoader
from utils.prompts import get_reference_template
from utils.prompt_manager import get_prompt, get_all_prompts, update_prompt, get_default_content, sync_defaults
from utils.supabase_client import supabase_client
from .document_ops import delete_document, add_document
from .rag_ingestion import load_document, create_chunks_markdown, embed_chunks, _parse_md_frontmatter
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
import traceback as _traceback
# Pre-import eval in the main thread so its module-level code (ConfigLoader, ChatOpenAI init)
# runs here, never inside a background thread where the shared Supabase client is not safe.
from .eval import load_test_questions, evaluate_LLM, evaluate_all

config = ConfigLoader()
app = FastAPI(title="MyBestFriend API")


# ---------------------------------------------------------------------------
# Admin auth dependency
# ---------------------------------------------------------------------------

def require_admin(x_admin_key: str = Header(default="")):
    """Validate the X-Admin-Key header for protected admin endpoints.
    If ADMIN_API_KEY is empty (default), auth is disabled for easy local dev.
    """
    expected = config.get_admin_api_key()
    if expected and x_admin_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing admin API key")


AdminAuth = Depends(require_admin)

# Sync all hardcoded prompt defaults to Supabase on startup so code changes take effect immediately.
sync_defaults()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class VerifyKeyRequest(BaseModel):
    key: str


@app.post("/api/auth/admin")
def verify_admin_key(request: VerifyKeyRequest):
    """Validate an admin key. Returns {valid: true} on success, 401 on failure.
    If no key is configured (open mode) any key (including empty) is accepted."""
    expected = config.get_admin_api_key()
    if not expected or request.key == expected:
        return {"valid": True, "open": not bool(expected)}
    raise HTTPException(status_code=401, detail="Invalid admin key")


class ChatRequest(BaseModel):
    message: str
    history: list[dict[str, str]] = []


class ChatResponse(BaseModel):
    answer: str
    no_info: bool = False
    sources: list = []


class JobPrepRequest(BaseModel):
    job_description: str
    word_limit: int | None = None


class JobPrepResponse(BaseModel):
    cover_letter: str
    word_limit: int


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    if config.get_use_graph():
        from src.conversation_graph import run_graph
        answer, _, no_info, sources = run_graph(request.message, request.history)
    else:
        answer, _, no_info, sources = generate_answer(request.message, request.history)
    return ChatResponse(answer=answer, no_info=no_info, sources=sources)


@app.post("/api/chat/stream")
def chat_stream(request: ChatRequest):
    def event_stream():
        for event in generate_answer_stream(request.message, request.history):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


@app.get("/api/scope")
def api_scope():
    """Return knowledge scope (doc_type counts, year range) for onboarding UI."""
    try:
        from src.twin_tools import get_knowledge_scope
        return get_knowledge_scope()
    except Exception as e:
        return {"doc_types": {}, "year_range": None, "error": str(e)}


@app.post("/api/job/cover-letter", response_model=JobPrepResponse)
def api_job_cover_letter(request: JobPrepRequest):
    """Generate a tailored cover letter from a job description using RAG context."""
    word_limit = (
        request.word_limit
        if request.word_limit is not None
        else config.get_cover_letter_word_limit()
    )
    if not request.job_description or not request.job_description.strip():
        raise HTTPException(status_code=400, detail="job_description is required")
    try:
        reqs = extract_job_requirements(request.job_description)
        _, context = get_job_context(request.job_description, reqs)
        frontend_cfg = config.get_frontend_config()
        owner_name = frontend_cfg.get("owner_name", "the candidate")
        owner_profile = f"Candidate: {owner_name}"
        requirements_str = "\n".join(f"- {r}" for r in reqs["requirements"][:15]) if reqs["requirements"] else "None extracted."
        keywords_str = ", ".join(reqs["keywords"][:25]) if reqs["keywords"] else "None extracted."
        prompt = get_prompt("COVER_LETTER_PROMPT").format(
            job_description=request.job_description.strip()[:8000],
            requirements=requirements_str,
            keywords=keywords_str,
            context=context[:12000] if context else "No relevant context found.",
            owner_profile=owner_profile,
            word_limit=word_limit,
        )
        llm = ChatOpenAI(model=config.get_generator_model())
        response = llm.invoke([
            SystemMessage(content=prompt),
            HumanMessage(content="Generate the cover letter now."),
        ])
        cover_letter = (response.content or "").strip()
        return JobPrepResponse(cover_letter=cover_letter, word_limit=word_limit)
    except HTTPException:
        raise
    except Exception as e:
        _traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"service": "MyBestFriend API", "health": "/health"}


# ---------------------------------------------------------------------------
# Contact / inquiry email
# ---------------------------------------------------------------------------

def _send_inquiry_email(requester_name: str, requester_email: str, question: str) -> None:
    """Send an inquiry email to the recipient configured in config.yaml."""
    recipient = config.get_recipient_email()
    if not recipient:
        raise ValueError("RECIPIENT_EMAIL is not configured.")

    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_password = os.environ.get("SMTP_PASSWORD", "")

    if not smtp_user or not smtp_password:
        raise ValueError("SMTP_USER and SMTP_PASSWORD environment variables are required.")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[MyBestFriend] Question from {requester_name}"
    msg["From"] = smtp_user
    msg["To"] = recipient
    msg["Reply-To"] = requester_email

    body = (
        f"Someone asked a question that wasn't in your knowledge base.\n\n"
        f"Name: {requester_name}\n"
        f"Email: {requester_email}\n\n"
        f"Question:\n{question}\n"
    )
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, recipient, msg.as_string())


class ContactRequest(BaseModel):
    requester_name: str
    requester_email: str
    question: str


@app.post("/api/contact")
def api_contact(request: ContactRequest):
    """Send an inquiry email to the owner when the chatbot couldn't answer a question."""
    if not request.requester_name.strip() or not request.requester_email.strip() or not request.question.strip():
        raise HTTPException(status_code=400, detail="name, email, and question are required")
    try:
        _send_inquiry_email(
            requester_name=request.requester_name.strip(),
            requester_email=request.requester_email.strip(),
            question=request.question.strip(),
        )
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        print(f"[contact] Email send error: {e}")
        raise HTTPException(status_code=502, detail="Failed to send email. Please try again later.")
    return {"status": "sent"}


@app.get("/api/config")
def get_config():
    """Return full editable config (frontend + models), pulling latest from Supabase first."""
    config.reload()
    return config.get_full_config()


class ConfigUpdateRequest(BaseModel):
    app_name: str | None = None
    owner_name: str | None = None
    embedding_model: str | None = None
    generator_model: str | None = None
    llm_model: str | None = None
    rewrite_model: str | None = None
    reranker_model: str | None = None
    evaluator_model: str | None = None
    recipient_email: str | None = None
    # Retrieval flags
    hybrid_search_enabled: bool | None = None
    lexical_weight: float | None = None
    metadata_filter_enabled: bool | None = None
    self_check_enabled: bool | None = None
    multi_step_enabled: bool | None = None
    use_graph: bool | None = None
    admin_api_key: str | None = None


@app.post("/api/config/push", dependencies=[AdminAuth])
def push_config_to_supabase():
    """Force-push the current in-memory config to Supabase (use once after creating the table)."""
    config.reload()
    config._push_to_supabase()
    return {"status": "ok", "config": config.get_full_config()}


@app.put("/api/config")
def update_config(request: ConfigUpdateRequest):
    """Update config values and persist to config.yaml."""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        return config.get_full_config()
    config.update_and_save(updates)
    return config.get_full_config()


@app.get("/api/knowledge")
def knowledge_tree():
    """Return tree structure of ingested documents for admin UI."""
    try:
        return get_knowledge_tree()
    except Exception as e:
        return {"tree": [], "totalChunks": 0, "error": str(e)}


class AddDocumentRequest(BaseModel):
    content: str
    filename: str
    doc_type: str


class RestructureRequest(BaseModel):
    raw_text: str
    doc_type: str = "career"
    year: str | None = None
    importance: str = "medium"


def _inject_frontmatter_override(
    content: str,
    type_val: str,
    year_val: str | None,
    importance_val: str,
) -> str:
    """Overwrite type, year, importance in frontmatter with user-provided values. Ensures they are applied."""
    meta, body = _parse_md_frontmatter(content)
    meta["type"] = type_val
    meta["importance"] = importance_val
    if year_val:
        meta["year"] = year_val
    else:
        meta.pop("year", None)
    lines = ["---"]
    for k, v in meta.items():
        if v is None:
            continue
        lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines) + "\n\n" + body


@app.post("/api/restructure", dependencies=[AdminAuth])
def api_restructure(request: RestructureRequest):
    """Restructure raw text into RAG-ready markdown using the reference format for the doc_type. Does not ingest."""
    if not request.raw_text.strip():
        raise HTTPException(status_code=400, detail="raw_text cannot be empty")
    reference_md = get_reference_template(request.doc_type)
    year_val = (request.year or "").strip() or None
    importance_val = (request.importance or "medium").strip().lower()
    if importance_val not in ("high", "medium", "low"):
        importance_val = "medium"
    prompt = get_prompt("RESTRUCTURE_TO_MD_PROMPT").format(
        reference_md=reference_md,
        raw_text=request.raw_text.strip(),
        user_type=request.doc_type,
        user_year=year_val or "(infer from content if possible, else omit)",
        user_importance=importance_val,
    )
    llm = ChatOpenAI(model=config.get_llm_model(), temperature=0)
    messages = [SystemMessage(content=prompt)]
    response = llm.invoke(messages)
    restructured = (response.content or "").strip()
    # Remove any leading/trailing code fence if the model wrapped output in ```md
    if restructured.startswith("```"):
        lines = restructured.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        restructured = "\n".join(lines)
    # Enforce user-provided type, year, importance in frontmatter (LLM sometimes ignores them)
    restructured = _inject_frontmatter_override(
        restructured,
        type_val=request.doc_type,
        year_val=year_val,
        importance_val=importance_val,
    )
    return {"restructured_md": restructured}


@app.post("/api/documents", dependencies=[AdminAuth])
def api_add_document(request: AddDocumentRequest):
    """Add a new document by markdown content."""
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty")
    result = add_document(
        content=request.content,
        filename=request.filename,
        doc_type=request.doc_type,
    )
    if result.get("error"):
        raise HTTPException(status_code=422, detail=result["error"])
    return result


@app.delete("/api/documents/{source}", dependencies=[AdminAuth])
def api_delete_document(source: str, doc_type: str | None = None):
    """Delete a document and its chunks by source filename."""
    return delete_document(source=source, doc_type=doc_type)


@app.post("/api/ingest", dependencies=[AdminAuth])
def api_ingest():
    """Re-ingest all documents from the data directory and rebuild the vector store."""
    try:
        from src.rag_ingestion import DATA_DIR
        from pathlib import Path

        documents = load_document()
        chunks = create_chunks_markdown(documents)
        vector_store = embed_chunks(chunks)
        reload_vectorstore(vector_store)

        # Sync every document to the Supabase `documents` table.
        # load_document() returns one Document per .md file; read the original
        # file from disk so we capture the frontmatter as well.
        synced = 0
        for doc in documents:
            filename = doc.metadata.get("source", "")
            doc_type = doc.metadata.get("doc_type", "misc")
            if not filename:
                continue
            file_path = next(Path(DATA_DIR).rglob(filename), None)
            content = file_path.read_text(encoding="utf-8") if file_path else doc.page_content
            try:
                supabase_client.table("documents").upsert(
                    {"filename": filename, "doc_type": doc_type, "content": content},
                    on_conflict="filename,doc_type",
                ).execute()
                synced += 1
            except Exception as sync_err:
                print(f"[api_ingest] documents sync warning for {filename}: {sync_err}")

        count_result = supabase_client.table("document_chunks").select("id", count="exact").execute()
        count = count_result.count or 0
        return {"chunks_count": count, "documents_synced": synced, "status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/prompts")
def api_get_prompts():
    """List all managed prompts with their current Supabase content."""
    return {"prompts": get_all_prompts()}


class PromptUpdateRequest(BaseModel):
    content: str


@app.put("/api/prompts/{key}", dependencies=[AdminAuth])
def api_update_prompt(key: str, request: PromptUpdateRequest):
    """Update a prompt by key. Returns the updated prompt and its default for comparison."""
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="content cannot be empty")
    success = update_prompt(key, request.content)
    if not success:
        raise HTTPException(status_code=404, detail=f"Unknown prompt key: {key}")
    return {"key": key, "status": "updated"}


@app.post("/api/prompts/{key}/reset", dependencies=[AdminAuth])
def api_reset_prompt(key: str):
    """Reset a prompt to its hardcoded default."""
    default = get_default_content(key)
    if not default:
        raise HTTPException(status_code=404, detail=f"Unknown prompt key: {key}")
    success = update_prompt(key, default)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to reset prompt")
    return {"key": key, "status": "reset", "content": default}


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

_eval_jobs: dict[str, dict] = {}


def _save_eval_result(result: dict) -> None:
    """Persist the latest eval result to the eval_results table."""
    try:
        supabase_client.table("eval_results").upsert(
            {
                "id": 1,  # single-row table — always overwrite the same row
                "status": result.get("status"),
                "finished_at": result.get("finished_at"),
                "result": result.get("result"),
            },
            on_conflict="id",
        ).execute()
    except Exception as e:
        print(f"[eval] Warning: could not persist result to Supabase: {e}")


def _load_eval_result() -> dict | None:
    """Load the last persisted eval result from the eval_results table."""
    try:
        row = (
            supabase_client.table("eval_results")
            .select("status, finished_at, result")
            .eq("id", 1)
            .execute()
        )
        rows = row.data or []
        if rows:
            return rows[0]
    except Exception as e:
        print(f"[eval] Warning: could not load result from Supabase: {e}")
    return None


@app.post("/api/evaluate")
def api_start_evaluation():
    """Start a background evaluation run. Returns a job_id to poll for results."""
    job_id = str(uuid.uuid4())[:8]
    _eval_jobs[job_id] = {"status": "running", "started_at": time.time(), "result": None, "error": None}

    config_snapshot = config.get_full_config()

    def run():
        try:
            tests = load_test_questions()
            llm_result = evaluate_LLM(tests)
            retrieval_result = evaluate_all(tests)
            result_payload = {
                "llm": llm_result.model_dump(),
                "retrieval": retrieval_result.model_dump(),
                "test_count": len(tests),
                "config_snapshot": config_snapshot,
            }
            _eval_jobs[job_id].update({
                "status": "done",
                "finished_at": time.time(),
                "result": result_payload,
            })
            _save_eval_result({
                "status": "done",
                "finished_at": time.time(),
                "result": result_payload,
            })
        except Exception as exc:
            _traceback.print_exc()
            _eval_jobs[job_id].update({"status": "error", "error": str(exc)})

    threading.Thread(target=run, daemon=True).start()
    return {"job_id": job_id, "status": "running"}


@app.get("/api/evaluate/latest")
def api_get_latest_evaluation():
    """Return the last completed evaluation result (survives server restarts)."""
    data = _load_eval_result()
    if not data:
        return {"status": "none"}
    return data


@app.get("/api/evaluate/{job_id}")
def api_get_evaluation(job_id: str):
    """Poll the status/result of an evaluation job."""
    job = _eval_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
