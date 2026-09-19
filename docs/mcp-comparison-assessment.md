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

## Write task, measured 2026-09-17

Semble shipped the app-password routing fix (cosmik-network/semble#930 via #936), and collection-merge ran end to end on the hosted API: four repetitions per server across two batches, 8 of 8 passes, zero cleanup errors, the account restored each time. Both servers produce the exact union and preserve originals. The difference is call volume: code mode merges in 4 or 5 MCP calls (one execute adds every card), official in 12 (one add-card call per card), at similar wall time (median 48 s vs 36 s). Neither server showed a write-safety problem at this scale; a larger merge would widen the call gap on the official side.

## Not measured

Multi-model behaviour: everything above is Luna. Haiku, Sonnet, and Terra ran on 09-12 on retired tasks only.

## What would move each server

Code mode: cut the discovery turns. The catalog is small enough that a compact listing (name, one-line description, key params) could ship with the execute description or as a single browse call, so common tasks start at execute. That is the whole latency gap on small tasks. Second, keep pushing projected results to include the material an explanation needs.

Official: it needs server-side aggregation for anything over a page or two, or a way to hand the model a filtered view instead of raw cards. Without that, the aggregation gap is permanent, and users will hit it on any library over a hundred cards.

## Addendum, 2026-09-15

**Grader correction.** The URL matcher used by shared-saves and collection-audit rejected a link followed by `)` or `,`, so markdown links failed. Three official collection-audit cells in the 20:44 batch were false fails; re-grading every stored cell with the corrected matcher changed no other verdict, so the official shared-saves omissions above are real.

**Nested schema experiment.** With FastMCP PR #5111 (get_schema lists field names one level inside typed returns), stacked on #4970, and `URLCard.card_content` typed, code mode dropped one execute per cell on collection-audit (2 to 1) and reading-recommendation (3 to 2) with pass rates unchanged; link-context and filing already used one execute. Measured with the pinned server running locally, so seconds are not comparable to the hosted numbers; turns and execute counts are. Cost of the change on this catalog: about 29 tokens per tool in a get_schema call, zero on 24 of 51 tools.

**A new code-mode weakness.** In two link-context cells the execute returned all ten saver handles in a compact list and the model dropped the same one while writing prose. The official server, with raw JSON in context, did not. Compact results reduce context but put more weight on faithful transcription; the official server's verbosity is a mild safeguard here.

## A third server: Jev-ranked search, 2026-09-19

`build_server(mode="jev")` exposes the same 51 SDK methods behind FastMCP's `search_tools` / `call_tool` pair, ranked by TypeSafe's Jev (vendored from PrefectHQ/fastmcp#5170). It is the official server's shape, one tool call per turn, with a learned ranker over our catalog instead of hand-curated tools. Three repetitions per task, Luna, local servers, results in `evals/results/2026-09-19T03-48-55.089Z-3023` and `…T04-03-40.507Z-7437` (merge):

| Task | Official | Code mode | Jev |
|---|---|---|---|
| shared-saves | 0/3 | 3/3 | 0/3 |
| collection-audit | 3/3 | 3/3 | 3/3 |
| link-context | 3/3 | 2/3 | 3/3 |
| link-connections | 1/3 | 3/3 | 3/3 |
| library-filing | 3/3 | 3/3 | 3/3 |
| reading-recommendation | 2/3 | 3/3 | 3/3 |
| collection-merge | 4/4 (earlier) | 4/4 (earlier) | 2/2 graded |

Median seconds on the small tasks: official 10 to 25, Jev 14 to 29, code mode 19 to 46. Jev matched or beat official on every read task and inherits official's aggregation failure, because it still returns raw pages into context. Its third merge cell never reached the model: a seed save timed out client-side after succeeding server-side, cleanup found the un-journaled card, and the account was restored by hand. Cleanup now reconciles against the before snapshot for exactly that case.

What this says about the two designs: the search quality gap between code mode's grep and a curated tool set is closable by a better ranker, and doing so recovers most of official's latency advantage. The aggregation gap is not about search at all; only executing code server-side closes it. The interesting server is therefore the one that has both, which is code mode with Jev ranking its discovery step, not a third mode.

## After the cutover: hosted jev, 2026-09-19

The hosted server now runs jev mode by default (`just mcp-mode code` reverts). Same seven tasks, three repetitions, official and jev hosted, code mode from a local server on the same commit. Results `evals/results/2026-09-19T06-27-16.748Z-43338` and `…T06-41-00.733Z-48199` (merge), cost $2.13, no rate-limit hits at concurrency two.

| Task | Official | Jev (hosted) | Code mode (local) |
|---|---|---|---|
| shared-saves | 0/3 | 0/3 | 3/3 |
| collection-merge | 3/3 | 2/3 | 3/3 |
| reading-recommendation | 3/3 | 3/3 | 2/3 |
| library-filing | 3/3 | 2/3 | 3/3 |
| link-context, collection-audit, link-connections | 3/3 each | 3/3 each | 3/3 each |

Shared-saves is the same mechanism on both one-call servers: jev asked for `limit: 1000`, the API silently capped each page at 100, the model treated page one as the whole library and listed 4 of 19 links over 800k input tokens; official paged correctly and overflowed the context window. Code mode returned 19 correct rows from 11.7k tokens. On merge, jev's one miss built a destination that was not the exact union; code mode's two execute errors (a Monty async misuse and an indentation slip) were both recovered within the run. Cleanup was clean on all nine merge cells and the account was restored.

Standing conclusion unchanged: jev fixes discovery and matches official's speed on small tasks; only code-mode-style execution survives aggregation. The API's silent limit clamp is worth reporting upstream, since an error or an echoed limit would have told the model to page.
