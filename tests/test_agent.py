import json, pathlib
import pytest
from agent.schema import Finding
from agent.graph import run, build
from agent.tools import InProcessTools
from eval.run_agent_eval import evaluate

D = pathlib.Path(__file__).resolve().parent.parent / "data"
GOLD = json.loads((D / "golden_findings.json").read_text())

def test_finding_rules_enforced():
    with pytest.raises(ValueError): Finding("C", "gap")                                   # no citation
    with pytest.raises(ValueError): Finding("C", "ok", cited_clause={"chunk_id": "X", "verified": True}, support_ok=False)
    with pytest.raises(ValueError): Finding("C", "gap", cited_clause={"chunk_id": "AP2.a", "verified": False}, support_ok=True)
    with pytest.raises(ValueError): Finding("C", "maybe")
    assert Finding("C", "not_assessed").verdict == "not_assessed"

def test_agent_has_only_readonly_retrieve():
    assert InProcessTools.names == ("retrieve",)
    assert not any(hasattr(InProcessTools, n) for n in ("write", "add", "delete", "branch_add"))

def test_tot_is_disabled():
    with pytest.raises(AssertionError): build(tot_enabled=True)

def test_all_gap_ok_are_cited():
    rep = run()
    assert rep["n"] == 11
    for f in rep["findings"]:
        if f["verdict"] in ("gap", "ok"):
            assert f["cited_clause"] and f["support_ok"] and f["cited_clause"]["verified"]

def test_fail_closed_when_tool_fails():
    class Broken:
        names = ("retrieve",)
        def retrieve(self, *a, **k): raise RuntimeError("server down")
    rep = run(tools=Broken())
    assert rep["not_assessed"] == 11 and rep["gap"] == 0 and rep["ok"] == 0
    assert all("fail-closed" in f["notes"] for f in rep["findings"])

def test_baseline_vs_golden_recorded():
    """Recorded baseline AFTER adding the one-shot re-query (stub LLM, author labels).
    If this changes, update eval/RESULTS_PHASE2.md deliberately."""
    ev = evaluate(run(), GOLD)
    assert ev["verdict_match"] == 11 and ev["assessed"] == 10 and ev["asi_match_on_assessed"] == 9
    assert ev["cited_rate_on_gap_ok"] == 1.0 and ev["not_assessed_correct"] == 1 and ev["wrong"] == []

def test_requery_used_only_where_support_failed_and_never_more_than_once():
    rep = run()
    rq = {f["claim_id"] for f in rep["findings"] if f["requeried"]}
    assert rq == {"C01", "C02", "C08"}          # the three claims that failed the support check first time
    assert all(isinstance(f["requeried"], bool) for f in rep["findings"])

def test_requery_budget_zero_restores_previous_baseline(monkeypatch):
    import agent.graph as g
    monkeypatch.setattr(g, "REQUERY_BUDGET", 0)
    ev = evaluate(g.run(), GOLD)
    assert ev["verdict_match"] == 8 and {w[0] for w in ev["wrong"]} == {"C01", "C02", "C08"}

def test_requery_does_not_run_after_tool_failure_or_abstain():
    class Counting:
        names = ("retrieve",); calls = 0
        def retrieve(self, *a, **k):
            Counting.calls += 1
            return {"abstain": True, "results": [], "gate": 0.05, "top_lexical": 0.0}
    rep = run(tools=Counting())
    assert Counting.calls == 11 and rep["not_assessed"] == 11   # one call per claim, no re-query on abstain

def test_hint_is_never_a_citation():
    rep = run()
    for f in rep["findings"]:
        if f["verdict"] in ("gap", "ok"):
            assert f["cited_clause"]["chunk_id"] == f["asi_id"] and f["cited_clause"]["verified"]
