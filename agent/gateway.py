"""LLM Gateway: the only place a model is called. Enforces retries, timeout, JSON-schema check, budget, audit.
Nothing a model returns reaches a verdict unless it passed validate()."""
from __future__ import annotations
import json, time, pathlib, os
from typing import Protocol

class LLMUnavailable(Exception): ...
class BudgetExceeded(Exception): ...
class MissingKey(Exception): ...
class Truncated(Exception): """Reply hit max_tokens; its JSON would be cut off."""

# output-token limit per role; the critic scores 3 options with rationale and needs more room
OUT_TOKENS = {"critic": 2000, "designer": 1200, "hint": 1000}

class Client(Protocol):
    def complete(self, model: str, system: str, user: str, max_tokens: int, timeout: float) -> tuple[str, int, int]: ...

class ClaudeClient:
    """Anthropic SDK, called directly (no LangChain). Not exercised in this repo's tests: needs a key and network."""
    def __init__(self, api_key: str | None = None):
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise MissingKey("ANTHROPIC_API_KEY is not set; use --llm stub or export the key")
        try:
            import anthropic
        except ImportError as e:
            raise MissingKey("pip install anthropic") from e
        self._c = anthropic.Anthropic(api_key=key)
    def complete(self, model, system, user, max_tokens, timeout):
        r = self._c.messages.create(model=model, max_tokens=max_tokens, system=system, timeout=timeout,
                                    messages=[{"role": "user", "content": user}])
        text = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
        if getattr(r, "stop_reason", None) == "max_tokens":
            e = Truncated(f"reply hit max_tokens={max_tokens}"); e.i, e.o = r.usage.input_tokens, r.usage.output_tokens
            raise e
        return text, r.usage.input_tokens, r.usage.output_tokens

class FakeClient:
    """Scripted client for tests. Each item: a str (reply), a (str, in, out) tuple, or an Exception to raise."""
    def __init__(self, script): self.script, self.calls = list(script), []
    def complete(self, model, system, user, max_tokens, timeout):
        self.calls.append({"model": model, "system": system, "user": user})
        item = self.script.pop(0)
        if isinstance(item, Exception): raise item
        return item if isinstance(item, tuple) else (item, 100, 50)

def validate(obj, schema: dict) -> str | None:
    """schema: {key: type | tuple(allowed values) | ("range", lo, hi)}. Returns an error string or None."""
    if not isinstance(obj, dict): return "not an object"
    for k, rule in schema.items():
        if k not in obj: return f"missing {k}"
        v = obj[k]
        if isinstance(rule, tuple) and rule and rule[0] == "range":
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not rule[1] <= v <= rule[2]: return f"{k} out of range"
        elif isinstance(rule, tuple):
            if v not in rule: return f"{k} not allowed"
        elif not isinstance(rule, type):
            if not rule(v): return f"{k} invalid"
        elif rule is float:
            if isinstance(v, bool) or not isinstance(v, (int, float)): return f"{k} wrong type"
        elif not isinstance(v, rule) or (rule is int and isinstance(v, bool)): return f"{k} wrong type"
    return None

def _extract_json(text: str):
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`").split("\n", 1)[-1].rsplit("```", 1)[0]
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        # model wrapped the object in prose; take the outermost {...}. Still goes through validate() after this.
        a, b = t.find("{"), t.rfind("}")
        if a == -1 or b <= a: raise
        return json.loads(t[a:b + 1])

class Gateway:
    def __init__(self, client: Client, max_calls=60, max_tokens=200_000, retries=2, timeout=30.0, audit_path=None, out_tokens=600):
        self.client, self.max_calls, self.max_tokens = client, max_calls, max_tokens
        self.retries, self.timeout, self.audit_path, self.out_tokens = retries, timeout, audit_path, out_tokens
        self.calls = self.tokens_in = self.tokens_out = 0
    @property
    def tokens(self): return self.tokens_in + self.tokens_out
    def _audit(self, rec):
        if self.audit_path:
            with open(self.audit_path, "a") as f: f.write(json.dumps(rec) + "\n")
    def call(self, role: str, model: str, system: str, user: str, schema: dict, limit: int | None = None) -> dict:
        ceiling = self.max_calls if limit is None else min(self.max_calls, limit)
        attempts, t_in, t_out, err = 0, 0, 0, "none"
        try:
            while attempts <= self.retries:
                if self.calls >= ceiling or self.tokens >= self.max_tokens:
                    raise BudgetExceeded(f"calls={self.calls}/{ceiling} tokens={self.tokens}/{self.max_tokens}")
                attempts += 1; self.calls += 1
                try:
                    text, i, o = self.client.complete(model, system, user, OUT_TOKENS.get(role, self.out_tokens), self.timeout)
                    self.tokens_in += i; self.tokens_out += o; t_in += i; t_out += o
                    obj = _extract_json(text)
                except Truncated as e:
                    i, o = getattr(e, "i", 0), getattr(e, "o", 0)
                    self.tokens_in += i; self.tokens_out += o; t_in += i; t_out += o
                    err = f"Truncated: {e}"; break   # same limit, same cut: retrying only burns budget
                except Exception as e:
                    err = f"{type(e).__name__}"; continue
                bad = validate(obj, schema)
                if bad: err = f"schema:{bad}"; continue
                self._audit({"role": role, "model": model, "in": t_in, "out": t_out, "attempts": attempts, "outcome": "ok", "ts": time.time()})
                return obj
            raise LLMUnavailable(f"{role}: {err} after {attempts} attempts")
        except (LLMUnavailable, BudgetExceeded) as e:
            self._audit({"role": role, "model": model, "in": t_in, "out": t_out, "attempts": attempts, "outcome": type(e).__name__, "detail": str(e)[:120], "ts": time.time()})
            raise
