import asyncio, json, sys, pathlib
from mcp_server.branch_store import BranchStore
ROOT = pathlib.Path(__file__).resolve().parent.parent

def test_add_get_order_and_depth():
    s = BranchStore(); a = s.add("r", "C01", None, "root A")["id"]
    b = s.add("r", "C01", a, "child", {"evidence": 0.8}, 0.7)
    assert b["depth"] == 1
    t = s.get("r", "C01")["branches"]
    assert [x["text"] for x in t] == ["root A", "child"] and t[1]["parent_id"] == a

def test_prune_keeps_row():
    s = BranchStore(); i = s.add("r", "C01", None, "x")["id"]
    assert s.prune(i) == {"ok": True}
    t = s.get("r", "C01")["branches"]; assert len(t) == 1 and t[0]["status"] == "pruned"

def test_structured_errors_not_exceptions():
    s = BranchStore()
    assert s.add("r", "C01", None, "  ")["error"]["code"] == "empty_text"
    assert s.add("r", "C01", 99, "x")["error"]["code"] == "unknown_parent"
    assert s.add("r", "C01", None, "x", {"e": 1.5})["error"]["code"] == "bad_score"
    assert s.prune(42)["error"]["code"] == "unknown_branch"

def test_parent_must_belong_to_same_claim():
    s = BranchStore(); a = s.add("r", "C01", None, "x")["id"]
    assert s.add("r", "C02", a, "y")["error"]["code"] == "unknown_parent"

def test_writes_only_to_its_own_file(tmp_path):
    db = tmp_path / "b.sqlite"; s = BranchStore(db); s.add("r", "C01", None, "x")
    assert db.exists() and [p.name for p in tmp_path.iterdir()] == ["b.sqlite"]

def test_stdio_server_exposes_exactly_three_tools(tmp_path):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    async def go():
        p = StdioServerParameters(command=sys.executable, args=["-m", "mcp_server.branch_server"], cwd=str(ROOT),
                                  env={"DESIGNBENCH_BRANCH_DB": str(tmp_path / "b.sqlite"), "PATH": "/usr/bin:/bin"})
        async with stdio_client(p) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()
                names = sorted(t.name for t in (await s.list_tools()).tools)
                add = json.loads((await s.call_tool("branch_add", {"run_id": "r", "claim_id": "C01", "text": "opt"})).content[0].text)
                got = json.loads((await s.call_tool("branch_get", {"run_id": "r", "claim_id": "C01"})).content[0].text)
                return names, add, got
    names, add, got = asyncio.run(go())
    assert names == ["branch_add", "branch_get", "branch_prune"] and add["id"] == 1 and len(got["branches"]) == 1
