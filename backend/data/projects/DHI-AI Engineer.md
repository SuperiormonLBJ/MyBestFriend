---
type: career
title: AI Engineer – Intelligent Automation & RAG Systems
importance: high
year: 2024
tags: [ai-engineer, rag, llm, agents, automation, langchain, langgraph, n8n, production-ai]
---

## 1. Role Overview

**Position:** AI Engineer  
**Duration:** Jan 2024 – Present  
**Location:** Singapore (Hybrid)

Focus:
- Building production-grade **LLM + RAG systems**
- AI workflow automation using agent frameworks
- Backend infrastructure for AI services and evaluation pipelines

Worked alongside platform and backend teams at **[United Overseas Bank](chatgpt://generic-entity?number=0)**-scale engineering environments and applied similar production patterns to AI systems.

---

## 2. Key Projects

### 2.1 Personal Knowledge RAG Assistant (Multi-source Retrieval System)

**Problem / Pain Points**
- Personal knowledge (CV, notes, docs) scattered across formats  
- LLM responses lacked grounding and factual consistency  
- No evaluation loop for retrieval quality  

**Actions**
- Built an end-to-end **RAG pipeline** using:
  - LangChain for orchestration  
  - Vector DB for semantic retrieval  
  - FastAPI for serving inference APIs  
- Implemented:
  - document chunking strategies
  - embedding optimization
  - metadata filtering
- Designed **admin panel** to debug:
  - retrieved chunks  
  - similarity scores  
  - hallucination signals  

**Impact / Results**
- Improved answer grounding and factual consistency  
- Reduced hallucination via retrieval filtering + prompt control  
- Created reusable architecture for production AI assistants  

**Skills / Signals**
rag, langchain, embeddings, vector-db, prompt-engineering, fastapi

---

### 2.2 AI Workflow Automation with Agent Graph (LangGraph + n8n)

**Problem / Pain Points**
- Manual multi-step workflows for document processing and automation  
- Hard to visualize execution and control agent reasoning  

**Actions**
- Designed **multi-agent workflow architecture** using:
  - LangGraph for stateful agent orchestration  
  - n8n for external tool automation  
- Implemented:
  - tool-calling agents  
  - structured output pipelines  
  - retry + fallback logic  
- Built execution tracing to debug:
  - tool latency
  - prompt failures
  - retrieval issues

**Impact / Results**
- Automated multi-step workflows (document → retrieval → response)  
- Reduced manual processing effort via AI-driven pipelines  
- Created modular agent workflow reusable across projects  

**Skills / Signals**
ai-agents, langgraph, workflow-automation, tool-calling, orchestration

---

### 2.3 RAG Evaluation & Observability Pipeline

**Problem / Pain Points**
- Difficult to measure RAG quality in production  
- No automated evaluation loop for retrieval correctness  

**Actions**
- Implemented evaluation pipeline:
  - cosine similarity scoring
  - answer correctness checks
  - retrieval debugging UI
- Integrated structured logging for:
  - prompt versions
  - latency metrics
  - retrieval traces  

**Impact / Results**
- Enabled measurable RAG quality signals  
- Established evaluation workflow aligned with production AI practices  

**Skills / Signals**
rag-evaluation, llmops, observability, experimentation

---

## 3. Tech Stack

**LLM / AI**
- LangChain  
- LangGraph  
- OpenAI / Mistral models  

**Backend**
- Python  
- FastAPI  
- REST APIs  

**Data**
- Vector databases (FAISS / Chroma)  
- Embeddings pipelines  

**Automation**
- n8n  

**Frontend**
- Next.js  
- Tailwind  
- AI-native UI patterns

---

## 4. RAG Signals / Career Retrieval

- Production-oriented LLM system design  
- Retrieval-Augmented Generation pipelines  
- Multi-agent workflow orchestration  
- AI evaluation and observability (LLMOps mindset)  
- End-to-end AI system architecture (frontend → backend → inference)