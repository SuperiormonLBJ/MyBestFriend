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

## Setup

1. Install dependencies: `uv sync`
2. Configure `.env` with `OPENAI_API_KEY`
3. Configure `config.yaml` for models and parameters
4. Run ingestion to populate vector database
5. Launch application

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
