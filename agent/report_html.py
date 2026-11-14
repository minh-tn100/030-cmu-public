"""Self-contained HTML report: inline CSS, no external resources, so it works offline."""
from html import escape as e

CSS = ("body{font:14px/1.45 system-ui,Arial,sans-serif;max-width:980px;margin:24px auto;color:#1a1a1a;padding:0 12px}"
       "h1{color:#0b1f4d}h2{color:#0b1f4d;border-bottom:2px solid #f7931e;padding-bottom:3px}table{border-collapse:collapse;width:100%}"
       "td,th{border:1px solid #ccd;padding:5px 7px;vertical-align:top;text-align:left}th{background:#eef2fb}"
       ".gap{color:#b42318;font-weight:700}.ok{color:#1e8449;font-weight:700}.na{color:#6b7280;font-weight:700}"
       ".pruned{color:#9aa0a6;text-decoration:line-through}.box{background:#f6f8fc;border:1px solid #ccd;padding:8px 12px;margin:8px 0}"
       ".warn{background:#fff4e0;border:1px solid #f7931e;padding:8px 12px;margin:8px 0}")
CLS = {"gap": "gap", "ok": "ok", "not_assessed": "na"}

def _tree(branches):
    kids = {}
    for b in branches: kids.setdefault(b["parent_id"], []).append(b)
    def walk(pid, d):
        out = ""
        for b in kids.get(pid, []):
            c = ' class="pruned"' if b["status"] == "pruned" else ""
            out += f'<div style="margin-left:{d*18}px"{c}>{e(b["text"])} <small>[score {b["total"]:.2f}]</small></div>' + walk(b["id"], d + 1)
        return out
    return walk(None, 0)

def render(r: dict) -> str:
    u, claims = r["usage"], {c["claim_id"]: c["text"] for c in r["claims"]}
    h = [f"<!doctype html><meta charset=utf-8><title>DesignBench review</title><style>{CSS}</style><h1>DesignBench review {e(r['run_id'])}</h1>"]
    h.append(f"<div class=box>LLM: <b>{e(r['llm'])}</b> | judge model: {e(r['models']['judge'])} | critic model: {e(r['models']['critic'])} | "
             f"calls: {u['calls']}/{u['max_calls']} | tokens in/out: {u['tokens_in']}/{u['tokens_out']} (cap {u['max_tokens']})</div>")
    h.append("<div class=warn>Labels and design are synthetic and author-assigned. A human decides; this report is evidence, not approval.</div>")
    for n in r["notes"] + r["errors"]: h.append(f"<div class=warn>{e(n)}</div>")
    rep = r["review"]
    h.append(f"<h2>Findings ({rep['gap']} gap, {rep['ok']} ok, {rep['not_assessed']} not assessed)</h2><table><tr><th>Claim</th><th>Verdict</th><th>Clause</th><th>Conf.</th><th>Re-queried</th><th>Notes</th></tr>")
    for f in rep["findings"]:
        q = e(f["cited_clause"]["quote"][:140]) + "..." if f.get("cited_clause") else "-"
        h.append(f"<tr><td><b>{e(f['claim_id'])}</b><br>{e(claims.get(f['claim_id'], ''))}</td><td class={CLS[f['verdict']]}>{e(f['verdict'])}</td>"
                 f"<td>{e(str(f.get('asi_id') or '-'))}<br><small>{q}</small></td><td>{f.get('confidence', 0)}</td><td>{'yes' if f.get('requeried') else 'no'}</td><td>{e(f.get('notes') or '')}</td></tr>")
    h.append("</table>")
    for t in r["tot"]:
        h.append(f"<h2>Options for {e(t['claim_id'])}: {e(t['status'])}</h2><div class=box>calls: {t['calls']} | seed: {e(str(t['seed']))} | widened: {t['widened']} | deepened: {t['deepened']} | "
                 f"reached stop threshold: {t['met_stop_threshold']} {e(t['note'])}</div>{_tree(t['tree'])}")
        for o in t["options"]: h.append(f"<div class=box><b>{'Recommended' if t['status'] == 'recommended' else 'For human decision'}:</b> {e(o['text'])} (score {o['total']:.2f})</div>")
        if t.get("baseline"): h.append(f"<div class=box><b>Without ToT</b> ({t['baseline']['calls']} call): {e(str(t['baseline']['suggestion']))}</div>")
    return "".join(h)
