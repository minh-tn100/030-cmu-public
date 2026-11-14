> SUPERSEDED by DesignBench_PRD.docx (section 6), which matches the built code. Kept for history.

# PRD 2a: Option Designer, Design Critic, Rubric, Prune/Stop
**Epic:** 2 Selective ToT | **Status:** Approved scope

## Problem
Fixing a high-impact gap needs compared options, not a single suggestion, but ToT costs 4-6x compute and must be used selectively.

## User stories
- As an architect, for each high-impact gap I get 3 distinct options with scores and a recommendation.

## Scope
In: ToT subgraph; trigger only for gaps flagged high-impact; Option Designer proposes 3 options; Design Critic scores (1-5 anchored, shuffled order, larger model); tools-first evidence check; weighted rubric (evidence 0.35, effectiveness 0.30, constraint fit 0.20, operability 0.15); prune <0.5; stop at >=0.7; tie within 0.05 escalates to human; beam width 2 (expansion rules: width 3 / depth 4 only when no option reaches 0.5 after depth 3 and budget remains); deterministic controller.
Out: learned policy, attack replay, CrewAI.

## Acceptance criteria
1. ToT runs only on gaps with `impact=high`; a medium gap triggers zero ToT calls.
2. Each ToT node produces exactly 3 options with distinct names.
3. The weighted score is computed in code from the critic's 1-5 scores; the model never supplies the total.
4. An option scoring <0.5 is pruned and never expanded.
5. The search stops as soon as one option scores >=0.7.
6. If top two options differ by <=0.05, the result is `escalate_to_human` with both options shown.
7. Expansion to width 3 / depth 4 happens only when no option reaches 0.5 at depth 3 and budget remains; otherwise the result is `unresolved`.
8. A ToT call that would exceed the budget is not made, and the result is `unresolved` (fail-closed).
9. Critic input order is shuffled with a recorded seed so a run is reproducible.

## Verification
`pytest tests/test_tot.py` with scripted fake critics for each branch (prune, stop, tie, expand, budget).
