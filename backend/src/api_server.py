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
from .eval_dataset_store import (
    load_eval_rows_from_supabase,
    save_eval_rows_to_supabase,
    clear_eval_rows,
    _row_to_test_question,
)
from utils.base_models import TestQuestion

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
    thread_id: str | None = None   # for LangGraph checkpointing / HITL
    mode: str | None = None        # override flags: "multi_agent", "graph", "direct"


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
    technical_requirements: list[str] = []
    culture: list[str] = []
    keywords: list[str] = []


class JobPrepFullResponse(JobPrepResponse):
    resume_suggestions: str
    interview_questions: str


def _prepare_job_context(job_description: str, word_limit_override: int | None = None):
    """Shared helper to extract job requirements, RAG context, and formatting strings."""
    word_limit = (
        word_limit_override
        if word_limit_override is not None
        else config.get_cover_letter_word_limit()
    )
    if not job_description or not job_description.strip():
        raise HTTPException(status_code=400, detail="job_description is required")

    reqs = extract_job_requirements(job_description)
    _, context = get_job_context(job_description, reqs)
    tech_reqs = reqs.get("technical_requirements") or reqs.get("requirements") or []
    culture = reqs.get("culture") or []
    keywords = reqs.get("keywords") or []
    frontend_cfg = config.get_frontend_config()
    owner_name = frontend_cfg.get("owner_name", "the candidate")
    owner_profile = f"Candidate: {owner_name}"
    requirements_str = (
        "\n".join(f"- {r}" for r in tech_reqs[:15]) if tech_reqs else "None extracted."
    )
    keywords_str = ", ".join(keywords[:25]) if keywords else "None extracted."
    safe_context = context[:12000] if context else "No relevant context found."

    return {
        "word_limit": word_limit,
        "tech_reqs": tech_reqs,
        "culture": culture,
        "keywords": keywords,
        "owner_profile": owner_profile,
        "requirements_str": requirements_str,
        "keywords_str": keywords_str,
        "safe_context": safe_context,
    }


def _resolve_mode(request: ChatRequest) -> str:
    """Determine execution mode: multi_agent > graph > direct (in priority order)."""
    if request.mode:
        return request.mode
    if config.get_use_multi_agent():
        return "multi_agent"
    if config.get_use_graph():
        return "graph"
    return "direct"


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    mode = _resolve_mode(request)
    if mode == "multi_agent":
        from src.multi_agent_graph import run_multi_agent_graph
        answer, _, no_info, sources = run_multi_agent_graph(
            request.message, request.history, thread_id=request.thread_id
        )
    elif mode == "graph":
        from src.conversation_graph import run_graph
        answer, _, no_info, sources = run_graph(request.message, request.history)
    else:
        answer, _, no_info, sources = generate_answer(request.message, request.history)
    return ChatResponse(answer=answer, no_info=no_info, sources=sources)


@app.post("/api/chat/stream")
def chat_stream(request: ChatRequest):
    mode = _resolve_mode(request)

    def event_stream():
        if mode == "multi_agent":
            from src.multi_agent_graph import run_multi_agent_graph_stream
            gen = run_multi_agent_graph_stream(
                request.message, request.history, thread_id=request.thread_id
            )
        else:
            gen = generate_answer_stream(request.message, request.history)
        for event in gen:
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
    try:
        ctx = _prepare_job_context(request.job_description, request.word_limit)
        prompt = get_prompt("COVER_LETTER_PROMPT").format(
            job_description=request.job_description.strip()[:8000],
            requirements=ctx["requirements_str"],
            keywords=ctx["keywords_str"],
            context=ctx["safe_context"],
            owner_profile=ctx["owner_profile"],
            word_limit=ctx["word_limit"],
        )
        llm = ChatOpenAI(model=config.get_generator_model())
        response = llm.invoke([
            SystemMessage(content=prompt),
            HumanMessage(content="Generate the cover letter now."),
        ])
        cover_letter = (response.content or "").strip()
        return JobPrepResponse(
            cover_letter=cover_letter,
            word_limit=ctx["word_limit"],
            technical_requirements=ctx["tech_reqs"],
            culture=ctx["culture"],
            keywords=ctx["keywords"],
        )
    except HTTPException:
        raise
    except Exception as e:
        _traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/job/prepare", response_model=JobPrepFullResponse)
def api_job_prepare(request: JobPrepRequest):
    """Run full job preparation once: analysis, cover letter, resume suggestions, interview questions."""
    try:
        ctx = _prepare_job_context(request.job_description, request.word_limit)
        llm = ChatOpenAI(model=config.get_generator_model())

        cover_prompt = get_prompt("COVER_LETTER_PROMPT").format(
            job_description=request.job_description.strip()[:8000],
            requirements=ctx["requirements_str"],
            keywords=ctx["keywords_str"],
            context=ctx["safe_context"],
            owner_profile=ctx["owner_profile"],
            word_limit=ctx["word_limit"],
        )
        cover_resp = llm.invoke([
            SystemMessage(content=cover_prompt),
            HumanMessage(content="Generate the cover letter now."),
        ])
        cover_letter = (cover_resp.content or "").strip()

        resume_prompt = get_prompt("RESUME_SUGGESTIONS_PROMPT").format(
            job_description=request.job_description.strip()[:8000],
            requirements=ctx["requirements_str"],
            keywords=ctx["keywords_str"],
            context=ctx["safe_context"],
        )
        resume_resp = llm.invoke([
            SystemMessage(content=resume_prompt),
            HumanMessage(content="List resume improvement suggestions now."),
        ])
        resume_suggestions = (resume_resp.content or "").strip()

        interview_prompt = get_prompt("INTERVIEW_QUESTIONS_PROMPT").format(
            job_description=request.job_description.strip()[:8000],
            requirements=ctx["requirements_str"],
            keywords=ctx["keywords_str"],
            context=ctx["safe_context"],
        )
        interview_resp = llm.invoke([
            SystemMessage(content=interview_prompt),
            HumanMessage(content="Generate interview questions and guidance now."),
        ])
        interview_questions = (interview_resp.content or "").strip()

        return JobPrepFullResponse(
            cover_letter=cover_letter,
            word_limit=ctx["word_limit"],
            technical_requirements=ctx["tech_reqs"],
            culture=ctx["culture"],
            keywords=ctx["keywords"],
            resume_suggestions=resume_suggestions,
            interview_questions=interview_questions,
        )
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
_eval_results: dict[str, dict] = {}  # multi-agent eval job results


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


@app.get("/api/eval/dataset")
def api_get_eval_dataset():
    """Return all eval dataset rows for the current owner."""
    tests = load_eval_rows_from_supabase()
    return [
        {
            "question": t.question,
            "ground_truth": t.ground_truth,
            "category": t.category,
            "keywords": t.keywords,
        }
        for t in tests
    ]


class EvalDatasetUpdateRequest(BaseModel):
    items: list[dict]


@app.put("/api/eval/dataset", dependencies=[AdminAuth])
def api_put_eval_dataset(request: EvalDatasetUpdateRequest):
    """Replace the eval dataset with the provided items."""
    tests: list = []
    for item in request.items:
        tests.append(_row_to_test_question(item))
    save_eval_rows_to_supabase(tests, replace=True)
    return {"count": len(tests)}


@app.post("/api/eval/dataset/clear", dependencies=[AdminAuth])
def api_clear_eval_dataset():
    """Clear all eval dataset rows for the current owner."""
    clear_eval_rows()
    return {"status": "cleared"}


class EvalDatasetUploadRequest(BaseModel):
    fileText: str


@app.post("/api/eval/dataset/upload", dependencies=[AdminAuth])
def api_upload_eval_dataset(request: EvalDatasetUploadRequest):
    """Upload a JSONL file content and replace the eval dataset."""
    lines = request.fileText.splitlines()
    tests: list[TestQuestion] = []
    for idx, line in enumerate(lines, start=1):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except Exception:
            raise HTTPException(status_code=400, detail=f"Invalid JSON on line {idx}")
        try:
            tests.append(_row_to_test_question(data))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid record on line {idx}: {e}")

    save_eval_rows_to_supabase(tests, replace=True)
    return {"count": len(tests)}


@app.get("/api/eval/dataset/download")
def api_download_eval_dataset():
    """Download the current eval dataset as JSONL."""
    tests = load_eval_rows_from_supabase()

    def iter_lines():
        for t in tests:
            obj = {
                "question": t.question,
                "ground_truth": t.ground_truth,
                "category": t.category,
                "keywords": t.keywords or [],
            }
            yield json.dumps(obj, ensure_ascii=False) + "\n"

    return StreamingResponse(
        iter_lines(),
        media_type="text/plain",
        headers={"Content-Disposition": 'attachment; filename="eval_data.jsonl"'},
    )


@app.get("/api/evaluate/{job_id}")
def api_get_evaluation(job_id: str):
    """Poll the status/result of an evaluation job (regular or multi-agent)."""
    job = _eval_jobs.get(job_id) or _eval_results.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


class EvalGenerateRequest(BaseModel):
    n: int | None = None
    mode: str | None = "replace"


@app.post("/api/eval/dataset/generate", dependencies=[AdminAuth])
def api_generate_eval_dataset(request: EvalGenerateRequest):
    """AI-generate eval dataset rows based on existing knowledge documents."""
    n = request.n or 20
    mode = (request.mode or "replace").lower()
    if mode not in ("replace", "append"):
        mode = "replace"

    try:
        # Sample chunks from the full RAG knowledge base
        resp = (
            supabase_client.table("document_chunks")
            .select("content, metadata")
            .limit(60)
            .execute()
        )
        rows = resp.data or []
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to load knowledge context: {e}")

    if not rows:
        raise HTTPException(status_code=400, detail="No knowledge context available to generate eval data.")

    parts: list[str] = []
    for row in rows:
        meta = row.get("metadata") or {}
        doc_type = meta.get("doc_type", "misc")
        title = meta.get("title") or meta.get("source") or "Untitled"
        year = meta.get("year")
        header = f"[{doc_type}] {title}"
        if year:
            header += f" ({year})"
        content = row.get("content", "")
        parts.append(f"{header}\n{content}")
    context = "\n\n---\n\n".join(parts)

    base_prompt = get_prompt("EVAL_DATASET_GENERATOR_PROMPT")
    system_text = base_prompt.format(context=context[:12000])

    llm = ChatOpenAI(model=config.get_generator_model())
    response = llm.invoke(
        [
            SystemMessage(content=system_text),
            HumanMessage(content="Generate the evaluation dataset JSON now."),
        ]
    )
    raw = (response.content or "").strip()

    # Best-effort: strip surrounding fences
    if raw.startswith("```"):
        lines = raw.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        raw = "\n".join(lines).strip()

    try:
        data = json.loads(raw)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model returned invalid JSON: {e}")

    if not isinstance(data, list):
        raise HTTPException(status_code=500, detail="Model output must be a JSON array.")

    tests: list[TestQuestion] = []
    for idx, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            continue
        try:
            tests.append(_row_to_test_question(item))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Invalid item at index {idx}: {e}")

    if not tests:
        raise HTTPException(status_code=500, detail="No valid eval rows generated.")

    replace = mode == "replace"
    if not replace:
        existing = load_eval_rows_from_supabase()
        tests = existing + tests

    save_eval_rows_to_supabase(tests, replace=True)
    return {"status": "ok", "count": len(tests), "mode": mode}


# ---------------------------------------------------------------------------
# Multi-agent endpoints
# ---------------------------------------------------------------------------

@app.get("/api/agent/graph")
def api_agent_graph():
    """Return the multi-agent graph topology as JSON. Useful for visualisation and demos."""
    from src.multi_agent_graph import get_graph_topology
    return get_graph_topology()


@app.get("/api/agent/trace/{run_id}")
def api_agent_trace(run_id: str):
    """Retrieve the full agent trace for a given run_id from agent_run_traces."""
    try:
        result = supabase_client.table("agent_run_traces").select("*").eq("run_id", run_id).execute()
        rows = result.data or []
        if not rows:
            raise HTTPException(status_code=404, detail=f"No trace found for run_id={run_id}")
        return rows[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agent/pending-reviews")
def api_agent_pending_reviews(_: None = AdminAuth):
    """List agent graph runs that have requested human-in-the-loop review."""
    try:
        result = (
            supabase_client.table("agent_run_traces")
            .select("run_id, thread_id, query, created_at")
            .execute()
        )
        # In a real HITL setup, interrupted runs would have a `status=pending_review` column.
        # For now, return all recent traces as a demonstration.
        rows = result.data or []
        return {"pending": rows[:20]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agent/resume/{thread_id}")
def api_agent_resume(thread_id: str, body: dict, _: None = AdminAuth):
    """
    Resume a paused (HITL-interrupted) graph run from its checkpoint.
    Body: {approved: bool, modified_answer: str | None}
    """
    approved = body.get("approved", True)
    if not approved:
        return {"status": "rejected", "thread_id": thread_id}

    if not config.get_hitl_enabled():
        raise HTTPException(status_code=400, detail="HITL is not enabled (HITL_ENABLED=false)")

    try:
        from src.multi_agent_graph import get_multi_agent_graph_with_checkpointing
        g = get_multi_agent_graph_with_checkpointing()
        # Resume from checkpoint by invoking with None input and the thread_id config
        result = g.invoke(None, config={"configurable": {"thread_id": thread_id}})
        return {
            "status": "resumed",
            "thread_id": thread_id,
            "answer": result.get("answer", ""),
            "no_info": result.get("no_info", True),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resume failed: {e}")


@app.post("/api/evaluate/multi-agent")
def api_evaluate_multi_agent(_: None = AdminAuth):
    """
    Trigger a background multi-agent evaluation job.
    Returns a job_id immediately; poll GET /api/evaluate/{job_id} for results.
    Multi-agent eval runs the graph with USE_MULTI_AGENT=true and measures:
    - Agent Routing Accuracy (ARA)
    - Agent Context Redundancy Ratio (ACRR)
    - Per-agent MRR
    - Synthesis faithfulness
    """
    job_id = str(uuid.uuid4())

    def _run_eval():
        try:
            from src.multi_agent_eval import evaluate_multi_agent_all
            tests = load_test_questions()
            if not tests:
                _eval_results[job_id] = {"status": "error", "error": "No test questions found"}
                return
            report = evaluate_multi_agent_all(tests)
            payload = {
                "status": "done",
                "finished_at": time.time(),
                "result": report.model_dump(),
            }
            _eval_results[job_id] = payload
            try:
                supabase_client.table("eval_results").upsert(
                    {"id": 2, **payload},
                    on_conflict="id",
                ).execute()
            except Exception as db_err:
                print(f"[multi-agent eval] DB write warning (non-fatal): {db_err}")
        except Exception as e:
            _eval_results[job_id] = {"status": "error", "error": str(e)}

    _eval_results[job_id] = {"status": "running"}
    threading.Thread(target=_run_eval, daemon=True).start()
    return {"job_id": job_id, "status": "running"}
