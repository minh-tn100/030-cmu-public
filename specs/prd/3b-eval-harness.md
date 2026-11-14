> SUPERSEDED by DesignBench_PRD.docx (section 6), which matches the built code. Kept for history.

# PRD 3b: Evaluation Harness (findings vs labels, cost, ToT vs baseline)
**Epic:** 3 | **Status:** Approved scope

## Problem
Without measurement the demo is only a claim, and the current labels are self-assigned.

## Scope
In: compare findings with `golden_findings.json`; support a second-labeler file; compute verdict match, ASI match, assessed count, calls and tokens; ToT vs no-ToT comparison on high-impact gaps; markdown results file.
Out: statistical significance testing.

## Acceptance criteria
1. The harness prints verdict match, ASI match and assessed count for any run folder.
2. It reports calls and tokens per run and per ToT gap.
3. With `--labels2`, it reports agreement between the two labelers (percent and Cohen's kappa).
4. The ToT vs baseline table shows, per high-impact gap, the baseline suggestion, the ToT recommendation, extra calls and extra tokens.
5. The results file states in one line that labels were author-assigned unless a second labeler was supplied.
6. A gap where ToT changed nothing is reported as "no change" and is not hidden.

## Verification
`pytest tests/test_eval.py`; run on stub output and fake-LLM output.
