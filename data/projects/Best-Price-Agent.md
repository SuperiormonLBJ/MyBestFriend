---
type: project
title: Best Price Notification Agent based on Fine-tuning and Multi-Agent
importance: high
year: 2026
tags: [llm, rag, fine-tuning, QLoRA, HuggingFace, Gradio, Llama, Weight]
---

## 1. Overview

**What is the project about?**  
A notification system that predicts best prices using AI, retrieval-augmented generation (RAG), and multi-agent orchestration.  
Designed to automate price monitoring and notification for products with improved accuracy over manual baselines.

## 2. Problem / Pain Points

- Human-curated price predictions are slow and inconsistent  
- Large product datasets make manual tracking infeasible  
- Existing AI models (e.g., GPT-4o) had higher prediction errors  

## 3. Actions Taken / Solution

- Fine-tuned **LLaMA-3.1-8B** using **QLoRA** on curated product datasets  
- Built **Chroma vector database** for product retrieval with optimized embeddings  
- Designed **multi-agent architecture**:
  - Planner → orchestrates tasks  
  - Scanner → retrieves product prices  
  - Price Predictor → forecasts best price  
  - Messenger → sends notifications  
- Delivered functional MVP using **Gradio** as frontend  
- Implemented query rewriting, re-ranking, and embedding optimizations for higher retrieval accuracy  

## 4. Technical Architecture

### Backend
- LLaMA-3.1-8B fine-tuned with QLoRA  
- Modal deployment for scalable inference  
- Chroma DB for RAG-based retrieval  
- Query optimization: rewriting + re-ranking  

### Frontend
- Gradio interface for demonstration and user interaction  
- Lightweight, fast prototyping of multi-agent workflow  

### Agent Orchestration
- Planner coordinates multi-agent tasks  
- Scanner retrieves product data  
- Price Predictor evaluates optimal pricing  
- Messenger delivers alerts  

## 5. Challenges & How They Were Overcome

- **Prediction accuracy:** Fine-tuned model reduced error 40% vs GPT-4o, 60% vs human baseline  
- **Vector retrieval coverage:** Achieved 0.92 MRR and 96% keyword coverage with embedding optimization  
- **Agent coordination:** Designed modular multi-agent system to handle task dependencies  

## 6. Business / Personal Impact

- Automated price tracking → faster decisions for end users  
- Improved accuracy over human labeling → reduces errors and manual effort  
- Demonstrates mastery of **RAG, multi-agent AI, and fine-tuning workflows**  

## 7. Future Improvements

- Add real-time product updates with streaming embeddings  
- Expand multi-agent coordination to support multiple product categories simultaneously  
- Integrate with notification channels (Slack, email) for production rollout  

## 8. Dependencies

- LLaMA-3.1-8B (model)  
- QLoRA (fine-tuning)  
- Chroma DB (RAG vector retrieval)  
- Modal (deployment)  
- Gradio (frontend MVP)  

## 9. Signals for RAG / Career Retrieval

- Multi-agent AI system design  
- Retrieval-augmented generation (RAG)  
- LLM fine-tuning and deployment  
- Vector DB design and optimization  
- End-to-end AI workflow implementation  