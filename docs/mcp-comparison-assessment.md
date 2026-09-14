# Official Semble MCP vs code-mode MCP: where each is better

Assessment as of 2026-09-14, from the Pi harness at the end of that day's changes (all methods described, 8s nested-call timeout, 60s execute budget, field-level validation errors, advisory judge). Actor and judge: Luna via Pi's openai-codex route. Numbers are from `evals/results/2026-09-14T19-33-39.080Z-3469` (five repetitions per cell) and `…T19-48-09.989Z-6605` (three repetitions, shared-saves). Cost figures are Pi's price-table estimates, not billing.

## The table

| Task | Grading | MCP | pass@1 | pass^3 | Median s | Median turns | $/cell |
|---|---|---|---:|---:|---:|---:|---:|
| shared-saves (6 libraries, ~1,200 cards) | API state | code-mode | 1.00 | 1.00 | 49 | 5 | 0.005 (one cell 0.19) |
| | | official | 0.00 | 0.00 | 49 | 3 | 0.34 |
| collection-audit | API state | code-mode | 1.00 | 1.00 | 30 | 6 | 0.005 |
| | | official | 1.00 | 1.00 | 10 | 2 | 0.003 |
| link-context | API state | code-mode | 1.00 | 1.00 | 33 | 5 | 0.005 |
| | | official | 1.00 | 1.00 | 13 | 2 | 0.004 |
| library-filing | coverage check; judge advisory | code-mode | 1.00 | 1.00 | 35 | 4 | 0.005 |
| | | official | 1.00 | 1.00 | 27 | 3 | 0.005 |
| reading-recommendation | verification check; judge advisory | code-mode | 1.00 | 1.00 | 46 | 6 | 0.006 |
| | | official | 0.80 | 0.40 | 28 | 4 | 0.007 |

Advisory judge quality (0-4, never affects verdicts): filing official 3.5 vs code-mode 2.8; recommendation official 3.3 vs code-mode 3.2. Blind pairwise preference on filing: official preferred 4 of 5 pairs. Recommendation pairs were inconclusive.

## Where code mode is better

**Anything that touches many records.** shared-saves needs fifteen pages across six libraries. Code mode paginates inside the sandbox and returns nineteen rows; official either stops after page one or pulls 2.6 MB of card JSON into the model and overflows its context window at 1.6 to 1.9 million input tokens. Three batches today, nine official cells, zero passes, at 60 to 80 times the cost per cell. This is architecture, not tuning: no tool description fixes a model that must read every card to count them.

**Correctness ceiling on checked tasks.** With the judge advisory and deterministic checks deciding, code mode passed every checked cell today (23 of 23 across the five tasks); official missed one recommendation cell on the "three verified unsaved links" check. Both are within noise on the small tasks, but code mode's floor on the aggregation task is what separates them.

**Cost stability on large data.** Code mode's cost per cell stays near half a cent unless the model chooses to return a whole dataset from execute (it did once today, $0.19). Official's cost is bounded by how much the tools return, which on large libraries is the whole library.

## Where the official MCP is better

**Latency on small tasks.** Two to three times faster on link-context, collection-audit, and filing (10 to 27 seconds versus 30 to 35). A named tool is one turn; code mode spends two or three turns on search and schema before the first execute. The gap is constant, not proportional to task size, so it matters most on the tasks users do most.

**Answer richness on judgment tasks.** On filing, the blind pairwise judge preferred official's plans 4 to 1 and scored them 3.5 versus 2.8. Official's tool results land verbatim in context, with titles, descriptions, and notes; code mode's model projects fields and tends to return less than it needs to explain itself. The execute guidance now says explanatory fields are evidence, but the effect is behavioral and only partly closed.

**Routing around a broken endpoint.** When Semble's account search started returning 500s, official's curated tool descriptions never led the model there, while code mode's catalog surfaced it first. That is fixed by descriptions now, but the general point stands: a curated tool set encodes route knowledge; a full SDK catalog does not, and every new upstream failure is a new routing hazard until described.

**Fewer ways to fail inside the loop.** Official's failure modes are context overflow and page-one laziness. Code mode adds sandbox errors: Monty's Python subset (no `__import__`, no generators), guessed field names, validation errors from guessed arguments. Today those were rare and recoverable, and every one is visible in the failures-by-method table, but they are a class official does not have.

## Not measured

Write tasks. collection-merge is blocked until Semble's app-password routing fix ships upstream, so nothing here says which server is safer or more reliable at mutating a library. Multi-model behaviour: everything above is Luna. Haiku, Sonnet, and Terra ran on 09-12 on retired tasks only.

## What would move each server

Code mode: cut the discovery turns. The catalog is small enough that a compact listing (name, one-line description, key params) could ship with the execute description or as a single browse call, so common tasks start at execute. That is the whole latency gap on small tasks. Second, keep pushing projected results to include the material an explanation needs.

Official: it needs server-side aggregation for anything over a page or two, or a way to hand the model a filtered view instead of raw cards. Without that, the aggregation gap is permanent, and users will hit it on any library over a hundred cards.
