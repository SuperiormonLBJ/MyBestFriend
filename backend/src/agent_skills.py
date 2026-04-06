"""
Skill-based agent definitions for the multi-agent system.

Each agent is defined as a (prompt_key, tool_names, tool_defaults, max_iterations) tuple.
This replaces the hardcoded _make_specialist_agent factory — adding a new agent
requires only a new entry here, not new code in multi_agent_graph.py.

Tool names reference tools defined in tool_registry.py.
Prompt keys reference prompts in prompt_manager.py (editable via admin UI).
"""
from dataclasses import dataclass, field


@dataclass
class AgentSkill:
    prompt_key: str
    tools: list[str]
    tool_defaults: dict[str, dict] = field(default_factory=dict)
    max_iterations: int = 3
    # Names of external MCP servers this agent may use (from config.yaml mcp_clients[].name).
    # Empty list = no external tools. ["*"] = all configured external servers.
    mcp_server_filter: list[str] = field(default_factory=list)


AGENT_SKILLS: dict[str, AgentSkill] = {
    "career_agent": AgentSkill(
        prompt_key="CAREER_AGENT_PROMPT",
        tools=["search_knowledge", "get_time_period_summary", "list_domain_items"],
        tool_defaults={"search_knowledge": {"doc_type": "career"}},
        max_iterations=3,
    ),
    "project_agent": AgentSkill(
        prompt_key="PROJECT_AGENT_PROMPT",
        tools=["search_knowledge", "list_domain_items", "get_knowledge_scope"],
        tool_defaults={"search_knowledge": {"doc_type": "project"}},
        max_iterations=3,
    ),
    "skills_agent": AgentSkill(
        prompt_key="SKILLS_AGENT_PROMPT",
        tools=["search_knowledge", "list_domain_items"],
        tool_defaults={"search_knowledge": {"doc_type": "cv"}},
        max_iterations=3,
    ),
    "personal_agent": AgentSkill(
        prompt_key="PERSONAL_AGENT_PROMPT",
        tools=["search_knowledge", "get_time_period_summary"],
        tool_defaults={"search_knowledge": {"doc_type": "personal"}},
        max_iterations=2,
    ),
    "job_prep_agent": AgentSkill(
        prompt_key="JOB_PREP_AGENT_PROMPT",
        tools=[
            "search_knowledge",
            "fetch_job_description",
            "score_job_fit",
            "extract_job_fit_signals",
            "search_recent_jobs",
        ],
        max_iterations=4,
    ),
    "calendar_agent": AgentSkill(
        prompt_key="CALENDAR_AGENT_PROMPT",
        tools=[],  # relies entirely on Google Calendar MCP tools
        mcp_server_filter=["google-calendar"],
        max_iterations=4,
    ),
}
