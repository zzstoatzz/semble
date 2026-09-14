# Agent eval frameworks and benchmarks, surveyed 2026-09-14

Question: what should the Semble MCP comparison borrow from, now that the harness has one deterministic task and two judge-heavy ones? Evidence is repository state read through the GitHub API on the date above, plus each project's own docs. Star counts and dates are as observed; nothing here was run.

## openai/evals is not a base

Not archived, 19.4k stars, 340 open issues, last push 2026-04-14. The last content commit was an IMO problems eval in July 2024; everything since is dependency pinning and removing a suite with defunct dependencies. Community PRs adding evals are closed unmerged, and the README's first line points at OpenAI's hosted dashboard evals. Its model is a YAML registry of static JSONL datasets scored by exact/fuzzy/includes matchers or a model-graded rubric. It has no notion of live state, fixtures, or tool calls beyond a "completion function" abstraction. Nothing to adopt.

## What is maintained

| Project | Last push | Stars | What it is |
|---|---|---|---|
| UKGovernmentBEIS/inspect_ai | 2026-09-14 | 2.8k | General eval framework: tasks, solvers, scorers, sandboxes, eval sets with retry/resume, log viewer. First-class MCP tools over stdio, HTTP, or an in-sandbox process. |
| eval-sys/mcpmark | 2026-06-12 | 460 | MCP benchmark over Notion, GitHub, Filesystem, Postgres, Playwright. 127 standard tasks plus 10 "easy" per service. Each task is a description, `meta.json`, and a `verify.py` run against the service's final state. Isolated environments per run. Reports pass@1, pass@k, pass^k, avg@k. "Verified" set pins environment versions and stabilizes verifiers; older results declared non-comparable. |
| sierra-research/tau2-bench | 2026-09-11 | 2.0k | Customer-service agent benchmark with a user simulator. Reward is the product of a DB end-state hash match and required communicated strings. A reference trajectory exists only to derive the target state; agents are not graded on the path taken. Metric is pass^k = C(successes, k) / C(trials, k). Infrastructure errors are counted separately from model failures. |
| SalesforceAIResearch/MCP-Universe | 2026-06-23 | 600 | MCP agent benchmark and framework. Tasks are JSON with an `output_format` and a list of evaluators of the form `func -> op -> value`, where `func` can call live service functions so ground truth is computed at grade time. Can run MCPMark tasks. |
| promptfoo/promptfoo | 2026-09-14 | 25k | Prompt and agent testing with an MCP provider that treats the server as the system under test. Its MCP material is oriented to red-teaming and robustness, not capability comparison. |
| langchain-ai/agentevals | 2026-07-14 | 722 | Trajectory evaluators: strict, unordered, subset, superset match on tool calls, plus an LLM judge over trajectories. |

## Design principles worth adopting

1. **Score outcomes, not trajectories.** tau2-bench's docs argue this explicitly and keep trajectory matching off by default because it penalizes correct-but-different solutions. agentevals is built around the opposite and is the wrong fit for comparing two servers whose whole point is taking different paths. Our merge and shared-saves checkers already grade state and answer content; keep it that way.
2. **Separate infrastructure failure from model failure.** tau2 counts `infra_error_count` apart from reward; MCPMark auto-retries a known list of retryable error patterns and resumes unfinished tasks. Our preflight-failure convention matches this; the summary should report the split explicitly.
3. **Reliability metrics, not just accuracy.** pass^k (all k runs succeed) is the standard for "can you trust this in production"; avg@k is mean over runs. Ten repetitions per cell already exist here, so pass^k at k=3 and k=5 costs nothing extra to report.
4. **Version the verifier and pin the environment.** MCPMark's "Verified" set and tau2's v1.0.1 grading note both say results across grader versions are not comparable. Our `gradingVersion` field exists; results directories should carry it and the summary should refuse to merge cells with different versions.
5. **Isolated fixtures per run.** MCPMark creates and destroys an environment per task run; tau2 replays actions onto a fresh DB. The designated write account with run-prefixed fixtures is the closest we can get on a hosted API; formalize cleanup verification as a grading input, which the merge task already does.
6. **Tiered task sets.** MCPMark keeps an "easy" set of 10 per service for smoke and CI and a standard set for reporting. We should have a cheap smoke tier and a reporting tier, and never tune on the reporting tier.
7. **Live ground truth computed at grade time.** MCP-Universe's evaluator functions and our before/after checkers are the same idea. Keep it, and keep the drift check that turns changed state into "inconclusive".

## Should we move off the Pi harness?

Inspect AI is the one general framework here that is maintained, has MCP as a first-class tool source, and gives multi-model matrices, epochs with reducers, eval-set retry/resume, and a log viewer for free. The cost is a Python rewrite of a working TypeScript harness and losing Pi's agent loop as the actor. Given the earlier decision to use Pi, the pragmatic path is to keep the harness and adopt the principles above: pass^k and infra-error reporting in the summary, grading-version guards, a smoke tier, and more state-graded tasks. Revisit Inspect if the suite outgrows one machine or needs sandboxed local MCP servers.

## Task shapes to add, adapted from MCPMark categories

MCPMark's task categories per service are practical workflows: organize, classify, deduplicate, cross-reference, audit, and multi-step edits, each with a verifier over final state. Semble equivalents that grade from API state:

- organize: the existing collection-merge write task once upstream auth lands; a "split one collection into two by topic" variant with membership checks.
- deduplicate: exact-duplicate connections or cards, on an account seeded with known duplicates rather than relying on Phi's live state.
- cross-reference: shared-saves, and "which of user A's saves have connections from user B".
- audit: "which saved links no longer resolve" would need fetches; "which collections are empty or single-item" is pure API state.

Each should specify the verifier before the prompt, record `gradingVersion`, and be run on the smoke tier once before joining the reporting tier.
