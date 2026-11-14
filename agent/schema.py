"""Finding schema. Hard rules are enforced at construction, so no code path can emit an unsupported verdict."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict

VERDICTS = ("gap", "ok", "not_assessed")

@dataclass
class Finding:
    claim_id: str
    verdict: str
    asi_id: str | None = None
    cited_clause: dict | None = None      # {"chunk_id","verified","quote"}
    support_ok: bool = False
    confidence: float = 0.0
    trace_tag: dict = field(default_factory=dict)   # threat, layer, control
    notes: str = ""
    requeried: bool = False

    def __post_init__(self):
        if self.verdict not in VERDICTS:
            raise ValueError(f"bad verdict {self.verdict!r}")
        if self.verdict in ("gap", "ok"):
            if not self.cited_clause or not self.support_ok:
                raise ValueError("gap/ok requires a cited clause that passed the support check")
            if not self.cited_clause.get("verified"):
                raise ValueError("an unverified chunk cannot be the sole basis of gap/ok")
    def to_dict(self): return asdict(self)
