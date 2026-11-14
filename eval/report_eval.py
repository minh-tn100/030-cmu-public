"""Evaluate a run folder: python -m eval.report_eval out/ [--labels2 file.json]. Writes out/RESULTS.md."""
import json, pathlib, sys
from eval.run_agent_eval import evaluate
D = pathlib.Path(__file__).resolve().parent.parent / "data"

def kappa(a: list[str], b: list[str]) -> float:
    n = len(a); po = sum(x == y for x, y in zip(a, b)) / n
    cats = set(a) | set(b); pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return 1.0 if pe == 1 else round((po - pe) / (1 - pe), 3)

def agreement(g1, g2):
    m1 = {x["claim_id"]: x["verdict"] for x in g1}; m2 = {x["claim_id"]: x["verdict"] for x in g2}
    ids = sorted(set(m1) & set(m2)); a, b = [m1[i] for i in ids], [m2[i] for i in ids]
    return {"n": len(ids), "percent": round(100 * sum(x == y for x, y in zip(a, b)) / len(ids), 1), "kappa": kappa(a, b)}

def results(report: dict, gold: list, gold2: list | None = None) -> str:
    ev = evaluate(report["review"], gold); u = report["usage"]
    L = [f"# Results for run {report['run_id']} ({report['llm']})", ""]
    L.append("Labels: " + ("author-assigned, plus a second labeler (see agreement)." if gold2 else "author-assigned only; no independent second labeler, so these numbers are weak evidence."))
    L += ["", f"- verdict match: {ev['verdict_match']}/{ev['n']}", f"- ASI match on assessed: {ev['asi_match_on_assessed']}", f"- assessed: {ev['assessed']}/{ev['n']}",
          f"- cited rate on gap/ok: {ev['cited_rate_on_gap_ok']}", f"- calls: {u['calls']}/{u['max_calls']}, tokens in/out: {u['tokens_in']}/{u['tokens_out']}"]
    if gold2:
        ag = agreement(gold, gold2); L.append(f"- labeler agreement: {ag['percent']}% on {ag['n']} claims, kappa {ag['kappa']}")
        ev2 = evaluate(report["review"], gold2); L.append(f"- verdict match vs second labeler: {ev2['verdict_match']}/{ev2['n']}")
    L += ["", "## ToT vs no ToT (high-impact gaps)", ""]
    if not report["tot"]: L.append("No ToT run in this folder.")
    else:
        L += ["| Claim | ToT status | ToT calls | ToT tokens | Baseline calls | Baseline tokens | Extra calls | Extra tokens |", "|---|---|---|---|---|---|---|---|"]
        for t_ in report["tot"]:
            b = t_.get("baseline")
            ec = t_["calls"] - b["calls"] if b else "-"; et = t_.get("tokens", 0) - b.get("tokens", 0) if b else "-"
            L.append(f"| {t_['claim_id']} | {t_['status']} | {t_['calls']} | {t_.get('tokens', '-')} | {b['calls'] if b else '-'} | {b.get('tokens', '-') if b else '-'} | {ec} | {et} |")
        L += ["", "### Side by side (read and judge; this file does not decide which is better)", ""]
        for t_ in report["tot"]:
            b = t_.get("baseline")
            rec = "; ".join(o["text"] for o in t_["options"]) or "none (status " + t_["status"] + ")"
            L += [f"**{t_['claim_id']}** ({t_['status']}, widened={t_['widened']}, deepened={t_['deepened']})", f"- ToT: {rec}",
                  f"- One-call baseline: {b['suggestion'] if b and b.get('suggestion') else 'not run'}", ""]
        L += ["Gaps that ended 'unconfirmed' or 'escalate_to_human' are listed like the others; none is dropped."]
    return "\n".join(L) + "\n"

if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1]); rep = json.loads((out / "report.json").read_text())
    gold = json.loads((D / "golden_findings.json").read_text())
    gold2 = json.loads(pathlib.Path(sys.argv[sys.argv.index("--labels2") + 1]).read_text()) if "--labels2" in sys.argv else None
    md = results(rep, gold, gold2); (out / "RESULTS.md").write_text(md); print(md)
