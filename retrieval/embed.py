"""Embedding interface. `Embedder.encode(texts) -> unit-norm ndarray (n, d)`.
StaticEmbedder = averaged static word vectors (stand-in used in Checkpoint 3.1, NOT a sentence-embedding model).
SentenceEmbedder = real sentence-embedding model; needs `sentence-transformers` and model weights (run on a machine that can download them)."""
from __future__ import annotations
import re, pathlib
from typing import Protocol
import numpy as np

_tok = lambda t: re.findall(r"[a-z]+", t.lower())

class Embedder(Protocol):
    name: str
    def encode(self, texts: list[str]) -> np.ndarray: ...

def _unit(m: np.ndarray) -> np.ndarray:
    return m / (np.linalg.norm(m, axis=1, keepdims=True) + 1e-9)

class StaticEmbedder:
    name = "static-word-vectors(en_core_web_md)"
    def __init__(self, idf: dict[str, float] | None = None):
        import en_core_web_md
        from spacy.vocab import Vocab
        p = pathlib.Path(en_core_web_md.__file__).parent
        d = [x for x in p.iterdir() if x.is_dir() and x.name.startswith("en_core")][0]
        self.voc = Vocab().from_disk(d / "vocab")
        self.idf = idf or {}
    def _one(self, t: str) -> np.ndarray:
        vs, ws = [], []
        for w in _tok(t):
            if self.voc.has_vector(w):
                vs.append(self.voc[w].vector); ws.append(self.idf.get(w, 1.0))
        if not vs: return np.zeros(300)
        return np.average(vs, axis=0, weights=ws)
    def encode(self, texts): return _unit(np.vstack([self._one(t) for t in texts]))

class SentenceEmbedder:
    def __init__(self, model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        self.name = f"sentence-transformers:{model}"
        self.m = SentenceTransformer(model)
    def encode(self, texts):
        return _unit(np.asarray(self.m.encode(list(texts), normalize_embeddings=False)))
