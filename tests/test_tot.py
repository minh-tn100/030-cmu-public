import json, pytest
from agent.gateway import Gateway, FakeClient
from agent.tot import Tot, decide, total_score, shuffled, WEIGHTS
from agent.tools import InProcessTools
from mcp_server.branch_store import BranchStore

CLAIM = {"claim_id": "C01", "text": "Agent reads instructions from the same model context as data."}
CLAUSE = {"id": "ASI01", "text": "Agent Goal Hijack. Mitigations: separate data from instructions."}

def D(names=("A1", "B1", "C1")):
    return json.dumps({"options": [{"name": n, "summary": f"{n} summary", "control_query": "Agent goal hijack separate instructions from data"} for n in names]})
def C(*totals5, open_mech=False):   # each entry: (e, f, c, o) scores in label order A, B, C...
    return json.dumps({"scores": [{"label": chr(65 + i), "evidence": t[0], "effectiveness": t[1], "constraint_fit": t[2], "operability": t[3], "open_mechanism": open_mech, "critique": "ok"} for i, t in enumerate(totals5)]})
def make(script, **k):
    gw = Gateway(FakeClient(script), max_calls=k.pop("max_calls", 60)); st = BranchStore()
    return Tot(gw, st, InProcessTools(), seed="7", **k), gw, st

def test_weighted_total_is_computed_in_code():
    assert total_score({k: 5 for k in WEIGHTS}) == 1.0 and total_score({k: 1 for k in WEIGHTS}) == 0.0
    assert total_score({"evidence": 5, "effectiveness": 1, "constraint_fit": 1, "operability": 1}) == 0.35

def test_stop_at_threshold_first_level():
    t, gw, st = make([D(), C((5, 5, 5, 5), (3, 3, 3, 3), (1, 1, 1, 1))])
    r = t.solve("r", CLAIM, CLAUSE)
    assert r["status"] == "recommended" and r["met_stop_threshold"] and r["calls"] == 2

def test_decide_rules():
    mk = lambda *t: [{"total": x, "id": i} for i, x in enumerate(t)]
    assert decide(mk(0.9, 0.4, 0.3), 1, False, False)[0] == "recommend"
    assert decide(mk(0.9, 0.88, 0.3), 1, False, False)[0] == "escalate"            # tie at the stop threshold goes to the human
    a, picked = decide(mk(0.65, 0.55, 0.52, 0.1), 1, False, False)
    assert a == "expand" and [o["total"] for o in picked] == [0.65, 0.55]             # beam 2, pruned never in beam
    a, picked = decide(mk(0.60, 0.58, 0.52, 0.1), 1, False, False)
    assert a == "expand_wide" and len(picked) == 3                                   # top two within 0.05 at level 1: width 3, once
    assert decide(mk(0.60, 0.58, 0.52), 1, True, False)[0] == "expand"               # never widened twice
    assert decide(mk(0.60, 0.58, 0.52), 2, False, False)[0] == "expand"              # widening only at level 1
    best = [{"total": 0.6, "id": 1, "open_mechanism": True}, {"total": 0.5, "id": 2}]
    assert decide(best, 3, False, False)[0] == "expand_deep"                         # depth 4 once, only with an open mechanism
    assert decide(best, 4, False, True)[0] == "recommend"                            # depth cap
    assert decide([{"total": 0.6, "id": 1, "open_mechanism": False}], 3, False, False)[0] == "recommend"
    assert decide(mk(0.3, 0.2, 0.1), 1, False, False)[0] == "unconfirmed"            # nothing viable: architect decides

def test_only_pruned_options_marked_pruned_and_beam_is_two():
    # find which label maps where by running with an all-equal critic so mapping is irrelevant: totals 0.6,0.6,0.6 -> expand with beam 2
    mid = (4, 3, 3, 3)    # 0.35*.75+.3*.5+.2*.5+.15*.5 = 0.5875
    script = [D(), C(mid, (3, 3, 3, 3), (3, 3, 3, 3))]
    for _ in range(2): script += [D(("x%d" % _, "y%d" % _, "z%d" % _))]
    script += [C((5, 5, 5, 5), (5, 5, 5, 4), (1, 1, 1, 1), (1, 1, 1, 1), (1, 1, 1, 1), (1, 1, 1, 1))]
    t, gw, st = make(script); r = t.solve("r", CLAIM, CLAUSE)
    assert r["calls"] == 5 and len([b for b in r["tree"] if b["depth"] == 0]) == 3 and len([b for b in r["tree"] if b["depth"] == 1]) == 6
    assert sum(1 for b in r["tree"] if b["status"] == "pruned") == 4 and r["status"] in ("recommended", "escalate_to_human")

def test_unsupported_evidence_is_capped():
    t, gw, st = make([D(("p", "q", "r")), C((5, 5, 5, 5), (5, 5, 5, 5), (5, 5, 5, 5))])
    # make every control_query miss the library
    t.tools = type("T", (), {"retrieve": lambda self, q, p, k: {"abstain": True, "results": []}})()
    r = t.solve("r", CLAIM, CLAUSE)
    # evidence capped at 2 -> total = .35*.25+.3+.2+.15 = .7375 still >= stop; but evidence must be 2 in stored scores
    assert all(b["scores"]["evidence"] == 2 for b in r["tree"])

def test_budget_exceeded_gives_unconfirmed_with_partial_tree():
    m = (3, 3, 3, 3)
    t, gw, st = make([D(), C(m, m, m), D(), D(), C(m, m, m, m, m, m)], max_calls=3)
    r = t.solve("r", CLAIM, CLAUSE)
    assert r["status"] == "unconfirmed" and "BudgetExceeded" in r["note"] and gw.calls == 3 and len(r["tree"]) >= 3

def test_per_gap_cap_blocks_extra_calls():
    m = (3, 3, 3, 3)
    t, gw, st = make([D(), C(m, m, m)] * 5, max_calls_per_gap=2)
    r = t.solve("r", CLAIM, CLAUSE)
    assert r["status"] == "unconfirmed" and r["calls"] <= 2

def test_critic_order_is_reproducible_and_seeded():
    o = [{"id": i} for i in range(5)]
    assert any(shuffled(o, "s") != shuffled(o, f"t{i}") for i in range(5))    # seed matters
    assert [x["id"] for x in shuffled(o, "s")] == [x["id"] for x in shuffled(o, "s")]

def test_duplicate_option_names_rejected_then_retried():
    t, gw, st = make([D(("same", "same", "z")), D(), C((5, 5, 5, 5), (3, 3, 3, 3), (1, 1, 1, 1))])
    assert t.solve("r", CLAIM, CLAUSE)["status"] == "recommended" and gw.calls == 3


def test_width_rises_to_three_once_when_top_two_tie_at_level_1():
    a, b, c = (4, 3, 3, 3), (4, 3, 3, 3), (3, 3, 3, 3)       # .5875 .5875 .5 -> tie, 3 survivors
    script = [D(), C(a, b, c)] + [D((f"w{i}", f"x{i}", f"y{i}")) for i in range(3)] + [C(*[(1, 1, 1, 1)] * 9)]
    t, gw, st = make(script); r = t.solve("r", CLAIM, CLAUSE)
    assert r["widened"] and not r["deepened"] and r["status"] == "unconfirmed"
    assert len([x for x in r["tree"] if x["depth"] == 1]) == 9 and r["calls"] == 6

def test_depth_rises_to_four_once_with_open_mechanism():
    mid = (4, 3, 3, 3)                                       # .5875: survives, below stop
    low = (1, 1, 1, 1)
    script = [D(), C(mid, low, low, open_mech=True)]         # level 1: one survivor
    script += [D(("a1", "a2", "a3")), C(mid, low, low, open_mech=True)]      # level 2
    script += [D(("b1", "b2", "b3")), C(mid, low, low, open_mech=True)]      # level 3: best .5875, open mechanism
    script += [D(("c1", "c2", "c3")), C(mid, low, low, open_mech=True)]      # level 4 (only once)
    t, gw, st = make(script); r = t.solve("r", CLAIM, CLAUSE)
    assert r["deepened"] and max(x["depth"] for x in r["tree"]) == 3 and r["status"] == "recommended" and not r["met_stop_threshold"] and r["calls"] == 8

def test_no_deepening_without_open_mechanism():
    mid, low = (4, 3, 3, 3), (1, 1, 1, 1)
    script = [D(), C(mid, low, low), D(("a1", "a2", "a3")), C(mid, low, low), D(("b1", "b2", "b3")), C(mid, low, low)]
    t, gw, st = make(script); r = t.solve("r", CLAIM, CLAUSE)
    assert not r["deepened"] and max(x["depth"] for x in r["tree"]) == 2 and r["calls"] == 6

def test_critic_cannot_supply_total():
    bad = json.dumps({"scores": [{"label": l, "evidence": 5, "effectiveness": 5, "constraint_fit": 5, "operability": 5, "open_mechanism": False, "total": 0.0} for l in "ABC"]})
    t, gw, st = make([D(), bad]); r = t.solve("r", CLAIM, CLAUSE)
    assert r["options"][0]["total"] == 1.0                    # the model's "total" field is ignored
