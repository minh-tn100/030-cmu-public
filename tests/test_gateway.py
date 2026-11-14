import json, pytest
from agent.gateway import Gateway, FakeClient, LLMUnavailable, BudgetExceeded, ClaudeClient, MissingKey, validate
S = {"a": str, "n": ("range", 0, 1)}
GOOD = json.dumps({"a": "x", "n": 0.5})

def test_bad_json_twice_then_good(tmp_path):
    gw = Gateway(FakeClient(["nope", '{"a":1}', GOOD]), audit_path=tmp_path / "a.jsonl")
    assert gw.call("t", "m", "s", "u", S)["a"] == "x"
    rec = json.loads((tmp_path / "a.jsonl").read_text().splitlines()[-1])
    assert rec["attempts"] == 3 and rec["outcome"] == "ok" and rec["in"] == 300

def test_unavailable_after_two_retries():
    gw = Gateway(FakeClient(["x", "y", "z", GOOD]))
    with pytest.raises(LLMUnavailable): gw.call("t", "m", "s", "u", S)
    assert gw.calls == 3                      # 1 try + 2 retries, never a 4th

def test_timeout_counts_as_failed_attempt():
    gw = Gateway(FakeClient([TimeoutError(), GOOD]))
    assert gw.call("t", "m", "s", "u", S)["n"] == 0.5 and gw.calls == 2

def test_call_budget():
    gw = Gateway(FakeClient([GOOD] * 5), max_calls=2)
    gw.call("t", "m", "s", "u", S); gw.call("t", "m", "s", "u", S)
    with pytest.raises(BudgetExceeded): gw.call("t", "m", "s", "u", S)

def test_token_budget():
    gw = Gateway(FakeClient([(GOOD, 100, 50)] * 3), max_tokens=150)
    gw.call("t", "m", "s", "u", S)
    with pytest.raises(BudgetExceeded): gw.call("t", "m", "s", "u", S)

def test_audit_line_per_call(tmp_path):
    p = tmp_path / "a.jsonl"; gw = Gateway(FakeClient([GOOD, GOOD]), audit_path=p)
    gw.call("r1", "m1", "s", "u", S); gw.call("r2", "m2", "s", "u", S)
    lines = [json.loads(l) for l in p.read_text().splitlines()]
    assert [l["role"] for l in lines] == ["r1", "r2"] and all({"model", "in", "out", "attempts", "outcome"} <= set(l) for l in lines)

def test_missing_key_before_network(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(MissingKey): ClaudeClient()

def test_validate_rules():
    assert validate({"a": "x", "n": 2}, S) == "n out of range"
    assert validate({"a": "x", "n": True}, S) == "n out of range"

def test_truncated_reply_fails_fast_and_counts_tokens(tmp_path):
    from agent.gateway import Truncated
    t = Truncated("cut"); t.i, t.o = 200, 600
    gw = Gateway(FakeClient([t, GOOD]), audit_path=tmp_path / "a.jsonl")
    with pytest.raises(LLMUnavailable): gw.call("critic", "m", "s", "u", S)
    assert gw.calls == 1 and gw.tokens == 800    # no retry on a cut-off reply, but its tokens are charged
    rec = json.loads((tmp_path / "a.jsonl").read_text().splitlines()[-1])
    assert "Truncated" in rec["detail"] and rec["out"] == 600

def test_out_tokens_per_role():
    from agent.gateway import OUT_TOKENS
    seen = []
    class C:
        def complete(self, model, system, user, max_tokens, timeout): seen.append(max_tokens); return GOOD, 1, 1
    gw = Gateway(C())
    gw.call("judge", "m", "s", "u", S); gw.call("critic", "m", "s", "u", S)
    assert seen == [600, OUT_TOKENS["critic"]] and OUT_TOKENS["critic"] >= 2000

def test_json_wrapped_in_prose_is_extracted_then_validated():
    gw = Gateway(FakeClient(["Sure, here it is: " + GOOD + " Hope that helps.", 'Note: {"a": 1} done']))
    assert gw.call("t", "m", "s", "u", S)["a"] == "x"
    with pytest.raises(LLMUnavailable): Gateway(FakeClient(['x {"a": 1} y'] * 3)).call("t", "m", "s", "u", S)  # schema still enforced
