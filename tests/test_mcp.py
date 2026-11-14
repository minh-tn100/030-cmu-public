import asyncio, json, sys, pathlib
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp_server.server import retrieve_impl, K_MAX
from retrieval.index import Index, load_corpus

ROOT = pathlib.Path(__file__).resolve().parent.parent

def test_validation_errors():
    for kw, code in [(dict(query=""), "empty_query"), (dict(query="x" * 1001), "query_too_long"),
                     (dict(query="memory", pillar="nope"), "bad_pillar"), (dict(query="memory", k="abc"), "bad_k")]:
        r = retrieve_impl(**kw)
        assert r["error"]["code"] == code and r["abstain"] and r["results"] == []

def test_k_is_clamped():
    r = retrieve_impl("Entries written to long-term memory carry source and trust score", k=999)
    assert len(r["results"]) <= K_MAX

def test_abstain_out_of_scope():
    r = retrieve_impl("How do I bake sourdough bread?")
    assert r["abstain"] and r["results"] == []

def test_in_scope_has_provenance():
    r = retrieve_impl("Entries written to long-term memory carry source and trust score", pillar="agent-security")
    assert not r["abstain"] and r["results"][0]["id"] == "ASI06"
    assert all({"id", "src", "verified", "date"} <= set(x) for x in r["results"])

def test_unverified_flagged():
    r = retrieve_impl("The agent pays with a limited-use token and never sees the card number", pillar="interoperability",
                      index=Index(load_corpus(ROOT / "data" / "corpus_v31.json")))   # frozen corpus with unverified chunks
    assert r["any_unverified"] and r["results"][0]["verified"] is False

def test_stdio_server_exposes_only_retrieve():
    async def go():
        p = StdioServerParameters(command=sys.executable, args=["-m", "mcp_server.server"], cwd=str(ROOT))
        async with stdio_client(p) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()
                names = [t.name for t in (await s.list_tools()).tools]
                res = await s.call_tool("retrieve", {"query": "Which third-party tool servers may the agent connect to?", "k": 4})
                return names, json.loads(res.content[0].text)
    names, d = asyncio.run(go())
    assert names == ["retrieve"]
    assert d["abstain"] is False and d["results"]
