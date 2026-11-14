# Run DesignBench with a real Claude model

Use your own Anthropic API key and **synthetic data only**. Requires Python 3.10+ (macOS's system `python3` is 3.9 and fails).

```bash
make setup                                # .venv + dependencies + spaCy model
make test                                 # 71 tests, offline
make demo-stub                            # offline fallback, no key: out-stub/report.html
export ANTHROPIC_API_KEY=...              # never write it into a file in the repo
export DB_JUDGE_MODEL=claude-sonnet-5-5   # planner, hint, judge, option designer
export DB_CRITIC_MODEL=claude-opus-5-5    # design critic (larger model)
make demo-claude                          # out-claude/report.html + RESULTS.md + audit.jsonl
```

Without the key, `--llm claude` stops with a clear error (exit code 3) and makes no calls.

## Budget

Defaults: 100 calls and 200k tokens per run (`--max-calls`, `--max-tokens`). Measured on 2026-11-14: **44 calls, ~27k tokens** for the 11-claim Bank X design with `--compare`. Review used 35 calls (about 3 per claim, plus re-queries); Tree-of-Thought used 2 per high-impact gap (it can use up to 11 if it widens and deepens); `--compare` adds 1 per gap. If a cap is hit, the claim ends `not_assessed` or the gap `unconfirmed` (fail-closed).

## What to check after a run

1. `out-claude/audit.jsonl`: every call has `outcome: ok`. `attempts > 1` means a schema retry; a `Truncated` detail means a role's output cap (in `agent/gateway.py`, `OUT_TOKENS`) is too small.
2. `report.html`: the header shows real calls and tokens; every gap/ok finding has a quoted clause.
3. `RESULTS.md`: verdict match against the labels and the ToT-vs-baseline table. Report rows as they are, including "no change".
4. Labels are author-assigned. For a real accuracy claim, have a second person label the claims and run `.venv/bin/python -m eval.report_eval out-claude --labels2 theirs.json`.

The first live run found three bugs the stub never triggered (planner pillar names the server rejected, critic replies cut off at 600 output tokens, JSON wrapped in prose). All are fixed; see [`eval/RESULTS.md`](eval/RESULTS.md), section 4. Expect run-to-run variation: models are not deterministic, and only one post-fix run has been measured.
