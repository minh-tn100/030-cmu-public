> SUPERSEDED by DesignBench_PRD.docx (section 6), which matches the built code. Kept for history.

# PRD 2b: Branch Store (SQLite) and MCP branch tools
**Epic:** 2 | **Status:** Approved scope

## Problem
Option trees must be saved, inspected and replayed without giving the agent any write path to Bank X.

## Scope
In: SQLite `branches` table; MCP tools `branch_add`, `branch_get`, `branch_prune`; tree export for the report.
Out: multi-user access, remote database.

## Acceptance criteria
1. `branch_add` stores run_id, claim_id, parent_id, option text, scores and status, and returns an id.
2. `branch_get` returns the full tree for a run and claim in parent-first order.
3. `branch_prune` sets status `pruned` and the row is kept (never deleted).
4. The only tables the server can write to are in the branch store file; a test asserts no other path is opened for writing.
5. Invalid input (empty text, unknown parent, score outside 0-1) returns a structured error, not an exception.
6. The branch tools live in their own MCP server, whose tool list is exactly `branch_add`, `branch_get`, `branch_prune`; the retrieval server stays exactly `retrieve` (amended: two servers keep the read-only retrieval guarantee intact).

## Verification
`pytest tests/test_branch_store.py`, including an MCP stdio round trip.
