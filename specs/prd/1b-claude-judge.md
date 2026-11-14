> SUPERSEDED by DesignBench_PRD.docx (section 6), which matches the built code. Kept for history.

# PRD 1b: Claude Planner/Judge with Unchanged Hard Rules
**Epic:** 1 | **Status:** Approved scope

## Problem
Replacing the stub with a real model must not weaken the rules that make findings trustworthy.

## User stories
- As the CIO, I want every gap/ok verdict backed by a verified clause, whatever model runs.

## Scope
In: `ClaudeLLM` implementing the existing `LLM` protocol (plan, judge, hypothesize); prompts that treat retrieved text as untrusted data; reuse of `Finding` hard rules and the re-query step.
Out: changes to the retrieval gate or `Finding` rules.

## Acceptance criteria
1. `ClaudeLLM` passes the same protocol checks as `StubLLM`.
2. A verdict of gap or ok without a cited, verified clause is rejected by `Finding` and stored as `not_assessed`.
3. When the model cites a clause not present in the retrieved chunks, the finding is `not_assessed`.
4. Retrieved chunk text is wrapped as quoted data, and a chunk containing "ignore previous instructions" does not change any verdict in the injection test.
5. The re-query step runs at most once per claim and at most 6 per run.
6. With `FakeClient` replaying recorded answers, the 11 Bank X claims produce 11 findings with no exception.

## Verification
`pytest tests/test_claude_judge.py`; injection fixture in `tests/fixtures/injection_chunk.json`.
