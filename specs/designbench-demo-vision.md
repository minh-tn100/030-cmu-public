# Vision Brief: DesignBench Demo (CMU Final Presentation)

**Date:** 2026-11-05
**Author:** Minh Tran Nhat
**Status:** Approved (2026-11-05)

## The Problem

Agent-payment designs (AP2/ACP/MCP/A2A) are reviewed by senior people reading documents against OWASP ASI01-ASI10. The review is slow, depends on who is in the room, and leaves no evidence trail. Gaps surface late, after design choices are locked. The CIO becomes the human quality gate.

## Who Feels It

Architects who write designs, and the CIO/Architecture Board who must approve them before they scale.

## Current State

Manual reading of the design against standards. Findings live in comments and heads. No measurement of whether the review itself was right. Checkpoints 1.1-4.1 designed a research agent for this, and phases 0-2 built a review loop with a stub model: 11/11 verdicts, 10 assessed (stub plus self-labelled data, so not proof of quality).

## Strategic Context

The CMU final presentation (Activity 7.1) needs a working, honest demonstration of the 4.1 design, not slides alone. The same pattern (control by design, not by people) applies to architecture review in any regulated bank.

## The Vision

An architect submits a design and gets back, within minutes, a cited review: each claim marked gap / ok / not assessed, every verdict tied to a clause, every high-impact gap with three compared fix options and a recommended one. The agent never guesses: with no evidence it says "not assessed". A human decides.

## Key Capabilities

1. **Must have:** Run a review from one command against a design file and a standards corpus, using a real Claude model.
2. **Must have:** Every verdict cites a verified clause; unsupported claims become "not assessed" (fail-closed).
3. **Must have:** For high-impact gaps, generate 3 options, score them on the weighted rubric, prune, and recommend one, within a hard call/token budget.
4. **Must have:** A readable HTML/JSON report with findings, option trees and citations, plus an audit log.
5. **Must have:** Evaluation harness that compares findings with labels and reports cost and calls per run.
6. **Nice to have:** Second-labeler import, LangSmith tracing, sentence-embedding retrieval, ASI03 attack replay.

## Inspiration

Tree-of-Thought (Yao) and the Long controller pattern; code review bots that must cite a line.

## What Success Looks Like

- **Early signal (1-2 weeks):** Live run on Bank X completes within budget; every finding has a citation; the demo runs offline with a stub if the network fails.
- **Real outcome (1-3 months):** Measured, not claimed: ToT vs no-ToT comparison on the high-impact gaps with actual call counts and cost, shown in the presentation, including where it did not help.

## Risks & Assumptions

- **Key assumption:** A real model does not break the fail-closed rules, because the rules live in code.
- **Biggest risk:** Circular evaluation (same author writes design, labels and agent), so results are weaker evidence than they look. The adapter is untested against the live API until you run it.

## Constraints & Context

Synthetic Bank X data and public sources only. Python, LangGraph (kept), no LangChain, Anthropic SDK direct, MCP read-only retrieval. You run it locally with your own API key. Demo timeline: before the final presentation.

## Open Questions

- Which Claude models for judge vs critic (cost vs quality)?
- Per-run call/token budget cap for the live demo?
- Present the stub-vs-real comparison as a headline or as an appendix?

## Feature Breakdown

### Epic 1: Real-LLM review core
- [ ] 1a: LLM Gateway + Claude adapter (retries, timeout, JSON-schema check, budget)
- [ ] 1b: Judge/Planner on Claude with the existing hard rules unchanged

### Epic 2: Selective ToT
- [ ] 2a: Option Designer and Design Critic roles, rubric scoring, prune/stop
- [ ] 2b: Branch store (SQLite) with MCP branch_add/get/prune

### Epic 3: Report and evidence
- [ ] 3a: CLI plus HTML/JSON report and audit log
- [ ] 3b: Evaluation harness: findings vs labels, cost per run, ToT vs baseline

### Sequencing (riskiest first)
Epic 1 (proves real-LLM safety) -> Epic 2 (the 4.1 claim) -> Epic 3 (shows it).
