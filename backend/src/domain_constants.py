"""Shared domain ↔ doc_type mappings for twin_tools (UI/MCP) and multi-agent retrieval."""

DOMAIN_DOC_TYPE_MAP: dict[str, str] = {
    "projects": "project",
    "jobs": "career",
    "skills": "cv",
    "education": "education",
    "hobbies": "personal",
    "personal": "personal",
}

DOMAIN_DOC_TYPES: dict[str, list[str]] = {
    "career_agent": ["career", "work", "job"],
    "project_agent": ["project"],
    "skills_agent": ["cv", "skills", "education"],
    "personal_agent": ["personal", "hobby", "life"],
    "job_prep_agent": ["career", "project", "cv", "skills"],
}
