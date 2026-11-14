"""Recall of gold chunk in top-k for sparse / dense / hybrid; abstain-gate check. Usage: python -m eval.run_recall [--st]"""
import json, pathlib, sys
from retrieval.index import Index
from retrieval.gate import GATE
HERE = pathlib.Path(__file__).parent
Q = json.loads((HERE / "queries23.json").read_text())
OOS = json.loads((HERE / "oos_queries.json").read_text())

def source_of(gold):  # framework filter implied by the plan's pillar
    return ["OWASP-ASI"] if gold[0].startswith("ASI") else None

def recall(ix, mode, k, filtered=False):
    n = 0
    for q in Q:
        r = ix.search(q["query"], k=k, mode=mode, source=source_of(q["gold"]) if filtered else None)
        n += any(c["id"] in q["gold"] for c, _, _ in r)
    return n

def run(ix):
    out = {"embedder": ix.embedder.name, "n_queries": len(Q), "n_chunks": len(ix.chunks), "recall_at_k": {}}
    for mode in ("sparse", "dense", "hybrid"):
        out["recall_at_k"][mode] = {k: recall(ix, mode, k) for k in (1, 2, 3, 4, 5)}
    out["hybrid_top1_with_pillar_filter"] = recall(ix, "hybrid", 1, True)
    out["misses_hybrid_k4"] = [(q["qid"], q["gold"]) for q in Q
        if not any(c["id"] in q["gold"] for c, _, _ in ix.search(q["query"], k=4))]
    out["gate"] = GATE
    out["in_scope_passed"] = int(sum(max(ix.scores(q["query"])[1]) >= GATE for q in Q))
    out["out_of_scope_stopped"] = int(sum(max(ix.scores(q)[1]) < GATE for q in OOS))
    out["n_oos"] = len(OOS)
    return out

if __name__ == "__main__":
    if "--st" in sys.argv:
        from retrieval.embed import SentenceEmbedder
        ix = Index(embedder=SentenceEmbedder())
    else:
        ix = Index()
    res = run(ix)
    print(json.dumps(res, indent=1))
