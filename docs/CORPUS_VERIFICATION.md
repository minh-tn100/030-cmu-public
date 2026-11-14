# Corpus verification log (2026-11-08)

Checked each chunk against its original source. Chunk text is a paraphrase, not a verbatim copy.

| Chunk | Source and version | Result |
|---|---|---|
| ASI01-ASI10 | OWASP Top 10 for Agentic Applications 2026, Version 2026, Dec 2025, CC BY-SA 4.0; printed pages 9-38 (PDF viewer page = printed + 1) | Metadata, license and page ranges match; key scenarios and mitigations found in each section. Titles aligned (ASI05 "(RCE)", ASI06 "&") |
| AP2.a | AP2 spec v0.2, ap2-protocol.org | **Corrected.** Old text used "intent/cart mandate"; v0.2 uses Checkout Mandate (open/closed) and Payment Mandate, built as verifiable digital credentials |
| AP2.b | AP2 spec v0.2 | Supported: non-repudiable audit trail, dispute evidence, accountability. Reworded to the spec's terms |
| ACP.a | ACP repo github.com/agentic-commerce-protocol/agentic-commerce-protocol, commit 7fdd78d (2026-07-17), spec 2026-04-17, Apache 2.0, maintained by OpenAI and Stripe (README; Stripe docs also name Meta) | **Corrected, then confirmed from the cloned repo.** "Limited-use" is supported: the Allowance schema has reason one_time, max_amount, currency, checkout_session_id, merchant_id, expires_at. Dropped my claim that the agent never sees raw card data: the spec does not state that. Merchant of record confirmed in the README |
| MCP.a | MCP spec 2025-11-25 (index, server/tools) | Reworded: tools/list, tools/call, inputSchema; hosts must obtain explicit consent; annotations untrusted unless from trusted server; server MUST validate inputs, rate limit, sanitise |
| A2A.a | A2A spec v1.0.0, a2a-protocol.org | **Corrected.** Old text said auth is "left to the deployment"; spec declares security schemes in the Agent Card, requires HTTPS in production, and MUST scope authorisation per client |

Limits: read from the spec pages and the A2A quick reference; A2A section 13.1 (security) was not reached because the page was truncated. Web specs have no page numbers, so `page` holds section names. MCP and A2A change versions; re-check before reuse.

Effect: all 15 chunks verified. Stub review output unchanged (7 gap, 3 ok, 1 not assessed). Retrieval on the new corpus: hybrid top-4 still 22/23; dense top-4 18 -> 17; hybrid top-1 16 -> 18; out-of-scope gate stopped 4 -> 3 of 5 (generic words "rate", "key" now appear in chunk text). The 3.1 numbers stay reproducible from data/corpus_v31.json.
