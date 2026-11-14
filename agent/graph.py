"""ReAct-style loop as a LangGraph graph: load_design -> (plan -> retrieve -> judge -> write)* -> report.
ToT slot (Checkpoint 4.1) is a designed-but-disabled edge: `tot_enabled=False`, nothing is wired."""
from __future__ import annotations
import json, pathlib
from typing import TypedDict
from langgraph.graph import StateGraph, END
from .schema import Finding
from .llm import LLM, StubLLM
from .tools import InProcessTools

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"
LAYER = {"ASI01": "input/goal", "ASI02": "tool", "ASI03": "identity", "ASI04": "supply chain", "ASI05": "runtime",
         "ASI06": "memory", "ASI07": "agent communication", "ASI08": "orchestration", "ASI09": "human interface", "ASI10": "governance"}

class S(TypedDict):
    claims: list
    i: int
    plan: dict
    tool_result: dict
    judged: dict
    hint: dict
    requeried: bool
    budget: int
    findings: list
    report: dict

def _control(chunk_text: str) -> str:
    tail = chunk_text.split("Mitigations:", 1)[-1].strip()
    return tail.split(";")[0].strip(" .")[:120]

REQUERY_BUDGET = 6   # total re-queries per run; at most one per claim

def build(llm: LLM | None = None, tools=None, tot_enabled: bool = False, claims: list | None = None):
    llm, tools = llm or StubLLM(), tools or InProcessTools()
    assert tools.names == ("retrieve",), "agent must have read-only retrieve as its only tool"
    assert not tot_enabled, "ToT is design-only in this build"

    def load_design(s):
        return {"claims": claims or json.loads((DATA / "bankx_claims.json").read_text()), "i": 0, "findings": [], "budget": REQUERY_BUDGET}
    def plan(s):
        text = s["claims"][s["i"]]["text"]
        return {"plan": llm.plan(text), "hint": llm.hypothesize(text), "requeried": False}
    def retrieve(s):
        p = s["plan"]
        try: r = tools.retrieve(p["query"], p["pillar"], p["k"])
        except Exception as e: r = {"error": {"code": "tool_failure", "message": repr(e)[:200]}, "abstain": True, "results": []}
        return {"tool_result": r}
    def judge(s):
        c, r = s["claims"][s["i"]], s["tool_result"]
        if r.get("error") or r.get("abstain") or not r.get("results"):
            return {"judged": {"fail_closed": r.get("error", {}).get("code") or "abstain"}}
        top = r["results"][0]
        j = llm.judge(c["text"], top); j["chunk"] = top
        return {"judged": j}
    def needs_requery(s):
        j = s["judged"]
        gate_passed_but_unsupported = "fail_closed" not in j and not j["supports"]
        return gate_passed_but_unsupported and s["hint"] and not s["requeried"] and s["budget"] > 0
    def route_judge(s): return "requery" if needs_requery(s) else "write"
    def requery(s):
        p, h = s["plan"], s["hint"]
        q = f"{p['query']} {h['name']}: {h['gloss']}"
        try: r = tools.retrieve(q, p["pillar"], p["k"])
        except Exception as e: r = {"error": {"code": "tool_failure", "message": repr(e)[:200]}, "abstain": True, "results": []}
        return {"tool_result": r, "requeried": True, "budget": s["budget"] - 1}
    def write(s):
        c, j = s["claims"][s["i"]], s["judged"]
        if "fail_closed" in j:
            f = Finding(c["claim_id"], "not_assessed", notes=f"fail-closed: {j['fail_closed']}", requeried=s["requeried"])
        else:
            ch = j["chunk"]
            if j["supports"] and j["verdict"] in ("gap", "ok"):
                f = Finding(c["claim_id"], j["verdict"], asi_id=ch["id"], support_ok=True, confidence=j["confidence"],
                            cited_clause={"chunk_id": ch["id"], "verified": ch["verified"], "quote": ch["text"][:200]},
                            trace_tag={"threat": ch["title"], "layer": LAYER.get(ch["id"], "n/a"), "control": _control(ch["text"])},
                            requeried=s["requeried"])
            else:
                why = "top clause failed the support check" if not j["supports"] else "claim not assessable from text"
                f = Finding(c["claim_id"], "not_assessed", notes=f"{why} (top={ch['id']}, lexical={ch['lexical']}, verified={ch['verified']})", requeried=s["requeried"])
        return {"findings": s["findings"] + [f.to_dict()], "i": s["i"] + 1}
    def route(s): return "plan" if s["i"] < len(s["claims"]) else "report"
    def report(s):
        fs = s["findings"]
        return {"report": {"n": len(fs), **{v: sum(f["verdict"] == v for f in fs) for v in ("gap", "ok", "not_assessed")}, "findings": fs}}

    g = StateGraph(S)
    for n, fn in [("load_design", load_design), ("plan", plan), ("retrieve", retrieve), ("judge", judge), ("requery", requery), ("write", write), ("report", report)]:
        g.add_node(n, fn)
    g.set_entry_point("load_design"); g.add_edge("load_design", "plan"); g.add_edge("plan", "retrieve")
    g.add_edge("retrieve", "judge"); g.add_conditional_edges("judge", route_judge, {"requery": "requery", "write": "write"}); g.add_edge("requery", "judge")
    g.add_conditional_edges("write", route, {"plan": "plan", "report": "report"}); g.add_edge("report", END)
    return g.compile()

def run(llm=None, tools=None, claims=None) -> dict:
    return build(llm, tools, claims=claims).invoke({}, {"recursion_limit": 200})["report"]
