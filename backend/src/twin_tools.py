"""
Twin-specific tools for agentic use.
Each tool queries the vector store or Supabase to produce structured outputs
that a downstream LLM agent can use for richer, task-oriented answers.
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.supabase_client import supabase_client


def summarize_time_period(year: str) -> str:
    """
    Return raw context text for all chunks tagged with the given year.
    Useful for 'summarize my work in 2023'-style queries.
    """
    try:
        resp = (
            supabase_client.table("document_chunks")
            .select("content, metadata")
            .filter("metadata->>year", "eq", str(year))
            .limit(20)
            .execute()
        )
        rows = resp.data or []
        if not rows:
            return f"No documents found for year {year}."
        return "\n\n".join(row.get("content", "") for row in rows[:12])
    except Exception as e:
        return f"Error retrieving data for year {year}: {e}"


def list_projects() -> list:
    """
    Return a sorted list of project titles/sources from the vector store.
    Useful for 'list all my projects' queries.
    """
    try:
        resp = (
            supabase_client.table("document_chunks")
            .select("metadata")
            .filter("metadata->>doc_type", "eq", "project")
            .execute()
        )
        titles: set = set()
        for row in (resp.data or []):
            meta = row.get("metadata") or {}
            title = meta.get("title") or meta.get("source", "").replace(".md", "")
            if title:
                titles.add(title)
        return sorted(titles)
    except Exception:
        return []


def get_knowledge_scope() -> dict:
    """
    Return document type counts and year ranges for knowledge-scope display in the UI.
    Used to power the onboarding section that tells users what the twin knows.
    """
    try:
        resp = supabase_client.table("document_chunks").select("metadata").execute()
        counts: dict = {}
        years: set = set()
        for row in (resp.data or []):
            meta = row.get("metadata") or {}
            dt = meta.get("doc_type", "unknown")
            counts[dt] = counts.get(dt, 0) + 1
            yr = str(meta.get("year", ""))
            if yr and yr.isdigit() and len(yr) == 4:
                years.add(yr)
        year_range = f"{min(years)}–{max(years)}" if years else None
        return {"doc_types": counts, "year_range": year_range}
    except Exception:
        return {"doc_types": {}, "year_range": None}


def generate_bio(context: str, style: str = "professional") -> str:
    """
    Generate a short bio from provided context text.
    Intended to be called after retrieving relevant docs.
    style: 'professional', 'casual', 'conference'
    """
    style_map = {
        "professional": "a concise 3-sentence professional bio suitable for a LinkedIn profile",
        "casual": "a friendly 2-sentence intro suitable for a personal website",
        "conference": "a 2-sentence speaker bio suitable for a conference programme",
    }
    instruction = style_map.get(style, style_map["professional"])
    return f"[bio/{style}] Write {instruction} based on the following context:\n\n{context[:3000]}"
