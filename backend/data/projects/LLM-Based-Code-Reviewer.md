---
type: project
title: LLM-based Bitbucket Code Reviewer
importance: high
year: 2025
tags: [llm, rag, code-review, automation, agent, dev-platform, serverless, prompt-engineering]
---

## 1. Overview

**Domain:** AI Developer Productivity / Code Automation

**Role:** AI Engineer / Full-stack Engineer

**Organization:** United Overseas Bank

**Summary:**

Built an automated LLM-powered code review platform integrated with Bitbucket to generate structured pull request feedback and interactive developer Q&A.

The system combines:

- LLM-based static analysis
- Cross-file retrieval (RAG)
- Interactive AI chat

## 2. Problem (Pain)

Manual pull request reviews caused:

- Inconsistent review quality across teams
- Missing deeper logic and security issues
- Slow review cycles
- No interactive clarification for comments

Key bottleneck:
Human reviewers cannot scale with increasing PR volume.

## 3. Solution (Architecture)

### High-Level Flow

Bitbucket PR

→ Webhook trigger

→ Diff extraction

→ RAG context building

→ LLM analysis

→ Structured review output

→ Interactive chat

### System Components

**Frontend**

- React / Next.js dashboard
- PR visualization
- AI chat interface

**Backend**

- Python Flask API
- Diff processing pipeline
- LLM orchestration layer

**Database**

- PostgreSQL
- PR metadata + chat memory

**LLM Layer**

- Groq API (Llama models)
- Prompt templates for review rubric

## 4. RAG Design (High-Value Section)

Goal:
Improve cross-file reasoning during PR review.

Retrieval strategy:

- Chunk by file
- Metadata tagging (language, file path)
- Diff-aware filtering

Context sources:

- Current PR diff
- Historical conversation memory
- Coding standards rubric

## 5. Prompt Engineering Strategy

Review rubric includes:

- Code correctness
- Security patterns
- SQL performance
- Java best practices

Optimization:

- Only analyze diffs (not full repo)
- Shortened prompts to reduce token usage
- Structured output format

## 6. Data Flow

Webhook triggered pipeline:

1. Receive PR webhook
2. Fetch diff from Bitbucket
3. Preprocess:
    - remove binary files
    - estimate token size
4. Chunk diff
5. Call LLM
6. Persist results

Interactive flow:

User → Chat UI → Backend → LLM → Response → Stored in DB

## 7. Tech Stack

**Backend**

- Python Flask
- SQLAlchemy
- PostgreSQL

**Frontend**

- Next.js
- React

**AI**

- Groq LLM API
- Prompt templates
- RAG retrieval

**Infra**

- Vercel deployment
- Serverless functions

**Security**

- Keycloak (OIDC + RBAC)

## 8. Challenges

### Large PR Token Limits

Problem:
Large diffs exceed LLM context window.

Solution:

- File-level chunking
- Two-pass summarization:
    - per-file review
    - global risk aggregation

### Cross-file Logic Loss

Problem:
Chunking breaks semantic relationships.

Solution:

- Metadata tagging
- Multi-stage reasoning

---

### External API Cost

Problem:
Repeated LLM calls increase cost.

Solution:

- Cache previous PR analysis
- Diff-only re-evaluation

---

## 9. Engineering Decisions (Interview Gold Section)

Why diff-only analysis?
→ reduces token usage and improves relevance.

Why serverless architecture?
→ low operational overhead for internal tooling.

Why Flask instead of FastAPI?
→ simplicity + faster prototyping.

Why Postgres memory?
→ persistent conversational context.

## 10. Performance Optimization

- Token estimation before LLM call
- Caching repeated PR results
- Skip binary files
- Structured prompts to reduce output tokens

## 11. Security Design

- Ignore sensitive files (.env etc.)
- RBAC via Keycloak
- Optional on-prem model support
- Webhook signature validation

## 12. Results (Business Impact)

- ~40% reduction in manual review time
- 10+ engineering teams onboarded
- Improved review consistency

## 13. System Design Extensions (Scaling Path)

Future improvements:

- Async job queue (Kafka / Redis)
- Streaming LLM responses
- Cross-repo knowledge retrieval
- Multi-model routing

## 14. Interview Snippets

**Q: How did you handle large diffs?**

A: Diff chunking + hierarchical summarization.

**Q: How does RAG help code review?**

A: Adds cross-file context and coding standards.

**Q: How would you scale the system?**

A: Introduce async queue and worker architecture.

## 15. Key Learnings

- LLM quality depends more on context than model size.
- Diff filtering is critical for token efficiency.
- Retrieval design matters more than prompt tuning.