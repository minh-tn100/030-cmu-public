> SUPERSEDED by DesignBench_PRD.docx (section 6), which matches the built code. Kept for history.

# PRD 1a: LLM Gateway + Claude Adapter
**Epic:** 1 Real-LLM review core | **Status:** Approved scope

## Problem
The agent only runs on a rule-based stub. A real model can return malformed JSON, time out, or overspend; none of that may reach a verdict unchecked.

## User stories
- As an architect, I run a review with my own API key and it never exceeds my call and token budget.
- As the CIO, I can see every model call that was made, with its cost.

## Scope
In: `LLMGateway` (retry, timeout, JSON-schema check, budget, audit), `ClaudeClient` (Anthropic SDK direct), `FakeClient` for tests, config via env (`ANTHROPIC_API_KEY`, `DB_JUDGE_MODEL`, `DB_CRITIC_MODEL`).
Out: other providers, streaming, caching.

## Acceptance criteria
1. The gateway rejects any response that fails the role's JSON schema and retries at most 2 times.
2. After 2 failed retries the gateway raises `LLMUnavailable`, and the caller records `not_assessed`.
3. A call that exceeds the timeout (default 30 s) counts as a failed attempt.
4. The gateway stops with `BudgetExceeded` when calls reach `max_calls` or tokens reach `max_tokens`.
5. Every call writes one audit line with role, model, input tokens, output tokens, attempts and outcome.
6. With no `ANTHROPIC_API_KEY`, `ClaudeClient` raises a clear error before any network call.
7. Tests run entirely on `FakeClient`; no test touches the network.

## Verification
`pytest tests/test_gateway.py` passes; a scripted fake returning bad JSON twice then good JSON yields one success with attempts=3.
