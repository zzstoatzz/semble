# Collection merge

A real write task graded entirely from Semble API state. No answer judge or pairwise preference judge runs.

```sh
SEMBLE_EVAL_HANDLE=bufo.uk just evals run collection-merge --model luna --repetitions 1
```

`SEMBLE_EVAL_HANDLE` must identify an explicitly designated test account and match the server credential's authenticated profile. The task creates public records; CLOSED means restricted contribution, not private visibility. Never point this at an unapproved account.

Each cell samples up to twelve existing saved cards and creates two fresh collections with overlap and unique cards on both sides. For a small test library, it temporarily saves enough real URLs from zzstoatzz.io's public library to reach eight cards. This seed user is replaceable; neither the actor prompt nor the correctness rule depends on those URLs. The API remains live throughout. Existing notes are never rewritten by setup.

The actor receives only the two collection IDs, a unique destination name, and this request:

> Combine these collections into a new collection. Keep both originals intact, reuse the existing cards, and preserve their notes. Leave everything else in my library unchanged. Give me a link to the result.

The checker fully enumerates collections and library records. A pass requires completed execution, one new destination with the exact union of source card IDs and URLs, unchanged original collections, unchanged saved card content and notes, and unchanged unrelated memberships. No score depends on prose, collection naming quality, or an LLM's interpretation. The final response's link is currently recorded but not graded.

Write cells serialize across setup, execution, verification and cleanup. Setup and cleanup use the direct API; the actor uses its assigned MCP. Each cell gets new source collections, so a previous actor cannot leave it a solved destination. The fixture cap bounds actor work; checker pagination has explicit limits and rejects incomplete reads. Runs without adequate evidence are inconclusive; execution limits are failures.

Artifacts include account-before/after, seed.json (temporary saved cards), fixture.json (source collection IDs), checker-before/after, API request timings/statuses, actor traces, evaluation.json and cleanup.json. Cleanup removes collection memberships before deleting only collections bearing this run's unique prefix, then removes only cards saved by setup and verifies the original library is restored. Cleanup errors remain visible; a task pass with failed cleanup becomes inconclusive. Unexpected actor-created collections outside the prefix are reported as failures and are not blindly deleted.

Limitations: post-state checks do not prove no transient edit occurred and do not cover connections or profile changes. Do not run other writers against this account during the experiment. Separate harness processes are not mutually locked. Process termination can interrupt cleanup; use the recorded fixture and seed IDs for recovery before another run. If source content changes independently during the actor run, inspect the evidence before attributing a preservation failure to the actor. The task tests union and preservation at small scale; it does not establish large-collection pagination performance or semantic merge quality.

## Status

As of 2026-09-14 this task has not completed an end-to-end run against either hosted MCP. Offline checker tests pass, but setup was blocked by hosted write authentication: api.semble.so logs bufo.uk in against its old, deactivated bsky.social account (see [the diagnosis](../../docs/semble-pds-auth-diagnosis.md)). Two preflights failed before any actor ran, so they say nothing about model performance: `results/2026-09-12T09-08-56.965Z-29703` (no publishing session) and `results/2026-09-12T09-27-07.911Z-35865` (account deactivated). Until the hosted backend carries the fix, do not run a full matrix. Once write preflight succeeds, run one Luna repetition per MCP, inspect setup, actor events, checks and cleanup, and fix harness bugs before reading scores.
