"""
FastAPI server for the MyBestFriend chatbot.
Run with: uvicorn api_server:app --reload --host 0.0.0.0 --port 8000
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from rag_retrieval import generate_answer
from utils.config_loader import ConfigLoader

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
