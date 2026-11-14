import json, pathlib, re
import pytest
from agent import pipeline
from agent.pipeline import review, high_impact_gaps, IMPACT
from agent.gateway import FakeClient, MissingKey
import cli
from eval.report_eval import results, kappa, agreement

class RoleFake:
    """Answers by role (from the system prompt), so any call order works."""
    def __init__(self, garbage=False): self.n, self.garbage, self.calls = 0, garbage, []
    def complete(self, model, system, user, max_tokens, timeout):
        self.calls.append(system[:30]); self.n += 1
        if self.garbage: return "not json", 10, 5
        if "Option Designer" in system:
            return json.dumps({"options": [{"name": f"opt{self.n}-{i}", "summary": "s", "control_query": "agent goal hijack separate instructions from data"} for i in range(3)]}), 100, 80
        if "Design Critic" in system:
            labels = re.findall(r"^Option ([A-Z]):", user, re.M); lv = [(5, 5, 5, 5), (4, 4, 4, 4), (2, 2, 2, 2)]
            return json.dumps({"scores": [dict(label=l, evidence=lv[i][0], effectiveness=lv[i][1], constraint_fit=lv[i][2], operability=lv[i][3], open_mechanism=False, critique="c") for i, l in enumerate(labels)]}), 200, 100
        if "Suggest ONE fix" in system: return json.dumps({"suggestion": "just add a filter"}), 50, 20
        if "retrieval query" in system: return json.dumps({"query": re.sub(r"^Claim: ", "", user), "pillar": "agent-security", "k": 4}), 40, 30
        if "most likely relates" in system: return json.dumps({"name": "none", "gloss": ""}), 30, 10
        cid = re.search(r"Clause id: (\S+)", user).group(1)
        return json.dumps({"verdict": "gap", "supports": True, "confidence": 0.8, "cited_chunk_id": cid}), 120, 40

def test_claude_mode_end_to_end_with_fake(tmp_path):
    rep = review("claude", tmp_path, client=RoleFake(), max_calls=200, compare=True)
    for f in ("report.html", "report.json", "audit.jsonl"): assert (tmp_path / f).exists()
    assert rep["review"]["n"] == 11 and 1 <= len(rep["tot"]) <= 3
    gaps = {f["claim_id"] for f in high_impact_gaps(rep["review"]["findings"])}
    assert {t["claim_id"] for t in rep["tot"]} <= gaps                                   # ToT only on high-impact gaps
    assert all(IMPACT[next(f for f in rep["review"]["findings"] if f["claim_id"] == t["claim_id"])["asi_id"]] == "high" for t in rep["tot"])
    assert all(t["baseline"]["calls"] == 1 for t in rep["tot"])
    html = (tmp_path / "report.html").read_text()
    assert "http://" not in html and "https://" not in html and "src=" not in html     # offline
    assert str(rep["usage"]["calls"]) in html and rep["models"]["critic"] in html
    assert len((tmp_path / "audit.jsonl").read_text().splitlines()) >= rep["usage"]["calls"] // 3

def test_budget_caps_total_calls(tmp_path):
    rep = review("claude", tmp_path, client=RoleFake(), max_calls=30)
    assert rep["usage"]["calls"] <= 30

def test_stub_runs_offline_and_says_tot_skipped(tmp_path):
    rep = review("stub", tmp_path)
    assert rep["tot"] == [] and rep["usage"]["calls"] == 0 and any("ToT skipped" in n for n in rep["notes"])

def test_cli_exit_codes(tmp_path, monkeypatch):
    assert cli.main(["review", "--out", str(tmp_path / "a")]) == 0
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert cli.main(["review", "--llm", "claude", "--out", str(tmp_path / "b")]) == 3
    monkeypatch.setattr(pipeline, "ClaudeClient", lambda: RoleFake(garbage=True))
    assert cli.main(["review", "--llm", "claude", "--out", str(tmp_path / "c")]) == 2   # model failures left claims unassessed

def test_eval_results_text_and_no_change_not_hidden(tmp_path):
    rep = review("claude", tmp_path, client=RoleFake(), max_calls=200, compare=True)
    gold = json.loads((pathlib.Path("data") / "golden_findings.json").read_text())
    md = results(rep, gold)
    assert "author-assigned only" in md and "ToT vs no ToT" in md and "calls:" in md
    assert "| C0" in md or "| C1" in md
    assert "One-call baseline: just add a filter" in md and "Extra calls" in md and "no change" not in md

def test_kappa_and_agreement():
    assert kappa(["a", "b", "a", "b"], ["a", "b", "a", "b"]) == 1.0
    assert agreement([{"claim_id": "1", "verdict": "gap"}, {"claim_id": "2", "verdict": "ok"}],
                     [{"claim_id": "1", "verdict": "gap"}, {"claim_id": "2", "verdict": "gap"}])["percent"] == 50.0
