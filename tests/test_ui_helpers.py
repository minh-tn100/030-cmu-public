from app.ui import load_report, claim_rows, tot_rows, run_info, LIVE_DIR

def test_claim_rows_live_run():
    rows = claim_rows(load_report(LIVE_DIR))
    assert len(rows) == 11 and rows[0]["Verdict"].endswith("GAP") and rows[0]["Control"] == "ASI01"
    assert rows[-1]["Verdict"].endswith("NOT ASSESSED") and rows[-1]["Control"] == "-"   # C11: no quote, shows the reason

def test_run_info_live_run():
    i = run_info(load_report(LIVE_DIR))
    assert (i["mode"], i["calls"], i["failed_calls"]) == ("live", 44, 0)

def test_failed_calls_and_stub_label():
    rep = {"llm": "stub", "usage": {"calls": 0, "max_calls": 0, "tokens_in": 0, "tokens_out": 0},
           "audit": [{"outcome": "ok"}, {"outcome": "error"}], "errors": [], "tot": [{"claim_id": "C1", "status": "escalate_to_human", "calls": 2, "tokens": 5, "options": [], "tree": []}]}
    assert run_info(rep)["mode"] == "stub" and run_info(rep)["failed_calls"] == 1
    assert tot_rows(rep)[0]["outcome"].startswith("tie")

def test_clean_clause_and_margin():
    from app.ui import clean_clause, margin_text
    assert clean_clause("Description: Cascades happen.", "ASI08", "Cascading Failures") == "ASI08 Cascading Failures: Cascades happen."
    assert clean_clause("Plain text") == "Plain text"
    assert margin_text({"total": 0.775}, [{"total": 0.7125}, {"total": 0.66}], 0.05) == "0.775 vs 0.7125, margin 0.0625, tie threshold 0.05"

def test_not_assessed_row_is_plain():
    r = claim_rows(load_report(LIVE_DIR))[-1]
    assert r["Quoted clause"].startswith("No clause supports") and r["Confidence"] == "-" and "lexical" in r["Why"]
