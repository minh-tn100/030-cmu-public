# Results for run 20261114T233607 (claude)

Labels: author-assigned only; no independent second labeler, so these numbers are weak evidence.

- verdict match: 10/11
- ASI match on assessed: 9
- assessed: 10/11
- cited rate on gap/ok: 1.0
- calls: 44/100, tokens in/out: 12685/14387

## ToT vs no ToT (high-impact gaps)

| Claim | ToT status | ToT calls | ToT tokens | Baseline calls | Baseline tokens | Extra calls | Extra tokens |
|---|---|---|---|---|---|---|---|
| C01 | recommended | 2 | 3157 | 1 | 341 | 1 | 2816 |
| C02 | recommended | 2 | 2825 | 1 | 315 | 1 | 2510 |
| C03 | recommended | 2 | 2928 | 1 | 325 | 1 | 2603 |

### Side by side (read and judge; this file does not decide which is better)

**C01** (recommended, widened=False, deepened=False)
- ToT: Dual-context isolation with quarantined extractor: Process payee-supplied invoice text in a separate, tool-less model call that can only output a fixed-schema structured record (amount, payee, invoice number). The privileged chat agent receives only the validated fields, never the raw invoice text, so injected instructions never reach the context that selects tasks or tools.
- One-call baseline: Separate instructions from untrusted content: keep system and task instructions in a privileged channel, and pass invoice text and customer chat only as clearly delimited, labeled data. Process payee-supplied invoice text in a quarantined step with no tool access, such as one that extracts a fixed-schema set of fields. Validate that output against the schema before the privileged agent sees it. Never let the model treat the content as instructions, and require human approval for any payment or account changes triggered by it.

**C02** (recommended, widened=False, deepened=False)
- ToT: Policy decision point with per-call limit and payee checks: Put an externalized policy engine (for example OPA or an existing rules service) in front of initiate_payment. It evaluates amount, payee, velocity, and agent identity on every call against role-based limits, and denies by default. Agent-supplied parameters are never trusted as authorization.
- One-call baseline: Replace the blanket permission with a scoped, policy-enforced grant. Enforce per-call limits server-side in the payment service, not in the agent: a maximum amount per transaction and per day, an allowlist of approved payees, and human approval or step-up authorization for payments above a threshold or to new payees. Issue the agent short-lived credentials bound to these constraints, and log every call for audit.

**C03** (recommended, widened=False, deepened=False)
- ToT: Execution-time mandate re-validation (policy decision point check): Keep the token as proof of initial approval, but add a mandatory check at the payment execution gateway. It reads the live mandate limit and rejects or escalates any payment that exceeds it, whatever the token says. The check uses read-only queries against the existing mandate store.
- One-call baseline: Bind each approval token to the mandate's current version and re-validate at execution time. Whenever the customer lowers or revokes the mandate limit, increment the version so existing tokens are invalidated. Before settlement, check that the payment amount is within the live mandate limit and that the token's mandate version matches. Also shorten token lifetime to minutes and make tokens single-use and scoped to a specific amount and payee.

Gaps that ended 'unconfirmed' or 'escalate_to_human' are listed like the others; none is dropped.

