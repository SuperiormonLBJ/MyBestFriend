"""
MCP server for MyBestFriend digital twin.

Exposes the twin's knowledge base as typed MCP tools, making it composable
with any MCP-compatible client (Claude Desktop, other LLMs, MCP inspector).

All tools are sourced from tool_registry.py — the single source of truth
shared with the multi-agent graph and API endpoints.

Run in stdio mode:
    uv run python -m src.mcp_server

Register with Claude Desktop by adding to claude_desktop_config.json:
    {
      "mcpServers": {
        "mybestfriend": {
          "command": "uv",
          "args": ["run", "--project", "/path/to/backend", "python", "-m", "src.mcp_server"]
        }
      }
    }
"""
import asyncio
import json
import utils.path_setup  # noqa: F401

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from src.tool_registry import ALL_TOOLS, TOOL_MAP

server = Server("mybestfriend-twin")


# ---------------------------------------------------------------------------
# Build MCP tool schemas from LangChain @tool definitions
# ---------------------------------------------------------------------------

def _langchain_to_mcp_schema(lc_tool) -> types.Tool:
    """Convert a LangChain @tool to an MCP Tool descriptor."""
    schema = lc_tool.args_schema.model_json_schema() if lc_tool.args_schema else {}
    properties = schema.get("properties", {})
    required = schema.get("required", [])

    input_schema = {
        "type": "object",
        "properties": properties,
        "required": required,
    }

    return types.Tool(
        name=lc_tool.name,
        description=lc_tool.description or "",
        inputSchema=input_schema,
    )


_MCP_TOOLS = [_langchain_to_mcp_schema(t) for t in ALL_TOOLS]


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return _MCP_TOOLS


# ---------------------------------------------------------------------------
# Tool handler — delegates to tool_registry
# ---------------------------------------------------------------------------

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    lc_tool = TOOL_MAP.get(name)
    if not lc_tool:
        result = json.dumps({"error": f"Unknown tool: {name}"})
        return [types.TextContent(type="text", text=result)]

    loop = asyncio.get_event_loop()
    raw_result = await loop.run_in_executor(None, lc_tool.invoke, arguments)

    if isinstance(raw_result, str):
        try:
            parsed = json.loads(raw_result)
            text = json.dumps(parsed, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            text = raw_result
    else:
        text = json.dumps(raw_result, ensure_ascii=False, indent=2)

    return [types.TextContent(type="text", text=text)]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
