# MyBestFriend - Personal Digital Twin

A grounded RAG chatbot & agent that answers questions about User using only documented data, with source citations and unknown question detection.

## Objective

Build a production-grade RAG system that:
- Answers only from documented data (no hallucinations)
- Always cites sources
- Notifies when information is unavailable
- Demonstrates production-grade RAG engineering

## Key Features

- **Grounded Responses**: All answers verified against source documents
- **Source Citations**: Every response includes document references
- **Unknown Detection**: Alerts when questions can't be answered
- **Modular Architecture**: Configurable vector database and models

## System Flow

1. **Ingestion**: Load and chunk documents with metadata
2. **Embedding**: Generate vector embeddings and store in database
3. **Retrieval**: Semantic search with similarity filtering
4. **Generation**: LLM generates answer from retrieved context
5. **Validation**: Verify answer is grounded in retrieved context
6. **Formatting**: Format response with citations

**Repo layout**: Frontend (Next.js) lives in `frontend/`; backend (FastAPI + RAG) lives in `backend/` with its own `pyproject.toml` and `uv.lock` so the two halves are independent.

## Setup

1. **Backend**: `cd backend && uv sync`. Configure `backend/src/.env` and `backend/config.yaml`.
2. **Frontend**: `cd frontend && npm install`.
3. Run backend: `cd backend && uv run uvicorn src.api_server:app --reload --host 0.0.0.0 --port 8000`.
4. Run frontend: `cd frontend && npm run dev`.
5. Configure ingestion and launch as needed.

## Configuration

Key parameters:
- Chunk size and overlap
- Top-K retrieval count
- Similarity threshold
- Embedding and LLM models
- Vector database backend

## Evaluation

System evaluated using RAGAS metrics:
- Faithfulness >0.9
- Context Precision >0.85
- Answer Relevance >0.85

## Planned Enhancements

- Advanced chunking strategies (section-based, semantic)
- Grounding validator for claim verification
- Safety guardrails for out-of-scope detection
- Observability and logging
- Multi-vector database support
