"""
MCP client for consuming tools from external MCP servers.

Connects to external MCP servers and wraps their tools as LangChain-compatible
tools that ReAct agents can use alongside the built-in tool_registry tools.

Configuration via config.yaml:
    mcp_clients:
      - name: "web-search"
        command: "npx"
        args: ["-y", "@anthropic/mcp-server-web-search"]
        env:
          ANTHROPIC_API_KEY: "..."

Usage:
    from src.mcp_client import load_external_tools
    external_tools = load_external_tools()  # returns list of LangChain tools
"""
import asyncio
import json
import threading
import utils.path_setup  # noqa: F401

from langchain_core.tools import StructuredTool
from utils.config_loader import ConfigLoader

_cached_tools: list | None = None
_cache_lock = threading.Lock()


def _build_langchain_tool(session, mcp_tool) -> StructuredTool:
    """Wrap a single MCP tool as a LangChain StructuredTool."""
    tool_name = mcp_tool.name
    tool_desc = mcp_tool.description or ""
    input_schema = mcp_tool.inputSchema or {"type": "object", "properties": {}}

    # Build a pydantic-compatible schema for arguments
    properties = input_schema.get("properties", {})
    required = set(input_schema.get("required", []))

    def _make_call_fn(sess, tname):
        def call_fn(**kwargs) -> str:
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(sess.call_tool(tname, kwargs))
                parts = []
                for content in result.content:
                    if hasattr(content, "text"):
                        parts.append(content.text)
                return "\n".join(parts) if parts else "No result"
            except Exception as e:
                return f"MCP tool error: {e}"
            finally:
                loop.close()
        return call_fn

    call_fn = _make_call_fn(session, tool_name)

    # Build function signature description from schema
    param_desc = []
    for pname, pschema in properties.items():
        ptype = pschema.get("type", "string")
        pdesc = pschema.get("description", "")
        req = " (required)" if pname in required else ""
        param_desc.append(f"  {pname}: {ptype}{req} — {pdesc}")

    full_desc = tool_desc
    if param_desc:
        full_desc += "\n\nParameters:\n" + "\n".join(param_desc)

    return StructuredTool.from_function(
        func=call_fn,
        name=f"mcp_{tool_name}",
        description=full_desc,
    )


async def _connect_and_list_tools(server_config: dict) -> list[StructuredTool]:
    """Connect to an MCP server and return its tools as LangChain tools."""
    try:
        from mcp import ClientSession
        from mcp.client.stdio import StdioServerParameters, stdio_client
    except ImportError:
        print("[mcp_client] mcp package not installed — skipping external MCP tools")
        return []

    command = server_config.get("command", "")
    args = server_config.get("args", [])
    env = server_config.get("env")
    server_name = server_config.get("name", command)

    if not command:
        print(f"[mcp_client] skipping server with no command: {server_config}")
        return []

    params = StdioServerParameters(command=command, args=args, env=env)

    try:
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools_response = await session.list_tools()
                lc_tools = []
                for mcp_tool in tools_response.tools:
                    try:
                        lc_tool = _build_langchain_tool(session, mcp_tool)
                        lc_tools.append(lc_tool)
                    except Exception as e:
                        print(f"[mcp_client] failed to wrap tool {mcp_tool.name} from {server_name}: {e}")
                print(f"[mcp_client] loaded {len(lc_tools)} tools from {server_name}")
                return lc_tools
    except Exception as e:
        print(f"[mcp_client] failed to connect to {server_name}: {e}")
        return []


def load_external_tools(force_reload: bool = False) -> list:
    """
    Load tools from all configured external MCP servers.

    Returns a list of LangChain StructuredTool instances.
    Results are cached per process; use force_reload=True to refresh.
    """
    global _cached_tools

    with _cache_lock:
        if _cached_tools is not None and not force_reload:
            return _cached_tools

    cfg = ConfigLoader()
    mcp_clients_config = cfg.config.get("mcp_clients", [])

    if not mcp_clients_config:
        _cached_tools = []
        return _cached_tools

    all_tools = []
    loop = asyncio.new_event_loop()
    try:
        for server_config in mcp_clients_config:
            tools = loop.run_until_complete(_connect_and_list_tools(server_config))
            all_tools.extend(tools)
    finally:
        loop.close()

    with _cache_lock:
        _cached_tools = all_tools

    print(f"[mcp_client] total external tools loaded: {len(all_tools)}")
    return all_tools


def load_external_tools_by_server(server_filter: list[str]) -> list:
    """
    Load tools from specific external MCP servers by name.

    server_filter: list of server names from config.yaml mcp_clients[].name.
      ["*"]          — all configured servers (same as load_external_tools)
      ["google-calendar"] — only the server named "google-calendar"

    Tools are loaded fresh per call (no cross-server caching at this level).
    """
    if not server_filter:
        return []

    if server_filter == ["*"]:
        return load_external_tools()

    cfg = ConfigLoader()
    mcp_clients_config = cfg.config.get("mcp_clients", [])
    if not mcp_clients_config:
        return []

    matched = [s for s in mcp_clients_config if s.get("name") in server_filter]
    if not matched:
        print(f"[mcp_client] no configured servers match filter {server_filter}")
        return []

    all_tools = []
    loop = asyncio.new_event_loop()
    try:
        for server_config in matched:
            tools = loop.run_until_complete(_connect_and_list_tools(server_config))
            all_tools.extend(tools)
    finally:
        loop.close()

    print(f"[mcp_client] loaded {len(all_tools)} tools for servers {server_filter}")
    return all_tools
