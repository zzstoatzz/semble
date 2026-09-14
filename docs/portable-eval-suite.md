The suite now also includes [collection-merge](../evals/tasks/collection-merge.md), a live write task with deterministic API-state grading and no LLM judge. It requires an explicitly designated test account via `SEMBLE_EVAL_HANDLE`; use `just evals run reading-recommendation library-filing` for the read-only subset. Write cells serialize their full fixture lifecycle.

# Portable live eval suite

`just evals` runs two tasks, three times each, with Luna against both MCPs:
12 actor runs, bounded to two concurrent jobs. The old URL-summary and overlap
cases are retired from the runnable suite; historical results remain on disk.

```sh
just evals run --repetitions 1                 # four-cell smoke round
just evals run reading-recommendation --repetitions 5
just evals run library-filing --server code-mode
just evals run --model luna --model haiku
just evals --dry-run
```

## tasks

**reading-recommendation:** the user is assembling a half-hour list for a named
person and wants three unsaved
things to read, ranked for their interests, with a comparative reason for the
first choice. A pass requires discovery, novelty, a grounded understanding of the
user's library, prioritization and consideration of whether the material is still
useful. It does not require specific topics, resources or publication cutoffs.
Older foundational reading can be the best answer.

**library-filing:** the user wants a concrete filing plan covering every saved
item, reusing existing collections when appropriate. A pass requires complete
coverage, correct user scope, coherent groupings, practical reuse, and reasons
for the decisions. No fixed taxonomy or number of collections is prescribed.
Keeping a sensible existing arrangement can be valid; the agent must not invent
changes simply to appear helpful. The plan is read-only.

Input handles live in `evals/tasks/library.json`. Prompts are constructed only
from the task kind and handle, never from reference observations. Both currently
use zzstoatzz.io's public library. The authenticated MCP account can differ from the requested handle. Prompts
therefore ask about the named person explicitly, rather than saying “my library”
while evaluating another account. The checker and actor are given the same target.

## verification and quality

The checker enumerates all saved items and owned collections before and after
the actor. Changed relevant evidence makes a completed run inconclusive. API or
schema failures are not empty datasets. A preflight failure stops before actor
inference. Actor execution failures remain failures.

Reading answers must link at least three distinct eligible items. Each link is
looked up independently in Semble after the answer and compared with the target
library. The judge distinguishes recommendations from links supplied as supporting
context. It checks the explanation against saved material, candidate metadata
and up to 16,000 characters of text from each publicly reachable HTTPS source.
Source fetching has byte, timeout and redirect bounds, pins validated public DNS
addresses, and never forwards Semble credentials. Failed fetches remain missing
evidence. Source text is untrusted and may be truncated. Publication dates are
retained when available; unknown dates stay unknown. A suggested time allocation
is a plan, not a claim that reading duration was measured.

Filing answers must link every saved item. The judge checks destinations against
the actual existing shelves and assesses proposed new groupings. No write is
performed by the checker; the actor is instructed not to change anything.

The judge checks required results and consistency, then scores personalization,
decision value and evidence from 0 to 4:

- 0: absent or wrong
- 1: generic or unsupported
- 2: plausible but shallow
- 3: specific, grounded and actionable
- 4: unusually useful prioritization or organization with clear tradeoffs

A pass requires factual correctness and at least 3 in every dimension. Missing
quality scores or insufficient material evidence remain inconclusive. Scores are
recorded in `judge.json`, with reasons; they are not deterministic measurements
of human satisfaction.

When both answers in a repetition pass and the library references agree, two
additional judge calls compare them as A/B, without MCP names, costs or timing.
The second call reverses the order. A stable preference is reported only if the
two judgments agree after remapping; disagreement is `order-sensitive`, not a
forced winner. Ties and inconclusive judgments are retained. Failed or incomplete
answers do not enter this preference comparison.

## cost and interpretation

The actor and judge use Luna by default. Reducing the suite concentrates spending
on repetitions of more demanding user goals. There is one config, no separate
cost tier. Model and server subsets, repetition counts, and dry runs use the
normal command interface. Pairwise judging spends nothing on ineligible pairs.
Actor, absolute-judge and pairwise costs are stored separately as Pi estimates.
No failed sample is replaced silently. Each invocation writes `summary.json` and
`summary.md` with outcome counts, per-run quality scores and actor/judge/pairwise
costs, so repeated runs do not require manually reconstructing a result table.

An unsaved URL is not necessarily unseen by the person. Semble metadata alone does not prove external page availability or full article
contents. Source retrieval adds evidence but does not prove claims outside the
captured text, or guarantee future availability. Candidate
observations occur after selection, not in a historical transaction snapshot.
Redirect aliases beyond metadata's canonical URL may need more verification.
The same model family acts and judges in isolated sessions, so correlated errors
remain possible. Review traces and score explanations before claiming progress;
prefer human review of representative decisions over treating a 4 as objective.

[shared-saves](../evals/tasks/shared-saves.md) is a read-only aggregation task across six public libraries, graded deterministically from live API state with no judge. It is excluded from pairwise comparison like collection-merge.

See [the 2026 framework survey](eval-frameworks-2026.md) for where the pass^k, infra-separation, grading-version, and smoke/report tier conventions come from.

[link-context](../evals/tasks/link-context.md) and [collection-audit](../evals/tasks/collection-audit.md) are small read-only tasks graded from API state, added so the hardened set is not only aggregation-shaped. As of the same change the judge no longer decides pass/fail on reading-recommendation or library-filing: deterministic checks decide, and the judge's quality scores are reported as an advisory column.
