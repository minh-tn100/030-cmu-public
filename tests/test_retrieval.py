"""Phase 0 regression: reproduce Checkpoint 3.1 numbers exactly (static word vectors)."""
import pytest
import pathlib
from retrieval.index import Index, load_corpus
V31 = pathlib.Path(__file__).resolve().parent.parent / "data" / "corpus_v31.json"  # frozen 3.1 corpus (5 protocol chunks unverified)
from eval.run_recall import run

@pytest.fixture(scope="module")
def res(): return run(Index(load_corpus(V31)))

@pytest.fixture(scope="module")
def res_now(): return run(Index())

def test_corpus_shape_v31():
    c = load_corpus(V31)
    assert len(c) == 15
    assert sum(x["verified"] for x in c) == 10          # 10 official OWASP ASI chunks
    assert all(x["verified"] is False for x in c if x["source"] != "OWASP-ASI")

def test_corpus_now_all_verified_with_source():
    c = load_corpus()
    assert len(c) == 15 and all(x["verified"] is True for x in c)
    for x in c:
        assert x["src"] and x["date"] and x.get("page"), x["id"]    # every chunk names source, version/date, section/page

def test_current_corpus_hybrid_top4_still_22(res_now):
    assert res_now["recall_at_k"]["hybrid"][4] == 22 and res_now["in_scope_passed"] == 23

def test_hybrid_top4_is_22_of_23(res):
    assert res["n_queries"] == 23 and res["recall_at_k"]["hybrid"][4] == 22
    assert res["misses_hybrid_k4"] == [("Q10", ["ASI08"])]

def test_baselines(res):
    assert res["recall_at_k"]["sparse"][4] == 22
    assert res["recall_at_k"]["dense"][4] == 18
    assert res["recall_at_k"]["hybrid"][1] == 16
    assert res["hybrid_top1_with_pillar_filter"] == 20

def test_gate(res):
    assert res["in_scope_passed"] == 23 and res["out_of_scope_stopped"] == 4
