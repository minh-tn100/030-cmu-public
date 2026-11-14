"""LLM interface. Phase 2 ships a deterministic StubLLM only (no API key needed).
The stub is rule-based and written by the same author as the labels: it tests the PLUMBING (schema, hard rules,
tool calls, fail-closed), NOT the reasoning quality of a real model. A real LLM plugs in behind the same two methods."""
from __future__ import annotations
import re
from typing import Protocol

class LLM(Protocol):
    def plan(self, claim_text: str) -> dict: ...                      # -> {"query","pillar","k"}
    def judge(self, claim_text: str, chunk: dict) -> dict: ...        # -> {"verdict","supports","confidence"}
    def hypothesize(self, claim_text: str) -> dict | None: ...        # -> {"name","gloss"} control the claim likely relates to, or None

POS = re.compile(r"mutually authenticated|digitally signed|sandbox|explicit customer confirmation|timeout that kills", re.I)
NEG = re.compile(r"\bno\b|\bnot\b|without|automatically|single permission|same model context|public registry", re.I)
LEXICAL_SUPPORT_MIN = 0.10   # fixed a priori, before seeing Bank X results

class StubLLM:
    def plan(self, claim_text):
        return {"query": claim_text, "pillar": "agent-security", "k": 4}
    def judge(self, claim_text, chunk):
        supports = chunk["verified"] and chunk["lexical"] >= LEXICAL_SUPPORT_MIN
        if POS.search(claim_text): v = "ok"
        elif NEG.search(claim_text): v = "gap"
        else: v = "not_assessed"
        return {"verdict": v, "supports": bool(supports), "confidence": round(min(1.0, chunk["lexical"] * 2), 2)}


# Stand-in for an LLM naming the control it expects ("Thought names the control", Checkpoint 3.1).
# Keyword rules written from the ASI titles and descriptions; glosses are short canned phrases.
# The hint is used ONLY to word a re-query. It never decides a verdict and never counts as a citation.
HINTS = [
    ("Cascading Failures", "propagation of a fault across agents", r"\bfails?\b|retries|failure|propagat"),
    ("Rogue Agents", "agents drifting from authorised scope, kill switch, inventory", r"inventory of agents|kill switch|register a new agent|misbehaving"),
    ("Memory and Context Poisoning", "poisoned stored memory, provenance of memory writes", r"long-term memory|memory stores|provenance"),
    ("Insecure Inter-Agent Communication", "authentication, signing and replay protection of agent messages", r"messages between|nonce|replay"),
    ("Unexpected Code Execution", "sandboxing of generated code", r"scripts|sandbox|generated code"),
    ("Agentic Supply Chain Vulnerabilities", "runtime-loaded third-party components, signed and pinned", r"registry|plugin|third-party|pinned"),
    ("Identity and Privilege Abuse", "cached credentials and permissions used after they change", r"token|credential|delegat|privilege|mandate limit"),
    ("Human-Agent Trust Exploitation", "user over-trust, confirmation of risky actions", r"customer confirmation|confirmation|reasoning is shown"),
    ("Tool Misuse and Exploitation", "over-scoped tool permissions, per-call validation", r"tool is granted|permission|per-call"),
    ("Agent Goal Hijack", "attacker text in content redirecting the agent's goal", r"same model context|instructions from data|prompt injection"),
]
def _hypothesize(self, claim_text):
    for name, gloss, pat in HINTS:
        if re.search(pat, claim_text, re.I): return {"name": name, "gloss": gloss}
    return None
StubLLM.hypothesize = _hypothesize
