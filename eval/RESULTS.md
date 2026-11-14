# DesignBench: evaluation results

All numbers below were measured; nothing is an estimate unless marked "design". Labels for the 11 Bank X claims are the **author's own** (no independent second labeler yet), so accuracy figures are weak evidence. Detailed lab notes from the earlier phases, in Vietnamese, are in `RESULTS_PHASE2.md`.

## 1. Retrieval (offline, static word vectors, 23 queries, 15 chunks)

Reproduce: `make recall`.

| Retriever | top-1 | top-2 | top-3 | top-4 | top-5 |
|---|---|---|---|---|---|
| Sparse (BM25-style) | 19 | 20 | 21 | 22 | 22 |
| Dense (static vectors) | 9 | 12 | 15 | 17 | 18 |
| **Hybrid** | 18 | 20 | 22 | **22** | 22 |

- Hybrid top-1 with the pillar filter: 20/23. The one top-4 miss is Q10 (expected ASI08).
- Abstain gate (lexical score 0.05): 23/23 in-scope queries pass; **3 of 5** out-of-scope queries are stopped. The gate is the weakest retrieval guardrail; the support check is the second layer.

## 2. Review agent, deterministic stub (offline)

Reproduce: `make eval`.

| Metric | Result |
|---|---|
| Verdict matches label | 11/11 |
| Verdict and ASI control both match | 10/11 |
| gap/ok findings with a verified, support-checked citation | 100% |

The stub's rules were written by the same author as the labels, after seeing failures; this proves the pipeline (schema, hard rules, tool calls, fail-closed, one re-query) and not reasoning quality. Known stub weakness: C10 gets the right verdict with the wrong clause (ASI04 instead of ASI10), because the support check is lexical.

## 3. Live run with Claude (2026-11-14)

Reproduce: `make demo-claude` (needs `ANTHROPIC_API_KEY`). Models: planner, hint, judge and option designer `claude-sonnet-5-5`; design critic `claude-opus-5-5`. Flags: `--compare --max-calls 100`. Artifacts of the final run: [`eval/live-20261114/`](live-20261114/) (`report.html`, `report.json`, `audit.jsonl`, `RESULTS.md`).

| Metric | Stub | Live, before fixes | **Live, after fixes** |
|---|---|---|---|
| Verdict matches label | 11/11 | 9/11 | **10/11** |
| Verdict and ASI both match | 10/11 | 8/11 | **9/11** |
| not_assessed | 1 | 3 | 1 (C11, matches label) |
| False assurance (true gap reported "ok") | 0 | 0 | **0** |
| gap/ok with verified citation | 100% | 100% | 100% |
| Failed model calls | – | 2 | **0** |
| ToT produced a recommendation | – | 0/2 gaps | **3/3 gaps** |
| Calls / tokens | 0 | 44 / ~26k | 44 / ~27k (12,685 in, 14,387 out) |

### Cost against the design estimate

| | Design estimate (Checkpoint 5.1) | Measured |
|---|---|---|
| Review, per claim | ~3 calls (plan, hint, judge) | 35 calls / 11 claims = **3.2** (re-queries on C08, C10) |
| ToT, per high-impact gap | ~8 calls, up to 11 with both expansions | **2 calls** (designer + critic): every gap stopped at the first level because the best option (0.75, 0.78, 0.96) passed the 0.7 stop threshold; no widening or deepening |
| One-call baseline, per gap | 1 | 1 |

### ToT against the one-call baseline

| Claim | ToT status | ToT calls / tokens | Baseline calls / tokens |
|---|---|---|---|
| C01 | recommended | 2 / 3,157 | 1 / 341 |
| C02 | recommended | 2 / 2,825 | 1 / 315 |
| C03 | recommended | 2 / 2,928 | 1 / 325 |

ToT costs about 2.5–2.8k extra tokens per gap. The evaluation does not decide which fix is better; `report.html` shows both side by side for a human reader. Whether ToT is worth its cost is **not yet shown**.

### Remaining disagreements with the labels

| Claim | Label | Claude | Note |
|---|---|---|---|
| C02 | gap, ASI02 | gap, ASI03 | Unlimited tool permission: ASI02 (tool misuse) and ASI03 (privilege abuse) are both defensible. |
| C09 | ok, ASI09 | gap, ASI09 | Right control, stricter verdict. Errs on the safe side (not false assurance). |

These are judgement calls, not code bugs. A second labeler is the right way to settle them.

## 4. Bugs the live run found (the stub never triggered them)

1. **Pillar mismatch.** The planner's schema allowed `payments-protocol`; the retrieval server accepts only `agent-security`, `interoperability`, `human-oversight`. Claude picked it for C03 and C09, retrieval returned `bad_pillar`, and both became `not_assessed`. **Fix:** the planner may only pick pillars that resolve to OWASP-ASI (`agent-security`, `human-oversight`); a test checks this against the server. A first fix that also allowed `interoperability` and steered payment claims to it dropped accuracy to **6/11** (five claims were sent to the protocol corpus, which has no ASI clause), and was reverted.
2. **Critic output truncated.** One output cap (600 tokens) for every role; the critic scores three options with rationale and was cut off on all three attempts, so ToT ended `unconfirmed`. **Fix:** per-role caps (critic 2,000, designer 1,200, hint 1,000); a reply that stops on `max_tokens` raises `Truncated`, is not retried (same cap, same cut), and its tokens are still charged.
3. **JSON inside prose.** One judge call failed three times although a valid object was in the reply. **Fix:** fall back to the outermost `{...}`; the result is still schema-validated.

Tests went from 67 to 71; four new tests pin these bugs.

## 5. What these results do not show

- Accuracy against an independent labeler (one author labelled everything).
- Run-to-run variance (one live run after the fixes).
- Injection resistance (the planned 10 planted-instruction cases are not built).
- Calibration (needs about 50 labelled claims).
- Whether ToT beats the one-call baseline.
