"""
FastAPI server for the MyBestFriend chatbot.
Run with: uvicorn api_server:app --reload --host 0.0.0.0 --port 8000
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from rag_retrieval import generate_answer

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
