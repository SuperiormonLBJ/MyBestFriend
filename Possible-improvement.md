# 🧠 Project: **ClearPath — AI-Powered Career Intelligence Platform**

---

## What It Does

ClearPath is a full-stack career coaching platform that analyzes a user's resume, LinkedIn profile, and job descriptions to provide **deeply personalized, AI-driven career guidance** — including skill gap analysis, interview prep, and real-time job market trend insights.

It goes far beyond a resume parser. It *understands* the user's career trajectory and acts like a personal career strategist.

---

## Real-World Problem It Solves

Job seekers spend dozens of hours tailoring resumes and prepping for interviews with generic advice. Recruiters reject 75%+ of resumes before a human reads them. ClearPath gives every candidate access to the kind of coaching previously reserved for expensive executive career consultants.

---

## HuggingFace Tasks Used

From the screenshots, the project integrates:

- **Document Question Answering** — parse and interrogate uploaded resumes/JDs
- **Text Classification** — classify job fit scores, seniority levels, industry tags
- **Sentence Similarity** — match resume skills to job description requirements semantically
- **Summarization** — condense long job descriptions into key requirements
- **Token Classification (NER)** — extract skills, companies, titles, and dates from resumes
- **Text Generation** — generate tailored cover letters and interview answer frameworks
- **Zero-Shot Classification** — categorize resumes into industries without labeled training data
- **Feature Extraction** — build embedding-based skill vectors for candidate-job matching

---

## Recommended Tech Stack

**Frontend**
- Next.js 14 (App Router) + TypeScript
- Tailwind CSS + shadcn/ui
- Framer Motion for dashboard animations

**Backend**
- FastAPI (Python) for HuggingFace inference orchestration
- Node.js + tRPC for frontend-backend type safety
- Celery + Redis for async job processing (resume analysis queues)

**AI/ML Layer**
- HuggingFace Inference API (serverless, no GPU needed)
- LangChain for chaining multi-step AI pipelines
- Pinecone or pgvector for semantic job-candidate matching

**Data & Storage**
- PostgreSQL (user profiles, job history)
- S3-compatible storage (resume file uploads)
- Upstash Redis (rate limiting, caching)

**Real-World APIs**
- LinkedIn Jobs API or RapidAPI job scrapers
- US Bureau of Labor Statistics API (salary & demand trends)
- GitHub API (for developers: auto-pull project highlights)

**Infrastructure**
- Docker + Docker Compose
- Railway or Render for deployment
- GitHub Actions CI/CD

---

## Architecture Highlights

```
User uploads resume (PDF)
        ↓
Token Classification (NER) → extracts skills, titles, companies
        ↓
Sentence Similarity → semantic match against live job postings
        ↓
Zero-Shot Classification → auto-detect industry & seniority
        ↓
Summarization → condense matched JDs into "what they really want"
        ↓
Text Generation → personalized cover letter + interview Q&A prep
        ↓
Dashboard → skill gap radar chart, match scores, trend graphs
```

---

## What Makes It Stand Out

| Feature | Why It's Impressive |
|---|---|
| Multi-model AI pipeline | Chains 6+ HuggingFace tasks in a single user flow |
| Semantic job matching | Goes beyond keyword matching using embeddings |
| Real-time labor market data | Integrates BLS API for live salary/demand context |
| Async processing | Celery queues handle heavy inference without blocking UX |
| Exportable reports | Users get a downloadable PDF career strategy report |

---

## Resume-Ready Impact Statement

> *"Built ClearPath, a full-stack AI career intelligence platform integrating 6 HuggingFace NLP models (NER, semantic similarity, summarization, text generation) with live job market APIs. Reduced average job application prep time by an estimated 70% through automated skill gap analysis and personalized cover letter generation. Architected async inference pipelines using FastAPI + Celery serving sub-3s results on resume parsing workflows."*

---

## Portfolio Value

- **Demonstrates end-to-end ownership** — frontend, backend, ML pipeline, infra
- **Solves a problem interviewers personally relate to**
- **Shows you can productionize AI**, not just prototype it
- **Easily extensible** — add voice mock interviews (ASR + Text-to-Speech tasks from the screenshots), video analysis, or a B2B recruiter dashboard for v2

---

**Estimated build time:** 8–10 weeks solo, 4–6 weeks with a partner. Ship an MVP at week 4 and iterate publicly on GitHub to show your commit history and growth.