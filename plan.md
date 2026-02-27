Personal Digital Twin (Grounded RAG System)

⸻

0. Project Objective

Build a grounded personal RAG chatbot that:
	•	Answers only using Beiji’s documented data
	•	Never hallucinates
	•	Always cites sources
	•	Notifies Beiji when answer is unknown
	•	Demonstrates production-grade RAG engineering

⸻

1. Project Setup (Using uv)

- [X] Step 1 — Initialize Project
  - [x] Run `uv init MyBestFriend`
  - [x] Navigate to project directory

- [x] Step 2 — Add Dependencies
  - [x] Install: `uv add openai chromadb pinecone-client fastapi uvicorn ragas pydantic python-dotenv tiktoken PyPDF2 sentence-transformers pyyaml`

- [x] Step 3 — Environment Variables
  - [x] Create `.env` file with:
    - [x] OPENAI_API_KEY=
    - [x] PINECONE_API_KEY=
    - [x] RECIPIENT_EMAIL=

- [x] Step 4 — Config File
  - [x] Create `config.yaml` with:
    - [x] chunk_size: 400
    - [x] overlap: 75
    - [x] top_k: 6
    - [x] similarity_threshold: 0.8
    - [x] embedding_model: text-embedding-3-large
    - [x] llm_model: gpt-4.1, gpt-4.1-mini for testing first
    - [x] vector_db: chroma


⸻

1.5. Config Loader (src/config_loader.py)

- [x] Implement `src/config_loader.py`:
  - [x] Load config.yaml
  - [x] Parse configuration values
  - [ ] Provide config access to other modules
  - [x] Validate config values -> no need for now

⸻

2. Folder Structure

- [x] Create folder structure:
  - [x] `src/` directory
  - [x] `prompts/` directory
  - [x] `evaluation/` directory
  - [x] `data/` directory
  - [x] Create all source files:
    - [ ] `src/main.py` (FastAPI entrypoint)
    - [ ] `src/engine.py` (RAG orchestrator)
    - [ ] `src/retriever.py`
    - [ ] `src/vectorstore.py`
    - [ ] `src/embedding.py`
    - [ ] `src/chunking.py`
    - [ ] `src/ingestion.py`
    - [ ] `src/formatter.py`
    - [ ] `src/safety.py`
    - [ ] `src/validator.py` (Grounding validator)
    - [ ] `src/logging.py` (Observability)
    - [ ] `src/tools.py` (Notify_Unknown_Question)
    - [ ] `src/config_loader.py`
  - [ ] `prompts/system_prompt.txt` (create with system instructions)
  - [ ] `evaluation/eval.py`
  - [ ] `evaluation/golden_set.json`
  - [ ] Place data files in `data/`:
    - [ ] `data/cv.pdf`
    - [ ] `data/linkedin.txt`
    - [ ] `data/website.html`


⸻

3. Data Ingestion (src/ingestion.py)

- [x] Implement `src/ingestion.py`:
  - [ ] Load CV (PDF)
  - [ ] Load LinkedIn (TXT)
  - [ ] Load Website (HTML)
  - [ ] Clean text but preserve headers
  - [x] MD file
  - [ ] Attach metadata:
    - [x] source
    - [x] doc_type
    - [ ] section
    - [ ] timestamp


⸻

4. Chunking Strategy (src/chunking.py)

- [ ] Implement `src/chunking.py`:
  - [ ] Split by headings → semantic paragraphs
        we are not using RecursiveCharacter here since that is more for unstructured/long text, here we have sections and bounderies. so RecursiveCharacter will only mix up the topics.
  - [ ] Chunk size = 450 tokens
  - [ ] Overlap = 75 tokens
  - [ ] One chunk = one logical unit (project/job/skill group)

⸻

5. Embedding Layer (src/embedding.py)

- [ ] Implement `src/embedding.py`:
  - [ ] Use text-embedding-3-large
  - [ ] Implement batch embedding
  - [ ] Cache embeddings locally

⸻

6. Vector DB Abstraction (src/vectorstore.py)

- [ ] Implement `src/vectorstore.py`:
  - [ ] Create Abstract Base Class
  - [ ] Implement Chroma implementation
  - [ ] Implement Pinecone implementation
  - [ ] Switch via config.yaml

⸻

7. Retrieval Pipeline (src/retriever.py)

- [ ] Implement `src/retriever.py`:
  - [ ] Retrieve top_k = 6
  - [ ] Drop chunks below similarity threshold
  - [ ] Sort by similarity
  - [ ] Optional reranking

⸻

8. RAG Orchestrator (src/engine.py)

- [ ] Implement `src/engine.py` with flow:
  - [ ] User Question input
  - [ ] Scope Check (safety.py)
  - [ ] Retrieval
  - [ ] Low confidence detection → Notify Tool
  - [ ] Context Assembly
  - [ ] LLM Call
  - [ ] Grounding Validator integration
  - [ ] Formatter integration


⸻

9. Grounding Validator (src/validator.py) 🔥

- [ ] Implement `src/validator.py`:
  - [ ] Verify key claims exist in retrieved context
  - [ ] If mismatch → reject answer and trigger fallback

⸻

10. Guardrails (src/safety.py)

- [ ] Implement `src/safety.py`:
  - [ ] Out-of-scope detector
  - [ ] Conflict detector (dates/projects mismatch)
  - [ ] Hard/Soft red-line placeholders

⸻

11. Tools (src/tools.py)

- [ ] Implement `src/tools.py`:
  - [ ] Notify_Unknown_Question function
  - [ ] Trigger when similarity score < threshold
  - [ ] Trigger when grounding validation fails
  - [ ] Trigger when question is out-of-scope

⸻

12. Formatter (src/formatter.py)

- [ ] Implement `src/formatter.py`:
  - [ ] Format answer text
  - [ ] Format sources with citations:
    - [ ] [1] CV — AI Projects
    - [ ] [2] LinkedIn — Work Experience


⸻

13. Observability (src/logging.py) 🔥

- [ ] Implement `src/logging.py`:
  - [ ] Log user query
  - [ ] Log retrieved chunks
  - [ ] Log similarity scores
  - [ ] Log token usage
  - [ ] Log LLM latency

⸻

14. API Layer (src/main.py)

- [ ] Implement `src/main.py`:
  - [ ] FastAPI app setup
  - [ ] POST /chat endpoint
  - [ ] Request model: `{"question": "text"}`
  - [ ] Response handling


⸻

15. Evaluation (evaluation/eval.py)

- [ ] Implement `evaluation/eval.py`:
  - [ ] Create golden dataset (`evaluation/golden_set.json`)
  - [ ] Run RAGAS metrics:
    - [ ] Faithfulness >0.9
    - [ ] Context Precision >0.85
    - [ ] Answer Relevance >0.85


⸻

16. Non-Functional Requirements
	•	Low latency
	•	Modular DB switching
	•	Embedding cache
	•	Observability enabled

⸻

17. Build Order

- [ ] 1. Ingestion + Chroma
- [ ] 2. Retrieval working
- [ ] 3. Chat loop
- [ ] 4. Grounding validator
- [ ] 5. Guardrails
- [ ] 6. Evaluation
- [ ] 7. Pinecone migration
- [ ] 8. Logging

⸻

✅ Completion Criteria

Project is complete when:
- [ ] Answers are always grounded
- [ ] Citations shown
- [ ] Unknown questions trigger notification
- [ ] RAGAS targets met
- [ ] API functional


allow user to delete with local deployemtn admin portal
finetune on model and parameters
generate eval themselves
check on eval dashboard and see the result

