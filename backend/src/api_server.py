"""
FastAPI server for the MyBestFriend chatbot.
Run with: uvicorn api_server:app --reload --host 0.0.0.0 --port 8000
"""
import threading
import time
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from rag_retrieval import generate_answer, get_knowledge_tree, reload_vectorstore
from utils.config_loader import ConfigLoader
from utils.prompts import get_reference_template
from utils.prompt_manager import get_prompt, get_all_prompts, update_prompt, get_default_content
from utils.supabase_client import supabase_client
from document_ops import delete_document, add_document
from rag_ingestion import load_document, create_chunks_markdown, embed_chunks, _parse_md_frontmatter
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
import traceback as _traceback
# Pre-import eval in the main thread so its module-level code (ConfigLoader, ChatOpenAI init)
# runs here, never inside a background thread where the shared Supabase client is not safe.
from eval import load_test_questions, evaluate_LLM, evaluate_all

config = ConfigLoader()
app = FastAPI(title="MyBestFriend API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    history: list[dict[str, str]] = []


class ChatResponse(BaseModel):
    answer: str


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    answer, _ = generate_answer(request.message, request.history)
    return ChatResponse(answer=answer)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/config")
def get_config():
    """Return full editable config (frontend + models), pulling latest from Supabase first."""
    config.reload()
    return config.get_full_config()


class ConfigUpdateRequest(BaseModel):
    app_name: str | None = None
    chat_title: str | None = None
    chat_subtitle: str | None = None
    input_placeholder: str | None = None
    empty_state_hint: str | None = None
    empty_state_examples: str | None = None
    embedding_model: str | None = None
    generator_model: str | None = None
    llm_model: str | None = None
    evaluator_model: str | None = None
    recipient_email: str | None = None


@app.post("/api/config/push")
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


@app.post("/api/restructure")
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


@app.post("/api/documents")
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


@app.delete("/api/documents/{source}")
def api_delete_document(source: str, doc_type: str | None = None):
    """Delete a document and its chunks by source filename."""
    return delete_document(source=source, doc_type=doc_type)


@app.post("/api/ingest")
def api_ingest():
    """Re-ingest all documents from the data directory and rebuild the vector store."""
    try:
        from rag_ingestion import DATA_DIR
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


@app.put("/api/prompts/{key}")
def api_update_prompt(key: str, request: PromptUpdateRequest):
    """Update a prompt by key. Returns the updated prompt and its default for comparison."""
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="content cannot be empty")
    success = update_prompt(key, request.content)
    if not success:
        raise HTTPException(status_code=404, detail=f"Unknown prompt key: {key}")
    return {"key": key, "status": "updated"}


@app.post("/api/prompts/{key}/reset")
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


@app.post("/api/evaluate")
def api_start_evaluation():
    """Start a background evaluation run. Returns a job_id to poll for results."""
    job_id = str(uuid.uuid4())[:8]
    _eval_jobs[job_id] = {"status": "running", "started_at": time.time(), "result": None, "error": None}

    def run():
        try:
            tests = load_test_questions()
            llm_result = evaluate_LLM(tests)
            retrieval_result = evaluate_all(tests)
            _eval_jobs[job_id].update({
                "status": "done",
                "finished_at": time.time(),
                "result": {
                    "llm": llm_result.model_dump(),
                    "retrieval": retrieval_result.model_dump(),
                    "test_count": len(tests),
                },
            })
        except Exception as exc:
            _traceback.print_exc()
            _eval_jobs[job_id].update({"status": "error", "error": str(exc)})

    threading.Thread(target=run, daemon=True).start()
    return {"job_id": job_id, "status": "running"}


@app.get("/api/evaluate/{job_id}")
def api_get_evaluation(job_id: str):
    """Poll the status/result of an evaluation job."""
    job = _eval_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
