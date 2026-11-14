"""Hybrid (lexical TF-IDF + dense) retrieval over the corpus. Pure library, no I/O besides loading corpus.json."""
from __future__ import annotations
import json, pathlib, re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from .embed import Embedder, StaticEmbedder

DATA = pathlib.Path(__file__).resolve().parent.parent / "data" / "corpus.json"
_tok = lambda t: re.findall(r"[a-z]+", t.lower())

def load_corpus(path: pathlib.Path = DATA) -> list[dict]:
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))

class Index:
    def __init__(self, chunks: list[dict] | None = None, embedder: Embedder | None = None):
        self.chunks = chunks if chunks is not None else load_corpus()
        self.docs = [c["title"] + ". " + c["text"] for c in self.chunks]
        self.tf = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
        self.S = self.tf.fit_transform(self.docs)
        if embedder is None:
            idf = dict(zip(self.tf.get_feature_names_out(), self.tf.idf_))
            idf = {w: idf.get(w, 1.0) for w in {w for d in self.docs for w in _tok(d)}}
            embedder = StaticEmbedder(idf)
        self.embedder = embedder
        self.D = embedder.encode(self.docs)

    def scores(self, q: str, mode: str = "hybrid", alpha: float = 0.5):
        sp = (self.S @ self.tf.transform([q]).T).toarray().ravel()
        de = self.D @ self.embedder.encode([q])[0]
        z = lambda x: (x - x.min()) / (x.max() - x.min() + 1e-9)
        pick = {"sparse": sp, "dense": de, "hybrid": alpha * z(de) + (1 - alpha) * z(sp)}[mode]
        return pick, sp, de

    def search(self, q: str, k: int = 4, mode: str = "hybrid", source: list[str] | None = None):
        sc, sp, _ = self.scores(q, mode)
        cand = [i for i, c in enumerate(self.chunks) if source is None or c["source"] in source]
        order = sorted(cand, key=lambda i: -sc[i])[:k]
        return [(self.chunks[i], float(sc[i]), float(sp[i])) for i in order]
