"""Thin Streamlit front-end for the capstone demo. Calls agent.pipeline.review(); no review logic lives here.
Run: make ui   (needs the optional extra: pip install -e ".[ui]")"""
from __future__ import annotations
import json, os, pathlib, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
LIVE_DIR = ROOT / "eval" / "live-20261114"
LABEL = {"gap": "🔴 GAP", "ok": "🟢 OK", "not_assessed": "⚪ NOT ASSESSED"}   # icon + text, never colour alone
OUTCOME = {"recommended": "recommended", "escalate_to_human": "tie: escalated to architect",
           "unconfirmed": "unconfirmed: escalated to architect"}
NO_CLAUSE = "No clause supports this claim, so it is not assessed."
CRITERIA = ("evidence", "effectiveness", "constraint_fit", "operability")

# ---- data-shaping helpers (pure, unit-tested) ----
def load_report(d) -> dict:
    d = pathlib.Path(d); rep = json.loads((d / "report.json").read_text())
    rep["audit"] = [json.loads(l) for l in (d / "audit.jsonl").read_text().splitlines() if l.strip()] if (d / "audit.jsonl").exists() else []
    return rep

def clean_clause(quote: str, asi_id: str | None = None, title: str | None = None, limit: int = 200) -> str:
    """Display only: drop the leading 'Description:' and prefix 'ASI08 Cascading Failures: ' when known."""
    q = quote.strip()
    if q.lower().startswith("description:"): q = q[len("description:"):].strip()
    q = (q[:limit].rstrip() + "…") if len(q) > limit else q
    head = " ".join(x for x in (asi_id, title) if x)
    return f"{head}: {q}" if head and q else q

def claim_rows(rep: dict) -> list[dict]:
    """Rows in claim order. Columns: Claim | Verdict | Control | Confidence | Claim text | Quoted clause. 'Why' is the raw audit reason."""
    text = {c["claim_id"]: c["text"] for c in rep["claims"]}
    rows = []
    for f in rep["review"]["findings"]:
        na = f["verdict"] == "not_assessed"
        quote = (f.get("cited_clause") or {}).get("quote", "")
        rows.append({"Claim": f["claim_id"], "Verdict": LABEL[f["verdict"]], "Control": f.get("asi_id") or "-",
                     "Confidence": "-" if na else f"{f.get('confidence', 0.0):.2f}", "Claim text": text.get(f["claim_id"], ""),
                     "Quoted clause": NO_CLAUSE if na or not quote else clean_clause(quote, f.get("asi_id"), (f.get("trace_tag") or {}).get("threat")),
                     "Why": f.get("notes", "") if na else ""})
    return rows

def margin_text(picked: dict, others: list[dict], tie: float) -> str:
    """e.g. '0.775 vs 0.7125, margin 0.0625, tie threshold 0.05'. Runner-up = best other candidate in the tree."""
    if not others: return f"{picked['total']:g}, no runner-up"
    r = max(others, key=lambda o: o["total"])
    return f"{picked['total']:g} vs {r['total']:g}, margin {round(picked['total'] - r['total'], 4):g}, tie threshold {tie:g}"

def tot_rows(rep: dict, tie: float | None = None) -> list[dict]:
    if tie is None:
        from agent.tot import TIE as tie     # read-only constant, so the UI shows the real threshold
    out = []
    for t in rep.get("tot", []):
        picked_ids = {o["id"] for o in t["options"]}
        pick = t["options"][0] if t["options"] else None
        others = [n for n in t.get("tree", []) if n["id"] not in picked_ids]
        cands = [{"Option": ("✅ PICKED: " if n["id"] in picked_ids else "") + n["text"], "Total": n["total"],
                  **{k.replace("_", " ").title(): n["scores"].get(k) for k in CRITERIA}} for n in t.get("tree", [])]
        out.append({"claim_id": t["claim_id"], "outcome": OUTCOME.get(t["status"], t["status"]), "calls": t["calls"], "tokens": t["tokens"],
                    "margin": margin_text(pick, others, tie) if pick else "", "candidates": cands,
                    "options": [{"Option": o["text"], "Total": o["total"], **{k.replace("_", " ").title(): o["scores"].get(k) for k in CRITERIA}} for o in t["options"]]})
    return out

def run_info(rep: dict) -> dict:
    u = rep["usage"]; audit = rep.get("audit", [])
    return {"mode": "live" if rep["llm"] == "claude" else "stub", "calls": u["calls"], "max_calls": u["max_calls"],
            "tokens_in": u["tokens_in"], "tokens_out": u["tokens_out"],
            "failed_calls": sum(1 for a in audit if a.get("outcome") != "ok") + len(rep.get("errors", []))}

def summary_line(rep: dict) -> str:
    rv = rep["review"]
    return f"{rv['gap']} gap / {rv['ok']} ok / {rv['not_assessed']} not assessed. Labels are mine, one labeler, one run."

# ---- UI ----
def main():
    import streamlit as st
    from agent.pipeline import review
    st.set_page_config(page_title="DesignBench demo", layout="wide")
    st.title("DesignBench: cited review of agent-payment designs")
    st.caption("Synthetic Bank X data only. Verdicts must cite a verified OWASP ASI clause or they stay 'not assessed'.")
    with st.sidebar:
        has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
        mode = st.radio("Model", ["stub (offline, rules only)", "live (Claude)"], index=0)
        if mode.startswith("live") and not has_key: st.error("ANTHROPIC_API_KEY is not set; live is unavailable.")
        src = st.radio("Input", ["Bank X: 11 claims", "Paste claims (JSON)"])
        pasted = st.text_area('[{"claim_id":"C01","text":"..."}]', height=140) if src.startswith("Paste") else ""
        run = st.button("Run review", type="primary", disabled=mode.startswith("live") and not has_key)
        load = st.button("Load committed live run (offline)")
        st.info("**Designed, not built:** risk router, injection scan, review queue. They are not part of this demo.")
    if load: st.session_state["rep"] = load_report(LIVE_DIR)
    if run:
        design = None; out = tempfile.mkdtemp(prefix="designbench-ui-")
        if pasted.strip():
            try: claims = json.loads(pasted); assert all("claim_id" in c and "text" in c for c in claims)
            except Exception: st.error("Pasted claims must be a JSON list of {claim_id, text}."); st.stop()
            design = str(pathlib.Path(out) / "claims.json"); pathlib.Path(design).write_text(json.dumps(claims))
        with st.spinner("Reviewing…"):
            review("claude" if mode.startswith("live") else "stub", out, design, compare=False)
        st.session_state["rep"] = load_report(out)
    rep = st.session_state.get("rep")
    if not rep: st.write("Pick an input and press **Run review**, or load the committed live run."); return
    info = run_info(rep); rv = rep["review"]
    st.subheader(f"Mode: {info['mode'].upper()}  ·  run {rep['run_id']}")
    c = st.columns(5); c[0].metric("Gap", rv["gap"]); c[1].metric("OK", rv["ok"]); c[2].metric("Not assessed", rv["not_assessed"])
    c[3].metric("Calls", f"{info['calls']}/{info['max_calls']}"); c[4].metric("Failed calls", info["failed_calls"])
    st.caption(f"{summary_line(rep)}  ·  Tokens in/out: {info['tokens_in']} / {info['tokens_out']}  ·  judge: {rep['models']['judge']}  ·  critic: {rep['models']['critic']}")
    for n in rep.get("notes", []): st.warning(n)
    rows = claim_rows(rep)
    TC = st.column_config.TextColumn
    st.dataframe([{k: v for k, v in r.items() if k != "Why"} for r in rows], width="stretch", hide_index=True, row_height=80,   # claim order, no auto-sort; >2x default row height so wrapped text is not clipped
                 column_config={"Claim": TC(width="small"), "Verdict": TC(width="small"), "Control": TC(width="small"), "Confidence": TC(width="small"),
                                "Claim text": TC(width="large"), "Quoted clause": TC(width="large")})
    whys = [r for r in rows if r["Why"]]
    if whys:
        with st.expander("Why? Raw audit reason for not-assessed claims"):
            for r in whys: st.markdown(f"**{r['Claim']}**: `{r['Why']}`")
    st.subheader("High-impact gaps: options, critic scores, outcome")
    if not rep.get("tot"): st.write("None in this run (the stub skips Tree-of-Thought)." if info["mode"] == "stub" else "None.")
    for t in tot_rows(rep):
        with st.expander(f"{t['claim_id']}: {t['outcome']}  ({t['calls']} calls, {t['tokens']} tokens)", expanded=True):
            st.markdown(f"**Picked: {t['margin']}**")
            st.dataframe(t["candidates"], width="stretch", hide_index=True,
                         column_config={"Option": TC(width="large"), "Total": st.column_config.NumberColumn(width="small", format="%.4g")})

if __name__ == "__main__":
    main()
