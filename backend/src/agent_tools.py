"""
Domain agent tool layer for the multi-agent graph.

Each specialist agent:
  A) Expands the query with domain-specific terms (template, no LLM) for better recall
  B) Calls fetch_context() with the domain-expanded query — diverse, targeted retrieval
  C) Generates a 2-3 sentence domain summary via a cheap LLM (runs in parallel)

job_prep_agent additionally:
  C*) Detects job-description context, extracts requirements via extract_job_requirements(),
      and searches with those requirements for targeted fit-signal retrieval.

All retrieval logic lives in rag_retrieval.py and is reused unchanged.
"""
import utils.path_setup  # noqa: F401

from src.agent_state import AgentResult
from src.domain_constants import DOMAIN_DOC_TYPES


# ---------------------------------------------------------------------------
# Token budget helpers
# ---------------------------------------------------------------------------

def estimate_token_count(text: str) -> int:
    """
    Approximate token count using word-count heuristic (words * 1.3).
    Avoids tiktoken import for speed inside parallel agent nodes.
    """
    return int(len(text.split()) * 1.3)


# ---------------------------------------------------------------------------
# Domain metadata
# ---------------------------------------------------------------------------

# Option A: domain-specialized query suffixes appended to the rewritten query.
# These expand the search vocabulary for each domain without an extra LLM call.
DOMAIN_QUERY_SUFFIXES: dict[str, str] = {
    "career_agent":   "professional work experience job role employment career history responsibilities achievements",
    "project_agent":  "software project built developed created technical implementation architecture outcome",
    "skills_agent":   "technical skills programming languages tools frameworks education qualifications certifications",
    "personal_agent": "personal background interests hobbies life activities outside work values personality",
    "job_prep_agent": "",  # job_prep builds its own query from extracted requirements
}

# Human-readable domain label used in summaries and synthesis prompt
DOMAIN_LABELS: dict[str, str] = {
    "career_agent":   "Career",
    "project_agent":  "Projects",
    "skills_agent":   "Skills & Education",
    "personal_agent": "Personal",
    "job_prep_agent": "Job Fit",
}


# ---------------------------------------------------------------------------
# Option A: Domain-specific query expansion (no LLM)
# ---------------------------------------------------------------------------

def expand_query_for_domain(query: str, agent_name: str) -> str:
    """
    Append domain-specific terms to the query for targeted retrieval.
    Template-based — zero LLM calls, near-zero latency.
    """
    suffix = DOMAIN_QUERY_SUFFIXES.get(agent_name, "")
    if suffix:
        return f"{query} {suffix}"
    return query


# ---------------------------------------------------------------------------
# Option B: Mini-summary generation
# ---------------------------------------------------------------------------

def generate_domain_summary(query: str, agent_name: str, docs: list) -> str:
    """
    Generate a 2-3 sentence domain summary using a cheap model.
    Runs inside each parallel agent node — wall-clock cost = max(agent_latency),
    not sum(agent_latency), so parallel execution keeps total latency low.

    Returns a plain-English summary attributed to the domain label.
    Falls back to a simple doc-count message if the LLM call fails.
    """
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage
    from utils.config_loader import ConfigLoader
    from utils.prompt_manager import get_prompt

    if not docs:
        domain_label = DOMAIN_LABELS.get(agent_name, agent_name)
        return f"No relevant {domain_label} information found."

    context = "\n\n".join(doc.page_content for doc in docs[:8])  # cap for speed
    domain_label = DOMAIN_LABELS.get(agent_name, agent_name)

    cfg = ConfigLoader()
    llm = ChatOpenAI(model=cfg.get_rewrite_model(), temperature=0)

    prompt = get_prompt("DOMAIN_SUMMARY_PROMPT").format(
        domain=domain_label,
        query=query,
        context=context,
    )
    try:
        response = llm.invoke([SystemMessage(content=prompt)])
        return (response.content or "").strip()
    except Exception as e:
        print(f"[{agent_name}] summary generation warning (non-fatal): {e}")
        doc_count = len(docs)
        return f"{doc_count} {domain_label} document(s) retrieved but summary generation failed."


# ---------------------------------------------------------------------------
# Option C: Job URL detection and scraping
# ---------------------------------------------------------------------------

import re as _re

_URL_PATTERN = _re.compile(r'https?://[^\s<>"\']+')

# LinkedIn job URL pattern: /jobs/view/<id>/
_LINKEDIN_JOB_PATTERN = _re.compile(r'linkedin\.com/jobs/view/(\d+)', _re.IGNORECASE)

_SCRAPE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}


def extract_job_url(query: str) -> str | None:
    """
    Extract the first HTTP/HTTPS URL from a query string.
    Strips trailing punctuation that may have been included accidentally.
    """
    match = _URL_PATTERN.search(query)
    if not match:
        return None
    return match.group(0).rstrip(".,)>\"'")


def scrape_job_description(url: str) -> str:
    """
    Fetch a job posting URL and extract the job description text.

    Strategy (in order):
    1. JSON-LD structured data (type=JobPosting) — works for LinkedIn, Greenhouse,
       Lever, Workday, and most modern job boards.
    2. Common CSS selector heuristics for job description containers.
    3. Full body text extraction as a last resort.

    Returns the extracted text (may be empty if scraping fails or login is required).
    """
    import json
    import httpx
    from bs4 import BeautifulSoup

    try:
        resp = httpx.get(url, headers=_SCRAPE_HEADERS, follow_redirects=True, timeout=15)
        if resp.status_code != 200:
            print(f"[job_scraper] HTTP {resp.status_code} for {url}")
            return ""
        soup = BeautifulSoup(resp.text, "lxml")
    except Exception as e:
        print(f"[job_scraper] Request failed for {url}: {e}")
        return ""

    # 1. JSON-LD structured data — most reliable
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            # Handle both a single object and an array
            candidates = data if isinstance(data, list) else [data]
            for obj in candidates:
                if obj.get("@type") == "JobPosting":
                    title = obj.get("title", "")
                    org = obj.get("hiringOrganization") or {}
                    company = org.get("name", "") if isinstance(org, dict) else ""
                    description_html = obj.get("description", "")
                    # Strip HTML tags from the description field
                    desc_text = BeautifulSoup(description_html, "lxml").get_text("\n")
                    location = ""
                    loc = obj.get("jobLocation") or {}
                    if isinstance(loc, dict):
                        addr = loc.get("address") or {}
                        location = addr.get("addressLocality", "") if isinstance(addr, dict) else ""

                    parts = []
                    if title:
                        parts.append(f"Job Title: {title}")
                    if company:
                        parts.append(f"Company: {company}")
                    if location:
                        parts.append(f"Location: {location}")
                    if desc_text.strip():
                        parts.append(f"\nJob Description:\n{desc_text.strip()}")
                    result = "\n".join(parts)
                    if len(result) > 100:
                        print(f"[job_scraper] JSON-LD extracted {len(result)} chars from {url}")
                        return result[:8000]
        except Exception:
            continue

    # 2. CSS selector heuristics for common job board containers
    _SELECTORS = [
        "[class*='description']",
        "[class*='job-desc']",
        "[class*='jobDescription']",
        "[class*='job_description']",
        "[id*='job-description']",
        "[id*='jobDescription']",
        "section.details",
        "main",
        "article",
    ]
    for selector in _SELECTORS:
        try:
            el = soup.select_one(selector)
            if el:
                text = el.get_text(separator="\n", strip=True)
                if len(text) > 300:
                    print(f"[job_scraper] selector '{selector}' extracted {len(text)} chars")
                    return text[:8000]
        except Exception:
            continue

    # 3. Full body text — last resort
    body = soup.find("body")
    if body:
        text = body.get_text(separator="\n", strip=True)
        if len(text) > 300:
            print(f"[job_scraper] body fallback extracted {len(text)} chars")
            return text[:8000]

    print(f"[job_scraper] Could not extract content from {url} (likely login-gated)")
    return ""


# ---------------------------------------------------------------------------
# Option C: Job-prep specialist helpers
# ---------------------------------------------------------------------------

_JOB_KEYWORDS = {
    "job description", "job desc", "jd:", "position:", "requirements:",
    "qualifications:", "responsibilities:", "we are looking", "we're looking",
    "minimum", "years of experience", "bachelor", "master", "degree in",
    "salary", "compensation", "apply", "hiring", "role:", "company:",
}

JOB_DESC_MIN_LENGTH = 200  # chars — short queries are unlikely to be JDs


def is_job_description_query(query: str) -> bool:
    """
    Heuristic: is this query a pasted job description rather than a plain question?
    Checks length and presence of job-description-specific phrases.
    """
    if len(query) < JOB_DESC_MIN_LENGTH:
        return False
    q_lower = query.lower()
    return any(kw in q_lower for kw in _JOB_KEYWORDS)


def retrieve_job_prep_docs(
    query: str,
    top_k: int = 5,
    scraped_job_text: str = "",
) -> tuple[list, str]:
    """
    Option C: Job-prep specific retrieval.

    Priority order for the source JD text:
    1. scraped_job_text — full text scraped from a job URL (richest signal)
    2. query — if it looks like a pasted JD (long + JD keywords)
    3. domain-expanded search — fallback for conversational job queries

    Returns (docs, fit_context_note) where fit_context_note describes
    what was extracted (shown in the agent summary).
    """
    from src.rag_retrieval import fetch_context, deduplicate_context, extract_job_requirements

    jd_text = scraped_job_text.strip() if scraped_job_text.strip() else (
        query if is_job_description_query(query) else ""
    )

    if jd_text:
        reqs = extract_job_requirements(jd_text)
        keywords = reqs.get("keywords", [])
        requirements = reqs.get("requirements", [])

        # Search with extracted keywords + first 500 chars of JD for semantic coverage
        req_query = " ".join(keywords[:15])
        if requirements:
            req_query += " " + " ".join(r[:60] for r in requirements[:3])

        docs = deduplicate_context(
            fetch_context(req_query) + fetch_context(jd_text[:500])
        )
        source = "URL" if scraped_job_text else "pasted text"
        fit_note = (
            f"Job description from {source}. "
            f"Extracted {len(requirements)} requirement(s). "
            f"Top keywords: {', '.join(keywords[:8])}."
        )
        return docs[:top_k * 3], fit_note
    else:
        domain_query = expand_query_for_domain(query, "job_prep_agent")
        docs = fetch_context(domain_query)
        return docs[:top_k * 3], ""


# ---------------------------------------------------------------------------
# AgentResult factory
# ---------------------------------------------------------------------------

def compute_confidence(docs: list) -> float:
    """
    Confidence score 0.0–1.0 based on number and quality of retrieved docs.
    Full marks at top_k=5 docs, linear penalty below.
    """
    if not docs:
        return 0.0
    return min(1.0, len(docs) / 5.0)


def build_agent_result(
    agent_name: str,
    docs: list,
    summary: str = "",
    error: str | None = None,
) -> AgentResult:
    """
    Build an AgentResult from retrieved documents and an optional summary.
    Calls _extract_sources() from rag_retrieval — no duplication of source logic.
    """
    from src.rag_retrieval import _extract_sources

    if error is not None or not docs:
        return AgentResult(
            agent_name=agent_name,
            docs=[],
            context="",
            summary=summary or f"No {DOMAIN_LABELS.get(agent_name, agent_name)} information retrieved.",
            sources=[],
            token_count=0,
            error=error,
            confidence=0.0,
        )

    context = "\n\n".join(doc.page_content for doc in docs)
    sources = _extract_sources(docs)
    token_count = estimate_token_count(context)
    confidence = compute_confidence(docs)

    return AgentResult(
        agent_name=agent_name,
        docs=docs,
        context=context,
        summary=summary,
        sources=sources,
        token_count=token_count,
        error=None,
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# Loop guard
# ---------------------------------------------------------------------------

MAX_TRACE_STEPS = 10


def is_loop_detected(state: dict) -> bool:
    """
    Returns True if the graph has taken too many steps — prevents infinite loops.
    Called at the start of every node.
    """
    return len(state.get("agent_trace", [])) >= MAX_TRACE_STEPS


# ---------------------------------------------------------------------------
# Notification helper
# ---------------------------------------------------------------------------

def send_unknown_query_notification(query: str, run_id: str = "") -> None:
    """
    Send a system email notification when a query could not be answered.
    Non-blocking: caller should run this in a background thread.
    """
    from utils.config_loader import ConfigLoader
    from utils.smtp_send import send_smtp_message

    cfg = ConfigLoader()
    recipient = cfg.get_recipient_email()
    if not recipient:
        print("[notification_agent] RECIPIENT_EMAIL not configured — skipping notification")
        return

    smtp_user = cfg.get_smtp_user()
    smtp_password = cfg.get_smtp_password()
    if not smtp_user or not smtp_password:
        print("[notification_agent] SMTP credentials not configured — skipping notification")
        return

    body = (
        f"Your digital twin could not answer a visitor's question.\n\n"
        f"Run ID: {run_id}\n\n"
        f"Question:\n{query}\n\n"
        f"Consider adding this topic to your knowledge base."
    )
    try:
        send_smtp_message(
            recipient,
            "[MyBestFriend] Unknown query received",
            body,
        )
        print(f"[notification_agent] Notification sent to {recipient}")
    except Exception as e:
        print(f"[notification_agent] Email send error (non-fatal): {e}")


# ---------------------------------------------------------------------------
# Synthesis input formatting
# ---------------------------------------------------------------------------

def format_agent_summaries(agent_results: list[AgentResult]) -> str:
    """
    Format per-agent LLM summaries into structured input for the synthesis prompt.
    Each line: [Domain Label] <summary text>
    This is Option B's payoff — synthesis gets structured domain summaries,
    not a raw merged context blob.
    """
    lines = []
    for result in agent_results:
        domain_label = DOMAIN_LABELS.get(result["agent_name"], result["agent_name"])
        if result.get("error"):
            lines.append(f"[{domain_label}] Error: {result['error']}")
        elif result.get("summary"):
            lines.append(f"[{domain_label}] {result['summary']}")
        else:
            lines.append(f"[{domain_label}] No relevant information found.")
    return "\n\n".join(lines)


def format_agent_summary(agent_results: list[AgentResult]) -> str:
    """Backwards-compatible alias for format_agent_summaries."""
    return format_agent_summaries(agent_results)


# ---------------------------------------------------------------------------
# Job tools: score_job_fit + search_recent_jobs
# ---------------------------------------------------------------------------

def score_job_fit(job_description: str, top_k: int = 5) -> dict:
    """
    Score how well the owner fits a job description against the knowledge base.

    Steps:
    1. Extract structured requirements via extract_job_requirements()
    2. Fetch relevant KB docs via get_job_context()
    3. LLM-assess each technical requirement against KB context (same LLM path as chat reply)
    4. Return score (0-100), matched/missing lists, keywords, and a context snippet.
    """
    import json as _json
    from src.rag_retrieval import extract_job_requirements, get_job_context

    # Guard: if input looks like a bare URL rather than a real JD, return empty score
    stripped = job_description.strip()
    if stripped.startswith(("http://", "https://")) and "\n" not in stripped and len(stripped) < 500:
        return {
            "score": 0,
            "matched_requirements": [],
            "missing_requirements": [],
            "keywords": [],
            "culture_signals": [],
            "doc_count": 0,
            "context_snippet": "",
            "error": "no_jd_text",
        }

    reqs = extract_job_requirements(job_description)
    docs, context = get_job_context(job_description, reqs)
    docs = docs[:top_k * 3]  # respect caller's budget

    tech_reqs = reqs.get("technical_requirements", [])
    keywords = reqs.get("keywords", [])

    matched: list[str] = []
    missing: list[str] = []

    if tech_reqs and context:
        # Use LLM to assess requirements against KB context — same signal path as the chat reply
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import SystemMessage, HumanMessage
            from utils.config_loader import config

            llm = ChatOpenAI(model=config.get_rewrite_model(), temperature=0)
            reqs_text = "\n".join(f"- {r}" for r in tech_reqs)
            system = SystemMessage(
                content=(
                    "You are assessing how well a candidate's profile matches job requirements. "
                    "Given a knowledge base excerpt about the candidate and a list of job requirements, "
                    "classify each requirement as either MATCHED (clearly evidenced in the profile) "
                    "or MISSING (not evidenced). "
                    "Return strict JSON: {\"matched\": [list of matched requirement strings], "
                    "\"missing\": [list of missing requirement strings]}. "
                    "Copy the requirement strings verbatim. No extra text."
                )
            )
            human = HumanMessage(
                content=(
                    f"CANDIDATE PROFILE (knowledge base):\n{context[:3000]}\n\n"
                    f"JOB REQUIREMENTS:\n{reqs_text}\n\n"
                    "Return JSON now."
                )
            )
            response = llm.invoke([system, human])
            data = _json.loads(response.content or "{}")
            matched = [r for r in data.get("matched", []) if isinstance(r, str)]
            missing = [r for r in data.get("missing", []) if isinstance(r, str)]

            # Fallback: if LLM returned nothing useful, put unclassified reqs in missing
            classified = set(matched) | set(missing)
            for req in tech_reqs:
                if req not in classified:
                    missing.append(req)
        except Exception:
            # Fallback to keyword matching if LLM call fails
            for req in tech_reqs:
                req_words = [w.lower() for w in req.split() if len(w) >= 2]
                if not req_words:
                    matched.append(req)
                    continue
                threshold = max(1, len(req_words) // 2)
                covered = any(
                    sum(1 for kw in req_words if kw in doc.page_content.lower()) >= threshold
                    for doc in docs
                )
                (matched if covered else missing).append(req)

    total = len(tech_reqs)
    req_score = int(len(matched) / total * 75) if total else 50
    context_bonus = min(25, len(docs) * 4)
    score = min(100, req_score + context_bonus)

    return {
        "score": score,
        "matched_requirements": matched,
        "missing_requirements": missing,
        "keywords": keywords,
        "culture_signals": reqs.get("culture", []),
        "doc_count": len(docs),
        "context_snippet": context[:1500] if context else "",
    }


def search_recent_jobs(
    keywords: list[str],
    hours: int = 168,
    sources: list[str] | None = None,
) -> list[dict]:
    """
    Search for job postings matching keywords from free public sources.

    Sources (tried in order):
    1. Arbeitnow API — free, broad job listings, no key required
    2. RemoteOK API — free, tech-focused remote jobs, no key required

    Strategy: collect all keyword-matching jobs regardless of age, then filter
    by the requested hours window.  If the filtered set is empty (the APIs
    refresh slowly, so narrow windows often return nothing), fall back to the
    full unfiltered set so the user always sees something useful.
    Note: LinkedIn requires authentication and cannot be searched here.
    """
    import httpx
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=hours)
    kw_str = " ".join(keywords[:5])
    kw_lower = [k.lower() for k in keywords]
    want_arbeitnow = not sources or "arbeitnow" in sources
    want_remoteok = not sources or "remoteok" in sources

    # Collect ALL keyword-matching jobs (no time filter yet)
    all_results: list[dict] = []

    # Source 1: Arbeitnow — free REST API, broad coverage
    if want_arbeitnow:
        try:
            resp = httpx.get(
                "https://www.arbeitnow.com/api/job-board-api",
                params={"search": kw_str},
                timeout=10,
            )
            if resp.status_code == 200:
                for job in resp.json().get("data", [])[:30]:
                    title = job.get("title", "") or ""
                    tags = [t.lower() for t in job.get("tags", [])]
                    tag_str = " ".join(tags)
                    if not any(kw in title.lower() or kw in tag_str for kw in kw_lower):
                        continue
                    created_at = job.get("created_at", "")
                    all_results.append({
                        "title": title,
                        "company": job.get("company_name", ""),
                        "location": job.get("location", "Remote"),
                        "url": job.get("url", ""),
                        "posted_at": created_at,
                        "tags": job.get("tags", [])[:8],
                        "source": "Arbeitnow",
                        "_posted_dt": _parse_dt(created_at),
                    })
        except Exception as e:
            print(f"[job_search] arbeitnow error (non-fatal): {e}")

    # Source 2: RemoteOK — tech/remote jobs, no key required
    if want_remoteok:
        try:
            tag = keywords[0].lower().replace(" ", "-") if keywords else "dev"
            resp = httpx.get(
                f"https://remoteok.com/api?tag={tag}",
                headers={"User-Agent": "MyBestFriend-JobSearch/1.0"},
                timeout=10,
            )
            if resp.status_code == 200:
                jobs = resp.json()
                if isinstance(jobs, list) and jobs and isinstance(jobs[0], dict) and "legal" in jobs[0]:
                    jobs = jobs[1:]
                for job in jobs[:20]:
                    title = job.get("position", "") or ""
                    if not title:
                        continue
                    epoch = job.get("epoch", 0)
                    if epoch:
                        posted_dt: datetime | None = datetime.fromtimestamp(int(epoch), tz=timezone.utc)
                        posted_iso = posted_dt.isoformat()
                    else:
                        posted_dt = None
                        posted_iso = ""
                    all_results.append({
                        "title": title,
                        "company": job.get("company", ""),
                        "location": job.get("location", "Remote") or "Remote",
                        "url": job.get("url") or f"https://remoteok.com/l/{job.get('slug', '')}",
                        "posted_at": posted_iso,
                        "tags": (job.get("tags") or [])[:8],
                        "source": "RemoteOK",
                        "_posted_dt": posted_dt,
                    })
        except Exception as e:
            print(f"[job_search] remoteok error (non-fatal): {e}")

    # Deduplicate
    seen: set[str] = set()
    deduped: list[dict] = []
    for job in all_results:
        key = f"{job['title'].lower()}|{job['company'].lower()}"
        if key not in seen:
            seen.add(key)
            deduped.append(job)

    # Sort by recency (jobs with no date go last)
    deduped.sort(key=lambda j: j["_posted_dt"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    # Apply time filter; fall back to full set if nothing passes
    time_filtered = [j for j in deduped if j.get("_posted_dt") and j["_posted_dt"] >= cutoff]
    final = time_filtered if time_filtered else deduped

    # Strip internal key before returning
    for j in final:
        j.pop("_posted_dt", None)

    return final[:15]


def _parse_dt(s: str):
    """Parse an ISO datetime string; return None on failure."""
    if not s:
        return None
    try:
        from datetime import datetime, timezone
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None
