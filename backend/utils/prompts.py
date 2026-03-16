LINKEDIN_PROMPT = """
You are a text cleaning and summarization assistant. 

I will provide you with a raw text dump from a LinkedIn page. Your task is to:

1. Remove all unnecessary website text, boilerplate, and repeated login/signup prompts.
2. Remove all \n, excessive spaces, and strange characters.
3. Extract only the **personal profile information** of the user, including:
   - Name
   - Headline / Summary
   - Location
   - Connections / Followers (optional)
   - Current Experience (Job Title + Company + Years)
   - Past Experience (Job Title + Company + Years)
   - Education (School + Degree + Years)
   - Certifications or Courses
   - Languages
   - Projects or notable achievements
4. Present the information in a **clean, readable, structured format**, like:
   
   Name: ...
   Headline: ...
   Location: ...
   Current Experience: ...
   Past Experience: ...
   Education: ...
   Certifications: ...
   Languages: ...
   Projects: ...
   
5. Ignore any text that is not part of the user profile (e.g., "Sign in", "Join now", LinkedIn navigation, footer, ads, etc.).
"""

SYSTEM_PROMPT_GENERATOR = """
You are a helpful assistant that can answer questions about an user's profile and daily life.
This response is used for a user to know more about the user's profile and daily life from a HR perspective.

You are given a question and a context retrieved from a knowledge base.
Answer the question using ONLY the information in the provided context. Do not use any prior knowledge.

CRITICAL RULE: If the context does not contain the specific information needed to answer the question, you MUST output ONLY the following token on a line by itself at the very end of your response, with no other text after it:
[[NO_INFO]]

Example of when to use [[NO_INFO]]:
- Question asks about a specific score, credential, or fact not mentioned anywhere in the context.
- You cannot find a direct or indirect answer in the context.

Do NOT add [[NO_INFO]] if the context contains enough information to give a meaningful answer.

Context:
{context}
"""

SYSTEM_PROMPT_RERANKER = """
You are a document re-ranker.
You are provided with a question and a list of relevant chunks of text from a query of a knowledge base.
The chunks are provided in the order they were retrieved; this should be approximately ordered by relevance, but you may be able to improve on that.
You must rank order the provided chunks by relevance to the question, with the most relevant chunk first.
Reply only with the list of ranked chunk ids, nothing else. Include all the chunk ids you are provided with, reranked.
"""

SYSTEM_PROMPT_EVALUATOR_GENERATOR = """
You are a helpful assistant that can answer questions about the user's CV and hobbies.
You are given a question and a context.
You need to evaluate the retrieval results based on the context.
User question:
{question}

Generated answer:
{generated_answer}

Golden answer:
{ground_truth}

Evaluation criteria:
- Accuracy: How many of the retrieval results are correct?
- Relevance: How relevant are the retrieval results to the question?
- Completeness: How complete are the retrieval results?
- Confidence: How confident are you in the retrieval results?
- Score: The average of accuracy, relevance, completeness

Return in the following format:
{{
    "accuracy": 3,
    "relevance": 2,
    "completeness": 4,
    "confidence": 0.9,
    "feedback": "The retrieval results is not relevant to the question but correct",
    "score": 3
}}
"""

REWRITE_PROMPT = """
You are a search query optimizer for a RAG system.You are about to look up information in a Knowledge Base to answer the user's question.

Rewrite the user question into a clear, standalone query
that maximizes keyword matching and retrieval accuracy.

Rules:
- Keep original meaning
- Expand abbreviations
- Replace pronouns with explicit entities
- Add important technical terms if implied
- Do NOT answer the question

Respond only with a short, refined question that you will use to search the Knowledge Base.
It should be a VERY short specific question most likely to surface content. Focus on the question details.
IMPORTANT: Respond ONLY with the precise knowledgebase query, nothing else.
"""

# ──────────────────────────────────────────────────────────────────────────────
# Inline reference templates — one per doc_type.
# These are self-contained and never depend on any files on disk, so they work
# for any fresh setup that has no existing data documents.
# ──────────────────────────────────────────────────────────────────────────────

REFERENCE_TEMPLATES: dict[str, str] = {
    "career": """\
---
type: career
title: <Generated: job title or role name>
importance: <user-provided>
year: <user-provided or inferred>
tags: [<generated kebab-case keywords>]
---

## 1. Role Overview

**Position:** <Job title>
**Duration:** <Start – End, e.g. Jan 2022 – Dec 2023>
**Location:** <City / Remote>

Focus:
- <Main responsibility 1>
- <Main responsibility 2>

## 2. Key Projects

### 2.1 <Project or Initiative Name>

**Problem / Pain Points**
- <What was broken, missing, or inefficient>

**Actions**
- <What was built or done>

**Impact / Results**
- <Quantified outcome or improvement>

**Skills / Signals**
<keyword1>, <keyword2>, <keyword3>

### 2.2 <Another Project>

**Problem / Pain Points**
- ...

**Actions**
- ...

**Impact / Results**
- ...

**Skills / Signals**
<keyword1>, <keyword2>

## 3. Publications

(List any papers, conference talks, or reports. Omit if none.)

## 4. RAG Signals / Career Retrieval

- <Retrieval-friendly phrase 1>
- <Retrieval-friendly phrase 2>
- <Tech stack keywords>
""",

    "project": """\
---
type: project
title: <Generated: project name>
importance: <user-provided>
year: <user-provided or inferred>
tags: [<generated kebab-case keywords>]
---

## 1. Overview

**Domain:** <e.g. Computer Vision / FinTech / NLP>
**Role:** <Your role on the project>
**Duration:** <e.g. 3 months / academic project / side project>

**Summary:**
<One or two sentences describing what the project does and why it matters.>

## 2. Problem (Pain)

<Describe the core problem being solved. Include pain points and why existing solutions were insufficient.>

Challenges:
- <Challenge 1>
- <Challenge 2>

## 3. Solution / Architecture

### <Pipeline or Component Name>

**Input**
- <What data or input the system receives>

**Processing**
- <Key steps, algorithms, or models used>

**Output**
- <What the system produces>

## 4. Tech Stack

- <Category: tools/frameworks>
- <Category: tools/frameworks>

## 5. Challenges

### <Challenge Name>

<Description of the challenge and how it was solved.>

## 6. Results

- <Metric or outcome 1>
- <Metric or outcome 2>

## 7. RAG Signals / Project Retrieval

- <Retrieval-friendly phrase 1>
- <Tech keywords>
""",

    "cv": """\
---
type: cv
title: Resume
importance: <user-provided>
year: <user-provided or inferred>
tags: [cv, resume, <generated skill keywords>]
---

## <Full Name>

Email: <email>
LinkedIn: <url>
GitHub: <url>
Portfolio: <url>

---

## 1. Career Summary

<2–4 sentence professional summary. Focus, domain, and goals.>

---

## 2. Work Experience

### <Job Title> — [<Company Name>]
<Start> – <End or Present>

#### Core Domains
- <Domain 1>
- <Domain 2>

#### Key Contributions

**<Initiative or Feature Name>**
- <What was built and impact>

**<Another Initiative>**
- <What was built and impact>

---

## 3. Project Experience

### <Project Name>
<Date>

Context: <Brief context, e.g. hackathon, side project>

#### Architecture
- Backend: <stack>
- Frontend: <stack>
- Deployment: <platform>

#### Contributions
- <Contribution 1>
- <Contribution 2>

---

## 4. Education

### <Degree> — <Institution>
<Year>

Focus: <Major or specialisation>

---

## 5. Skills

**Languages & Frameworks:** <list>
**Cloud & DevOps:** <list>
**AI / ML:** <list>
**Tools:** <list>
""",

    "personal": """\
---
type: personal
title: <Generated: e.g. Hobbies & Personal Development>
importance: <user-provided>
year: <user-provided or inferred>
tags: [<generated kebab-case keywords>]
---

## 1. <Hobby or Topic Name>

Context:
<Background — when started, why, how long.>

Experience / Highlights:
- <Milestone or achievement>
- <Milestone or achievement>

Skills Developed:
- <Skill or trait 1>
- <Skill or trait 2>

Personal Insight:
<One sentence connecting this hobby to professional or personal growth.>

## 2. <Another Hobby or Topic>

Context:
...

Experience / Highlights:
- ...

Skills Developed:
- ...

Personal Insight:
...

## 3. Personality Signals (Used for Behavioural Reasoning)

<Trait>:
- <Supporting evidence from hobbies>

<Trait>:
- <Supporting evidence>
""",

    "misc": """\
---
type: misc
title: <Generated: descriptive title>
importance: <user-provided>
year: <user-provided or inferred>
tags: [<generated kebab-case keywords>]
---

## 1. Overview

<Brief description of what this document covers.>

## 2. Key Points

- <Point 1>
- <Point 2>
- <Point 3>

## 3. Details

<Expanded content, subsections as needed.>

## 4. RAG Signals

- <Retrieval-friendly phrase 1>
- <Keyword 1>, <Keyword 2>
""",
}

# Default fallback if an unknown doc_type is requested
REFERENCE_TEMPLATES["default"] = REFERENCE_TEMPLATES["misc"]


def get_reference_template(doc_type: str) -> str:
    """Return the built-in reference template for the given doc_type.
    Never reads from disk — works for any fresh setup with no existing data files.
    """
    return REFERENCE_TEMPLATES.get(doc_type, REFERENCE_TEMPLATES["default"])


# Instruction for restructuring raw text into RAG-ready markdown (structure varies by doc type)
SELF_CHECK_PROMPT = """You are a factual accuracy checker for a RAG (Retrieval-Augmented Generation) system.

Your task: determine if the draft answer below is fully supported by the provided context.

Context:
{context}

Draft answer:
{answer}

Instructions:
- For each claim in the draft answer, check if it is explicitly or clearly implied by the context.
- If ALL claims are supported: respond with exactly: YES
- If any claim is NOT supported: respond with: UNSUPPORTED: [brief comma-separated list of the specific unsupported claims]
- Be strict but fair. Do NOT add commentary beyond the required format."""

MULTI_STEP_PROMPT = """You are a search query planner for a personal knowledge base RAG system.

The user asked: {query}

Here is the initial context retrieved so far:
{initial_context}

The answer may be incomplete. Generate up to 2 targeted follow-up search queries to retrieve additional relevant information that was NOT covered in the initial context.

Rules:
- Queries must be short and specific (under 12 words each)
- Do NOT repeat the original query verbatim
- One query per line
- If the initial context already seems sufficient to fully answer the question, reply with exactly: SUFFICIENT

Respond only with the follow-up queries (one per line) or SUFFICIENT."""

COVER_LETTER_PROMPT = """You are a cover letter writer. Your task is to write a concise, personalized cover letter for the candidate based on the job description and the candidate's profile context.

Job description:
{job_description}

Extracted requirements / keywords (for reference):
Requirements: {requirements}
Keywords: {keywords}

Candidate profile (from knowledge base):
{owner_profile}

Relevant context from the candidate's documents (CV, projects, career, etc.):
{context}

Instructions:
- Write a professional cover letter that highlights how the candidate's experience and skills match the job.
- Use ONLY information from the candidate profile and context above. Do not invent qualifications or facts.
- Keep the cover letter under {word_limit} words. Be concise and impactful.
- Address the role and company when evident from the job description.
- Output only the cover letter text, no headings or meta-commentary."""

RESTRUCTURE_TO_MD_PROMPT = """You are a document structuring assistant. You will receive raw, unstructured text and must restructure it into a clean markdown document for a RAG knowledge base.

**Document type for this task:** {user_type}

The reference below is a canonical template for this document type. You MUST follow its section layout, heading style, and field conventions. Replace all placeholder text in angle brackets with real content from the user's raw text.

## Reference template (follow this structure exactly)

```
{reference_md}
```

## User-provided metadata (put these in frontmatter)

- **type**: {user_type} (use exactly this value)
- **year**: {user_year}
- **importance**: {user_importance} (use exactly this value)

If year says "(infer from content if possible, else omit)", infer from the content or omit the year field.

## Rules

1. **Frontmatter**: YAML between --- lines. Use the user-provided type, year, and importance exactly. Generate `title` from the content (job title, project name, or descriptive title). Generate `tags` as a YAML array of kebab-case keywords derived from the content.
2. **Structure**: Follow the reference template section-by-section. Keep all sections present in the template; write "N/A" or omit a subsection only if the user's text has genuinely no content for it.
3. **Content**: Preserve every factual detail from the user's raw text. Do not invent information.
4. **RAG Signals**: End with a bullet list of retrieval-friendly phrases and keywords summarising the document.
5. Output only valid markdown. No commentary, no code fences, no extra text before or after.

## Raw text from user

{raw_text}
"""

RESUME_REWRITE_PROMPT = """You are a resume rewrite assistant.

You receive:
- A job description
- Extracted requirements and keywords
- RAG context from the candidate's existing documents
- The candidate's current resume text

Your task:
- Rewrite the resume so it is tailored to the job description.
- Use ONLY facts from the original resume and context; do not invent new jobs, degrees, or skills.
- Emphasize experience, projects, and skills that match the job requirements.
- De‑emphasize or shorten irrelevant parts.
- Output a COMPLETE resume in **Markdown**, with clear sections such as uploaded resume.

Inputs:
- Job description:
{job_description}

- Extracted requirements:
{requirements}

- Keywords:
{keywords}

- Candidate context (from knowledge base):
{context}

- Original resume text:
{original_resume}
"""

RESUME_SUGGESTIONS_PROMPT = """You are a resume coach.

You receive:
- A job description
- Extracted requirements and keywords
- RAG context from the candidate's existing documents and resume

Your task:
- Suggest concrete, factual improvements the candidate can make to their EXISTING resume so it better matches the role.
- Use ONLY facts from the context. Do not invent new jobs, degrees, employers, dates, or technologies that are not clearly supported by the context text.
- When something is missing, describe it as a SUGGESTION (e.g. "If you have X, highlight it") rather than asserting it as fact.
- Every suggestion MUST be traceable to specific sentences or bullet points in the context. If you cannot find evidence, do NOT claim it as true.

Guidelines:
- Focus on alignment with requirements and keywords.
- For each suggestion, briefly mention which project/role or phrase in the context supports it.
- Avoid rewriting the full resume. Output a prioritized list of actionable edits grouped by section (Summary, Experience, Projects, Skills, Other).
- Use clean Markdown headings and bullet lists so the output is easy to read.

Inputs:
- Job description:
{job_description}

- Extracted requirements:
{requirements}

- Keywords:
{keywords}

- Candidate context (from knowledge base and existing resume):
{context}
"""

INTERVIEW_QUESTIONS_PROMPT = """You are an interview preparation assistant.

You receive:
- A job description
- Extracted requirements and keywords
- RAG context from the candidate's existing documents and resume

Your task:
- Generate realistic interview questions the candidate is likely to be asked for this role.
- Questions should focus on the candidate's real projects, responsibilities, and technologies from the context, plus role-specific technical topics.
- Do NOT generate generic behavioral questions (like "Tell me about a time you failed" or "What are your strengths and weaknesses").
- For each question, also include 1–3 bullet points describing how the candidate can answer using ONLY facts from the context.
- If the context does not support a strong answer, say so explicitly instead of guessing.

Guidelines:
- Cover technical and role-specific questions grounded in the candidate's real experience.
- Prefer questions that connect directly to projects, achievements, and tools visible in the context.
- Do NOT invent projects or responsibilities that are not clearly supported by the context.
- Use clean Markdown headings, numbered lists for questions, and bullet lists for answer notes.

Inputs:
- Job description:
{job_description}

- Extracted requirements:
{requirements}

- Keywords:
{keywords}

- Candidate context (from knowledge base and existing resume):
{context}
"""