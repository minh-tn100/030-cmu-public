"""End-to-end review: review graph (all claims) -> selective ToT on high-impact gaps -> report dict.
Model failures never create verdicts: they surface as not_assessed and a non-zero exit code."""
from __future__ import annotations
import json, pathlib, time
from .graph import run, DATA
from .llm import StubLLM
from .gateway import Gateway, ClaudeClient
from .claude_llm import ClaudeLLM
from .tot import Tot, build_graph
from .tools import InProcessTools
from mcp_server.branch_store import BranchStore

IMPACT = json.loads((DATA / "impact.json").read_text())

def high_impact_gaps(findings: list[dict]) -> list[dict]:
    return [f for f in findings if f["verdict"] == "gap" and IMPACT.get(f.get("asi_id")) == "high"]

def review(llm_kind="stub", out_dir="out", design=None, standards=None, max_calls=100, max_tokens=200_000,
           max_gaps=3, client=None, compare=False, seed="0") -> dict:
    out = pathlib.Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    audit = out / "audit.jsonl"; audit.write_text("")
    claims = json.loads(pathlib.Path(design).read_text()) if design else json.loads((DATA / "bankx_claims.json").read_text())
    index = None
    if standards:
        from retrieval.index import Index, load_corpus
        index = Index(load_corpus(pathlib.Path(standards)))
    tools = InProcessTools(index)
    run_id = time.strftime("%Y%m%dT%H%M%S")
    gw = None; tot_results, notes, errors = [], [], []
    if llm_kind == "claude":
        gw = Gateway(client or ClaudeClient(), max_calls=max_calls, max_tokens=max_tokens, audit_path=audit)
        llm = ClaudeLLM(gw)
    else:
        llm = StubLLM(); notes.append("stub model: ToT skipped (needs --llm claude); verdicts come from rules, not reasoning")
    rep = run(llm, tools, claims)
    if gw:
        errors = list(llm.errors)
        store = BranchStore(out / "branches.sqlite")
        tot = Tot(gw, store, tools, seed=seed); tot_graph = build_graph(tot)
        gaps = high_impact_gaps(rep["findings"])
        for f in gaps[:max_gaps]:
            claim = next(c for c in claims if c["claim_id"] == f["claim_id"])
            clause = {"id": f["asi_id"], "text": f["cited_clause"]["quote"]}
            r = tot_graph.invoke({"run_id": run_id, "claim": claim, "clause": clause})["result"]     # LangGraph wrapper around the pure controller
            if compare:
                r["baseline"] = tot.baseline(claim, clause)
            tot_results.append(r)
        if len(gaps) > max_gaps: notes.append(f"{len(gaps) - max_gaps} high-impact gaps not explored (max_gaps={max_gaps})")
    report = {"run_id": run_id, "llm": llm_kind, "claims": claims, "review": rep, "tot": tot_results, "notes": notes, "errors": errors,
              "usage": {"calls": gw.calls if gw else 0, "tokens_in": gw.tokens_in if gw else 0, "tokens_out": gw.tokens_out if gw else 0,
                        "max_calls": max_calls if gw else 0, "max_tokens": max_tokens if gw else 0},
              "models": {"judge": getattr(llm, "model", "stub"), "critic": tot.critic_model if gw else "-"}}
    (out / "report.json").write_text(json.dumps(report, indent=2))
    from .report_html import render
    (out / "report.html").write_text(render(report))
    return report
