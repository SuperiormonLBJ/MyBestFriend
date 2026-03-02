"""
FastAPI server for the MyBestFriend chatbot.
Run with: uvicorn api_server:app --reload --host 0.0.0.0 --port 8000
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from rag_retrieval import generate_answer, get_knowledge_tree, reload_vectorstore
from utils.config_loader import ConfigLoader
from document_ops import delete_document, add_document
from rag_ingestion import load_document, create_chunks_markdown, embed_chunks

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
