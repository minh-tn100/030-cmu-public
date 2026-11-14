> SUPERSEDED by DesignBench_PRD.docx (section 6), which matches the built code. Kept for history.

# PRD 3a: CLI, HTML/JSON Report, Audit Log
**Epic:** 3 Report and evidence | **Status:** Approved scope

## Scope
In: `designbench review --design --standards --budget --llm {stub,claude}`; self-contained HTML report; JSON report; JSONL audit log.
Out: web UI, PDF export (user can print the HTML).

## Acceptance criteria
1. One command produces `report.html`, `report.json` and `audit.jsonl` in the output folder.
2. The report lists every claim with verdict, cited clause, confidence and whether it was re-queried.
3. Each ToT gap shows its option tree with scores, pruned options marked, and the recommendation or escalation.
4. The HTML has no external network resource (works offline).
5. The report header shows model names, calls used, tokens used and the budget.
6. `--llm stub` runs with no key and no network, so the demo works if the network fails.
7. Exit code is non-zero if any call failed budget or schema checks that left a claim unassessed.

## Verification
`pytest tests/test_cli.py`; open `report.html` offline.
