"""MCP server for the branch store. Exactly three tools. The retrieval server (server.py) stays read-only and separate."""
import os
from mcp.server.fastmcp import FastMCP
from .branch_store import BranchStore

mcp = FastMCP("designbench-branches")
STORE = BranchStore(os.environ.get("DESIGNBENCH_BRANCH_DB", "branches.sqlite"))

@mcp.tool()
def branch_add(run_id: str, claim_id: str, text: str, parent_id: int | None = None, scores: dict | None = None, total: float = 0.0) -> dict:
    """Add one option to the option tree. Writes only to the branch store."""
    return STORE.add(run_id, claim_id, parent_id, text, scores, total)

@mcp.tool()
def branch_get(run_id: str, claim_id: str) -> dict:
    """Return the whole option tree for one claim, parent first."""
    return STORE.get(run_id, claim_id)

@mcp.tool()
def branch_prune(branch_id: int) -> dict:
    """Mark an option as pruned. The row is kept."""
    return STORE.prune(branch_id)

if __name__ == "__main__":
    mcp.run()
