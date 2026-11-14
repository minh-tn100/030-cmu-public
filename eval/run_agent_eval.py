"""Compare agent findings with golden (author self-assigned) labels. Usage: python -m eval.run_agent_eval [--mcp]"""
import json, pathlib, sys
from agent.graph import run
from agent.tools import InProcessTools, McpTools
D = pathlib.Path(__file__).resolve().parent.parent / "data"

def evaluate(report, gold):
    g = {x["claim_id"]: x for x in gold}; f = {x["claim_id"]: x for x in report["findings"]}
    rows = [(cid, g[cid]["verdict"], f[cid]["verdict"], g[cid]["asi_id"], f[cid]["asi_id"]) for cid in g]
    gok = [r for r in rows if r[2] in ("gap", "ok")]
    return dict(n=len(rows),
        verdict_match=sum(r[1] == r[2] for r in rows),
        asi_match_on_assessed=sum(r[3] == r[4] for r in rows if r[1] != "not_assessed" and r[2] != "not_assessed"),
        assessed=sum(r[2] != "not_assessed" for r in rows),
        cited_rate_on_gap_ok=(sum(bool(f[r[0]]["cited_clause"]) for r in gok) / len(gok)) if gok else None,
        not_assessed_correct=sum(r[1] == "not_assessed" and r[2] == "not_assessed" for r in rows),
        wrong=[r for r in rows if r[1] != r[2]], rows=rows)

if __name__ == "__main__":
    rep = run(tools=McpTools() if "--mcp" in sys.argv else InProcessTools())
    ev = evaluate(rep, json.loads((D / "golden_findings.json").read_text()))
    print(json.dumps({"summary": {k: v for k, v in rep.items() if k != "findings"}, "eval": ev}, indent=1))
