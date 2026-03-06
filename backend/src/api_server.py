"""
FastAPI server for the MyBestFriend chatbot.
Run with: uvicorn api_server:app --reload --host 0.0.0.0 --port 8000
"""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from rag_retrieval import generate_answer, get_knowledge_tree, reload_vectorstore
from utils.config_loader import ConfigLoader
from utils.prompts import RESTRUCTURE_TO_MD_PROMPT
from document_ops import delete_document, add_document
from rag_ingestion import load_document, create_chunks_markdown, embed_chunks, _parse_md_frontmatter
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

config = ConfigLoader()
BACKEND_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_ROOT / "data"

# One reference .md per doc_type so the LLM follows the right structure
REFERENCE_BY_TYPE = {
    "career": DATA_DIR / "career" / "NUS-Research-Engineer.md",
    "projects": DATA_DIR / "projects" / "NUS-Master-Project.md",
    "project": DATA_DIR / "projects" / "NUS-Master-Project.md",
    "cv": DATA_DIR / "cv" / "cv.md",
    "personal": DATA_DIR / "personal" / "hobby.md",
    "misc": DATA_DIR / "career" / "NUS-Research-Engineer.md",
}
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
    """Return full editable config (frontend + models) from config.yaml."""
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


def _get_reference_md(doc_type: str) -> str:
    """Load reference markdown for the given doc_type so the LLM follows the right structure."""
    path = REFERENCE_BY_TYPE.get(doc_type) or REFERENCE_BY_TYPE.get("career")
    if path and path.exists():
        return path.read_text(encoding="utf-8")
    return """---
type: career
title: Example Role
importance: high
year: 2023
tags: [example, role]
---

## 1. Role Overview
**Position:** ...
**Duration:** ...
**Location:** ...

## 2. Key Projects
### 2.1 Project Name
**Problem / Pain Points**
**Actions**
**Impact / Results**
**Skills / Signals**

## 3. Publications
## 4. RAG Signals / Career Retrieval
"""


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
    reference_md = _get_reference_md(request.doc_type)
    year_val = (request.year or "").strip() or None
    importance_val = (request.importance or "medium").strip().lower()
    if importance_val not in ("high", "medium", "low"):
        importance_val = "medium"
    prompt = RESTRUCTURE_TO_MD_PROMPT.format(
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
        documents = load_document()
        chunks = create_chunks_markdown(documents)
        vector_store = embed_chunks(chunks)
        reload_vectorstore(vector_store)
        count = vector_store._collection.count()
        return {"chunks_count": count, "status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
