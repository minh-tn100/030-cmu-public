"""Tool access for the agent. The ONLY tool is `retrieve` (read-only). Two interchangeable clients."""
from __future__ import annotations
import asyncio, json, pathlib, sys
from mcp_server.server import retrieve_impl

ROOT = pathlib.Path(__file__).resolve().parent.parent
ALLOWED_TOOLS = ("retrieve",)

class InProcessTools:
    names = ALLOWED_TOOLS
    def __init__(self, index=None): self.index = index
    def retrieve(self, query, pillar="", k=4): return retrieve_impl(query, pillar, k, self.index)

class McpTools:
    """Calls the real MCP server over stdio (one short-lived server process per call)."""
    names = ALLOWED_TOOLS
    def retrieve(self, query, pillar="", k=4):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        async def go():
            p = StdioServerParameters(command=sys.executable, args=["-m", "mcp_server.server"], cwd=str(ROOT))
            async with stdio_client(p) as (r, w):
                async with ClientSession(r, w) as s:
                    await s.initialize()
                    res = await s.call_tool("retrieve", {"query": query, "pillar": pillar, "k": k})
                    return json.loads(res.content[0].text)
        return asyncio.run(go())
