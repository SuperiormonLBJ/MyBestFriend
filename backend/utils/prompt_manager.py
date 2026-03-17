"""
PromptManager: reads and writes LLM prompts via Supabase `prompts` table.
Falls back to hardcoded defaults from utils/prompts.py if Supabase is unavailable.

Usage:
    from utils.prompt_manager import get_prompt
    system_msg = get_prompt("SYSTEM_PROMPT_GENERATOR").format(context=ctx)
"""

import os
import sys
import threading
from pathlib import Path

_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from utils.prompts import (
    RESUME_REWRITE_PROMPT,
    SYSTEM_PROMPT_GENERATOR,
    SYSTEM_PROMPT_RERANKER,
    REWRITE_PROMPT,
    RESTRUCTURE_TO_MD_PROMPT,
    LINKEDIN_PROMPT,
    SYSTEM_PROMPT_EVALUATOR_GENERATOR,
    SELF_CHECK_PROMPT,
    MULTI_STEP_PROMPT,
    COVER_LETTER_PROMPT,
    RESUME_SUGGESTIONS_PROMPT,
    INTERVIEW_QUESTIONS_PROMPT,
    EVAL_DATASET_GENERATOR_PROMPT,
)

# Registry of all managed prompts: key → {content, description}
_DEFAULTS: dict[str, dict] = {
    "SYSTEM_PROMPT_GENERATOR": {
        "content": SYSTEM_PROMPT_GENERATOR,
        "description": "Core RAG answer generator. Receives {context} placeholder filled with retrieved document chunks.",
    },
    "SYSTEM_PROMPT_RERANKER": {
        "content": SYSTEM_PROMPT_RERANKER,
        "description": "Re-ranks retrieved document chunks by relevance to the user's query.",
    },
    "REWRITE_PROMPT": {
        "content": REWRITE_PROMPT,
        "description": "Rewrites the user's question into an optimized RAG search query.",
    },
    "RESTRUCTURE_TO_MD_PROMPT": {
        "content": RESTRUCTURE_TO_MD_PROMPT,
        "description": "Structures raw text into RAG-ready markdown. Placeholders: {user_type}, {reference_md}, {user_year}, {user_importance}, {raw_text}.",
    },
    "LINKEDIN_PROMPT": {
        "content": LINKEDIN_PROMPT,
        "description": "Cleans and extracts structured profile data from raw LinkedIn page text.",
    },
    "SYSTEM_PROMPT_EVALUATOR_GENERATOR": {
        "content": SYSTEM_PROMPT_EVALUATOR_GENERATOR,
        "description": "Evaluates RAG answer quality. Placeholders: {question}, {generated_answer}, {ground_truth}.",
    },
    "SELF_CHECK_PROMPT": {
        "content": SELF_CHECK_PROMPT,
        "description": "Post-generation factual grounding check. Verifies all answer claims are supported by context. Placeholders: {context}, {answer}.",
    },
    "MULTI_STEP_PROMPT": {
        "content": MULTI_STEP_PROMPT,
        "description": "Generates follow-up retrieval queries for complex multi-step questions. Placeholders: {query}, {initial_context}.",
    },
    "COVER_LETTER_PROMPT": {
        "content": COVER_LETTER_PROMPT,
        "description": "Job Preparation: generates a tailored cover letter from job description and RAG context. Placeholders: {job_description}, {requirements}, {keywords}, {context}, {owner_profile}, {word_limit}.",
    },
    "RESUME_REWRITE_PROMPT": {
        "content": RESUME_REWRITE_PROMPT,
        "description": "Rewrites a resume in Markdown, tailored to a job description using RAG context.",
    },
    "RESUME_SUGGESTIONS_PROMPT": {
        "content": RESUME_SUGGESTIONS_PROMPT,
        "description": "Job Preparation: suggests grounded edits to the existing resume based on job description and RAG context.",
    },
    "INTERVIEW_QUESTIONS_PROMPT": {
        "content": INTERVIEW_QUESTIONS_PROMPT,
        "description": "Job Preparation: generates interview questions and grounded answer guidance from job description and RAG context.",
    },
    "EVAL_DATASET_GENERATOR_PROMPT": {
        "content": EVAL_DATASET_GENERATOR_PROMPT,
        "description": "Generates RAG evaluation questions/answers from the ingested knowledge base. Placeholder: {context}.",
    },
}


# Thread-local storage so each thread gets its own Supabase client (httpx is not thread-safe to share).
_tl = threading.local()


def _client():
    if not hasattr(_tl, "client"):
        from supabase import create_client
        _tl.client = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_SECRET_KEY"],
        )
    return _tl.client


def seed_if_empty() -> None:
    """Insert default prompts into Supabase if the table is empty. Non-fatal."""
    try:
        result = _client().table("prompts").select("key").limit(1).execute()
        if not (result.data or []):
            rows = [
                {"key": k, "content": v["content"], "description": v["description"]}
                for k, v in _DEFAULTS.items()
            ]
            _client().table("prompts").upsert(rows, on_conflict="key").execute()
            print(f"[prompt_manager] Seeded {len(rows)} prompts into Supabase")
    except Exception as e:
        print(f"[prompt_manager] Seed warning (non-fatal): {e}")


def sync_defaults() -> None:
    """Upsert all hardcoded defaults into Supabase so code changes are always applied on startup."""
    try:
        rows = [
            {"key": k, "content": v["content"], "description": v["description"]}
            for k, v in _DEFAULTS.items()
        ]
        _client().table("prompts").upsert(rows, on_conflict="key").execute()
        # Clear the thread-local client so the next get_prompt call reads the fresh values.
        if hasattr(_tl, "client"):
            del _tl.client
        print(f"[prompt_manager] Synced {len(rows)} default prompts to Supabase")
    except Exception as e:
        print(f"[prompt_manager] sync_defaults warning (non-fatal): {e}")


def get_prompt(key: str) -> str:
    """
    Return the current content for the given prompt key.
    Reads from Supabase; falls back to the hardcoded default on error.
    """
    try:
        result = _client().table("prompts").select("content").eq("key", key).execute()
        rows = result.data or []
        if rows:
            return rows[0]["content"]
    except Exception as e:
        print(f"[prompt_manager] get_prompt warning for {key}: {e}")
    return _DEFAULTS.get(key, {}).get("content", "")


def get_default_content(key: str) -> str:
    """Return the original hardcoded default for a prompt key."""
    return _DEFAULTS.get(key, {}).get("content", "")


def get_all_prompts() -> list[dict]:
    """
    Return all prompts as [{key, content, description}] sorted by key.
    Merges Supabase rows with defaults so newly added default keys are always included.
    """
    try:
        result = (
            _client()
            .table("prompts")
            .select("key, content, description")
            .execute()
        )
        rows: dict[str, dict] = {r["key"]: r for r in (result.data or [])}
        for k, v in _DEFAULTS.items():
            if k not in rows:
                rows[k] = {
                    "key": k,
                    "content": v["content"],
                    "description": v["description"],
                }
        return sorted(rows.values(), key=lambda r: r["key"])
    except Exception as e:
        print(f"[prompt_manager] get_all_prompts warning: {e}")
    return [
        {"key": k, "content": v["content"], "description": v["description"]}
        for k, v in sorted(_DEFAULTS.items())
    ]


def update_prompt(key: str, content: str) -> bool:
    """
    Upsert a prompt in Supabase.
    Returns True on success, False if the key is unknown or on error.
    """
    if key not in _DEFAULTS:
        return False
    try:
        _client().table("prompts").upsert(
            {
                "key": key,
                "content": content,
                "description": _DEFAULTS[key]["description"],
            },
            on_conflict="key",
        ).execute()
        return True
    except Exception as e:
        print(f"[prompt_manager] update_prompt error for {key}: {e}")
        return False


# Seed on module import so the table is always populated
seed_if_empty()
